import json

import pytest

from src.kr_market_indicators import (
    build_kr_breadth_input_schema,
    build_kr_breadth_metrics,
    build_kr_market_page_model,
    calculate_kr_average_change_pct,
    calculate_kr_equal_weight_change,
    calculate_kr_median_change_pct,
    calculate_kr_rise_ratio,
    calculate_kr_turnover_change,
    get_kr_computed_indicators,
    get_kr_official_indices,
    render_kr_market_indicator_demo_markdown,
    validate_kr_market_indicator_result,
)
from src.market_index_matrix import build_market_page_model


def _items(page):
    return [item for group in page["groups"] for item in group["items"]]


def _find_item(page, name):
    for item in _items(page):
        if item["name"] == name:
            return item
    raise AssertionError(f"missing item: {name}")


DEMO_ROWS = [
    {"symbol": "DEMOA.KR", "name": "示例韩股A", "market_board": "KOSPI", "change_pct": 1.2},
    {"symbol": "DEMOB.KR", "name": "示例韩股B", "market_board": "KOSDAQ", "change_pct": -0.8},
    {"symbol": "demo_kr_stock_001", "name": "示例韩股A", "market_board": "KOSPI", "change_pct": 0.2},
    {"symbol": "DEMOA.KR", "name": "示例韩股B", "market_board": "KOSDAQ", "change_pct": ""},
    {"symbol": "DEMOB.KR", "name": "示例韩股A", "market_board": "KOSPI", "change_pct": None},
    {"symbol": "demo_kr_stock_001", "name": "示例韩股B", "market_board": "KOSDAQ", "change_pct": "bad"},
]


def test_kr_page_contains_required_groups():
    page = build_kr_market_page_model()
    assert [group["key"] for group in page["groups"]] == ["core_weight", "growth_tech", "market_breadth"]
    assert page["market"] == "kr"
    assert page["has_realtime_data"] is False
    assert page["data_mode"] == "model_only"


@pytest.mark.parametrize("name", ["KOSPI", "KOSPI 200", "KRX 300", "KOSDAQ", "KOSDAQ 150"])
def test_kr_official_indices_are_official_index(name):
    item = _find_item(build_kr_market_page_model(), name)
    assert item["item_type"] == "official_index"
    assert item["is_official"] is True
    assert item["is_computed"] is False


@pytest.mark.parametrize("name", ["韩股中位数涨跌幅", "韩股平均涨跌幅", "韩股上涨家数占比", "韩股全市场等权涨跌", "韩股成交额变化"])
def test_kr_breadth_items_are_non_official_computed_indicators(name):
    item = _find_item(build_kr_market_page_model(), name)
    assert item["item_type"] == "computed_indicator"
    assert item["is_official"] is False
    assert item["is_computed"] is True
    assert "非官方指数" in item["disclaimer"]


def test_kr_index_helpers_split_official_and_computed_items():
    official_names = {item["name"] for item in get_kr_official_indices()}
    computed_names = {item["name"] for item in get_kr_computed_indicators()}
    assert {"KOSPI", "KOSPI 200", "KRX 300", "KOSDAQ", "KOSDAQ 150"} <= official_names
    assert {"韩股中位数涨跌幅", "韩股上涨家数占比", "韩股全市场等权涨跌"} <= computed_names


def test_kr_calculations_ignore_invalid_change_pct_values():
    assert calculate_kr_median_change_pct(DEMO_ROWS) == 0.2
    assert calculate_kr_average_change_pct(DEMO_ROWS) == 0.2
    assert calculate_kr_rise_ratio(DEMO_ROWS) == pytest.approx(2 / 3, rel=1e-4)
    assert calculate_kr_equal_weight_change(DEMO_ROWS) == 0.2


def test_kr_turnover_change_status_and_value():
    assert calculate_kr_turnover_change(current_turnover=100)["status"] == "insufficient_data"
    assert calculate_kr_turnover_change(current_turnover=110, previous_turnover=100) == {
        "status": "available",
        "value": 10.0,
        "unit": "%",
    }


def test_kr_breadth_metrics_have_stable_structured_output():
    result = build_kr_breadth_metrics(DEMO_ROWS)
    assert result["market"] == "kr"
    assert result["status"] == "available"
    assert result["data_mode"] == "computed_from_input"
    assert result["sample_size"] == len(DEMO_ROWS)
    assert result["valid_change_count"] == 3
    assert result["metrics"]["limit_up_down_diff_status"] == "pending_market_rule"
    assert result["metrics"]["turnover_change_status"] == "insufficient_data"
    assert validate_kr_market_indicator_result(result) is True


def test_kr_empty_or_invalid_input_returns_data_insufficient_status():
    empty = build_kr_breadth_metrics([])
    invalid = build_kr_breadth_metrics([{"symbol": "DEMOA.KR", "name": "示例韩股A", "change_pct": ""}])
    assert empty["status"] == "empty"
    assert invalid["status"] == "insufficient_data"
    assert empty["valid_change_count"] == 0
    assert invalid["valid_change_count"] == 0


def test_kr_schema_does_not_enable_limit_up_down_diff():
    schema = build_kr_breadth_input_schema()
    assert schema["market"] == "kr"
    assert "limit_up_down_diff" in schema["unsupported_fields"]


def test_kr_markdown_demo_has_required_sections_and_no_forbidden_actions():
    markdown = render_kr_market_indicator_demo_markdown(build_kr_breadth_metrics(DEMO_ROWS))
    assert "# 韩股指数矩阵与体感指标 Demo" in markdown
    assert "## 1. 权重核心指数" in markdown
    assert "## 2. 成长科技指数" in markdown
    assert "系统计算指标，非官方指数。" in markdown
    for forbidden in ["买入", "卖出", "加仓", "减仓"]:
        assert forbidden not in markdown


def test_kr_outputs_do_not_include_sensitive_or_account_terms():
    text = json.dumps(
        {
            "page": build_kr_market_page_model(),
            "metrics": build_kr_breadth_metrics(DEMO_ROWS),
            "markdown": render_kr_market_indicator_demo_markdown(build_kr_breadth_metrics(DEMO_ROWS)),
        },
        ensure_ascii=False,
    ).lower()
    forbidden_terms = [
        "真实价格",
        "真实成交额",
        "真实金额",
        "成本价",
        "账户资产",
        "webhook",
        "token",
        "api key",
        "api_key",
    ]
    assert all(term not in text for term in forbidden_terms)


def test_p5_l0_kr_page_remains_compatible():
    page = build_market_page_model("kr")
    assert [group["key"] for group in page["groups"]] == ["core_weight", "growth_tech", "market_breadth"]
    assert _find_item(page, "韩股全市场等权涨跌")["item_type"] == "computed_indicator"
