import json

from src.cn_quote_dry_run_provider import fetch_cn_quote_dry_run
from src.cn_quote_local_only_provider import fetch_cn_quote_local_only
from src.cn_quote_real_provider import (
    QUOTE_FIELDS,
    CnQuoteRealProvider,
    build_cn_quote_real_provider_config,
    fetch_cn_quote_real,
    render_cn_quote_real_markdown,
    summarize_cn_quote_real_results,
    validate_cn_quote_real_provider_config,
    validate_cn_quote_real_result,
)
from src.provider_registry import build_provider_registry, validate_provider_registry
from src.provider_safety import validate_provider_config
from src.realtime_quote_provider import FixtureQuoteProvider, QuoteRequest

DEMO_STOCK = {"asset_id": "demo_stock_001", "code": "000001", "symbol": "000001", "name": "示例股票A", "type": "stock", "market": "CN"}
DEMO_ETF = {"asset_id": "demo_etf_001", "code": "000000", "symbol": "000000", "name": "示例ETF", "type": "etf", "market": "cn"}
DEMO_INDEX = {"asset_id": "demo_index_001", "code": "DEMOA", "symbol": "DEMOA", "name": "示例指数", "type": "index", "market": "A股", "is_official_index": True}


def enabled_config():
    config = build_cn_quote_real_provider_config()
    config.update({"network_enabled": True, "provider_enabled": True, "enabled": True, "allow_real_request": True})
    return config


def fake_response(request):
    return {
        "asset_id": request["asset_id"],
        "code": request["code"],
        "symbol": request["symbol"],
        "name": request["name"],
        "type": request["type"],
        "market": request["market"],
        "source_status": "ok",
        "quote": {field: None for field in QUOTE_FIELDS},
    }


def test_default_config_is_disabled_and_non_committable():
    config = build_cn_quote_real_provider_config()

    assert validate_cn_quote_real_provider_config(config) == []
    assert validate_provider_config(config) == []
    assert config["network_enabled"] is False
    assert config["provider_enabled"] is False
    assert config["allow_real_request"] is False
    assert config["default_enabled"] is False
    assert config["allow_commit_to_repo"] is False
    assert config["cache_scope"] == "local_only"


def test_default_fetch_returns_disabled_without_calling_fetcher():
    called = {"value": False}

    def fetcher(request):
        called["value"] = True
        return fake_response(request)

    result = CnQuoteRealProvider(fetcher=fetcher).fetch_quote(DEMO_STOCK)

    assert result["data_status"] == "disabled_by_default"
    assert called["value"] is False
    assert result["provider_checks"]["network_enabled"] is False
    assert result["source"]["checked_at"]
    assert result["source"]["source_status"] == "disabled_by_default"


def test_partial_gates_do_not_call_fetcher():
    for updates in [
        {"network_enabled": True},
        {"provider_enabled": True, "enabled": True},
        {"allow_real_request": True},
        {"network_enabled": True, "provider_enabled": True, "enabled": True},
    ]:
        called = {"value": False}
        config = build_cn_quote_real_provider_config()
        config.update(updates)

        def fetcher(request):
            called["value"] = True
            return fake_response(request)

        result = CnQuoteRealProvider(config=config, fetcher=fetcher).fetch_quote(DEMO_STOCK)

        assert result["data_status"] in {"disabled_by_default", "provider_policy_blocked"}
        assert called["value"] is False


def test_all_gates_open_calls_fake_fetcher_and_normalizes_result():
    called = {"count": 0}

    def fetcher(request):
        called["count"] += 1
        return fake_response(request)

    result = CnQuoteRealProvider(config=enabled_config(), fetcher=fetcher).fetch_quote(DEMO_STOCK)

    assert called["count"] == 1
    assert validate_cn_quote_real_result(result) == []
    assert result["data_status"] == "real_provider_available"
    assert result["has_real_market_data"] is True
    assert result["allow_commit_to_repo"] is False
    assert result["provider_checks"]["network_enabled"] is True
    assert result["provider_checks"]["provider_enabled"] is True
    assert result["provider_checks"]["allow_real_request"] is True
    assert result["provider_checks"]["allow_commit_to_repo"] is False
    assert result["provider_checks"]["cache_scope"] == "local_only"
    assert result["source"]["checked_at"]
    assert result["source"]["source_status"] == "real_provider"
    assert set(result["quote"]) == set(QUOTE_FIELDS)


