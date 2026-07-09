#!/usr/bin/env python3
"""Local manual smoke runner for off-exchange fund NAV providers.

Closed by default: dry-run mode does not request real NAV data, read user
configuration, or write files. Real-provider mode is only for explicit local
manual runs and requires CLI + environment + provider-config gates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Mapping

# Allow running as `python scripts/run_fund_nav_provider_smoke.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fund_nav_dry_run_provider import fetch_fund_nav_dry_run
from src.fund_nav_local_only_provider import fetch_fund_nav_local_only
from src.fund_nav_real_provider import FundNavRealProvider, build_fund_nav_real_provider_config

REAL_ENV_GATES = (
    "FUND_NAV_ENABLE_REAL_PROVIDER",
    "FUND_NAV_NETWORK_ENABLED",
    "FUND_NAV_ALLOW_REAL_REQUEST",
)
SENSITIVE_TOKENS = ("token", "api key", "api_key", "apikey", "webhook", "cookie", "authorization", "bearer", "password", "secret")
CI_REAL_BLOCK_MESSAGE = "CI 环境禁止真实基金净值 provider 请求。"
DEFAULT_DRY_RUN_MESSAGE = "默认 dry-run，不请求真实基金净值。"


def is_ci_environment(env: Mapping[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("CI", "")).lower() == "true" or str(values.get("GITHUB_ACTIONS", "")).lower() == "true"


def assert_not_ci_for_real_request(env: Mapping[str, str] | None = None) -> None:
    if is_ci_environment(env):
        raise RuntimeError(CI_REAL_BLOCK_MESSAGE)


def build_asset(args: argparse.Namespace) -> dict[str, Any]:
    return {"asset_id": args.code, "code": args.code, "name": args.name, "type": args.asset_type, "market": args.market}


def _missing_real_gates(env: Mapping[str, str], config: Mapping[str, Any]) -> list[str]:
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


def build_real_provider_config(provider_name: str, timeout: int, env: Mapping[str, str]) -> dict[str, Any]:
    config = build_fund_nav_real_provider_config(provider_name)
    if all(env.get(name) == "1" for name in REAL_ENV_GATES):
        config.update({"network_enabled": True, "provider_enabled": True, "allow_real_request": True})
    config.update({"allow_commit_to_repo": False, "cache_scope": "local_only", "timeout_seconds": timeout, "retry": 0, "retry_limit": 0})
    return config


def _blocked_result(asset: Mapping[str, Any], provider: str, data_status: str, reason: str, mode: str = "real_provider") -> dict[str, Any]:
    return {
        "status": data_status,
        "data_status": data_status,
        "provider": provider,
        "provider_name": provider,
        "code": asset.get("code", ""),
        "type": asset.get("type", ""),
        "market": asset.get("market", "CN"),
        "data_mode": mode,
        "source_status": data_status,
        "will_fetch_real_data": False,
        "has_real_nav_data": False,
        "allow_commit_to_repo": False,
        "message": reason,
        "warnings": ["真实结果仅允许本地手动打印到控制台；本脚本不写入仓库。", "盘中估算仅供观察，最终以基金公司公布净值为准。"],
    }


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            key_text = str(key)
            if any(token in key_text.lower().replace("-", "_") for token in SENSITIVE_TOKENS):
                redacted[key_text] = "<redacted>"
            else:
                redacted[key_text] = _redact(nested)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str) and any(token in value.lower() for token in SENSITIVE_TOKENS):
        return "<redacted>"
    return value


def run_smoke(argv: list[str] | None = None, *, env: Mapping[str, str] | None = None, real_fetcher: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="本地手动试跑场外基金净值 provider；默认 dry-run，不联网。")
    parser.add_argument("--provider", default="eastmoney_fund")
    parser.add_argument("--code", required=True)
    parser.add_argument("--type", dest="asset_type", default="fund")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--name", default="示例场外基金A")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--local-only", action="store_true", default=False)
    parser.add_argument("--real", action="store_true", default=False)
    parser.add_argument("--no-save", action="store_true", default=True)
    parser.add_argument("--print-json", action="store_true", default=False)
    parser.add_argument("--redact", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--yes-i-know-this-is-local-only", action="store_true", default=False)
    args = parser.parse_args(argv)
    current_env = env if env is not None else os.environ
    asset = build_asset(args)

    if args.real:
        if is_ci_environment(current_env):
            return _blocked_result(asset, args.provider, "provider_policy_blocked", CI_REAL_BLOCK_MESSAGE)
        config = build_real_provider_config(args.provider, args.timeout, current_env)
        missing = _missing_real_gates(current_env, config)
        if missing:
            return _blocked_result(asset, args.provider, "provider_policy_blocked", "真实请求开关不完整：" + ", ".join(missing))
        provider = FundNavRealProvider(args.provider, config=config, fetcher=real_fetcher)
        result = provider.fetch_one(asset)
    elif args.local_only:
        result = fetch_fund_nav_local_only(asset, {"data_mode": "local_only_fixture", "has_real_nav_data": False, "source_status": "local_fixture_only", "rows": [{"asset_id": args.code, "code": args.code, "name": args.name, "type": "fund", "market": args.market, "provider_symbol": "local_manual_fixture", "provider_status": "ok", "nav": {"unit_nav": None, "accumulated_nav": None, "daily_change_pct": None, "nav_date": None}, "estimate": {"estimated_nav": None, "estimated_change_pct": None, "estimated_change_amount": None, "estimate_time": None}}]})
    else:
        result = fetch_fund_nav_dry_run(asset, args.provider)
        result["status"] = result.get("data_status")
        result["provider"] = result.get("provider_name")
        result["message"] = DEFAULT_DRY_RUN_MESSAGE

    result.setdefault("status", result.get("data_status"))
    result.setdefault("provider", result.get("provider_name", args.provider))
    result.setdefault("allow_commit_to_repo", False)
    result.setdefault("has_real_nav_data", False)
    result.setdefault("will_fetch_real_data", False)
    if args.no_save:
        result["no_save"] = True
        result["will_write_files"] = False
    return _redact(result) if args.redact else result


def main(argv: list[str] | None = None) -> int:
    result = run_smoke(argv)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("data_status") not in {"invalid_request"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
