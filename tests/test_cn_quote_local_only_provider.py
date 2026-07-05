import json

from src.cn_quote_dry_run_provider import fetch_cn_quote_dry_run
from src.cn_quote_local_only_provider import (
    QUOTE_FIELDS,
    CnQuoteLocalOnlyProvider,
    build_cn_quote_local_only_config,
    build_cn_quote_local_only_fixture,
    fetch_cn_quote_local_only,
    render_cn_quote_local_only_markdown,
    summarize_cn_quote_local_only_results,
    validate_cn_quote_local_only_config,
    validate_cn_quote_local_only_result,
)
from src.provider_registry import build_provider_registry, validate_provider_registry
from src.provider_safety import validate_provider_config
from src.realtime_quote_provider import FixtureQuoteProvider, QuoteRequest

DEMO_STOCK = {"asset_id": "demo_stock_001", "code": "000001", "symbol": "000001", "name": "示例股票A", "type": "stock", "market": "CN"}
DEMO_ETF = {"asset_id": "demo_etf_001", "code": "000000", "symbol": "000000", "name": "示例ETF", "type": "etf", "market": "cn"}
DEMO_INDEX = {"asset_id": "demo_index_001", "code": "DEMOA", "symbol": "DEMOA", "name": "示例指数", "type": "index", "market": "A股", "is_official_index": True}


def _assert_local_only_available(result):
    assert validate_cn_quote_local_only_result(result) == []
    assert result["data_status"] == "local_only_available"
    assert result["data_status"] != "available"
    assert result["has_real_market_data"] is False
    assert result["will_fetch_real_data"] is False
    assert result["source"]["source_status"] == "local_fixture_only"
    assert result["source"]["checked_at"]
    assert set(QUOTE_FIELDS) == set(result["quote"])
    assert all(result["quote"][field] is None for field in QUOTE_FIELDS)
    assert result["provider_checks"]
    assert result["provider_checks"]["network_enabled"] is False
    assert result["provider_checks"]["will_fetch_real_data"] is False
    assert result["provider_checks"]["has_real_market_data"] is False
    assert result["warnings"]


def test_generates_stock_etf_and_official_index_local_only_results():
    for item, expected_type in [(DEMO_STOCK, "stock"), (DEMO_ETF, "etf"), (DEMO_INDEX, "official_index")]:
        result = fetch_cn_quote_local_only(item)
        _assert_local_only_available(result)
        assert result["type"] == expected_type


def test_config_is_local_only_and_safety_checked():
    config = build_cn_quote_local_only_config()

    assert validate_cn_quote_local_only_config(config) == []
    assert validate_provider_config(config) == []
    assert config["network_enabled"] is False
    assert config["will_fetch_real_data"] is False
    assert config["has_real_market_data"] is False
    assert config["source_status"] == "local_fixture_only"
    rendered = json.dumps(config, ensure_ascii=False).lower()
    assert not any(term in rendered for term in ["tok" + "en", "api" + "_key", "web" + "hook", "coo" + "kie", "author" + "ization", "bear" + "er"])


def test_unsupported_and_invalid_request_boundaries():
    cases = [
        ({**DEMO_STOCK, "type": "fund"}, "unsupported", "场外基金应使用 fund_nav_provider"),
        ({**DEMO_STOCK, "type": "company"}, "unsupported", "企业本身不是可直接报价对象"),
        ({**DEMO_STOCK, "type": "industry"}, "unsupported", "行业 / 主题后续通过指数或系统计算指标实现"),
        ({**DEMO_STOCK, "type": "theme"}, "unsupported", "行业 / 主题后续通过指数或系统计算指标实现"),
        ({**DEMO_STOCK, "item_type": "computed_indicator"}, "unsupported", "系统计算指标由市场广度模块生成"),
        ({**DEMO_STOCK, "type": "unknown"}, "invalid_request", "unknown asset type"),
        ({**DEMO_STOCK, "market": "US"}, "unsupported", "非 CN 市场资产"),
    ]
    for item, status, reason in cases:
        result = fetch_cn_quote_local_only(item)
        assert result["data_status"] == status
        assert reason in result["reason"]
        assert result["has_real_market_data"] is False


def test_fixture_row_missing_fields_returns_invalid_response():
    fixture = build_cn_quote_local_only_fixture()
    fixture["rows"][0].pop("provider_symbol")

    result = CnQuoteLocalOnlyProvider(fixture=fixture).fetch_quote(DEMO_STOCK)

    assert result["data_status"] == "invalid_response"
    assert "missing fields" in result["reason"]


def test_provider_status_error_stale_and_conflict_are_preserved():
    for provider_status, expected in [("error", "provider_error"), ("stale", "stale_data"), ("conflict", "conflict")]:
        fixture = build_cn_quote_local_only_fixture()
        fixture["rows"][0]["provider_status"] = provider_status
        fixture["rows"][0]["warning"] = "示例指数"
        fixture["rows"][0]["stale_reason"] = "示例指数"

        result = CnQuoteLocalOnlyProvider(fixture=fixture).fetch_quote(DEMO_STOCK)

        assert result["data_status"] == expected
        assert result["source"]["checked_at"]
        assert any("示例指数" in item for item in result["warnings"])


def test_markdown_is_local_only_and_contains_no_real_values_or_secrets():
    markdown = render_cn_quote_local_only_markdown(fetch_cn_quote_local_only(DEMO_STOCK))

    assert "# A股 / ETF Provider Local-only Demo" in markdown
    assert "本阶段仅做 local-only fixture 测试，不请求真实行情。" in markdown
    assert "本结果不包含真实价格、涨跌幅或成交额。" in markdown
    assert "local-only 结果不得被当作 real_provider 数据。" in markdown
    assert "已接入真实行情" not in markdown
    forbidden = ["真实价格：", "真实涨跌幅：", "真实成交额：", "Tok" + "en", "API " + "Key", "Web" + "hook", "api" + "_key"]
    assert not any(term in markdown for term in forbidden)


def test_summary_keeps_local_only_boundaries():
    summary = summarize_cn_quote_local_only_results([fetch_cn_quote_local_only(DEMO_STOCK), fetch_cn_quote_local_only(DEMO_ETF)])

    assert summary["summary_type"] == "cn_quote_local_only_summary"
    assert summary["has_real_market_data"] is False
    assert summary["will_fetch_real_data"] is False
    assert summary["status_counts"]["local_only_available"] == 2


def test_related_provider_modules_still_behave():
    dry_run = fetch_cn_quote_dry_run(DEMO_STOCK)
    registry = build_provider_registry()
    realtime = FixtureQuoteProvider().fetch_quote(QuoteRequest(symbol="000001", asset_type="stock", market="CN", request_id="demo_stock_001"))

    assert dry_run["data_mode"] == "dry_run"
    assert dry_run["will_fetch_real_data"] is False
    assert validate_provider_registry(registry) == []
    assert realtime.fixture_only is True
    assert realtime.price is None
