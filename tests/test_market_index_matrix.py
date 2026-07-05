import json

from src.market_index_matrix import (
    build_market_index_dashboard_model,
    build_market_page_model,
    get_default_market,
    get_market_tabs,
    get_supported_markets,
    is_computed_indicator,
    is_official_index,
)


def _items(page):
    return [item for group in page.get("groups", []) for item in group.get("items", [])]


def _find_item(page, name):
    for item in _items(page):
        if item["name"] == name:
            return item
    raise AssertionError(f"missing item: {name}")


def test_supported_markets_default_and_tabs_are_stable():
    assert get_supported_markets() == ["global", "cn", "hk", "us", "kr"]
    assert get_default_market() == "global"
    assert get_market_tabs() == [
        {"key": "global", "label": "全球总览", "enabled": True},
        {"key": "cn", "label": "A股", "enabled": True},
        {"key": "hk", "label": "港股", "enabled": True},
        {"key": "us", "label": "美股", "enabled": True},
        {"key": "kr", "label": "韩股", "enabled": True},
    ]


def test_dashboard_contains_all_market_pages():
    dashboard = build_market_index_dashboard_model()
    assert dashboard["default_market"] == "global"
    assert set(dashboard["pages"]) == {"global", "cn", "hk", "us", "kr"}
    assert dashboard["has_realtime_data"] is False
    assert dashboard["data_mode"] == "model_only"


def test_market_group_orders():
    assert [g["key"] for g in build_market_page_model("cn")["groups"]] == [
        "core_weight",
        "small_mid",
        "growth_tech",
        "market_breadth",
    ]
    assert [g["key"] for g in build_market_page_model("hk")["groups"]] == [
        "core_weight",
        "growth_tech",
        "broad_market",
        "market_breadth",
    ]
    assert [g["key"] for g in build_market_page_model("us")["groups"]] == [
        "core_weight",
        "growth_tech",
        "small_mid",
        "market_breadth",
    ]
    assert [g["key"] for g in build_market_page_model("kr")["groups"]] == [
        "core_weight",
        "growth_tech",
        "market_breadth",
    ]


def test_official_and_computed_classification_examples():
    cn = build_market_page_model("cn")
    hk = build_market_page_model("hk")
    us = build_market_page_model("us")
    kr = build_market_page_model("kr")

    cn_median = _find_item(cn, "A股中位数涨跌幅")
    us_median = _find_item(us, "美股中位数涨跌幅")
    nyse_ratio = _find_item(us, "NYSE上涨家数占比")

    assert is_computed_indicator(cn_median) is True
    assert is_official_index(cn_median) is False
    assert is_computed_indicator(us_median) is True
    assert is_computed_indicator(nyse_ratio) is True

    assert is_official_index(_find_item(us, "标普500")) is True
    assert is_official_index(_find_item(cn, "沪深300")) is True
    assert is_official_index(_find_item(hk, "恒生科技指数")) is True
    assert is_official_index(_find_item(kr, "KOSPI 200")) is True


def test_computed_indicators_have_non_official_disclaimer():
    dashboard = build_market_index_dashboard_model()
    for market in ["cn", "hk", "us", "kr"]:
        for item in _items(dashboard["pages"][market]):
            if item["item_type"] == "computed_indicator":
                assert "非官方指数" in item["disclaimer"] or "不是官方指数" in item["disclaimer"]
                assert item["source_status"] == "computed_later"
                assert item["quote_capability"]["price_mode"] == "computed_metric"
            else:
                assert item["source_status"] == "pending_data_source"
                assert item["quote_capability"]["price_mode"] == "index_quote"


def test_all_pages_are_model_only_without_realtime_data():
    dashboard = build_market_index_dashboard_model()
    assert dashboard["has_realtime_data"] is False
    assert dashboard["data_mode"] == "model_only"
    for page in dashboard["pages"].values():
        assert page["has_realtime_data"] is False
        assert page["data_mode"] == "model_only"


def test_output_does_not_contain_real_quote_or_sensitive_values():
    text = json.dumps(build_market_index_dashboard_model(), ensure_ascii=False).lower()
    forbidden_terms = [
        "真实价格",
        "真实涨跌幅",
        "真实成交额",
        "真实金额",
        "成本价",
        "账户资产",
        "webhook",
        "token",
        "api key",
        "api_key",
        "个人邮箱",
        "手机号",
        "身份证",
    ]
    assert all(term not in text for term in forbidden_terms)


def test_unknown_market_has_no_index_matrix():
    page = build_market_page_model("unknown")
    assert page["market"] == "unknown"
    assert page["groups"] == []
    assert page["has_realtime_data"] is False
    assert page["data_mode"] == "model_only"
