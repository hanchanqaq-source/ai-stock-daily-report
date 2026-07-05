"""Model-only global market index matrix and page switching helpers.

This module defines stable page structures for global market index dashboards.
It does not fetch quote data, read user configuration, persist market values, or
connect to external data providers.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DATA_MODE = "model_only"
DEFAULT_MARKET = "global"
MARKET_ORDER = ("global", "cn", "hk", "us", "kr")
CHILD_MARKETS = ("cn", "hk", "us", "kr")
MODEL_ONLY_DISCLAIMER = "本阶段仅定义指数矩阵，不抓取真实行情。"
COMPUTED_DISCLAIMER = "该指标为系统后续根据市场数据计算的体感指标，非官方指数。"

_MARKET_LABELS = {
    "global": "全球总览",
    "cn": "A股",
    "hk": "港股",
    "us": "美股",
    "kr": "韩股",
    "unknown": "未知市场",
}

_GROUP_LABELS = {
    "core_weight": "权重核心",
    "growth_tech": "成长科技",
    "small_mid": "中小盘",
    "broad_market": "大中小盘 / 覆盖",
    "market_breadth": "市场体感",
}

_MARKET_GROUP_ORDER = {
    "cn": ("core_weight", "small_mid", "growth_tech", "market_breadth"),
    "hk": ("core_weight", "growth_tech", "broad_market", "market_breadth"),
    "us": ("core_weight", "growth_tech", "small_mid", "market_breadth"),
    "kr": ("core_weight", "growth_tech", "market_breadth"),
}

# Tuples are: item_id, name, market, category, item_type, description.
_INDEX_ITEMS = (
    ("cn_sse_composite", "上证指数", "cn", "core_weight", "official_index", "用于观察A股上海市场整体表现。"),
    ("cn_szse_component", "深证成指", "cn", "core_weight", "official_index", "用于观察A股深圳市场核心成分表现。"),
    ("cn_csi_300", "沪深300", "cn", "core_weight", "official_index", "用于观察A股大盘核心资产表现。"),
    ("cn_csi_a500", "中证A500", "cn", "core_weight", "official_index", "用于观察A股代表性宽基资产表现。"),
    ("cn_sse_50", "上证50", "cn", "core_weight", "official_index", "用于观察A股超大盘权重资产表现。"),
    ("cn_csi_500", "中证500", "cn", "small_mid", "official_index", "用于观察A股中盘资产表现。"),
    ("cn_csi_1000", "中证1000", "cn", "small_mid", "official_index", "用于观察A股小盘资产表现。"),
    ("cn_csi_2000", "中证2000", "cn", "small_mid", "official_index", "用于观察A股更广泛小微盘资产表现。"),
    ("cn_cni_2000", "国证2000", "cn", "small_mid", "official_index", "用于观察A股国证体系小盘资产表现。"),
    ("cn_chinext", "创业板指", "cn", "growth_tech", "official_index", "用于观察A股创业板成长资产表现。"),
    ("cn_chinext_50", "创业板50", "cn", "growth_tech", "official_index", "用于观察创业板代表性成长资产表现。"),
    ("cn_star_50", "科创50", "cn", "growth_tech", "official_index", "用于观察A股科创板核心科技资产表现。"),
    ("cn_star_100", "科创100", "cn", "growth_tech", "official_index", "用于观察科创板更广覆盖科技资产表现。"),
    ("cn_bse_50", "北证50", "cn", "growth_tech", "official_index", "用于观察北交所代表性资产表现。"),
    ("cn_median_change_pct", "A股中位数涨跌幅", "cn", "market_breadth", "computed_indicator", "用于观察普通股票的市场体感，非官方指数。"),
    ("cn_average_change_pct", "A股平均涨跌幅", "cn", "market_breadth", "computed_indicator", "用于观察A股整体平均涨跌体感，非官方指数。"),
    ("cn_advancing_ratio", "A股上涨家数占比", "cn", "market_breadth", "computed_indicator", "用于观察A股上涨股票覆盖面，非官方指数。"),
    ("cn_limit_up_down_spread", "A股涨跌停差", "cn", "market_breadth", "computed_indicator", "用于观察A股涨停与跌停结构差异，非官方指数。"),
    ("cn_equal_weight_change", "全A等权涨跌", "cn", "market_breadth", "computed_indicator", "用于观察全A等权口径的市场体感，非官方指数。"),
    ("cn_turnover_change", "A股成交额变化", "cn", "market_breadth", "computed_indicator", "用于观察A股成交活跃度变化，非官方指数。"),
    ("hk_hsi", "恒生指数", "hk", "core_weight", "official_index", "用于观察港股核心权重资产表现。"),
    ("hk_hscei", "恒生中国企业指数", "hk", "core_weight", "official_index", "用于观察港股中国企业权重资产表现。"),
    ("hk_hsci", "恒生综合指数", "hk", "core_weight", "official_index", "用于观察港股较广市场表现。"),
    ("hk_hstech", "恒生科技指数", "hk", "growth_tech", "official_index", "用于观察港股科技成长资产表现。"),
    ("hk_large_cap", "恒生大型股指数", "hk", "broad_market", "official_index", "用于观察港股大型股覆盖表现，不包含真实点位。"),
    ("hk_mid_cap", "恒生中型股指数", "hk", "broad_market", "official_index", "用于观察港股中型股覆盖表现，不包含真实点位。"),
    ("hk_small_cap", "恒生小型股指数", "hk", "broad_market", "official_index", "用于观察港股小型股覆盖表现，不包含真实点位。"),
    ("hk_median_change_pct", "港股中位数涨跌幅", "hk", "market_breadth", "computed_indicator", "用于观察港股普通股票市场体感，非官方指数。"),
    ("hk_average_change_pct", "港股平均涨跌幅", "hk", "market_breadth", "computed_indicator", "用于观察港股整体平均涨跌体感，非官方指数。"),
    ("hk_rise_ratio", "港股上涨家数占比", "hk", "market_breadth", "computed_indicator", "用于观察港股上涨股票覆盖面，非官方指数。"),
    ("hk_equal_weight_change_pct", "港股全市场等权涨跌", "hk", "market_breadth", "computed_indicator", "用于观察港股等权口径市场体感，非官方指数。"),
    ("hk_turnover_change", "港股成交额变化", "hk", "market_breadth", "computed_indicator", "用于观察港股成交活跃度变化，非官方指数。"),
    ("us_sp_500", "标普500", "us", "core_weight", "official_index", "用于观察美股大盘核心资产表现。"),
    ("us_djia", "道琼斯工业平均指数", "us", "core_weight", "official_index", "用于观察美股蓝筹工业代表资产表现。"),
    ("us_nasdaq_composite", "纳斯达克综合指数", "us", "core_weight", "official_index", "用于观察纳斯达克市场整体表现。"),
    ("us_nasdaq_100", "纳斯达克100", "us", "growth_tech", "official_index", "用于观察美股大型科技成长资产表现。"),
    ("us_sox", "费城半导体指数", "us", "growth_tech", "official_index", "用于观察美股半导体产业链代表资产表现。"),
    ("us_russell_2000", "罗素2000", "us", "small_mid", "official_index", "用于观察美股小盘资产表现。"),
    ("us_sp_400", "标普400", "us", "small_mid", "official_index", "用于观察美股中盘资产表现。"),
    ("us_sp_600", "标普600", "us", "small_mid", "official_index", "用于观察美股小盘代表资产表现。"),
    ("us_sp_500_equal_weight", "标普500等权指数", "us", "market_breadth", "official_index", "用于观察标普500等权口径市场表现。"),
    ("us_nyse_advancing_ratio", "NYSE上涨家数占比", "us", "market_breadth", "computed_indicator", "用于观察NYSE上涨股票覆盖面，非官方指数。"),
    ("us_nasdaq_advancing_ratio", "Nasdaq上涨家数占比", "us", "market_breadth", "computed_indicator", "用于观察Nasdaq上涨股票覆盖面，非官方指数。"),
    ("us_median_change_pct", "美股中位数涨跌幅", "us", "market_breadth", "computed_indicator", "用于观察美股普通股票市场体感，非官方指数。"),
    ("us_average_change_pct", "美股平均涨跌幅", "us", "market_breadth", "computed_indicator", "用于观察美股整体平均涨跌体感，非官方指数。"),
    ("kr_kospi", "KOSPI", "kr", "core_weight", "official_index", "用于观察韩股主板市场表现。"),
    ("kr_kospi_200", "KOSPI 200", "kr", "core_weight", "official_index", "用于观察韩股核心权重资产表现。"),
    ("kr_krx_300", "KRX 300", "kr", "core_weight", "official_index", "用于观察韩股更广代表性资产表现。"),
    ("kr_kosdaq", "KOSDAQ", "kr", "growth_tech", "official_index", "用于观察韩股成长市场表现。"),
    ("kr_kosdaq_150", "KOSDAQ 150", "kr", "growth_tech", "official_index", "用于观察韩股成长市场代表资产表现。"),
    ("kr_median_change_pct", "韩股中位数涨跌幅", "kr", "market_breadth", "computed_indicator", "用于观察韩股普通股票市场体感，非官方指数。"),
    ("kr_advancing_ratio", "韩股上涨家数占比", "kr", "market_breadth", "computed_indicator", "用于观察韩股上涨股票覆盖面，非官方指数。"),
    ("kr_average_change_pct", "韩股平均涨跌幅", "kr", "market_breadth", "computed_indicator", "用于观察韩股整体平均涨跌体感，非官方指数。"),
    ("kr_turnover_change", "韩股成交额变化", "kr", "market_breadth", "computed_indicator", "用于观察韩股成交活跃度变化，非官方指数。"),
)


def get_default_market() -> str:
    return DEFAULT_MARKET


def get_supported_markets() -> list[str]:
    return list(MARKET_ORDER)


def get_market_tabs() -> list[dict[str, Any]]:
    return [{"key": key, "label": _MARKET_LABELS[key], "enabled": True} for key in MARKET_ORDER]


def _quote_capability(item_type: str) -> dict[str, Any]:
    if item_type == "computed_indicator":
        return {"price_mode": "computed_metric", "realtime_supported": False, "needs_data_source": True}
    return {"price_mode": "index_quote", "realtime_supported": True, "needs_data_source": True}


def _build_item(item_id: str, name: str, market: str, category: str, item_type: str, description: str) -> dict[str, Any]:
    computed = item_type == "computed_indicator"
    return {
        "id": item_id,
        "name": name,
        "market": market,
        "category": category,
        "item_type": item_type,
        "display_group": _GROUP_LABELS[category],
        "source_status": "computed_later" if computed else "pending_data_source",
        "quote_capability": _quote_capability(item_type),
        "description": description,
        "is_computed": computed,
        "is_official": not computed,
        "disclaimer": COMPUTED_DISCLAIMER if computed else MODEL_ONLY_DISCLAIMER,
    }


def get_market_index_matrix(market: str) -> list[dict[str, Any]]:
    if market not in CHILD_MARKETS:
        return []
    return [_build_item(*item) for item in _INDEX_ITEMS if item[2] == market]


def build_market_index_groups(market: str) -> list[dict[str, Any]]:
    matrix = get_market_index_matrix(market)
    groups = []
    for key in _MARKET_GROUP_ORDER.get(market, ()):
        groups.append({
            "key": key,
            "label": _GROUP_LABELS[key],
            "items": [item for item in matrix if item["category"] == key],
        })
    return groups


def get_global_market_overview_model() -> dict[str, Any]:
    return {
        "market": "global",
        "label": _MARKET_LABELS["global"],
        "default_child_markets": list(CHILD_MARKETS),
        "sections": [
            {"key": "market_overview", "label": "市场概览", "markets": list(CHILD_MARKETS)},
            {"key": "risk_watch", "label": "风险观察", "description": "后续用于展示各市场风险雷达。"},
            {"key": "breadth_watch", "label": "体感观察", "description": "后续用于展示各市场上涨家数、中位数涨跌等体感指标。"},
        ],
        "has_realtime_data": False,
        "data_mode": DATA_MODE,
        "disclaimer": "本阶段仅定义全球市场页面结构，不抓取真实行情。",
    }


def build_market_page_model(market: str) -> dict[str, Any]:
    if market == "global":
        return get_global_market_overview_model()
    if market not in CHILD_MARKETS:
        return {
            "market": "unknown",
            "label": _MARKET_LABELS["unknown"],
            "status": "unavailable",
            "groups": [],
            "has_realtime_data": False,
            "data_mode": DATA_MODE,
            "disclaimer": "未知市场默认不展示指数矩阵。",
        }
    page = {
        "market": market,
        "label": _MARKET_LABELS[market],
        "status": "available",
        "groups": build_market_index_groups(market),
        "has_realtime_data": False,
        "data_mode": DATA_MODE,
        "disclaimer": MODEL_ONLY_DISCLAIMER,
    }
    validate_market_index_matrix(page["groups"])
    return page


def build_market_index_dashboard_model() -> dict[str, Any]:
    pages = {market: build_market_page_model(market) for market in MARKET_ORDER}
    return {
        "status": "available",
        "default_market": DEFAULT_MARKET,
        "supported_markets": get_supported_markets(),
        "tabs": get_market_tabs(),
        "pages": pages,
        "data_mode": DATA_MODE,
        "has_realtime_data": False,
        "warnings": ["本阶段仅定义指数矩阵和页面切换模型，不抓取真实行情。"],
    }


def is_official_index(item: dict[str, Any]) -> bool:
    return item.get("item_type") == "official_index" and item.get("is_official") is True and item.get("is_computed") is False


def is_computed_indicator(item: dict[str, Any]) -> bool:
    return item.get("item_type") == "computed_indicator" and item.get("is_computed") is True and item.get("is_official") is False


def validate_market_index_matrix(matrix: list[dict[str, Any]]) -> bool:
    for group in matrix:
        if group.get("key") not in _GROUP_LABELS:
            raise ValueError("unknown market index group")
        for item in group.get("items", []):
            if item.get("source_status") == "verified":
                raise ValueError("model-only matrix must not mark sources as verified")
            if is_computed_indicator(item) and "非官方指数" not in item.get("disclaimer", ""):
                raise ValueError("computed_indicator must include a non-official disclaimer")
            if item.get("item_type") not in {"official_index", "computed_indicator"}:
                raise ValueError("unknown market index item_type")
    return True


def get_next_market_steps() -> list[dict[str, str]]:
    return deepcopy([
        {"key": "P5-L1", "description": "A股指数矩阵 + 中位数 / 体感指标"},
        {"key": "P5-L2", "description": "港股指数矩阵 + 港股体感指标"},
        {"key": "P5-L3", "description": "美股指数矩阵 + 等权 / 广度 / 体感指标"},
        {"key": "P5-L4", "description": "韩股指数矩阵 + 韩股体感指标"},
        {"key": "P5-L5", "description": "股票 / ETF 实时涨跌抓取框架"},
        {"key": "Web-P14", "description": "全球市场指数看板"},
    ])
