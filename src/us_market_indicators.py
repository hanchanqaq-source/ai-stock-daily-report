"""Model-only U.S. market index matrix and breadth indicator helpers.

This module never fetches market data, reads account configuration, or persists
quote values. All calculations are based only on caller-provided demo rows.
"""

from __future__ import annotations

from copy import deepcopy
from statistics import mean, median
from typing import Any

from src.market_index_matrix import build_market_page_model, get_market_index_matrix, validate_market_index_matrix

US_COMPUTED_DISCLAIMER = "该指标为系统根据输入美股涨跌幅计算的体感指标，非官方指数。"
US_MODEL_DISCLAIMER = "本阶段仅定义美股指数矩阵和体感指标计算框架，不抓取真实行情。"

_METRIC_DEFS = (
    ("us_median_change_pct", "美股中位数涨跌幅", "median_change_pct", "%"),
    ("us_average_change_pct", "美股平均涨跌幅", "average_change_pct", "%"),
    ("us_rise_ratio", "美股上涨家数占比", "rise_ratio", "ratio"),
    ("us_equal_weight_change_pct", "美股全市场等权涨跌", "equal_weight_change_pct", "%"),
    ("us_nyse_advancing_ratio", "NYSE上涨家数占比", "nyse_rise_ratio", "ratio"),
    ("us_nasdaq_advancing_ratio", "Nasdaq上涨家数占比", "nasdaq_rise_ratio", "ratio"),
)


