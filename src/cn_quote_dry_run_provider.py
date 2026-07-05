"""A股 / ETF provider dry-run adapter.

This module validates the CN quote provider request plan and safety boundaries
before any real provider is connected. It never imports provider SDKs, performs
network requests, reads user configuration, writes caches, or returns real quote
values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from src.asset_model import normalize_asset_type, normalize_market, scan_asset_for_sensitive_values
from src.provider_registry import get_provider_evaluation
from src.provider_safety import (
    assert_real_data_not_written_to_repo,
    scan_provider_config_for_secrets,
    validate_provider_config,
)
from src.realtime_quote_provider import QuoteRequest

QUOTE_FIELDS = ("last_price", "change_pct", "change_amount", "volume", "turnover")
SUPPORTED_DRY_RUN_TYPES = frozenset({"stock", "etf", "official_index"})
DRY_RUN_DATA_STATUSES = frozenset({
    "dry_run_only",
    "disabled_by_default",
    "unsupported",
    "invalid_request",
    "provider_not_registered",
    "provider_policy_blocked",
    "provider_error",
})
DISCLAIMER = "本阶段仅验证 A股 / ETF provider 接入计划，不抓取真实行情。"
DRY_RUN_DELAY_NOTE = "本阶段仅做 dry-run，不请求真实行情。"
NETWORK_DISABLED_WARNING = "真实 provider 需要 network_enabled，但当前为 dry-run，不请求网络。"
DEFAULT_DISABLED_WARNING = "真实 provider 默认关闭，必须显式启用 network_enabled。"
NO_REAL_DATA_WARNING = "本结果不包含真实行情。"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_cn_market(value: Any) -> str:
    text = str(value or "").strip()
    if text in {"A股", "a股"}:
        return "CN"
    return normalize_market(text)


def _provider_or_none(provider_name: str) -> dict[str, Any] | None:
    try:
        return get_provider_evaluation(provider_name)
    except KeyError:
        return None


def _item_to_mapping(item: Any) -> dict[str, Any]:
    if isinstance(item, QuoteRequest):
        asset_type = item.normalized_asset_type()
        return {
            "request_id": item.request_id or item.symbol,
            "asset_id": item.request_id or item.symbol,
            "code": item.symbol,
            "symbol": item.symbol,
            "name": item.name,
            "type": "index" if asset_type == "official_index" else asset_type,
            "item_type": asset_type if asset_type == "official_index" else item.item_type,
            "market": item.market,
            **dict(item.metadata),
        }
    if isinstance(item, Mapping):
        return dict(item)
    return {"type": "unknown", "market": "unknown", "raw_item_type": type(item).__name__}


def _asset_type_and_reason(asset: Mapping[str, Any]) -> tuple[str, str | None]:
    raw_type = str(asset.get("type") or asset.get("asset_type") or "unknown").strip().lower()
    item_type = str(asset.get("item_type") or asset.get("index_type") or asset.get("category") or "").strip().lower()
    asset_type = normalize_asset_type(raw_type)
    if item_type == "computed_indicator":
        return "computed_indicator", None
    if raw_type in {"official_index", "official index"} or item_type in {"official_index", "official"}:
        return "official_index", None
    if asset_type == "index":
        if asset.get("is_official_index") is True or item_type in {"official_index", "official"}:
            return "official_index", None
        return "index", "只有 official index 可生成 A股 / ETF provider dry-run plan。"
    return asset_type, None


def _unsupported_reason(asset_type: str) -> str:
    return {
        "computed_indicator": "系统计算指标由市场广度模块生成，不直接请求 provider 行情。",
        "fund": "场外基金应使用 fund_nav_provider，不进入 A股 / ETF quote provider。",
        "company": "企业本身不是可直接报价对象，需关联 stock asset。",
        "industry": "行业 / 主题后续通过指数或系统计算指标实现。",
        "theme": "行业 / 主题后续通过指数或系统计算指标实现。",
    }.get(asset_type, "该资产不属于本阶段 A股 / ETF provider dry-run 支持范围。")


def _provider_checks(provider: Mapping[str, Any] | None) -> dict[str, Any]:
    if not provider:
        return {
            "provider_registered": False,
            "provider_candidate_only": False,
            "network_required": False,
            "network_enabled": False,
            "default_enabled": False,
            "field_mapping_ready": False,
            "cache_policy_ready": False,
            "failure_policy_ready": False,
            "allow_commit_to_repo": False,
            "secret_scan_passed": True,
            "provider_safety_passed": False,
        }
    config = {
        "provider_type": provider.get("provider_type"),
        "enabled": provider.get("default_enabled"),
        "network_enabled": False,
        "data_mode": "dry_run",
        "timeout_seconds": provider.get("enablement_policy", {}).get("requires_timeout_seconds"),
        "retry": provider.get("enablement_policy", {}).get("requires_retry_limit"),
        "rate_limit": provider.get("requires_rate_limit"),
    }
    policy_errors = validate_provider_config(config)
    secret_findings = scan_provider_config_for_secrets(provider)
    allow_commit = bool(provider.get("allow_commit_to_repo"))
    try:
        assert_real_data_not_written_to_repo({"has_real_market_data": False, "allow_commit_to_repo": allow_commit})
        repo_write_safe = True
    except ValueError:
        repo_write_safe = False
    return {
        "provider_registered": True,
        "provider_candidate_only": provider.get("status") == "candidate_only",
        "network_required": bool(provider.get("network_required")),
        "network_enabled": False,
        "default_enabled": bool(provider.get("default_enabled")),
        "field_mapping_ready": bool(provider.get("field_mapping")),
        "cache_policy_ready": bool(provider.get("cache_policy")),
        "failure_policy_ready": bool(provider.get("failure_policy")),
        "allow_commit_to_repo": allow_commit,
        "secret_scan_passed": not secret_findings,
        "provider_safety_passed": not policy_errors and repo_write_safe,
    }


def build_cn_quote_dry_run_request(asset_or_request: Any, provider_name: str = "akshare") -> dict[str, Any]:
    asset = _item_to_mapping(asset_or_request)
    provider = _provider_or_none(provider_name)
    provider_status = provider.get("status") if provider else "provider_not_registered"
    asset_type, _ = _asset_type_and_reason(asset)
    symbol = str(asset.get("symbol") or asset.get("code") or "").strip()
    asset_id = str(asset.get("asset_id") or asset.get("request_id") or symbol or "").strip()
    return {
        "request_id": str(asset.get("request_id") or asset_id or symbol),
        "asset_id": asset_id,
        "code": str(asset.get("code") or symbol),
        "symbol": symbol,
        "name": str(asset.get("name") or ""),
        "type": asset_type,
        "market": _normalize_cn_market(asset.get("market")),
        "provider_name": provider_name,
        "provider_status": provider_status,
        "data_kind": "realtime_quote",
        "data_mode": "dry_run",
        "network_required": bool(provider.get("network_required")) if provider else False,
        "network_enabled": False,
        "default_enabled": bool(provider.get("default_enabled")) if provider else False,
        "will_fetch_real_data": False,
        "will_write_cache": False,
        "allow_commit_to_repo": bool(provider.get("allow_commit_to_repo")) if provider else False,
    }


def validate_cn_quote_dry_run_request(request: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(request, Mapping):
        return ["request must be a mapping"]
    if request.get("will_fetch_real_data") is not False:
        errors.append("dry-run request must not fetch real data")
    if request.get("network_enabled") is not False:
        errors.append("dry-run request must keep network_enabled=false")
    if request.get("allow_commit_to_repo") is not False:
        errors.append("dry-run request must not allow repo writes")
    if scan_asset_for_sensitive_values(dict(request)):
        errors.append("dry-run request contains sensitive values")
    return errors


def _base_result(item: Any, provider_name: str, data_status: str, reason: str = "") -> dict[str, Any]:
    request = build_cn_quote_dry_run_request(item, provider_name)
    provider = _provider_or_none(provider_name)
    checked_at = _utc_now_iso()
    checks = _provider_checks(provider)
    warnings = [DEFAULT_DISABLED_WARNING, NO_REAL_DATA_WARNING]
    if checks["network_required"] and not checks["network_enabled"]:
        warnings.insert(1, NETWORK_DISABLED_WARNING)
    if reason:
        warnings.append(reason)
    return {
        **{key: request[key] for key in ("request_id", "asset_id", "code", "symbol", "name", "type", "market", "provider_name")},
        "data_status": data_status,
        "data_mode": "dry_run",
        "has_real_market_data": False,
        "will_fetch_real_data": False,
        "quote": {field: None for field in QUOTE_FIELDS},
        "provider_checks": checks,
        "source": {
            "provider": provider_name,
            "provider_type": provider.get("provider_type") if provider else "unknown",
            "source_status": "dry_run_only" if data_status == "dry_run_only" else data_status,
            "checked_at": checked_at,
            "delay_note": DRY_RUN_DELAY_NOTE,
        },
        "warnings": warnings,
        "reason": reason,
        "disclaimer": DISCLAIMER,
    }


def build_dry_run_disabled_result(item: Any, provider_name: str, reason: str) -> dict[str, Any]:
    return _base_result(item, provider_name, "disabled_by_default", reason)


def build_dry_run_unsupported_result(item: Any, provider_name: str, reason: str) -> dict[str, Any]:
    return _base_result(item, provider_name, "unsupported", reason)


def build_dry_run_invalid_request_result(item: Any, provider_name: str, reason: str) -> dict[str, Any]:
    return _base_result(item, provider_name, "invalid_request", reason)


def fetch_cn_quote_dry_run(item: Any, provider_name: str = "akshare") -> dict[str, Any]:
    provider = _provider_or_none(provider_name)
    if not provider:
        return _base_result(item, provider_name, "provider_not_registered", "provider 不存在于 provider_registry。")
    request = build_cn_quote_dry_run_request(item, provider_name)
    request_errors = validate_cn_quote_dry_run_request(request)
    asset = _item_to_mapping(item)
    asset_type, index_reason = _asset_type_and_reason(asset)
    if request_errors:
        return build_dry_run_invalid_request_result(item, provider_name, "; ".join(request_errors))
    if asset_type == "unknown":
        return build_dry_run_invalid_request_result(item, provider_name, "unknown asset type is invalid for dry-run request。")
    if request["market"] != "CN":
        return build_dry_run_unsupported_result(item, provider_name, "非 CN 市场资产不进入 A股 / ETF quote provider。")
    if asset_type in {"fund", "company", "industry", "theme", "computed_indicator"}:
        return build_dry_run_unsupported_result(item, provider_name, _unsupported_reason(asset_type))
    if index_reason:
        return build_dry_run_unsupported_result(item, provider_name, index_reason)
    if asset_type not in SUPPORTED_DRY_RUN_TYPES:
        return build_dry_run_unsupported_result(item, provider_name, _unsupported_reason(asset_type))
    result = _base_result(item, provider_name, "dry_run_only")
    validate_errors = validate_cn_quote_dry_run_result(result)
    if validate_errors:
        return _base_result(item, provider_name, "provider_policy_blocked", "; ".join(validate_errors))
    return result


def fetch_cn_quotes_dry_run(items: list[Any], provider_name: str = "akshare") -> list[dict[str, Any]]:
    return [fetch_cn_quote_dry_run(item, provider_name) for item in items]


def build_cn_quote_dry_run_plan(items: list[Any], provider_name: str = "akshare") -> dict[str, Any]:
    requests = [build_cn_quote_dry_run_request(item, provider_name) for item in items]
    return {
        "provider_name": provider_name,
        "data_mode": "dry_run",
        "will_fetch_real_data": False,
        "will_write_cache": False,
        "network_enabled": False,
        "requests": requests,
        "request_errors": [validate_cn_quote_dry_run_request(request) for request in requests],
    }


def validate_cn_quote_dry_run_result(result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("data_status") not in DRY_RUN_DATA_STATUSES:
        errors.append("unsupported dry-run data_status")
    if result.get("data_status") == "available":
        errors.append("dry-run result cannot be available")
    if result.get("has_real_market_data") is not False:
        errors.append("dry-run result cannot contain real market data")
    if result.get("will_fetch_real_data") is not False:
        errors.append("dry-run result cannot fetch real data")
    if result.get("source", {}).get("source_status") == "real_provider":
        errors.append("dry-run source cannot be real_provider")
    quote = result.get("quote", {})
    if any(quote.get(field) is not None for field in QUOTE_FIELDS):
        errors.append("dry-run quote fields must be null")
    if scan_asset_for_sensitive_values(dict(result)):
        errors.append("dry-run result contains sensitive values")
    return errors


def summarize_cn_quote_dry_run_results(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("data_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "summary_type": "cn_quote_dry_run_summary",
        "data_mode": "dry_run",
        "has_real_market_data": False,
        "will_fetch_real_data": False,
        "total": len(results),
        "status_counts": status_counts,
        "results": list(results),
        "disclaimer": DISCLAIMER,
    }


def render_cn_quote_dry_run_markdown(result_or_summary: Mapping[str, Any]) -> str:
    result = result_or_summary
    if result_or_summary.get("summary_type") == "cn_quote_dry_run_summary":
        result = (result_or_summary.get("results") or [{}])[0]
    checks = result.get("provider_checks", {})
    source = result.get("source", {})
    lines = [
        "# A股 / ETF Provider Dry-run Demo",
        "",
        "## 1. Provider 信息",
        f"- provider：{result.get('provider_name', '')}",
        f"- provider 类型：{source.get('provider_type', '')}",
        f"- 状态：{result.get('data_status', '')}",
        f"- 是否需要网络：{str(checks.get('network_required', False)).lower()}",
        f"- 是否默认启用：{str(checks.get('default_enabled', False)).lower()}",
        "",
        "## 2. 请求计划",
        f"- 资产：{result.get('name') or result.get('asset_id') or result.get('symbol')}",
        f"- 类型：{result.get('type', '')}",
        f"- 市场：{result.get('market', '')}",
        "- 是否会请求真实行情：false",
        "- 是否会写入缓存：false",
        "- 是否允许写入仓库：false",
        "",
        "## 3. 检查结果",
        f"- provider_registered：{str(checks.get('provider_registered', False)).lower()}",
        f"- field_mapping_ready：{str(checks.get('field_mapping_ready', False)).lower()}",
        f"- cache_policy_ready：{str(checks.get('cache_policy_ready', False)).lower()}",
        f"- failure_policy_ready：{str(checks.get('failure_policy_ready', False)).lower()}",
        "",
        "## 4. 数据说明",
        f"- {DRY_RUN_DELAY_NOTE}",
        f"- {DEFAULT_DISABLED_WARNING}",
        "- 本结果不包含真实价格、涨跌幅或成交额。",
    ]
    return "\n".join(lines) + "\n"


class CnQuoteDryRunProvider:
    """QuoteProvider-compatible dry-run provider for future CN providers."""

    def __init__(self, provider_name: str = "akshare") -> None:
        self.provider_name = provider_name

    def fetch_quote(self, request: Any) -> dict[str, Any]:
        return fetch_cn_quote_dry_run(request, self.provider_name)

    def fetch_quotes(self, requests: list[Any]) -> list[dict[str, Any]]:
        return fetch_cn_quotes_dry_run(requests, self.provider_name)

    def fetch_one(self, item: Any) -> dict[str, Any]:
        return self.fetch_quote(item)

    def fetch_many(self, items: list[Any]) -> list[dict[str, Any]]:
        return self.fetch_quotes(items)
