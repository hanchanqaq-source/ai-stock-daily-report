"""Model-only Korean market index matrix and breadth indicator helpers.

This module never fetches market data, reads account configuration, or persists
quote values. All calculations are based only on caller-provided demo rows.
"""

from __future__ import annotations

from copy import deepcopy
from statistics import mean, median
from typing import Any

from src.market_index_matrix import build_market_page_model, get_market_index_matrix, validate_market_index_matrix

KR_COMPUTED_DISCLAIMER = "该指标为系统根据输入韩股涨跌幅计算的体感指标，非官方指数。"
KR_MODEL_DISCLAIMER = "本阶段仅定义韩股指数矩阵和体感指标计算框架，不抓取行情数据。"

_METRIC_DEFS = (
    ("kr_median_change_pct", "韩股中位数涨跌幅", "median_change_pct", "%"),
    ("kr_average_change_pct", "韩股平均涨跌幅", "average_change_pct", "%"),
    ("kr_rise_ratio", "韩股上涨家数占比", "rise_ratio", "ratio"),
    ("kr_equal_weight_change_pct", "韩股全市场等权涨跌", "equal_weight_change_pct", "%"),
    ("kr_turnover_change", "韩股成交额变化", "turnover_change_status", "status"),
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


def get_kr_index_matrix() -> list[dict[str, Any]]:
    return get_market_index_matrix("kr")


def get_kr_official_indices() -> list[dict[str, Any]]:
    return [item for item in get_kr_index_matrix() if item["item_type"] == "official_index"]


def get_kr_computed_indicators() -> list[dict[str, Any]]:
    return [item for item in get_kr_index_matrix() if item["item_type"] == "computed_indicator"]


def build_kr_market_page_model() -> dict[str, Any]:
    page = deepcopy(build_market_page_model("kr"))
    page["disclaimer"] = KR_MODEL_DISCLAIMER
    page["data_mode"] = "model_only"
    page["has_realtime_data"] = False
    validate_market_index_matrix(page["groups"])
    return page


def build_kr_breadth_input_schema() -> dict[str, Any]:
    return {
        "market": "kr",
        "data_mode": "caller_provided_input",
        "required_fields": ["change_pct"],
        "optional_fields": ["symbol", "name", "market_board", "turnover", "previous_turnover"],
        "unsupported_fields": ["limit_up_down_diff"],
        "disclaimer": "本阶段仅定义输入结构，不联网、不抓取行情；韩股不默认计算涨跌停差。",
    }


def calculate_kr_median_change_pct(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(float(median(values)), 4) if values else None


def calculate_kr_average_change_pct(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(float(mean(values)), 4) if values else None


def calculate_kr_rise_ratio(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(sum(1 for value in values if value > 0) / len(values), 4) if values else None


def calculate_kr_equal_weight_change(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    return calculate_kr_average_change_pct(stock_changes)


def calculate_kr_turnover_change(current_turnover: Any = None, previous_turnover: Any = None) -> dict[str, Any]:
    current = _to_number(current_turnover)
    previous = _to_number(previous_turnover)
    if current is None or previous is None or previous == 0:
        return {"status": "insufficient_data", "value": None, "unit": "%"}
    return {"status": "available", "value": round((current - previous) / previous * 100, 4), "unit": "%"}


def _indicator(indicator_id: str, name: str, value: Any, unit: str) -> dict[str, Any]:
    return {
        "id": indicator_id,
        "name": name,
        "value": value,
        "unit": unit,
        "item_type": "computed_indicator",
        "is_computed": True,
        "is_official": False,
        "disclaimer": KR_COMPUTED_DISCLAIMER,
    }


def build_kr_breadth_metrics(stock_rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = stock_rows or []
    valid_count = len(_valid_changes(rows))
    turnover_change = calculate_kr_turnover_change()
    metrics = {
        "median_change_pct": calculate_kr_median_change_pct(rows),
        "average_change_pct": calculate_kr_average_change_pct(rows),
        "rise_ratio": calculate_kr_rise_ratio(rows),
        "equal_weight_change_pct": calculate_kr_equal_weight_change(rows),
        "turnover_change_status": turnover_change["status"],
        "turnover_change_pct": turnover_change["value"],
        "limit_up_down_diff_status": "pending_market_rule",
    }
    result = {
        "market": "kr",
        "status": "available" if valid_count else ("empty" if not rows else "insufficient_data"),
        "data_mode": "computed_from_input",
        "sample_size": len(rows),
        "valid_change_count": valid_count,
        "metrics": metrics,
        "computed_indicators": [_indicator(item_id, name, metrics[key], unit) for item_id, name, key, unit in _METRIC_DEFS],
        "warnings": [] if valid_count else ["有效 change_pct 数据不足，无法计算韩股体感指标。"],
    }
    validate_kr_market_indicator_result(result)
    return result


def validate_kr_market_indicator_result(result: dict[str, Any]) -> bool:
    if result.get("market") != "kr":
        raise ValueError("result market must be kr")
    if result.get("metrics", {}).get("limit_up_down_diff_status") not in {"pending_market_rule", "not_applicable"}:
        raise ValueError("韩股不默认照搬 A 股涨跌停差")
    for item in result.get("computed_indicators", []):
        if item.get("item_type") != "computed_indicator" or item.get("is_official") is not False:
            raise ValueError("韩股体感指标必须是非官方 computed_indicator")
        if "非官方指数" not in item.get("disclaimer", ""):
            raise ValueError("computed_indicator 必须标注非官方指数")
    return True


def render_kr_market_indicator_demo_markdown(result: dict[str, Any]) -> str:
    page = build_kr_market_page_model()
    groups = {group["key"]: group for group in page["groups"]}

    def official_names(key: str) -> str:
        return "\n".join(f"- {item['name']}" for item in groups[key]["items"] if item["item_type"] == "official_index")

    metrics = result.get("metrics", {})
    return "\n".join([
        "# 韩股指数矩阵与体感指标 Demo",
        "",
        "## 1. 权重核心指数",
        official_names("core_weight"),
        "",
        "## 2. 成长科技指数",
        official_names("growth_tech"),
        "",
        "## 3. 市场体感指标",
        "系统计算指标，非官方指数。",
        f"- 韩股中位数涨跌幅：{metrics.get('median_change_pct')}",
        f"- 韩股平均涨跌幅：{metrics.get('average_change_pct')}",
        f"- 韩股上涨家数占比：{metrics.get('rise_ratio')}",
        f"- 韩股全市场等权涨跌：{metrics.get('equal_weight_change_pct')}",
        f"- 韩股成交额变化：{metrics.get('turnover_change_status')}",
        f"- 韩股涨跌停差：{metrics.get('limit_up_down_diff_status')}",
        "",
        "## 4. 数据说明",
        "本阶段仅使用输入样例计算，不联网、不抓取行情。",
        "韩股体感指标不等于官方指数。",
        "韩股体感指标不照搬 A 股涨跌停差逻辑。",
    ])
