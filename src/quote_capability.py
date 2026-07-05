"""Public-safe quote capability helpers for unified assets.

This module only marks which quote display mode an asset type can theoretically
use. It never fetches market data, reads user configuration, stores prices, or
connects to external quote providers.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from src.asset_model import AssetModelError, normalize_asset_type, normalize_market, scan_asset_for_sensitive_values

STOCK_REALTIME_MARKETS = frozenset({"CN", "HK", "US", "JP", "KR"})
PRICE_MODES = (
    "realtime_quote",
    "exchange_realtime_quote",
    "index_quote",
    "daily_nav",
    "estimated_nav",
    "estimated_nav_or_daily_nav",
    "unsupported",
    "unknown",
)

_CAPABILITY_RULES: dict[str, dict[str, Any]] = {
    "stock": {
        "realtime_supported": True,
        "exchange_quote_supported": True,
        "daily_nav_supported": False,
        "intraday_estimate_supported": False,
        "price_mode": "realtime_quote",
        "display_label": "实时 / 接近实时涨跌",
        "data_mode_note": "股票行情可展示交易所实时或接近实时行情，具体延迟以后由数据源决定。",
        "needs_data_source": True,
        "disclaimer": "行情数据以后需要接入可查证数据源，当前仅为能力标记。",
    },
    "etf": {
        "realtime_supported": True,
        "exchange_quote_supported": True,
        "daily_nav_supported": False,
        "intraday_estimate_supported": False,
        "price_mode": "exchange_realtime_quote",
        "display_label": "交易所行情",
        "data_mode_note": "ETF / 场内基金可展示交易所实时或接近实时行情，具体延迟以后由数据源决定。",
        "needs_data_source": True,
        "disclaimer": "行情数据以后需要接入可查证数据源，当前仅为能力标记。",
    },
    "index": {
        "realtime_supported": True,
        "exchange_quote_supported": False,
        "daily_nav_supported": False,
        "intraday_estimate_supported": False,
        "price_mode": "index_quote",
        "display_label": "指数行情",
        "data_mode_note": "指数可展示行情点位与涨跌幅，具体延迟以后由数据源决定。",
        "needs_data_source": True,
        "disclaimer": "指数行情以后需要接入可查证数据源，当前仅为能力标记。",
    },
    "fund": {
        "realtime_supported": False,
        "exchange_quote_supported": False,
        "daily_nav_supported": True,
        "intraday_estimate_supported": True,
        "price_mode": "estimated_nav_or_daily_nav",
        "display_label": "净值 / 估算净值",
        "data_mode_note": "场外基金不支持真正实时涨跌，盘中数据只能作为估算，最终以基金公司公布净值为准。",
        "needs_data_source": True,
        "disclaimer": "不能把场外基金估算涨跌写成实时涨跌。",
    },
    "company": {
        "realtime_supported": False,
        "exchange_quote_supported": False,
        "daily_nav_supported": False,
        "intraday_estimate_supported": False,
        "price_mode": "unsupported",
        "display_label": "暂不展示行情",
        "data_mode_note": "企业本身不直接展示行情；如有股票代码，后续应通过关联股票资产展示行情。",
        "needs_data_source": False,
        "disclaimer": "当前仅标记企业资产能力，本阶段不做企业股票关联。",
    },
    "industry": {
        "realtime_supported": False,
        "exchange_quote_supported": False,
        "daily_nav_supported": False,
        "intraday_estimate_supported": False,
        "price_mode": "unsupported",
        "display_label": "暂不展示行情",
        "data_mode_note": "行业资产暂不直接展示行情；后续可通过行业指数补充。",
        "needs_data_source": False,
        "disclaimer": "当前仅为能力标记，本阶段不接入行业指数。",
    },
    "theme": {
        "realtime_supported": False,
        "exchange_quote_supported": False,
        "daily_nav_supported": False,
        "intraday_estimate_supported": False,
        "price_mode": "unsupported",
        "display_label": "暂不展示行情",
        "data_mode_note": "主题资产暂不直接展示行情；后续可通过概念指数补充。",
        "needs_data_source": False,
        "disclaimer": "当前仅为能力标记，本阶段不接入概念指数。",
    },
}
_UNKNOWN_CAPABILITY = {
    "realtime_supported": False,
    "exchange_quote_supported": False,
    "daily_nav_supported": False,
    "intraday_estimate_supported": False,
    "price_mode": "unknown",
    "display_label": "暂不展示行情",
    "data_mode_note": "资产类型或市场未确认，暂不展示实时涨跌。",
    "needs_data_source": False,
    "disclaimer": "请先确认资产类型和市场。",
}


def get_quote_capability_for_type(asset_type: Any, market: Any = None) -> dict[str, Any]:
    """Return quote capability by normalized asset type and market."""

    normalized_type = normalize_asset_type(asset_type)
    normalized_market = normalize_market(market)
    if normalized_type == "stock" and normalized_market not in STOCK_REALTIME_MARKETS:
        capability = dict(_UNKNOWN_CAPABILITY)
        capability["price_mode"] = "unknown" if normalized_market == "unknown" else "unsupported"
        capability["data_mode_note"] = "股票市场未确认或暂不在实时行情能力范围内，暂不展示实时涨跌。"
        capability["disclaimer"] = "请先确认股票市场；当前仅为能力标记。"
        return capability
    return dict(_CAPABILITY_RULES.get(normalized_type, _UNKNOWN_CAPABILITY))


def get_quote_capability(asset: dict[str, Any]) -> dict[str, Any]:
    """Return only the nested quote capability for an asset object."""

    return build_quote_capability(asset)["quote_capability"]


def build_quote_capability(asset: dict[str, Any]) -> dict[str, Any]:
    """Build a public-safe quote capability payload for one asset."""

    if not isinstance(asset, dict):
        raise AssetModelError("asset must be an object.")
    findings = scan_asset_for_sensitive_values(asset)
    if findings:
        raise AssetModelError("Sensitive values are not allowed in quote capability: " + "; ".join(findings))

    asset_type = normalize_asset_type(asset.get("type", "unknown"))
    market = normalize_market(asset.get("market", "unknown"))
    return {
        "asset_id": asset.get("asset_id", ""),
        "code": asset.get("code", "") or "",
        "type": asset_type if asset_type in _CAPABILITY_RULES or asset_type == "unknown" else "unknown",
        "market": market,
        "quote_capability": get_quote_capability_for_type(asset_type, market),
    }


def supports_realtime_quote(asset: dict[str, Any]) -> bool:
    return bool(get_quote_capability(asset)["realtime_supported"])


def supports_exchange_quote(asset: dict[str, Any]) -> bool:
    return bool(get_quote_capability(asset)["exchange_quote_supported"])


def supports_daily_nav(asset: dict[str, Any]) -> bool:
    return bool(get_quote_capability(asset)["daily_nav_supported"])


def supports_intraday_estimate(asset: dict[str, Any]) -> bool:
    return bool(get_quote_capability(asset)["intraday_estimate_supported"])


def get_price_mode(asset: dict[str, Any]) -> str:
    return str(get_quote_capability(asset)["price_mode"])


def get_quote_display_label(asset: dict[str, Any]) -> str:
    return str(get_quote_capability(asset)["display_label"])


def get_quote_disclaimer(asset: dict[str, Any]) -> str:
    return str(get_quote_capability(asset)["disclaimer"])


def build_quote_capability_summary(assets: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize quote capabilities without reading or fetching quote data."""

    if not isinstance(assets, list):
        raise AssetModelError("assets must be a list.")
    capabilities = [get_quote_capability(asset) for asset in assets]
    by_price_mode = Counter(capability["price_mode"] for capability in capabilities)
    return {
        "total": len(capabilities),
        "realtime_supported_count": sum(1 for item in capabilities if item["realtime_supported"]),
        "exchange_quote_supported_count": sum(1 for item in capabilities if item["exchange_quote_supported"]),
        "daily_nav_supported_count": sum(1 for item in capabilities if item["daily_nav_supported"]),
        "intraday_estimate_supported_count": sum(1 for item in capabilities if item["intraday_estimate_supported"]),
        "unsupported_count": sum(1 for item in capabilities if item["price_mode"] in {"unsupported", "unknown"}),
        "by_price_mode": dict(by_price_mode),
        "warnings": [],
    }
