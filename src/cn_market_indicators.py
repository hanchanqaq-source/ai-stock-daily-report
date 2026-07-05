"""Model-only A-share index matrix and breadth indicator helpers.

This module never fetches market data, reads account configuration, or persists
quote values. All calculations are based only on caller-provided demo rows.
"""

from __future__ import annotations

from copy import deepcopy
from statistics import mean, median
from typing import Any

from src.market_index_matrix import build_market_page_model, get_market_index_matrix, validate_market_index_matrix

CN_COMPUTED_DISCLAIMER = "该指标为系统根据输入股票涨跌幅计算的体感指标，非官方指数。"
CN_MODEL_DISCLAIMER = "本阶段仅定义A股指数矩阵和体感指标计算框架，不抓取真实行情。"

_METRIC_DEFS = (
    ("cn_median_change_pct", "A股中位数涨跌幅", "median_change_pct", "%"),
    ("cn_average_change_pct", "A股平均涨跌幅", "average_change_pct", "%"),
    ("cn_rise_ratio", "A股上涨家数占比", "rise_ratio", "ratio"),
    ("cn_limit_up_down_diff", "A股涨跌停差", "limit_up_down_diff", "count"),
    ("cn_equal_weight_change_pct", "全A等权涨跌", "equal_weight_change_pct", "%"),
    ("cn_turnover_change", "A股成交额变化", "turnover_change_status", "status"),
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


def get_cn_index_matrix() -> list[dict[str, Any]]:
    return get_market_index_matrix("cn")


def get_cn_official_indices() -> list[dict[str, Any]]:
    return [item for item in get_cn_index_matrix() if item["item_type"] == "official_index"]


def get_cn_computed_indicators() -> list[dict[str, Any]]:
    return [item for item in get_cn_index_matrix() if item["item_type"] == "computed_indicator"]


def build_cn_market_page_model() -> dict[str, Any]:
    page = deepcopy(build_market_page_model("cn"))
    page["disclaimer"] = CN_MODEL_DISCLAIMER
    page["data_mode"] = "model_only"
    page["has_realtime_data"] = False
    validate_market_index_matrix(page["groups"])
    return page


def build_cn_breadth_input_schema() -> dict[str, Any]:
    return {
        "market": "cn",
        "data_mode": "caller_provided_input",
        "required_fields": ["change_pct"],
        "optional_fields": ["code", "name", "turnover", "previous_turnover", "is_limit_up", "is_limit_down"],
        "disclaimer": "本阶段仅定义输入结构，不联网、不抓取真实行情。",
    }


def calculate_cn_median_change_pct(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(float(median(values)), 4) if values else None


def calculate_cn_average_change_pct(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(float(mean(values)), 4) if values else None


def calculate_cn_rise_ratio(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    values = _valid_changes(stock_changes)
    return round(sum(1 for value in values if value > 0) / len(values), 4) if values else None


def calculate_cn_limit_up_down_diff(stock_rows: list[dict[str, Any]] | None) -> int:
    rows = stock_rows or []
    return sum(1 for row in rows if row.get("is_limit_up") is True) - sum(1 for row in rows if row.get("is_limit_down") is True)


def calculate_cn_equal_weight_change(stock_changes: list[Any] | tuple[Any, ...] | None) -> float | None:
    return calculate_cn_average_change_pct(stock_changes)


def _indicator(indicator_id: str, name: str, value: Any, unit: str) -> dict[str, Any]:
    return {
        "id": indicator_id,
        "name": name,
        "value": value,
        "unit": unit,
        "item_type": "computed_indicator",
        "is_computed": True,
        "is_official": False,
        "disclaimer": CN_COMPUTED_DISCLAIMER,
    }


def build_cn_breadth_metrics(stock_rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = stock_rows or []
    changes = _valid_changes(rows)
    valid_count = len(changes)
    limit_up_count = sum(1 for row in rows if row.get("is_limit_up") is True)
    limit_down_count = sum(1 for row in rows if row.get("is_limit_down") is True)
    metrics = {
        "median_change_pct": calculate_cn_median_change_pct(rows),
        "average_change_pct": calculate_cn_average_change_pct(rows),
        "rise_ratio": calculate_cn_rise_ratio(rows),
        "limit_up_count": limit_up_count,
        "limit_down_count": limit_down_count,
        "limit_up_down_diff": limit_up_count - limit_down_count,
        "equal_weight_change_pct": calculate_cn_equal_weight_change(rows),
        "turnover_change_status": "insufficient_data",
    }
    result = {
        "market": "cn",
        "status": "available" if valid_count else ("empty" if not rows else "insufficient_data"),
        "data_mode": "computed_from_input",
        "sample_size": len(rows),
        "valid_change_count": valid_count,
        "metrics": metrics,
        "computed_indicators": [_indicator(item_id, name, metrics[key], unit) for item_id, name, key, unit in _METRIC_DEFS],
        "warnings": [] if valid_count else ["有效 change_pct 数据不足，无法计算涨跌幅体感指标。"],
    }
    validate_cn_market_indicator_result(result)
    return result


def validate_cn_market_indicator_result(result: dict[str, Any]) -> bool:
    if result.get("market") != "cn":
        raise ValueError("result market must be cn")
    for item in result.get("computed_indicators", []):
        if item.get("item_type") != "computed_indicator" or item.get("is_official") is not False:
            raise ValueError("A股体感指标必须是非官方 computed_indicator")
        if "非官方指数" not in item.get("disclaimer", ""):
            raise ValueError("computed_indicator 必须标注非官方指数")
    return True


def render_cn_market_indicator_demo_markdown(result: dict[str, Any]) -> str:
    page = build_cn_market_page_model()
    groups = {group["key"]: group for group in page["groups"]}

    def names(key: str) -> str:
        return "\n".join(f"- {item['name']}" for item in groups[key]["items"])

    metrics = result.get("metrics", {})
    return "\n".join([
        "# A股指数矩阵与体感指标 Demo",
        "",
        "## 1. 权重核心指数",
        names("core_weight"),
        "",
        "## 2. 中小盘指数",
        names("small_mid"),
        "",
        "## 3. 成长科技指数",
        names("growth_tech"),
        "",
        "## 4. 市场体感指标",
        "系统计算指标，非官方指数。",
        f"- A股中位数涨跌幅：{metrics.get('median_change_pct')}",
        f"- A股平均涨跌幅：{metrics.get('average_change_pct')}",
        f"- A股上涨家数占比：{metrics.get('rise_ratio')}",
        f"- A股涨跌停差：{metrics.get('limit_up_down_diff')}",
        f"- 全A等权涨跌：{metrics.get('equal_weight_change_pct')}",
        f"- A股成交额变化：{metrics.get('turnover_change_status')}",
        "",
        "## 5. 数据说明",
        "本阶段仅使用输入样例计算，不联网、不抓取真实行情。",
    ])
