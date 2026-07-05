"""Account-level realtime quote / fund NAV summary framework.

This module is intentionally offline and fixture-only. It routes active account
assets to existing quote and fund NAV framework contracts, merges public-safe
provider status, and never reads user_config, fetches network data, persists
market values, or emits trading advice.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from src.asset_model import (
    ALLOWED_ASSET_STATUSES,
    build_asset_public_safe_view,
    is_active_asset,
    normalize_asset_status,
    normalize_asset_type,
    normalize_market,
)
from src.fund_nav_provider import FundNavProvider, build_fund_nav_request, fetch_fund_nav
from src.quote_capability import get_quote_capability
from src.realtime_quote_provider import QuoteProvider, QuoteRequest, fetch_realtime_quotes

ACTIVE_STATUSES = frozenset({"holding", "watching"})
INACTIVE_STATUSES = frozenset({"cleared", "archived", "deleted"})
QUOTE_ASSET_TYPES = frozenset({"stock", "etf"})
UNSUPPORTED_ASSET_TYPES = frozenset({"company", "industry", "theme"})
BASE_WARNINGS = [
    "本阶段为 fixture/mock 数据，不代表真实行情或真实基金净值。",
    "场外基金估算净值不等于最终净值，最终以基金公司公布净值为准。",
]
DISCLAIMER = "本阶段仅验证账户行情 / 净值汇总框架，不抓取真实行情，不构成交易建议。"
COMPANY_UNSUPPORTED_REASON = "企业本身不是直接报价对象，后续可通过关联 stock asset 展示行情。"
THEME_UNSUPPORTED_REASON = "行业 / 主题本阶段不直接抓行情，后续可通过指数或系统计算指标实现。"
COMPUTED_UNSUPPORTED_REASON = "computed_indicator 由市场指标模块生成，本阶段不直接抓 quote。"
UNKNOWN_INVALID_REASON = "资产类型 unknown，无法生成账户行情 / 净值请求。"


def _assets(group: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(asset) for asset in group.get("assets", []) if isinstance(asset, Mapping)]


def _safe_asset(asset: Mapping[str, Any]) -> dict[str, Any]:
    prepared = {
        "asset_id": str(asset.get("asset_id") or asset.get("code") or ""),
        "type": normalize_asset_type(asset.get("type")),
        "code": str(asset.get("code") or ""),
        "name": str(asset.get("name") or ""),
        "market": normalize_market(asset.get("market")),
        "status": normalize_asset_status(asset.get("status") or "watching"),
        "tags": list(asset.get("tags") or []),
        "weight_level": int(asset.get("weight_level") or 1),
        "source_status": str(asset.get("source_status") or "manual_user_input"),
    }
    return build_asset_public_safe_view(prepared)


def _asset_counts(assets: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in ALLOWED_ASSET_STATUSES}
    for asset in assets:
        status = normalize_asset_status(asset.get("status") or "watching")
        if status in counts:
            counts[status] += 1
    return {
        "total": len(assets),
        "active": counts["holding"] + counts["watching"],
        "holding": counts["holding"],
        "watching": counts["watching"],
        "cleared": counts["cleared"],
        "archived": counts["archived"],
        "deleted": counts["deleted"],
    }


def split_assets_for_realtime_summary(group: Mapping[str, Any]) -> dict[str, Any]:
    """Return public-safe active/inactive asset buckets without mutating input."""

    assets = [_safe_asset(asset) for asset in _assets(group)]
    active = [asset for asset in assets if is_active_asset(asset)]
    inactive = [asset for asset in assets if normalize_asset_status(asset.get("status")) in INACTIVE_STATUSES]
    return {
        "active": active,
        "inactive": inactive,
        "holding": [asset for asset in active if asset.get("status") == "holding"],
        "watching": [asset for asset in active if asset.get("status") == "watching"],
        "by_type": {asset_type: [asset for asset in active if asset.get("type") == asset_type] for asset_type in ["stock", "etf", "fund", "index", "company", "industry", "theme", "unknown"]},
        "asset_counts": _asset_counts(assets),
    }


def _index_item_type(asset: Mapping[str, Any]) -> str:
    item_type = str(asset.get("item_type") or asset.get("index_type") or asset.get("kind") or "").strip().lower()
    if item_type in {"computed_indicator", "official_index"}:
        return item_type
    capability = get_quote_capability(dict(asset))
    price_mode = str(capability.get("price_mode") or "")
    return "official_index" if price_mode == "index_quote" else item_type


def build_asset_market_data_request(asset: Mapping[str, Any]) -> dict[str, Any]:
    """Build a routing request descriptor; no network or persistence is performed."""

    safe = _safe_asset(asset)
    asset_type = safe["type"]
    if asset_type in QUOTE_ASSET_TYPES:
        return {"request_kind": "realtime_quote", "asset": safe, "request": QuoteRequest(symbol=safe["code"], asset_type=asset_type, market=safe["market"], name=safe["name"], request_id=safe["asset_id"])}
    if asset_type == "index":
        item_type = _index_item_type(asset)
        if item_type == "computed_indicator":
            return {"request_kind": "unsupported", "asset": safe, "reason": COMPUTED_UNSUPPORTED_REASON}
        return {"request_kind": "realtime_quote", "asset": safe, "request": QuoteRequest(symbol=safe["code"], asset_type="index", market=safe["market"], name=safe["name"], request_id=safe["asset_id"], item_type="official_index")}
    if asset_type == "fund":
        return {"request_kind": "fund_nav", "asset": safe, "request": build_fund_nav_request(safe)}
    if asset_type == "company":
        return {"request_kind": "unsupported", "asset": safe, "reason": COMPANY_UNSUPPORTED_REASON}
    if asset_type in {"industry", "theme"}:
        return {"request_kind": "unsupported", "asset": safe, "reason": THEME_UNSUPPORTED_REASON}
    return {"request_kind": "invalid_request", "asset": safe, "reason": UNKNOWN_INVALID_REASON}


def _unsupported_result(asset: Mapping[str, Any], reason: str, kind: str = "unsupported") -> dict[str, Any]:
    return {
        "asset": _safe_asset(asset),
        "result_kind": kind,
        "data_status": kind,
        "provider": "account_realtime_summary",
        "checked_at": None,
        "source_status": kind,
        "fixture_only": False,
        "has_real_market_data": False,
        "reason": reason,
        "disclaimer": DISCLAIMER,
    }


def _quote_result(asset: Mapping[str, Any], result: Any) -> dict[str, Any]:
    data = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    status = "available" if data.get("success") else str(data.get("source_status") or "provider_error")
    return {
        "asset": _safe_asset(asset),
        "result_kind": "realtime_quote",
        "data_status": status,
        "provider": data.get("provider"),
        "checked_at": data.get("checked_at"),
        "source_status": data.get("source_status"),
        "fixture_only": bool(data.get("fixture_only")),
        "has_real_market_data": False,
        "reason": data.get("message") or "",
        "disclaimer": DISCLAIMER,
    }


def _fund_result(asset: Mapping[str, Any], result: Any) -> dict[str, Any]:
    data = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    source = data.get("source") or {}
    status = str(data.get("data_status") or "provider_error")
    return {
        "asset": _safe_asset(asset),
        "result_kind": "fund_nav",
        "data_status": "available" if status in {"available", "estimate_only", "daily_nav_only"} else status,
        "provider": source.get("provider"),
        "checked_at": source.get("checked_at"),
        "source_status": source.get("source_status"),
        "fixture_only": source.get("source_status") == "fixture_only",
        "has_real_market_data": False,
        "reason": data.get("reason") or "",
        "warnings": list(data.get("warnings") or []),
        "disclaimer": DISCLAIMER,
    }


def fetch_asset_market_data(asset: Mapping[str, Any], quote_provider: QuoteProvider | None = None, fund_nav_provider: FundNavProvider | None = None) -> dict[str, Any]:
    descriptor = build_asset_market_data_request(asset)
    kind = descriptor["request_kind"]
    safe = descriptor["asset"]
    if kind == "realtime_quote":
        result = fetch_realtime_quotes([descriptor["request"]], quote_provider)[0]
        return _quote_result(safe, result)
    if kind == "fund_nav":
        return _fund_result(safe, fetch_fund_nav(safe, fund_nav_provider))
    if kind == "invalid_request":
        return _unsupported_result(safe, descriptor["reason"], "invalid_request")
    return _unsupported_result(safe, descriptor["reason"], "unsupported")


def fetch_account_market_data(group: Mapping[str, Any], quote_provider: QuoteProvider | None = None, fund_nav_provider: FundNavProvider | None = None) -> list[dict[str, Any]]:
    active_assets = [asset for asset in _assets(group) if normalize_asset_status(asset.get("status") or "watching") in ACTIVE_STATUSES]
    return [fetch_asset_market_data(asset, quote_provider, fund_nav_provider) for asset in active_assets]


def summarize_account_market_data(results: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "available_count": sum(1 for item in results if item.get("data_status") == "available"),
        "unsupported_count": sum(1 for item in results if item.get("data_status") == "unsupported"),
        "provider_error_count": sum(1 for item in results if item.get("data_status") == "provider_error"),
        "invalid_request_count": sum(1 for item in results if item.get("data_status") == "invalid_request"),
        "fixture_only_count": sum(1 for item in results if item.get("fixture_only") is True),
    }


def summarize_by_asset_status(results: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    return {status: _status_summary([item for item in results if (item.get("asset") or {}).get("status") == status]) for status in ACTIVE_STATUSES}


def summarize_by_asset_type(results: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    buckets = {key: [] for key in ["stock", "etf", "fund", "index", "unsupported", "invalid_request"]}
    for item in results:
        key = (item.get("asset") or {}).get("type")
        if item.get("data_status") in {"unsupported", "invalid_request"} and key not in {"stock", "etf", "fund", "index"}:
            key = item.get("data_status")
        buckets.setdefault(str(key), []).append(item)
    return {key: _status_summary(value) for key, value in buckets.items()}


def _status_summary(items: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "total": len(items),
        "quote_available_count": sum(1 for item in items if item.get("result_kind") == "realtime_quote" and item.get("data_status") == "available"),
        "fund_nav_available_count": sum(1 for item in items if item.get("result_kind") == "fund_nav" and item.get("data_status") == "available"),
        "unsupported_count": sum(1 for item in items if item.get("data_status") == "unsupported"),
        "provider_error_count": sum(1 for item in items if item.get("data_status") == "provider_error"),
        "invalid_request_count": sum(1 for item in items if item.get("data_status") == "invalid_request"),
    }


def summarize_holding_vs_watching_market_data(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "holding": _status_summary([item for item in results if (item.get("asset") or {}).get("status") == "holding"]),
        "watching": _status_summary([item for item in results if (item.get("asset") or {}).get("status") == "watching"]),
    }


def _request_summary(results: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "quote_request_count": sum(1 for item in results if item.get("result_kind") == "realtime_quote"),
        "fund_nav_request_count": sum(1 for item in results if item.get("result_kind") == "fund_nav"),
        "unsupported_count": sum(1 for item in results if item.get("result_kind") == "unsupported"),
        "invalid_request_count": sum(1 for item in results if item.get("result_kind") == "invalid_request"),
    }


def _overall_status(results: list[Mapping[str, Any]]) -> str:
    if not results:
        return "empty"
    summary = summarize_account_market_data(results)
    if summary["provider_error_count"] == len(results):
        return "provider_error"
    if summary["available_count"] == len(results):
        return "available"
    if summary["available_count"] > 0:
        return "partial_available"
    if summary["unsupported_count"] or summary["invalid_request_count"]:
        return "insufficient_data"
    return "provider_error" if summary["provider_error_count"] else "insufficient_data"


def build_account_market_data_empty_result(group: Mapping[str, Any], reason: str) -> dict[str, Any]:
    assets = [_safe_asset(asset) for asset in _assets(group)]
    return {
        "account_id": str(group.get("account_id") or ""),
        "account_name": str(group.get("account_name") or group.get("name") or ""),
        "status": "empty",
        "data_mode": "model_only",
        "has_real_market_data": False,
        "asset_counts": _asset_counts(assets),
        "request_summary": {"quote_request_count": 0, "fund_nav_request_count": 0, "unsupported_count": 0, "invalid_request_count": 0},
        "result_summary": {"available_count": 0, "unsupported_count": 0, "provider_error_count": 0, "invalid_request_count": 0, "fixture_only_count": 0},
        "holding": {"assets": [], "summary": _status_summary([])},
        "watching": {"assets": [], "summary": _status_summary([])},
        "by_type": summarize_by_asset_type([]),
        "results": [],
        "warnings": BASE_WARNINGS + [reason],
        "disclaimer": DISCLAIMER,
    }


def build_account_realtime_summary(group: Mapping[str, Any], quote_provider: QuoteProvider | None = None, fund_nav_provider: FundNavProvider | None = None) -> dict[str, Any]:
    """Build account-level quote / NAV summary without mutating the group."""

    group_snapshot = deepcopy(dict(group))
    split = split_assets_for_realtime_summary(group_snapshot)
    if not split["active"]:
        return build_account_market_data_empty_result(group_snapshot, "当前没有 holding / watching 资产可汇总。")
    results = fetch_account_market_data(group_snapshot, quote_provider, fund_nav_provider)
    warnings = list(BASE_WARNINGS)
    if split["holding"] and not split["watching"]:
        warnings.append("当前没有收藏资产可对比。")
    if split["watching"] and not split["holding"]:
        warnings.append("当前没有持有资产可对比。")
    holding_results = [item for item in results if (item.get("asset") or {}).get("status") == "holding"]
    watching_results = [item for item in results if (item.get("asset") or {}).get("status") == "watching"]
    return {
        "account_id": str(group_snapshot.get("account_id") or ""),
        "account_name": str(group_snapshot.get("account_name") or group_snapshot.get("name") or ""),
        "status": _overall_status(results),
        "data_mode": "fixture_only" if any(item.get("fixture_only") for item in results) else "model_only",
        "has_real_market_data": False,
        "asset_counts": split["asset_counts"],
        "request_summary": _request_summary(results),
        "result_summary": summarize_account_market_data(results),
        "holding": {"assets": holding_results, "summary": _status_summary(holding_results)},
        "watching": {"assets": watching_results, "summary": _status_summary(watching_results)},
        "by_type": summarize_by_asset_type(results),
        "results": results,
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }


def validate_account_realtime_summary(result: Mapping[str, Any]) -> bool:
    if result.get("has_real_market_data") is not False:
        return False
    if result.get("status") not in {"available", "partial_available", "empty", "insufficient_data", "provider_error"}:
        return False
    if result.get("data_mode") not in {"fixture_only", "model_only", "mixed_fixture_only"}:
        return False
    for item in result.get("results") or []:
        if item.get("result_kind") not in {"realtime_quote", "fund_nav", "unsupported", "invalid_request"}:
            return False
        if item.get("has_real_market_data") is not False:
            return False
    return True


def render_account_realtime_summary_markdown(result: Mapping[str, Any]) -> str:
    counts = result.get("asset_counts") or {}
    result_summary = result.get("result_summary") or {}
    holding = result.get("holding") or {}
    watching = result.get("watching") or {}

    def line_for(section: Mapping[str, Any], kind: str) -> str:
        summary = section.get("summary") or {}
        if kind == "quote":
            return str(summary.get("quote_available_count", 0))
        if kind == "fund":
            return str(summary.get("fund_nav_available_count", 0))
        return str(summary.get("unsupported_count", 0) + summary.get("invalid_request_count", 0))

    return "\n".join([
        "# 账户行情 / 基金净值汇总 Demo",
        "",
        "## 1. 账户概览",
        f"- 账户：{result.get('account_name') or result.get('account_id') or '-'}",
        f"- active 资产数量：{counts.get('active', 0)}",
        f"- 持有资产数量：{counts.get('holding', 0)}",
        f"- 收藏资产数量：{counts.get('watching', 0)}",
        "",
        "## 2. 持有资产",
        f"- 股票 / ETF / 指数：{line_for(holding, 'quote')}",
        f"- 场外基金：{line_for(holding, 'fund')}",
        f"- 暂不支持：{line_for(holding, 'unsupported')}",
        "",
        "## 3. 收藏资产",
        f"- 股票 / ETF / 指数：{line_for(watching, 'quote')}",
        f"- 场外基金：{line_for(watching, 'fund')}",
        f"- 暂不支持：{line_for(watching, 'unsupported')}",
        "",
        "## 4. 数据状态",
        f"- 可用：{result_summary.get('available_count', 0)}",
        f"- 不支持：{result_summary.get('unsupported_count', 0)}",
        f"- provider_error：{result_summary.get('provider_error_count', 0)}",
        f"- invalid_request：{result_summary.get('invalid_request_count', 0)}",
        "",
        "## 5. 数据说明",
        "- 本阶段为 mock / fixture 数据，不代表真实行情。",
        "- 场外基金不支持真正实时价格，盘中估算仅供观察，最终以基金公司公布净值为准。",
        "- 本结果只做观察，不构成交易建议。",
    ])
