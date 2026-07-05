import json

from src.market_index_matrix import build_market_page_model
from src.us_market_indicators import (
    build_us_breadth_input_schema,
    build_us_breadth_metrics,
    build_us_market_page_model,
    calculate_us_average_change_pct,
    calculate_us_equal_weight_change,
    calculate_us_exchange_rise_ratio,
    calculate_us_median_change_pct,
    calculate_us_rise_ratio,
    get_us_computed_indicators,
    get_us_official_indices,
    render_us_market_indicator_demo_markdown,
)


def _items(page):
    return [item for group in page.get("groups", []) for item in group.get("items", [])]


def _find_item(page, name):
    for item in _items(page):
        if item["name"] == name:
            return item
    raise AssertionError(f"missing item: {name}")


def demo_rows():
    return [
        {"symbol": "DEMOA", "name": "示例美股A", "exchange": "NYSE", "change_pct": 1.2},
        {"symbol": "DEMOB", "name": "示例美股B", "exchange": "NASDAQ", "change_pct": -0.8},
        {"symbol": "demo_us_stock_001", "name": "示例美股A", "exchange": "Nasdaq", "change_pct": 0.2},
        {"symbol": "DEMOA", "name": "示例美股B", "exchange": "NYSE", "change_pct": ""},
        {"symbol": "DEMOB", "name": "示例美股A", "exchange": "NASDAQ", "change_pct": None},
        {"symbol": "demo_us_stock_001", "name": "示例美股B", "exchange": "NYSE", "change_pct": "bad"},
    ]


def test_us_page_contains_required_groups():
    page = build_us_market_page_model()
    assert [group["key"] for group in page["groups"]] == ["core_weight", "growth_tech", "small_mid", "breadth"]
    assert page["has_realtime_data"] is False
    assert page["data_mode"] == "model_only"


def test_us_official_indices_and_computed_indicators_are_classified():
    page = build_us_market_page_model()
    for name in [
        "标普500",
        "道琼斯工业平均指数",
        "纳斯达克综合指数",
        "纳斯达克100",
        "费城半导体指数",
        "罗素2000",
        "标普400",
        "标普600",
        "标普500等权指数",
    ]:
        item = _find_item(page, name)
        assert item["item_type"] == "official_index"
        assert item["is_official"] is True
        assert item["is_computed"] is False

    for name in ["美股中位数涨跌幅", "NYSE上涨家数占比", "Nasdaq上涨家数占比", "美股全市场等权涨跌"]:
        item = _find_item(page, name)
        assert item["item_type"] == "computed_indicator"
        assert item["is_computed"] is True
        assert item["is_official"] is False
        assert "非官方指数" in item["disclaimer"]


def test_us_matrix_accessor_helpers_split_official_and_computed_items():
    assert all(item["item_type"] == "official_index" for item in get_us_official_indices())
    computed = get_us_computed_indicators()
    assert all(item["item_type"] == "computed_indicator" for item in computed)
    assert any(item["name"] == "美股全市场等权涨跌" for item in computed)


def test_us_breadth_input_schema_is_model_only():
    schema = build_us_breadth_input_schema()
    assert schema["market"] == "us"
    assert "limit_up_down_diff" in schema["unsupported_fields"]
    assert "不联网" in schema["disclaimer"]


def test_us_basic_metric_calculations_ignore_invalid_values():
    rows = demo_rows()
    assert calculate_us_median_change_pct(rows) == 0.2
    assert calculate_us_average_change_pct(rows) == 0.2
    assert calculate_us_rise_ratio(rows) == 0.6667
    assert calculate_us_equal_weight_change(rows) == 0.2


def test_us_exchange_rise_ratio_handles_nyse_and_nasdaq_and_missing_samples():
    rows = demo_rows()
    assert calculate_us_exchange_rise_ratio(rows, "NYSE") == {"status": "available", "value": 1.0, "valid_change_count": 1}
    assert calculate_us_exchange_rise_ratio(rows, "NASDAQ") == {"status": "available", "value": 0.5, "valid_change_count": 2}
    assert calculate_us_exchange_rise_ratio(rows, "AMEX")["status"] == "insufficient_data"


def test_us_breadth_metrics_structured_output_and_no_limit_diff_logic():
    result = build_us_breadth_metrics(demo_rows())
    assert result["market"] == "us"
    assert result["status"] == "available"
    assert result["sample_size"] == 6
    assert result["valid_change_count"] == 3
    assert result["metrics"]["limit_up_down_diff_status"] == "not_applicable"
    assert result["metrics"]["nyse_rise_ratio"] == 1.0
    assert result["metrics"]["nasdaq_rise_ratio"] == 0.5
    for indicator in result["computed_indicators"]:
        assert indicator["item_type"] == "computed_indicator"
        assert indicator["is_official"] is False
        assert "非官方指数" in indicator["disclaimer"]


def test_us_breadth_metrics_empty_or_invalid_input_is_not_available():
    assert build_us_breadth_metrics([])["status"] == "empty"
    invalid = build_us_breadth_metrics([{"symbol": "DEMOA", "name": "示例美股A", "exchange": "NYSE", "change_pct": ""}])
    assert invalid["status"] == "insufficient_data"
    assert invalid["valid_change_count"] == 0


def test_us_markdown_demo_is_safe_and_has_required_sections():
    markdown = render_us_market_indicator_demo_markdown(build_us_breadth_metrics(demo_rows()))
    assert markdown.startswith("# 美股指数矩阵与广度指标 Demo")
    assert "## 1. 权重核心指数" in markdown
    assert "## 2. 科技成长指数" in markdown
    assert "## 3. 中小盘指数" in markdown
    assert "## 4. 等权 / 广度指标" in markdown
    assert "系统计算指标，非官方指数" in markdown
    forbidden_terms = [
        "买入",
        "卖出",
        "加仓",
        "减仓",
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
    lowered = markdown.lower()
    assert all(term not in lowered for term in forbidden_terms)


def test_us_outputs_do_not_include_forbidden_sensitive_or_real_quote_terms():
    payload = {
        "page": build_us_market_page_model(),
        "metrics": build_us_breadth_metrics(demo_rows()),
    }
    text = json.dumps(payload, ensure_ascii=False).lower()
    forbidden_terms = ["真实价格", "真实成交额", "真实金额", "成本价", "账户资产", "webhook", "token", "api key", "api_key"]
    assert all(term not in text for term in forbidden_terms)


def test_p5_l0_us_page_remains_compatible_with_market_index_matrix():
    page = build_market_page_model("us")
    assert [group["key"] for group in page["groups"]] == ["core_weight", "growth_tech", "small_mid", "market_breadth"]
    assert _find_item(page, "美股全市场等权涨跌")["item_type"] == "computed_indicator"
