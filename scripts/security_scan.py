#!/usr/bin/env python3
"""Public-repository sensitive content scanner.

The scanner is intentionally read-only: it reports likely leaks but never edits or
removes files. It is tuned for this repository's public-safe examples and docs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

SCAN_VERSION = 1
SEVERITIES = ("BLOCKER", "HIGH", "MEDIUM", "INFO")
HIGH_RISK = {"BLOCKER", "HIGH"}

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "tmp",
    "cache",
}
SKIP_PREFIXES = {"output/cards"}
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".sqlite",
    ".db",
    ".pyc",
}
TEXT_EXTENSIONS = {
    "",
    ".env",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".py",
    ".txt",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".ps1",
}

DISCORD_WEBHOOK_RE = re.compile(r"https://(?:discord(?:app)?\.com)/api/webhooks/[A-Za-z0-9_./?=&%:-]+")
GITHUB_TOKEN_RE = re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}")
OPENAI_KEY_RE = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}")
ENV_SECRET_RE = re.compile(r"\b(?:OPENAI_API_KEY|DEEPSEEK_API_KEY|ZHIPU_API_KEY|API_KEY)\s*=\s*([^\s#'\"]{12,})")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ID_CARD_RE = re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)")

SENSITIVE_FIELDS = {
    "amount",
    "asset",
    "assets",
    "balance",
    "cost",
    "cost_price",
    "holding_amount",
    "position_amount",
    "profit",
    "real_amount",
    "account_value",
    "账户资产",
    "成本价",
    "持仓金额",
    "收益金额",
}
FIELD_VALUE_RE = re.compile(
    r"(?P<key>\b(?:amount|asset|assets|balance|cost|cost_price|holding_amount|position_amount|profit|real_amount|account_value)\b|账户资产|成本价|持仓金额|收益金额)"
    r"\s*[:=]\s*(?P<value>[0-9][0-9_,]*(?:\.[0-9]+)?)",
    re.IGNORECASE,
)

EXAMPLE_MARKERS = ("example", "demo", "sample", "示例", "public")
DOC_EXTENSIONS = {".md", ".txt"}


@dataclass(frozen=True)
class Finding:
    severity: str
    rule_id: str
    path: str
    line: int
    message: str
    masked_value: str
    recommendation: str


def _posix(path: Path) -> str:
    return path.as_posix()


def is_example_path(rel_path: str) -> bool:
    lowered = rel_path.lower()
    return any(marker in lowered for marker in EXAMPLE_MARKERS) or "/examples/" in lowered


def is_documentation_path(rel_path: str) -> bool:
    return Path(rel_path).suffix.lower() in DOC_EXTENSIONS or rel_path.startswith("docs/")


def mask_value(value: str, *, keep_start: int = 6, keep_end: int = 3) -> str:
    value = value.strip()
    if len(value) <= keep_start + keep_end + 3:
        return "***"
    return f"{value[:keep_start]}***{value[-keep_end:]}"


def mask_url(value: str) -> str:
    match = re.match(r"(https://[^/]+/api/webhooks/)", value)
    if match:
        return match.group(1) + "***"
    return mask_value(value)


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    placeholders = (
        "demo",
        "example",
        "sample",
        "placeholder",
        "secret_name",
        "_secret",
        "your_",
        "xxx",
        "000000",
        "test",
        "fake",
        "mock",
        "dummy",
        "stale",
        "legacy",
        "runtime",
        "secret",
        "示例",
    )
    return any(token in lowered for token in placeholders)


def should_skip(path: Path, root: Path) -> bool:
    rel = _posix(path.relative_to(root))
    if any(rel == prefix or rel.startswith(prefix + "/") for prefix in SKIP_PREFIXES):
        return True
    if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
        return True
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    return False


def iter_candidate_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            path = current / filename
            if should_skip(path, root):
                continue
            suffix = path.suffix.lower()
            if suffix in TEXT_EXTENSIONS or filename.startswith(".env") or filename in {"README.md"}:
                yield path


def _finding(severity: str, rule_id: str, rel_path: str, line_no: int, message: str, masked_value: str, recommendation: str) -> Finding:
    return Finding(severity, rule_id, rel_path, line_no, message, masked_value, recommendation)


def scan_line(rel_path: str, line_no: int, line: str) -> list[Finding]:
    findings: list[Finding] = []
    test_fixture = rel_path.startswith("tests/") or "/tests/" in rel_path
    line_placeholder = is_placeholder(line)
    doc_or_example = is_documentation_path(rel_path) or is_example_path(rel_path) or test_fixture or line_placeholder

    for match in DISCORD_WEBHOOK_RE.finditer(line):
        value = match.group(0)
        severity = "INFO" if doc_or_example else "BLOCKER"
        findings.append(_finding(severity, "discord_webhook_url", rel_path, line_no, "疑似 Discord Webhook URL", mask_url(value), "删除真实 webhook，改用 GitHub Secrets。"))

    for match in GITHUB_TOKEN_RE.finditer(line):
        value = match.group(0)
        severity = "INFO" if is_placeholder(value) or doc_or_example else "BLOCKER"
        findings.append(_finding(severity, "github_token", rel_path, line_no, "疑似 GitHub Token", mask_value(value), "撤销并重新签发 token，仓库仅保留 Secret 名称。"))

    for match in OPENAI_KEY_RE.finditer(line):
        value = match.group(0)
        severity = "INFO" if is_placeholder(value) or doc_or_example else "HIGH"
        findings.append(_finding(severity, "api_key", rel_path, line_no, "疑似 API Key", mask_value(value), "删除真实 API Key，改用 GitHub Secrets 或本地环境变量。"))

    env_match = ENV_SECRET_RE.search(line)
    if env_match:
        value = env_match.group(1).strip().strip("'\"")
        if not is_placeholder(value) and not doc_or_example:
            findings.append(_finding("HIGH", "env_api_key", rel_path, line_no, "疑似环境变量密钥真实值", mask_value(value), "不要提交真实 env 密钥，保留 Secret 名称或占位符。"))
        else:
            findings.append(_finding("INFO", "env_api_key_placeholder", rel_path, line_no, "环境变量密钥占位符", mask_value(value), "确认仅为占位符。"))

    if not doc_or_example and Path(rel_path).suffix.lower() in {".json", ".yaml", ".yml", ".env"}:
        for match in FIELD_VALUE_RE.finditer(line):
            findings.append(_finding("MEDIUM", "sensitive_financial_field", rel_path, line_no, "疑似金额/成本价/账户资产字段带数值", mask_value(match.group("value")), "公开仓库不要保存真实金额、成本价或账户资产。"))

    for match in EMAIL_RE.finditer(line):
        value = match.group(0)
        if value == "41898282+github-actions[bot]@users.noreply.github.com" or is_placeholder(value) or doc_or_example:
            continue
        findings.append(_finding("MEDIUM", "email", rel_path, line_no, "疑似私人邮箱", mask_value(value), "确认是否为真实私人邮箱，必要时移至私有配置。"))

    if not doc_or_example and Path(rel_path).suffix.lower() in {".json", ".yaml", ".yml", ".env"}:
        for regex, rule_id, message in ((PHONE_RE, "china_phone", "疑似中国手机号"), (ID_CARD_RE, "china_id_card", "疑似身份证号")):
            for match in regex.finditer(line):
                findings.append(_finding("HIGH", rule_id, rel_path, line_no, message, mask_value(match.group(0)), "不要在公开仓库保存个人身份信息。"))

    return findings


def scan_path_risk(rel_path: str) -> list[Finding]:
    lowered = rel_path.lower()
    if is_example_path(rel_path):
        return []
    high_patterns = (
        r"^data/user_config/.+\.json$",
        r"^local_config/.+\.json$",
        r"^private_config/.+\.json$",
        r"\.local\.json$",
        r"\.secret\.json$",
    )
    if any(re.search(pattern, lowered) for pattern in high_patterns):
        return [_finding("HIGH", "private_config_path", rel_path, 1, "疑似真实用户或私有配置文件路径", rel_path, "不要提交真实用户配置、local/private/secret 配置。")]
    if Path(rel_path).name in {".env", ".env.local", ".env.production"}:
        return [_finding("HIGH", "env_file_path", rel_path, 1, "疑似 .env 文件被提交", rel_path, "不要提交 .env 文件，仅提交 .env.example。")]
    return []


def scan_file(path: Path, root: Path) -> list[Finding]:
    rel_path = _posix(path.relative_to(root))
    findings = scan_path_risk(rel_path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return findings
    except OSError:
        return findings
    for line_no, line in enumerate(text.splitlines(), start=1):
        findings.extend(scan_line(rel_path, line_no, line))
    return findings


def scan_repository(root: str | Path = ".") -> dict:
    root_path = Path(root).resolve()
    findings: list[Finding] = []
    checked_files = 0
    for path in iter_candidate_files(root_path):
        checked_files += 1
        findings.extend(scan_file(path, root_path))
    summary = {severity.lower(): 0 for severity in SEVERITIES}
    for item in findings:
        summary[item.severity.lower()] += 1
    status = "failed" if summary["blocker"] or summary["high"] else ("warning" if summary["medium"] else "pass")
    return {
        "scan_version": SCAN_VERSION,
        "status": status,
        "checked_files": checked_files,
        "findings": [asdict(item) for item in findings],
        "summary": summary,
    }


def print_summary(result: dict) -> None:
    summary = result["summary"]
    print(f"Security scan status: {result['status']}")
    print(f"Checked files: {result['checked_files']}")
    print("Findings: " + ", ".join(f"{key}={summary[key]}" for key in ("blocker", "high", "medium", "info")))
    for finding in result["findings"][:20]:
        print(f"- {finding['severity']} {finding['rule_id']} {finding['path']}:{finding['line']} {finding['message']} ({finding['masked_value']})")
    if len(result["findings"]) > 20:
        print(f"... {len(result['findings']) - 20} more findings omitted; use --json for full structured output.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan repository for public-repo sensitive content risks.")
    parser.add_argument("--root", default=".", help="Repository root to scan (default: current directory).")
    parser.add_argument("--json", action="store_true", help="Print structured JSON result.")
    parser.add_argument("--fail-on-high", action="store_true", help="Exit non-zero when BLOCKER/HIGH findings exist (default behavior).")
    args = parser.parse_args(argv)

    result = scan_repository(args.root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result)
    return 1 if result["summary"]["blocker"] or result["summary"]["high"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
