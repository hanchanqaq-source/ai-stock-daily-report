from copy import deepcopy
import json

from src.account_realtime_summary import (
    build_account_realtime_summary,
    build_asset_market_data_request,
    fetch_asset_market_data,
    render_account_realtime_summary_markdown,
    split_assets_for_realtime_summary,
    validate_account_realtime_summary,
)
from src.fund_nav_provider import FixtureFundNavProvider
from src.realtime_quote_provider import FixtureQuoteProvider


def asset(asset_id, type, status="holding", code="000001", name="示例股票A", **extra):
    data = {
        "asset_id": asset_id,
        "type": type,
        "code": code,
        "name": name,
        "market": "CN",
        "status": status,
    }
    data.update(extra)
    return data


def mixed_group():
    return {
        "account_id": "demo_mixed_group",
        "account_name": "示例混合账户",
        "assets": [
            asset("demo_stock_001", "stock", "holding", "000001", "示例股票A"),
            asset("demo_etf_001", "etf", "holding", "DEMOA", "示例ETF"),
            asset("demo_index_001", "index", "watching", "000000", "示例指数", item_type="official_index"),
            asset("demo_fund_001", "fund", "watching", "000000", "示例场外基金A"),
            asset("demo_company_001", "company", "holding", "DEMOA", "示例企业A"),
            asset("demo_theme_001", "theme", "watching", "DEMOA", "示例主题A"),
            asset("demo_computed_001", "index", "watching", "DEMOA", "示例指数", item_type="computed_indicator"),
            asset("demo_unknown_001", "unknown", "watching", "DEMOA", "示例主题A"),
            asset("demo_cleared_001", "stock", "cleared", "000001", "示例股票A"),
            asset("demo_archived_001", "fund", "archived", "000000", "示例场外基金A"),
            asset("demo_deleted_001", "etf", "deleted", "DEMOA", "示例ETF"),
        ],
    }


def payload_text(payload):
    return json.dumps(payload, ensure_ascii=False)


def test_active_assets_are_read_and_inactive_are_excluded_from_results():
    split = split_assets_for_realtime_summary(mixed_group())
    assert split["asset_counts"]["active"] == 8
    assert split["asset_counts"]["cleared"] == 1
    assert split["asset_counts"]["archived"] == 1
    assert split["asset_counts"]["deleted"] == 1
    assert all(item["status"] in {"holding", "watching"} for item in split["active"])

    result = build_account_realtime_summary(mixed_group())
    result_ids = {item["asset"]["asset_id"] for item in result["results"]}
    assert "demo_cleared_001" not in result_ids
    assert "demo_archived_001" not in result_ids
    assert "demo_deleted_001" not in result_ids


def test_holding_and_watching_are_summarized_separately():
    result = build_account_realtime_summary(mixed_group())
    assert result["holding"]["summary"]["total"] == 3
    assert result["watching"]["summary"]["total"] == 5
    assert result["holding"]["summary"]["quote_available_count"] == 2
    assert result["watching"]["summary"]["fund_nav_available_count"] == 1


def test_stock_etf_official_index_route_to_realtime_quote_provider():
    for item in [
        asset("demo_stock_001", "stock"),
        asset("demo_etf_001", "etf", code="DEMOA", name="示例ETF"),
        asset("demo_index_001", "index", code="000000", name="示例指数", item_type="official_index"),
    ]:
        request = build_asset_market_data_request(item)
        assert request["request_kind"] == "realtime_quote"
        result = fetch_asset_market_data(item)
        assert result["result_kind"] == "realtime_quote"
        assert result["provider"] == "mock_quote_provider"
        assert result["checked_at"]
        assert result["source_status"] == "fixture_only"


def test_fund_routes_to_fund_nav_provider():
    result = fetch_asset_market_data(asset("demo_fund_001", "fund", "watching", "000000", "示例场外基金A"))
    assert result["result_kind"] == "fund_nav"
    assert result["provider"] == "mock_fund_nav"
    assert result["checked_at"]
    assert result["source_status"] == "fixture_only"