def _to_number(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _valid_changes(stock_changes: list[Any] | tuple[Any, ...] | None) -> list[float]:
    if not stock_changes:
        return []
    values: list[float] = []
    for item in stock_changes:
        value = item.get("change_pct") if isinstance(item, dict) else item
        number = _to_number(value)
        if number is not None:
            values.append(number)
    return values


def get_us_index_matrix() -> list[dict[str, Any]]:
    return get_market_index_matrix("us")


def get_us_official_indices() -> list[dict[str, Any]]:
    return [item for item in get_us_index_matrix() if item["item_type"] == "official_index"]


def get_us_computed_indicators() -> list[dict[str, Any]]:
    return [item for item in get_us_index_matrix() if item["item_type"] == "computed_indicator"]


def build_us_market_page_model() -> dict[str, Any]:
    page = deepcopy(build_market_page_model("us"))
    page["disclaimer"] = US_MODEL_DISCLAIMER
    page["data_mode"] = "model_only"
    page["has_realtime_data"] = False
    for group in page["groups"]:
        if group["key"] == "growth_tech":
            group["label"] = "科技成长"
        if group["key"] == "market_breadth":
            group["key"] = "breadth"
            group["label"] = "等权 / 广度"
            for item in group["items"]:
                item["category"] = "breadth"
                item["display_group"] = "等权 / 广度"
    # Validate the source P5-L0-compatible groups before the local display-key remap.
    validate_market_index_matrix(build_market_page_model("us")["groups"])
    return page


def build_us_breadth_input_schema() -> dict[str, Any]:
    return {
        "market": "us",
        "data_mode": "caller_provided_input",
        "required_fields": ["change_pct"],
        "optional_fields": ["symbol", "name", "exchange", "turnover"],
        "unsupported_fields": ["limit_up_down_diff"],
        "disclaimer": "本阶段仅定义输入结构，不联网、不抓取真实行情；美股不默认计算涨跌停差。",
    }


def calculate_us_median_change_pct(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(float(median(values)), 4) if values else None


def calculate_us_average_change_pct(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(float(mean(values)), 4) if values else None


def calculate_us_rise_ratio(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(sum(1 for value in values if value > 0) / len(values), 4) if values else None


def calculate_us_equal_weight_change(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    return calculate_us_average_change_pct(stock_changes)


def calculate_us_exchange_rise_ratio(stock_rows: list[dict[str, Any]] | None, exchange: str) -> dict[str, Any]:
    target = (exchange or "").strip().upper()
    rows = stock_rows or []
    matched = []
    for row in rows:
        row_exchange = str(row.get("exchange", "")).strip().upper()
        if row_exchange == target and _to_number(row.get("change_pct")) is not None:
            matched.append(row)
    if not matched:
        return {"status": "insufficient_data", "value": None, "valid_change_count": 0}
    value = calculate_us_rise_ratio(matched)
    return {"status": "available", "value": value, "valid_change_count": len(matched)}


def _indicator(indicator_id: str, name: str, value: Any, unit: str) -> dict[str, Any]:
    return {
        "id": indicator_id,
        "name": name,
        "value": value,
        "unit": unit,
        "item_type": "computed_indicator",
        "is_computed": True,
        "is_official": False,
        "disclaimer": US_COMPUTED_DISCLAIMER,
    }


def build_us_breadth_metrics(stock_rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = stock_rows or []
    valid_count = len(_valid_changes(rows))
    nyse = calculate_us_exchange_rise_ratio(rows, "NYSE")
    nasdaq = calculate_us_exchange_rise_ratio(rows, "NASDAQ")
    metrics = {
        "median_change_pct": calculate_us_median_change_pct(rows),
        "average_change_pct": calculate_us_average_change_pct(rows),
        "rise_ratio": calculate_us_rise_ratio(rows),
        "equal_weight_change_pct": calculate_us_equal_weight_change(rows),
        "nyse_rise_ratio": nyse["value"],
        "nyse_rise_ratio_status": nyse["status"],
        "nasdaq_rise_ratio": nasdaq["value"],
        "nasdaq_rise_ratio_status": nasdaq["status"],
        "limit_up_down_diff_status": "not_applicable",
    }
    result = {
        "market": "us",
        "status": "available" if valid_count else ("empty" if not rows else "insufficient_data"),
        "data_mode": "computed_from_input",
        "sample_size": len(rows),
        "valid_change_count": valid_count,
        "metrics": metrics,
        "computed_indicators": [_indicator(item_id, name, metrics[key], unit) for item_id, name, key, unit in _METRIC_DEFS],
        "warnings": [] if valid_count else ["有效 change_pct 数据不足，无法计算美股广度 / 体感指标。"],
    }
    validate_us_market_indicator_result(result)
    return result


def validate_us_market_indicator_result(result: dict[str, Any]) -> bool:
    if result.get("market") != "us":
        raise ValueError("result market must be us")
    if result.get("metrics", {}).get("limit_up_down_diff_status") != "not_applicable":
        raise ValueError("美股不默认计算涨跌停差")
    for item in result.get("computed_indicators", []):
        if item.get("item_type") != "computed_indicator" or item.get("is_official") is not False:
            raise ValueError("美股体感指标必须是非官方 computed_indicator")
        if "非官方指数" not in item.get("disclaimer", ""):
            raise ValueError("computed_indicator 必须标注非官方指数")
    return True


def render_us_market_indicator_demo_markdown(result: dict[str, Any]) -> str:
    page = build_us_market_page_model()
    groups = {group["key"]: group for group in page["groups"]}

    def official_names(key: str) -> str:
        return "\n".join(f"- {item['name']}" for item in groups[key]["items"] if item["item_type"] == "official_index")

    metrics = result.get("metrics", {})
    return "\n".join([
        "# 美股指数矩阵与广度指标 Demo",
        "",
        "## 1. 权重核心指数",
        official_names("core_weight"),
        "",
        "## 2. 科技成长指数",
        official_names("growth_tech"),
        "",
        "## 3. 中小盘指数",
        official_names("small_mid"),
        "",
        "## 4. 等权 / 广度指标",
        "系统计算指标，非官方指数。",
        f"- 美股中位数涨跌幅：{metrics.get('median_change_pct')}",
        f"- 美股平均涨跌幅：{metrics.get('average_change_pct')}",
        f"- 美股上涨家数占比：{metrics.get('rise_ratio')}",
        f"- 美股全市场等权涨跌：{metrics.get('equal_weight_change_pct')}",
        f"- NYSE上涨家数占比：{metrics.get('nyse_rise_ratio')}",
        f"- Nasdaq上涨家数占比：{metrics.get('nasdaq_rise_ratio')}",
        f"- 美股涨跌停差：{metrics.get('limit_up_down_diff_status')}",
        "",
        "## 5. 数据说明",
        "本阶段仅使用输入样例计算，不联网、不抓取真实行情。",
        "美股体感指标不等于官方指数。",
        "美股不照搬 A 股涨跌停差逻辑。",
    ])
