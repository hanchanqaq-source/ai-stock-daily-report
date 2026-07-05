#!/usr/bin/env python3
"""Local manual smoke runner for the gated CN quote providers.

The script is intentionally dry-run by default. Real-provider mode is only
allowed for explicit local manual use after all CLI, environment, and provider
config gates are open. It never writes provider output to the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.cn_quote_dry_run_provider import fetch_cn_quote_dry_run
from src.cn_quote_local_only_provider import fetch_cn_quote_local_only
from src.cn_quote_real_provider import CnQuoteRealProvider, build_cn_quote_real_provider_config
from src.provider_safety import assert_real_data_not_written_to_repo, scan_provider_config_for_secrets

REAL_ENV_GATES = (
    "CN_QUOTE_ENABLE_REAL_PROVIDER",
    "CN_QUOTE_NETWORK_ENABLED",
    "CN_QUOTE_ALLOW_REAL_REQUEST",
)
SENSITIVE_WORDS = (
    "token",
    "api key",
    "api_key",
    "apikey",
    "webhook",
    "cookie",
    "authorization",
    "bearer",
    "password",
    "secret",
)
SUPPORTED_CLI_TYPES = {"stock", "etf", "index", "fund", "unknown"}

Fetcher = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def is_ci_environment(env: Mapping[str, str] | None = None) -> bool:
    active_env = env or os.environ
    return str(active_env.get("CI", "")).lower() == "true" or str(active_env.get("GITHUB_ACTIONS", "")).lower() == "true"


def assert_not_ci_for_real_request(env: Mapping[str, str] | None = None) -> None:
    if is_ci_environment(env):
        raise RuntimeError("CI 环境禁止真实 provider 请求。")


def _is_sensitive_text(value: Any) -> bool:
    text = str(value or "").lower().replace("-", "_")
    return any(word in text or word.replace(" ", "_") in text for word in SENSITIVE_WORDS)


def redact_output(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            safe_key = "<redacted_key>" if _is_sensitive_text(key) else str(key)
            redacted[safe_key] = "<redacted>" if _is_sensitive_text(key) else redact_output(nested)
        return redacted
    if isinstance(value, list):
        return [redact_output(item) for item in value]
    if isinstance(value, str) and _is_sensitive_text(value):
        return "<redacted>"
    return value


def build_asset(args: argparse.Namespace) -> dict[str, Any]:
    asset = {
        "asset_id": args.code,
        "code": args.code,
        "symbol": args.code,
        "name": args.name,
        "type": args.type,
        "market": args.market,
    }
    if args.type == "index":
        asset["item_type"] = "official_index"
        asset["is_official_index"] = True
    return asset


def build_real_config(args: argparse.Namespace, env: Mapping[str, str]) -> dict[str, Any]:
    config = build_cn_quote_real_provider_config(args.provider)
    config.update(
        {
            "network_enabled": env.get("CN_QUOTE_NETWORK_ENABLED") == "1",
            "provider_enabled": env.get("CN_QUOTE_ENABLE_REAL_PROVIDER") == "1",
            "enabled": env.get("CN_QUOTE_ENABLE_REAL_PROVIDER") == "1",
            "allow_real_request": env.get("CN_QUOTE_ALLOW_REAL_REQUEST") == "1",
            "allow_commit_to_repo": False,
            "cache_scope": "local_only",
            "timeout_seconds": args.timeout,
        }
    )
    return config


def missing_real_gates(config: Mapping[str, Any], env: Mapping[str, str]) -> list[str]:
    missing = [name for name in REAL_ENV_GATES if env.get(name) != "1"]
    if config.get("network_enabled") is not True:
        missing.append("provider config network_enabled=true")
    if config.get("provider_enabled") is not True:
        missing.append("provider config provider_enabled=true")
    if config.get("allow_real_request") is not True:
        missing.append("provider config allow_real_request=true")
    if config.get("allow_commit_to_repo") is not False:
        missing.append("provider config allow_commit_to_repo=false")
    if config.get("cache_scope") != "local_only":
        missing.append("provider config cache_scope=local_only")
    return missing


def _finalize_result(result: Mapping[str, Any], *, message: str, args: argparse.Namespace) -> dict[str, Any]:
    output = dict(result)
    output.setdefault("provider", output.get("provider_name", args.provider))
    output.setdefault("status", output.get("data_status", "unknown"))
    output.setdefault("source_status", output.get("source", {}).get("source_status"))
    output.setdefault("will_fetch_real_data", False)
    output.setdefault("has_real_market_data", False)
    output["allow_commit_to_repo"] = False
    output["will_write_cache"] = False
    output["no_save"] = True
    output["message"] = message
    output["safety_red_lines"] = [
        "默认 dry-run，不请求真实行情。",
        "真实结果只打印到控制台，不写入仓库、data/history 或 config。",
        "CI 环境禁止真实 provider 请求。",
    ]
    assert_real_data_not_written_to_repo({"has_real_market_data": False, "allow_commit_to_repo": False})
    return output


def run_smoke(argv: list[str] | None = None, *, env: Mapping[str, str] | None = None, real_fetcher: Fetcher | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="A股 / ETF provider 本地手动 smoke test（默认 dry-run）。")
    parser.add_argument("--provider", default="akshare")
    parser.add_argument("--code", default="000001")
    parser.add_argument("--type", default="stock", choices=sorted(SUPPORTED_CLI_TYPES))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--name", default="示例资产")
    parser.add_argument("--dry-run", action="store_true", help="显式 dry-run；默认即为 dry-run。")
    parser.add_argument("--local-only", action="store_true", help="使用 local-only fixture，不联网。")
    parser.add_argument("--real", action="store_true", help="尝试真实 provider；需要所有显式开关且非 CI。")
    parser.add_argument("--no-save", action="store_true", default=True, help="保留参数兼容；本阶段始终不保存。")
    parser.add_argument("--print-json", action="store_true", help="打印结构化 JSON。")
    parser.add_argument("--redact", action=argparse.BooleanOptionalAction, default=True, help="输出脱敏，默认开启。")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--yes-i-know-this-is-local-only", action="store_true")
    args = parser.parse_args(argv)

    active_env = env or os.environ
    asset = build_asset(args)

    if args.type == "unknown":
        result = fetch_cn_quote_dry_run(asset, args.provider)
        return _finalize_result(result, message="unknown asset type is invalid for smoke request。", args=args)

    if scan_provider_config_for_secrets(asset):
        result = {"data_status": "invalid_request", "data_mode": "dry_run", "has_real_market_data": False, "will_fetch_real_data": False, "provider_name": args.provider, "reason": "request contains sensitive fields"}
        return _finalize_result(result, message="请求包含敏感字段，已拒绝。", args=args)

    if args.real:
        config = build_real_config(args, active_env)
        if is_ci_environment(active_env):
            result = {"data_status": "provider_policy_blocked", "data_mode": "real_provider", "has_real_market_data": False, "will_fetch_real_data": False, "provider_name": args.provider, "source": {"provider": args.provider, "source_status": "provider_policy_blocked"}, "provider_checks": {"allow_commit_to_repo": False, "cache_scope": "local_only"}, "reason": "CI 环境禁止真实 provider 请求。"}
            return _finalize_result(result, message="CI 环境禁止真实 provider 请求。", args=args)
        missing = missing_real_gates(config, active_env)
        if missing:
            result = {"data_status": "provider_policy_blocked", "data_mode": "real_provider", "has_real_market_data": False, "will_fetch_real_data": False, "provider_name": args.provider, "source": {"provider": args.provider, "source_status": "provider_policy_blocked"}, "provider_checks": {"network_enabled": config.get("network_enabled") is True, "provider_enabled": config.get("provider_enabled") is True, "allow_real_request": config.get("allow_real_request") is True, "allow_commit_to_repo": False, "cache_scope": "local_only"}, "reason": "缺少真实 provider 开关: " + ", ".join(missing)}
            return _finalize_result(result, message="真实请求被安全策略拦截。", args=args)
        assert_not_ci_for_real_request(active_env)
        provider = CnQuoteRealProvider(provider_name=args.provider, config=config, fetcher=real_fetcher)
        result = provider.fetch_quote(asset)
        return _finalize_result(result, message="真实 provider 路径已显式开启；结果仅打印到控制台，不保存。", args=args)

    if args.local_only:
        result = fetch_cn_quote_local_only(asset)
        return _finalize_result(result, message="local-only fixture 模式，不联网、不请求真实行情。", args=args)

    result = fetch_cn_quote_dry_run(asset, args.provider)
    return _finalize_result(result, message="默认 dry-run，不请求真实行情。", args=args)


def main(argv: list[str] | None = None) -> int:
    result = run_smoke(argv)
    printable = redact_output(result) if result.get("redact", True) else result
    print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("data_status") not in {"invalid_request"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
