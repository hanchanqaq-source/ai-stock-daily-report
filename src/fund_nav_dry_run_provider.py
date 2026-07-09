"""Dry-run adapter for future off-exchange fund NAV providers.

This module validates request planning and provider safety boundaries only.  It
never connects to real providers, reads user configuration, writes cache files,
or returns real NAV / estimated NAV values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from src.asset_model import normalize_asset_type, normalize_market, scan_asset_for_sensitive_values
from src.fund_nav_provider import FundNavRequest, _empty_estimate, _empty_nav
from src.fund_nav_provider_registry import get_fund_nav_provider_evaluation
from src.provider_safety import (
    FUND_ESTIMATE_WARNING,
    assert_real_data_not_written_to_repo,
    scan_provider_config_for_secrets,
    validate_provider_config,
    validate_provider_result,
)

DRY_RUN_STATUSES = frozenset({
    "dry_run_only",
    "disabled_by_default",
    "unsupported",
    "invalid_request",
    "provider_not_registered",
    "provider_policy_blocked",
    "provider_error",
})
REQUESTED_DATA = ["daily_nav", "estimated_nav"]
DISCLAIMER = "本阶段仅验证场外基金净值 provider 接入计划，不抓取真实基金净值。"
DELAY_NOTE = "本阶段仅做 dry-run，不请求真实基金净值。"
UNSUPPORTED_REASONS = {
    "stock": "股票应使用 A股 / ETF quote provider。",
    "etf": "ETF 属于交易所交易品种，应使用股票 / ETF provider。",
    "index": "指数应使用 index quote 或市场指数模块。",
    "company": "企业本身不是基金净值对象。",
    "industry": "行业 / 主题不直接获取基金净值。",
    "theme": "行业 / 主题不直接获取基金净值。",
    "computed_indicator": "系统计算指标由市场广度模块生成，不直接请求基金净值 provider。",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _data(item: Mapping[str, Any] | FundNavRequest) -> dict[str, Any]:
    return item.to_dict() if isinstance(item, FundNavRequest) else dict(item)


def _provider(provider_name: str) -> dict[str, Any] | None:
    try:
        return get_fund_nav_provider_evaluation(provider_name)
    except KeyError:
        return None


def _checks(candidate: Mapping[str, Any] | None, network_enabled: bool = False) -> dict[str, Any]:
    mapping = (candidate or {}).get("field_mapping") or {}
    cache = (candidate or {}).get("cache_policy") or {}
    failure = (candidate or {}).get("failure_policy") or {}
    if candidate is None:
        return {
            "provider_registered": False,
            "provider_candidate_only": False,
            "network_required": None,
            "network_enabled": bool(network_enabled),
            "default_enabled": False,
            "daily_nav_mapping_ready": False,
            "estimated_nav_mapping_ready": False,
            "cache_policy_ready": False,
            "failure_policy_ready": False,
            "allow_commit_to_repo": False,
        }
    return {
        "provider_registered": True,
        "provider_candidate_only": candidate.get("status") == "candidate_only",
        "network_required": bool(candidate.get("network_required") is True),
        "network_enabled": bool(network_enabled),
        "default_enabled": bool(candidate.get("default_enabled") is True),
        "daily_nav_mapping_ready": bool(mapping.get("daily_nav_fields")),
        "estimated_nav_mapping_ready": bool(mapping.get("estimated_nav_fields")),
        "cache_policy_ready": bool(cache.get("policies")),
        "failure_policy_ready": bool(failure.get("failure_policy")),
        "allow_commit_to_repo": bool(candidate.get("allow_commit_to_repo") is True),
    }


def _base_payload(item: Mapping[str, Any] | FundNavRequest, provider_name: str) -> dict[str, Any]:
    data = _data(item)
    return {
        "request_id": str(data.get("request_id") or data.get("asset_id") or data.get("code") or ""),
        "asset_id": str(data.get("asset_id") or ""),
        "code": str(data.get("code") or ""),
        "name": str(data.get("name") or ""),
        "type": normalize_asset_type(data.get("type")),
        "market": normalize_market(data.get("market") or "CN"),
        "provider_name": provider_name,
    }


def _warnings(candidate: Mapping[str, Any] | None) -> list[str]:
    warnings = [
        FUND_ESTIMATE_WARNING,
        "本结果不包含真实基金净值。",
    ]
    if candidate and candidate.get("default_enabled") is False:
        warnings.insert(0, "真实基金净值 provider 默认关闭，必须显式启用 network_enabled。")
    if candidate and candidate.get("network_required") is True:
        warnings.append("真实基金净值 provider 需要 network_enabled，但当前为 dry-run，不请求网络。")
    return warnings


def build_fund_nav_dry_run_request(asset_or_request: Mapping[str, Any] | FundNavRequest, provider_name: str = "eastmoney_fund") -> dict[str, Any]:
    candidate = _provider(provider_name)
    base = _base_payload(asset_or_request, provider_name)
    checks = _checks(candidate)
    request = {
        **base,
        "provider_status": (candidate or {}).get("status", "provider_not_registered"),
        "data_kind": "fund_nav",
        "requested_data": list(REQUESTED_DATA),
        "data_mode": "dry_run",
        "network_required": checks["network_required"],
        "network_enabled": False,
        "default_enabled": checks["default_enabled"],
        "will_fetch_real_data": False,
        "will_write_cache": False,
        "allow_commit_to_repo": checks["allow_commit_to_repo"],
    }
    validate_fund_nav_dry_run_request(request)
    return request


def build_fund_nav_dry_run_plan(items: list[Mapping[str, Any] | FundNavRequest], provider_name: str = "eastmoney_fund") -> dict[str, Any]:
    requests = [build_fund_nav_dry_run_request(item, provider_name) for item in items]
    return {"data_mode": "dry_run", "provider_name": provider_name, "requests": requests, "will_fetch_real_data": False, "will_write_cache": False}


def validate_fund_nav_dry_run_request(request: Mapping[str, Any]) -> bool:
    if request.get("data_mode") != "dry_run" or request.get("will_fetch_real_data") is not False:
        return False
    if request.get("network_enabled") is not False or request.get("allow_commit_to_repo") is not False:
        return False
    return not scan_asset_for_sensitive_values(request) and not scan_provider_config_for_secrets(request)


def _result(item: Mapping[str, Any] | FundNavRequest, provider_name: str, status: str, reason: str = "") -> dict[str, Any]:
    candidate = _provider(provider_name)
    base = _base_payload(item, provider_name)
    checks = _checks(candidate)
    provider_type = (candidate or {}).get("provider_type", "unknown")
    result = {
        **base,
        "data_status": status,
        "data_mode": "dry_run",
        "has_real_nav_data": False,
        "will_fetch_real_data": False,
        "nav": _empty_nav(),
        "estimate": _empty_estimate(),
        "provider_checks": checks,
        "source": {"provider": provider_name, "provider_type": provider_type, "source_status": "dry_run_only", "checked_at": _utc_now_iso(), "delay_note": DELAY_NOTE},
        "warnings": _warnings(candidate),
        "disclaimer": DISCLAIMER,
        "reason": reason,
    }
    if candidate is None:
        result["data_status"] = "provider_not_registered"
        result["source"]["source_status"] = "dry_run_only"
        result["warnings"] = ["provider 未在 fund_nav_provider_registry 中注册。"]
        validate_fund_nav_dry_run_result(result)
        return result
    if scan_provider_config_for_secrets(candidate) or validate_provider_config({"provider_type": provider_type, "data_mode": "dry_run", "enabled": False, "network_enabled": False, "timeout_seconds": 10, "retry": 0, "rate_limit": "dry_run"}):
        result["data_status"] = "provider_policy_blocked"
    try:
        assert_real_data_not_written_to_repo({"has_real_market_data": False, "allow_commit_to_repo": False})
    except ValueError:
        result["data_status"] = "provider_policy_blocked"
    validate_fund_nav_dry_run_result(result)
    return result


def validate_fund_nav_dry_run_result(result: Mapping[str, Any]) -> bool:
    if result.get("data_status") not in DRY_RUN_STATUSES or result.get("data_status") == "available":
        return False
    if result.get("has_real_nav_data") is not False or result.get("will_fetch_real_data") is not False:
        return False
    if result.get("data_mode") == "real_provider" or (result.get("source") or {}).get("source_status") == "real_provider":
        return False
    if any(value is not None for value in (result.get("nav") or {}).values()):
        return False
    if any(value is not None for value in (result.get("estimate") or {}).values()):
        return False
    return not scan_asset_for_sensitive_values(result) and not scan_provider_config_for_secrets(result) and not validate_provider_result(result)


def build_fund_nav_dry_run_disabled_result(item: Mapping[str, Any] | FundNavRequest, provider_name: str, reason: str) -> dict[str, Any]:
    return _result(item, provider_name, "disabled_by_default", reason)


def build_fund_nav_dry_run_unsupported_result(item: Mapping[str, Any] | FundNavRequest, provider_name: str, reason: str) -> dict[str, Any]:
    return _result(item, provider_name, "unsupported", reason)


def build_fund_nav_dry_run_invalid_request_result(item: Mapping[str, Any] | FundNavRequest, provider_name: str, reason: str) -> dict[str, Any]:
    return _result(item, provider_name, "invalid_request", reason)


def fetch_fund_nav_dry_run(item: Mapping[str, Any] | FundNavRequest, provider_name: str = "eastmoney_fund") -> dict[str, Any]:
    candidate = _provider(provider_name)
    if candidate is None:
        return _result(item, provider_name, "provider_not_registered", "provider 未登记在 fund_nav_provider_registry。")
    data = _base_payload(item, provider_name)
    if data["type"] == "unknown":
        return build_fund_nav_dry_run_invalid_request_result(item, provider_name, "资产类型 unknown，无法生成基金净值 dry-run 请求。")
    if data["type"] != "fund":
        return build_fund_nav_dry_run_unsupported_result(item, provider_name, UNSUPPORTED_REASONS.get(data["type"], "该资产类型不进入基金净值 provider。"))
    if data["market"] not in {"CN", "中国"}:
        return build_fund_nav_dry_run_unsupported_result(item, provider_name, "非 CN 市场基金暂不进入场外基金净值 provider dry-run。")
    return _result(item, provider_name, "dry_run_only", "dry-run only; no network request is made")


def fetch_fund_navs_dry_run(items: list[Mapping[str, Any] | FundNavRequest], provider_name: str = "eastmoney_fund") -> dict[str, Any]:
    results = [fetch_fund_nav_dry_run(item, provider_name) for item in items]
    return {"data_mode": "dry_run", "provider_name": provider_name, "results": results, "summary": summarize_fund_nav_dry_run_results(results)}


class FundNavDryRunProvider:
    name = "fund_nav_dry_run"
    provider_type = "dry_run"

    def __init__(self, provider_name: str = "eastmoney_fund") -> None:
        self.provider_name = provider_name

    def supports_market(self, market: str) -> bool:
        return normalize_market(market) in {"CN", "中国"}

    def supports_item(self, item: FundNavRequest) -> bool:
        return isinstance(item, FundNavRequest) and item.type == "fund" and self.supports_market(item.market)

    def fetch_one(self, request: FundNavRequest) -> Any:
        return fetch_fund_nav_dry_run(request, self.provider_name)

    def fetch_many(self, requests: list[FundNavRequest]) -> list[dict[str, Any]]:
        return [self.fetch_one(request) for request in requests]


def summarize_fund_nav_dry_run_results(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {status: sum(1 for item in results if item.get("data_status") == status) for status in DRY_RUN_STATUSES}
    return {"data_mode": "dry_run", "total": len(results), **{f"{k}_count": v for k, v in counts.items()}, "has_real_nav_data": False, "will_fetch_real_data": False, "warnings": [DELAY_NOTE, FUND_ESTIMATE_WARNING]}


def render_fund_nav_dry_run_markdown(result_or_summary: Mapping[str, Any]) -> str:
    data = dict(result_or_summary)
    if "summary" in data and data.get("results"):
        data = dict(data["results"][0])
    checks = data.get("provider_checks") or {}
    source = data.get("source") or {}
    return "\n".join([
        "# 场外基金净值 Provider Dry-run Demo",
        "",
        "## 1. Provider 信息",
        f"- provider：{data.get('provider_name', '-')}",
        f"- provider 类型：{source.get('provider_type', '-')}",
        f"- 状态：{data.get('data_status', '-')}",
        f"- 是否需要网络：{str(checks.get('network_required', False)).lower()}",
        f"- 是否默认启用：{str(checks.get('default_enabled', False)).lower()}",
        "",
        "## 2. 请求计划",
        f"- 基金：{data.get('name') or '-'} / {data.get('code') or '-'}",
        f"- 类型：{data.get('type', '-')}",
        f"- 市场：{data.get('market', '-')}",
        "- 请求数据：daily_nav / estimated_nav",
        "- 是否会请求真实基金净值：false",
        "- 是否会写入缓存：false",
        "- 是否允许写入仓库：false",
        "",
        "## 3. 检查结果",
        f"- provider_registered：{str(checks.get('provider_registered', False)).lower()}",
        f"- daily_nav_mapping_ready：{str(checks.get('daily_nav_mapping_ready', False)).lower()}",
        f"- estimated_nav_mapping_ready：{str(checks.get('estimated_nav_mapping_ready', False)).lower()}",
        f"- cache_policy_ready：{str(checks.get('cache_policy_ready', False)).lower()}",
        f"- failure_policy_ready：{str(checks.get('failure_policy_ready', False)).lower()}",
        "",
        "## 4. 数据说明",
        "本阶段仅做 dry-run，不请求真实基金净值。",
        "场外基金不支持真正实时价格。",
        "盘中估算仅供观察，最终以基金公司公布净值为准。",
        "本结果不包含真实单位净值、估算净值或涨跌幅。",
    ]) + "\n"
