import json

from src.cn_market_indicators import (
    build_cn_breadth_metrics,
    build_cn_market_page_model,
    calculate_cn_average_change_pct,
    calculate_cn_equal_weight_change,
    calculate_cn_limit_up_down_diff,
    calculate_cn_median_change_pct,
    calculate_cn_rise_ratio,
    get_cn_computed_indicators,
    render_cn_market_indicator_demo_markdown,
)
from src.market_index_matrix import build_market_index_dashboard_model


def _items(page):
    return [item for group in page.get("groups", []) for item in group.get("items", [])]


def _find_item(page, name):
    for item in _items(page):
        if item["name"] == name:
            return item
    raise AssertionError(f"missing item: {name}")


def _demo_rows():
    return [
        {"code": "000000", "name": "示例股票A", "change_pct": 1.2, "is_limit_up": True, "is_limit_down": False},
        {"code": "000001", "name": "示例股票B", "change_pct": -0.8, "is_limit_up": False, "is_limit_down": False},
        {"code": "000002", "name": "demo_stock_001", "change_pct": 0.2, "is_limit_up": False, "is_limit_down": True},
        {"code": "demo_stock_001", "name": "示例股票A", "change_pct": "", "is_limit_up": False, "is_limit_down": False},
        {"code": "000000", "name": "示例股票B", "change_pct": None, "is_limit_up": False, "is_limit_down": False},
        {"code": "000001", "name": "demo_stock_001", "change_pct": "bad", "is_limit_up": False, "is_limit_down": False},
    ]


def test_cn_page_contains_required_groups():
    page = build_cn_market_page_model()
    assert [group["key"] for group in page["groups"]] == [
        "core_weight",
        "small_mid",
        "growth_tech",
        "market_breadth",
    ]
    assert page["has_realtime_data"] is False
    assert page["data_mode"] == "model_only"


def test_cn_official_index_examples_are_official_index():
    page = build_cn_market_page_model()
    assert _find_item(page, "沪深300")["item_type"] == "official_index"
    assert _find_item(page, "中证A500")["item_type"] == "official_index"
    assert _find_item(page, "科创50")["item_type"] == "official_index"


def test_cn_computed_indicators_are_non_official_with_disclaimer():
    page = build_cn_market_page_model()
    median = _find_item(page, "A股中位数涨跌幅")
    ratio = _find_item(page, "A股上涨家数占比")
    for item in [median, ratio, *get_cn_computed_indicators()]:
        assert item["item_type"] == "computed_indicator"
        assert item["is_computed"] is True
        assert item["is_official"] is False
        assert "非官方指数" in item["disclaimer"]


def test_cn_breadth_calculations_ignore_invalid_change_pct():
    rows = _demo_rows()
    assert calculate_cn_median_change_pct(rows) == 0.2
    assert calculate_cn_average_change_pct(rows) == 0.2
    assert calculate_cn_rise_ratio(rows) == 0.6667
    assert calculate_cn_limit_up_down_diff(rows) == 0
    assert calculate_cn_equal_weight_change(rows) == 0.2


def test_empty_input_returns_empty_or_insufficient_data():
    result = build_cn_breadth_metrics([])
    assert result["status"] in {"empty", "insufficient_data"}
    assert result["sample_size"] == 0
    assert result["valid_change_count"] == 0


def test_build_cn_breadth_metrics_outputs_stable_structure():
    result = build_cn_breadth_metrics(_demo_rows())
    assert result["market"] == "cn"
    assert result["status"] == "available"
    assert result["sample_size"] == 6
    assert result["valid_change_count"] == 3
    assert result["metrics"]["limit_up_count"] == 1
    assert result["metrics"]["limit_down_count"] == 1
    assert result["metrics"]["turnover_change_status"] == "insufficient_data"
    for item in result["computed_indicators"]:
        assert item["item_type"] == "computed_indicator"
        assert item["is_official"] is False
        assert "非官方指数" in item["disclaimer"]


def test_render_markdown_omits_trading_advice_and_sensitive_terms():
    markdown = render_cn_market_indicator_demo_markdown(build_cn_breadth_metrics(_demo_rows()))
    forbidden_terms = [
        "买入",
        "卖出",
        "加仓",
        "减仓",
        "真实价格",
        "真实成交额",
        "金额",
        "成本价",
        "账户资产",
        "webhook",
        "token",
        "api key",
        "api_key",
    ]
    lowered = markdown.lower()
    assert "# A股指数矩阵与体感指标 Demo" in markdown
    assert "系统计算指标，非官方指数。" in markdown
    assert all(term not in lowered for term in forbidden_terms)


def test_structured_output_omits_real_price_turnover_money_and_secrets():
    text = json.dumps(build_cn_breadth_metrics(_demo_rows()), ensure_ascii=False).lower()
    forbidden_terms = [
        "真实价格",
        "真实成交额",
        "金额",
        "成本价",
        "账户资产",
        "webhook",
        "token",
        "api key",
        "api_key",
    ]
    assert all(term not in text for term in forbidden_terms)


def test_existing_dashboard_keeps_other_market_pages_available():
    dashboard = build_market_index_dashboard_model()
    assert set(dashboard["pages"]) == {"global", "cn", "hk", "us", "kr"}
    assert dashboard["has_realtime_data"] is False
    assert dashboard["pages"]["hk"]["status"] == "available"
    assert dashboard["pages"]["us"]["status"] == "available"
    assert dashboard["pages"]["kr"]["status"] == "available"