def test_supported_stock_etf_and_official_index():
    provider = CnQuoteRealProvider(config=enabled_config(), fetcher=fake_response)

    for item, expected_type in [(DEMO_STOCK, "stock"), (DEMO_ETF, "etf"), (DEMO_INDEX, "official_index")]:
        result = provider.fetch_quote(item)
        assert result["data_status"] == "real_provider_available"
        assert result["type"] == expected_type


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
    provider = CnQuoteRealProvider(config=enabled_config(), fetcher=fake_response)
    for item, status, reason in cases:
        result = provider.fetch_quote(item)
        assert result["data_status"] == status
        assert reason in result["reason"]


def test_fetcher_failures_are_isolated():
    def error_fetcher(request):
        raise RuntimeError("demo provider failed")

    def timeout_fetcher(request):
        raise TimeoutError("demo timeout")

    assert CnQuoteRealProvider(config=enabled_config(), fetcher=error_fetcher).fetch_quote(DEMO_STOCK)["data_status"] == "provider_error"
    assert CnQuoteRealProvider(config=enabled_config(), fetcher=timeout_fetcher).fetch_quote(DEMO_STOCK)["data_status"] == "provider_timeout"
    assert CnQuoteRealProvider(config=enabled_config()).fetch_quote(DEMO_STOCK)["data_status"] == "provider_error"


def test_invalid_stale_and_conflict_responses():
    provider = CnQuoteRealProvider(config=enabled_config(), fetcher=lambda request: {"quote": {"last_price": None}})
    assert provider.fetch_quote(DEMO_STOCK)["data_status"] == "invalid_response"

    stale = CnQuoteRealProvider(config=enabled_config(), fetcher=lambda request: {"source_status": "stale_data", "reason": "示例指数"})
    assert stale.fetch_quote(DEMO_STOCK)["data_status"] == "stale_data"

    conflict = CnQuoteRealProvider(config=enabled_config(), fetcher=lambda request: {"source_status": "conflict", "reason": "示例指数"})
    assert conflict.fetch_quote(DEMO_STOCK)["data_status"] == "conflict"


def test_provider_safety_blocks_plaintext_secret_fields():
    for field in ["tok" + "en", "api" + "_key", "web" + "hook"]:
        config = build_cn_quote_real_provider_config()
        config[field] = "demo"
        result = CnQuoteRealProvider(config=config, fetcher=fake_response).fetch_quote(DEMO_STOCK)
        assert result["data_status"] == "provider_policy_blocked"
        assert "secret" in result["reason"]


def test_markdown_is_gated_and_contains_no_real_values_or_secrets():
    markdown = render_cn_quote_real_markdown(fetch_cn_quote_real(DEMO_STOCK))

    assert "# A股 / ETF Provider Real-request Minimal Demo" in markdown
    assert "真实 provider 默认关闭，必须显式开启 network_enabled、provider_enabled 和 allow_real_request。" in markdown
    assert "真实 provider 结果不得写入 public 仓库。" in markdown
    assert "CI 测试不会请求真实行情。" in markdown
    assert "已接入真实行情" not in markdown
    forbidden = ["真实价格：", "真实涨跌幅：", "真实成交额：", "Tok" + "en", "API " + "Key", "Web" + "hook", "api" + "_key"]
    assert not any(term in markdown for term in forbidden)


def test_summary_and_related_provider_modules_still_behave():
    real_results = [CnQuoteRealProvider(config=enabled_config(), fetcher=fake_response).fetch_quote(DEMO_STOCK)]
    summary = summarize_cn_quote_real_results(real_results)
    dry_run = fetch_cn_quote_dry_run(DEMO_STOCK)
    local_only = fetch_cn_quote_local_only(DEMO_STOCK)
    registry = build_provider_registry()
    realtime = FixtureQuoteProvider().fetch_quote(QuoteRequest(symbol="000001", asset_type="stock", market="CN", request_id="demo_stock_001"))

    assert summary["summary_type"] == "cn_quote_real_summary"
    assert summary["allow_commit_to_repo"] is False
    assert dry_run["data_mode"] == "dry_run"
    assert dry_run["will_fetch_real_data"] is False
    assert local_only["data_mode"] == "local_only_fixture"
    assert local_only["has_real_market_data"] is False
    assert validate_provider_registry(registry) == []
    assert realtime.fixture_only is True
    assert realtime.price is None
    rendered = json.dumps(summary, ensure_ascii=False).lower()
    assert not any(term in rendered for term in ["tok" + "en", "api" + "_key", "web" + "hook"])
