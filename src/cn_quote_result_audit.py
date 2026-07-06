"""Audit helpers for local CN A-share / ETF quote provider results.

The audit layer is intentionally offline-only and persistence-free. It accepts
in-memory QuoteResult-like mappings, redacts market values and secrets for
reporting, and marks real-provider results as unsafe to commit.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

QUOTE_VALUE_FIELDS = ("last_price", "change_pct", "change_amount", "volume", "turnover", "open", "high", "low", "previous_close")
SECRET_FIELDS = ("token", "api_key", "apikey", "secret", "password", "webhook", "cookie", "authorization", "bearer", "client_secret", "private_key")
AUDIT_STATUSES = {"passed", "passed_with_warnings", "failed", "blocked"}
SEVERITIES = {"info": 0, "low": 1, "medium": 2, "high": 3, "blocker": 4}
WARNING_REAL_LOCAL_ONLY = "真实行情值仅允许本地内存使用，不得提交到 public 仓库。"
REDACTED = "<redacted>"


def build_cn_quote_audit_policy() -> dict[str, Any]:
    return {
        "policy_name": "cn_quote_result_audit_policy",
        "market": "CN",
        "data_kinds": ["realtime_quote", "index_quote"],
        "allow_real_values_in_memory": True,
        "allow_real_values_in_repo": False,
        "allow_commit_to_repo_required": False,
        "required_source_fields": ["provider", "source_status", "checked_at"],
        "required_provider_checks": ["allow_commit_to_repo", "cache_scope"],
        "allowed_cache_scopes": ["local_only"],
        "max_age_seconds": 120,
        "redact_real_quote_values": True,
        "forbidden_secret_fields": list(SECRET_FIELDS),
    }


def validate_cn_quote_audit_policy(policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if policy.get("allow_real_values_in_repo") is not False:
        errors.append("allow_real_values_in_repo must be false")
    if policy.get("redact_real_quote_values") is not True:
        errors.append("redact_real_quote_values must be true")
    if "local_only" not in set(policy.get("allowed_cache_scopes") or []):
        errors.append("allowed_cache_scopes must include local_only")
    if int(policy.get("max_age_seconds") or 0) <= 0:
        errors.append("max_age_seconds must be positive")
    return errors


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _source(result: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(result.get("source"))


def _checks(result: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(result.get("provider_checks"))


def _provider(result: Mapping[str, Any]) -> str:
    return str(result.get("provider") or result.get("provider_name") or _source(result).get("provider") or "")


def normalize_audit_severity(severity: str) -> str:
    return severity if severity in SEVERITIES else "info"


def build_audit_warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _secret_key(key: Any, forbidden: Sequence[str] = SECRET_FIELDS) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(secret in normalized for secret in forbidden)


def scan_quote_result_for_sensitive_fields(result: Any) -> list[str]:
    found: set[str] = set()

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                key_text = str(key)
                next_path = f"{path}.{key_text}" if path else key_text
                if _secret_key(key_text):
                    found.add(next_path)
                walk(nested, next_path)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                walk(nested, f"{path}[{index}]")

    walk(result)
    return sorted(found)


def redact_quote_result_for_audit(result: Any) -> Any:
    cloned = copy.deepcopy(result)

    def redact(value: Any, parent_key: str = "") -> Any:
        if isinstance(value, Mapping):
            output: dict[str, Any] = {}
            for key, nested in value.items():
                key_text = str(key)
                if _secret_key(key_text):
                    output[key_text] = REDACTED
                elif parent_key == "quote" and key_text in QUOTE_VALUE_FIELDS and nested is not None:
                    output[key_text] = REDACTED
                else:
                    output[key_text] = redact(nested, key_text)
            return output
        if isinstance(value, list):
            return [redact(item, parent_key) for item in value]
        return value

    return redact(cloned)


def is_real_quote_value_present(result: Mapping[str, Any]) -> bool:
    quote = _as_mapping(result.get("quote"))
    return any(field in quote and quote.get(field) is not None for field in QUOTE_VALUE_FIELDS)


def check_quote_source_metadata(result: Mapping[str, Any]) -> dict[str, Any]:
    source = _source(result)
    missing = [field for field in ("provider", "source_status", "checked_at") if not (result.get(field) or source.get(field))]
    return {"ok": not missing, "missing_fields": missing, "issues": [f"missing_source_{field}" for field in missing]}


def _parse_checked_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        text = str(value).strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def check_quote_result_freshness(result: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    active_policy = dict(build_cn_quote_audit_policy(), **dict(policy or {}))
    checked_at = result.get("checked_at") or _source(result).get("checked_at")
    if not checked_at:
        return {"freshness_status": "missing_checked_at", "checked_at": checked_at, "age_seconds": None}
    parsed = _parse_checked_at(checked_at)
    if parsed is None:
        return {"freshness_status": "unknown", "checked_at": checked_at, "age_seconds": None}
    age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    return {"freshness_status": "stale" if age > int(active_policy["max_age_seconds"]) else "fresh", "checked_at": checked_at, "age_seconds": max(0, int(age))}


def is_result_commit_safe(result: Mapping[str, Any]) -> bool:
    if result.get("has_real_market_data") is True or result.get("data_mode") == "real_provider":
        return False
    if result.get("allow_commit_to_repo") is False or _checks(result).get("allow_commit_to_repo") is False:
        mode = result.get("data_mode")
        return mode in {"fixture_only", "model_only", "dry_run", "local_only_fixture"}
    return True


def check_quote_result_repository_safety(result: Mapping[str, Any]) -> dict[str, Any]:
    checks = _checks(result)
    cache_scope = checks.get("cache_scope", result.get("cache_scope"))
    allow_commit = checks.get("allow_commit_to_repo", result.get("allow_commit_to_repo"))
    has_real = result.get("has_real_market_data") is True or result.get("data_mode") == "real_provider"
    issues: list[str] = []
    warnings: list[str] = []
    blocked = False
    if has_real and allow_commit is True:
        issues.append("real_provider_result_must_not_be_committed")
        blocked = True
    if cache_scope and cache_scope != "local_only" and has_real:
        warnings.append("real_provider_cache_scope_must_be_local_only")
    return {"commit_safe": False if has_real else is_result_commit_safe(result), "allow_commit_to_repo": allow_commit, "cache_scope": cache_scope, "issues": issues, "warnings": warnings, "blocked": blocked}


def check_quote_result_data_status(result: Mapping[str, Any]) -> dict[str, Any]:
    status = str(result.get("data_status") or "")
    ok_statuses = {"real_provider_available", "disabled_by_default", "provider_policy_blocked", "unsupported", "invalid_request", "provider_error", "provider_timeout", "invalid_response", "stale_data", "conflict", "fixture_only", "model_only", "available"}
    return {"ok": status in ok_statuses, "data_status": status, "issues": [] if status in ok_statuses else ["unknown_data_status"]}


def audit_cn_quote_result(result: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    active_policy = dict(build_cn_quote_audit_policy(), **dict(policy or {}))
    issues: list[str] = []
    warnings: list[str] = []
    secrets = scan_quote_result_for_sensitive_fields(result)
    source_meta = check_quote_source_metadata(result)
    freshness = check_quote_result_freshness(result, active_policy)
    repo = check_quote_result_repository_safety(result)
    data_status = check_quote_result_data_status(result)
    issues.extend(source_meta["issues"])
    issues.extend(repo["issues"])
    issues.extend(data_status["issues"])
    warnings.extend(repo["warnings"])
    if result.get("has_real_market_data") is True or result.get("data_mode") == "real_provider" or is_real_quote_value_present(result):
        warnings.append(WARNING_REAL_LOCAL_ONLY)
    if freshness["freshness_status"] == "missing_checked_at":
        issues.append("missing_checked_at")
    elif freshness["freshness_status"] in {"stale", "unknown"}:
        warnings.append(f"freshness_status={freshness['freshness_status']}")
    if secrets:
        issues.extend([f"sensitive_field_detected:{field}" for field in secrets])

    blocked = bool(secrets) or repo["blocked"]
    if blocked:
        audit_status, severity = "blocked", "blocker"
    elif issues:
        audit_status, severity = "failed", "high"
    elif warnings:
        audit_status, severity = "passed_with_warnings", "low"
    else:
        audit_status, severity = "passed", "info"

    display_safe = not blocked and freshness["freshness_status"] != "stale"
    return {
        "asset_id": result.get("asset_id"),
        "code": result.get("code"),
        "type": result.get("type"),
        "market": result.get("market"),
        "provider": _provider(result),
        "audit_status": audit_status,
        "severity": severity,
        "has_real_market_data": result.get("has_real_market_data") is True,
        "contains_real_quote_values": is_real_quote_value_present(result),
        "real_values_redacted": active_policy.get("redact_real_quote_values") is True,
        "commit_safe": repo["commit_safe"],
        "display_safe": display_safe,
        "source_metadata_ok": source_meta["ok"],
        "freshness_status": freshness["freshness_status"],
        "cache_scope": repo["cache_scope"],
        "allow_commit_to_repo": repo["allow_commit_to_repo"],
        "contains_secret": bool(secrets),
        "sensitive_fields": secrets,
        "issues": issues,
        "warnings": warnings,
        "redacted_result": redact_quote_result_for_audit(result),
    }


def audit_cn_quote_results(results: Sequence[Mapping[str, Any]], policy: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    return [audit_cn_quote_result(result, policy) for result in results]


def build_cn_quote_audit_summary(audit_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for audit in audit_results:
        status = str(audit.get("audit_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {"summary_type": "cn_quote_audit_summary", "total": len(audit_results), "status_counts": counts, "blocked": counts.get("blocked", 0), "passed": counts.get("passed", 0), "results": list(audit_results), "redacted": True}


def validate_cn_quote_audit_result(audit: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if audit.get("audit_status") not in AUDIT_STATUSES:
        errors.append("unsupported audit_status")
    if audit.get("severity") not in SEVERITIES:
        errors.append("unsupported severity")
    rendered = repr(audit.get("redacted_result"))
    if any(field in rendered and audit.get("contains_secret") for field in audit.get("sensitive_fields", [])):
        errors.append("redacted_result may expose sensitive field path")
    return errors


def render_cn_quote_audit_markdown(audit_or_summary: Mapping[str, Any]) -> str:
    audit = audit_or_summary
    if audit_or_summary.get("summary_type") == "cn_quote_audit_summary":
        audit = (audit_or_summary.get("results") or [{}])[0]
    lines = [
        "# A股 / ETF Provider 结果审计 Demo",
        "",
        "## 1. 审计概览",
        f"- audit_status：{audit.get('audit_status', '')}",
        f"- severity：{audit.get('severity', '')}",
        f"- provider：{audit.get('provider', '')}",
        f"- market：{audit.get('market', '')}",
        f"- 是否含真实行情：{str(audit.get('has_real_market_data', False)).lower()}",
        f"- 是否可提交仓库：{str(audit.get('commit_safe', False)).lower()}",
        f"- 是否可本地展示：{str(audit.get('display_safe', False)).lower()}",
        "",
        "## 2. 来源检查",
        f"- provider：{audit.get('provider', '')}",
        f"- source_status：{audit.get('redacted_result', {}).get('source', {}).get('source_status', '') if isinstance(audit.get('redacted_result'), Mapping) else ''}",
        f"- checked_at：{audit.get('redacted_result', {}).get('source', {}).get('checked_at', '') if isinstance(audit.get('redacted_result'), Mapping) else ''}",
        f"- freshness_status：{audit.get('freshness_status', '')}",
        "",
        "## 3. 安全检查",
        f"- allow_commit_to_repo：{str(audit.get('allow_commit_to_repo', False)).lower()}",
        f"- cache_scope：{audit.get('cache_scope', '')}",
        f"- 是否发现 secret：{str(audit.get('contains_secret', False)).lower()}",
        f"- 是否已脱敏：{str(audit.get('real_values_redacted', True)).lower()}",
        "",
        "## 4. 数据说明",
        f"- {WARNING_REAL_LOCAL_ONLY}",
        "- 审计输出会脱敏价格、涨跌幅、成交额等字段。",
        "- CI 测试不会请求真实行情。",
    ]
    return "\n".join(lines) + "\n"