def test_computed_indicator_company_industry_theme_unknown_do_not_fetch_quotes():
    computed = fetch_asset_market_data(asset("demo_index_001", "index", code="DEMOA", name="示例指数", item_type="computed_indicator"))
    company = fetch_asset_market_data(asset("demo_company_001", "company", code="DEMOA", name="示例企业A"))
    industry = fetch_asset_market_data(asset("demo_industry_001", "industry", code="DEMOA", name="示例主题A"))
    theme = fetch_asset_market_data(asset("demo_theme_001", "theme", code="DEMOA", name="示例主题A"))
    unknown = fetch_asset_market_data(asset("demo_unknown_001", "unknown", code="DEMOA", name="示例主题A"))
    assert computed["result_kind"] == "unsupported"
    assert company["result_kind"] == "unsupported"
    assert industry["result_kind"] == "unsupported"
    assert theme["result_kind"] == "unsupported"
    assert unknown["result_kind"] == "invalid_request"


def test_partial_provider_failures_do_not_break_batch_and_summary_counts_statuses():
    result = build_account_realtime_summary(
        mixed_group(),
        quote_provider=FixtureQuoteProvider({"DEMOA": "provider_error"}),
        fund_nav_provider=FixtureFundNavProvider({"000000": "provider_error"}),
    )
    assert result["status"] == "partial_available"
    assert result["result_summary"]["available_count"] == 2
    assert result["result_summary"]["unsupported_count"] == 3
    assert result["result_summary"]["provider_error_count"] == 2
    assert result["result_summary"]["invalid_request_count"] == 1
    assert validate_account_realtime_summary(result)


def test_result_flags_are_fixture_only_and_no_real_market_data():
    result = build_account_realtime_summary(mixed_group())
    assert result["has_real_market_data"] is False
    assert result["data_mode"] in {"fixture_only", "model_only"}
    assert result["result_summary"]["fixture_only_count"] == 4
    assert all(item["has_real_market_data"] is False for item in result["results"])


def test_markdown_demo_contains_required_disclaimer_and_no_forbidden_trading_words():
    markdown = render_account_realtime_summary_markdown(build_account_realtime_summary(mixed_group()))
    assert "最终以基金公司公布净值为准" in markdown
    assert "本阶段为 mock / fixture 数据，不代表真实行情。" in markdown
    assert "本结果只做观察，不构成交易建议。" in markdown
    for forbidden in ["买入", "卖出", "加仓", "减仓", "必须买", "必须卖", "实时基金涨跌", "实时基金净值"]:
        assert forbidden not in markdown


def test_output_excludes_real_prices_money_account_assets_and_secrets():
    result = build_account_realtime_summary(mixed_group())
    text = payload_text(result) + render_account_realtime_summary_markdown(result)
    for forbidden in [
        "真实价格",
        "真实涨跌幅",
        "真实净值",
        "真实估算净值",
        "真实成交额",
        "金额",
        "成本价",
        "账户资产",
        "webhook",
        "Webhook",
        "Token",
        "API Key",
    ]:
        assert forbidden not in text


def test_input_group_is_not_modified():
    group = mixed_group()
    before = deepcopy(group)
    build_account_realtime_summary(group)
    assert group == before


def test_single_side_warnings_are_emitted():
    holding_only = {"account_id": "demo_mixed_group", "account_name": "示例混合账户", "assets": [asset("demo_stock_001", "stock")]}
    watching_only = {"account_id": "demo_mixed_group", "account_name": "示例混合账户", "assets": [asset("demo_fund_001", "fund", "watching", "000000", "示例场外基金A")]}
    assert "当前没有收藏资产可对比。" in build_account_realtime_summary(holding_only)["warnings"]
    assert "当前没有持有资产可对比。" in build_account_realtime_summary(watching_only)["warnings"]
