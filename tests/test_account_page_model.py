from __future__ import annotations

from copy import deepcopy

from src.account_page_model import build_account_page_model, filter_assets_for_page, get_visible_pages_for_account


def asset(asset_id="a1", type="fund", status="holding", **extra):
    item = {
        "asset_id": asset_id,
        "type": type,
        "code": "000000",
        "name": f"示例{asset_id}",
        "market": "CN",
        "tags": ["示例"],
        "status": status,
        "weight_level": 3,
        "source_status": "manual_user_input",
    }
    item.update(extra)
    return item


def group(assets):
    return {
        "account_id": "demo_group",
        "account_name": "示例账户",
        "enabled": True,
        "risk_profile": "balanced",
        "assets": assets,
    }


def model(assets):
    return build_account_page_model(group(assets))


def flatten_values(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from flatten_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from flatten_values(child)
    else:
        yield str(value)


def test_only_fund_shows_funds_not_stocks():
    pages = get_visible_pages_for_account(group([asset(type="fund")]))
    assert pages == ["overview", "funds"]
    assert "stocks" not in pages


def test_only_etf_shows_funds_not_stocks():
    pages = get_visible_pages_for_account(group([asset(type="etf")]))
    assert pages == ["overview", "funds"]
    assert "stocks" not in pages


def test_only_stock_shows_stocks_not_funds():
    pages = get_visible_pages_for_account(group([asset(type="stock")]))
    assert pages == ["overview", "stocks"]
    assert "funds" not in pages


def test_fund_and_stock_show_both_pages():
    pages = get_visible_pages_for_account(group([asset("f1", "fund"), asset("s1", "stock")]))
    assert pages[:3] == ["overview", "funds", "stocks"]


def test_company_shows_companies_page():
    assert "companies" in get_visible_pages_for_account(group([asset(type="company")]))


def test_industry_theme_index_show_themes_page():
    for asset_type in ("industry", "theme", "index"):
        assert "themes" in get_visible_pages_for_account(group([asset(type=asset_type)]))


def test_watching_asset_shows_watching_page():
    assert "watching" in get_visible_pages_for_account(group([asset(status="watching")]))


def test_holding_and_watching_show_comparison_page():
    pages = get_visible_pages_for_account(group([asset("h1", status="holding"), asset("w1", status="watching")]))
    assert "holding_vs_watching" in pages


def test_cleared_asset_shows_history_and_is_not_active():
    result = model([asset(status="cleared")])
    assert result["asset_counts"]["active"] == 0
    assert result["visible_pages"] == ["empty_state", "history"]


def test_archived_asset_is_not_active_and_can_show_history():
    result = model([asset(status="archived")])
    assert result["asset_counts"]["active"] == 0
    assert result["visible_pages"] == ["empty_state", "history"]


def test_deleted_asset_is_not_active_and_does_not_show_history():
    result = model([asset(status="deleted")])
    assert result["asset_counts"]["active"] == 0
    assert result["visible_pages"] == ["empty_state"]


def test_only_cleared_and_archived_show_empty_state_and_history():
    result = model([asset("c1", status="cleared"), asset("a1", status="archived")])
    assert result["visible_pages"] == ["empty_state", "history"]


def test_empty_group_shows_only_empty_state():
    result = model([])
    assert result["visible_pages"] == ["empty_state"]
    assert result["status"] == "empty"


def test_default_page_is_first_visible_page():
    result = model([asset(type="stock")])
    assert result["default_page"] == "overview"
    assert result["default_page"] == result["visible_pages"][0]


def test_tabs_order_is_stable():
    result = model([
        asset("s1", "stock", "holding"),
        asset("f1", "fund", "watching"),
        asset("c1", "company", "holding"),
        asset("t1", "theme", "watching"),
        asset("old", "fund", "cleared"),
    ])
    assert [tab["key"] for tab in result["tabs"]] == [
        "overview",
        "funds",
        "stocks",
        "companies",
        "themes",
        "watching",
        "holding_vs_watching",
        "history",
    ]


def test_page_data_uses_public_safe_asset_fields_only():
    result = model([asset("f1", "fund", "holding")])
    item = result["pages"]["funds"]["assets"][0]
    assert set(item) == {"asset_id", "type", "code", "name", "market", "tags", "status", "weight_level", "source_status"}


def test_page_model_does_not_include_money_cost_account_assets_or_secrets():
    result = model([asset("f1", "fund", "holding"), asset("w1", "stock", "watching"), asset("c1", "fund", "cleared")])
    text = " ".join(flatten_values(result)).lower()
    forbidden = ["amount", "cost_price", "成本价", "账户资产", "webhook", "token", "api_key", "apikey"]
    assert not any(word in text for word in forbidden)
    assert "weight_level" in text
    assert "balanced" not in text


def test_input_group_is_not_modified():
    source = group([asset("f1", "fund", "holding"), asset("w1", "stock", "watching")])
    before = deepcopy(source)
    build_account_page_model(source)
    assert source == before


def test_filter_assets_for_page_returns_only_matching_public_assets():
    source = group([asset("f1", "fund", "holding"), asset("s1", "stock", "watching"), asset("old", "stock", "cleared")])
    assert [item["asset_id"] for item in filter_assets_for_page(source, "stocks")] == ["s1"]
    assert [item["asset_id"] for item in filter_assets_for_page(source, "history")] == ["old"]
