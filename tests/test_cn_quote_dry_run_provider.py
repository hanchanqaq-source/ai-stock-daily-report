import json

from src.cn_quote_dry_run_provider import (
    CnQuoteDryRunProvider,
    build_cn_quote_dry_run_plan,
    build_cn_quote_dry_run_request,
    fetch_cn_quote_dry_run,
    fetch_cn_quotes_dry_run,
    render_cn_quote_dry_run_markdown,
    summarize_cn_quote_dry_run_results,
    validate_cn_quote_dry_run_result,
)
from src.provider_registry import get_provider_evaluation
from src.realtime_quote_provider import QuoteRequest

DEMO_STOCK = {"asset_id": "demo_stock_001", "code": "000001", "symbol": "000001", "name": "示例股票A", "type": "stock", "market": "CN"}
DEMO_ETF = {"asset_id": "demo_etf_001", "code": "000000", "symbol": "000000", "name": "示例ETF", "type": "etf", "market": "cn"}
DEMO_INDEX = {"asset_id": "demo_index_001", "code": "DEMOA", "symbol": "DEMOA", "name": "示例指数", "type": "index", "market": "A股", "item_type": "official_index"}


def test_builds_cn_stock_etf_and_official_index_dry_run_requests():
    stock = build_cn_quote_dry_run_request(DEMO_STOCK)
    etf = build_cn_quote_dry_run_request(DEMO_ETF)
    index = build_cn_quote_dry_run_request(DEMO_INDEX)

    assert stock["type"] == "stock"
    assert etf["type"] == "etf"
    assert index["type"] == "official_index"
    assert [stock["market"], etf["market"], index["market"]] == ["CN", "CN", "CN"]
    for request in (stock, etf, index):
        assert request["provider_status"] == "candidate_only"
        assert request["data_mode"] == "dry_run"
        assert request["network_required"] is True
        assert request["network_enabled"] is False
        assert request["default_enabled"] is False
        assert request["will_fetch_real_data"] is False
        assert request["allow_commit_to_repo"] is False


def test_fetch_supported_assets_returns_dry_run_only_without_real_quote_values():
    results = fetch_cn_quotes_dry_run([DEMO_STOCK, DEMO_ETF, DEMO_INDEX])

    assert [result["data_status"] for result in results] == ["dry_run_only", "dry_run_only", "dry_run_only"]
    for result in results:
        assert result["has_real_market_data"] is False
        assert result["will_fetch_real_data"] is False
        assert result["source"]["source_status"] == "dry_run_only"
        assert result["source"]["checked_at"]
        assert result["quote"] == {"last_price": None, "change_pct": None, "change_amount": None, "volume": None, "turnover": None}
        assert result["provider_checks"]["provider_registered"] is True
        assert result["provider_checks"]["provider_candidate_only"] is True
        assert result["provider_checks"]["default_enabled"] is False
        assert result["provider_checks"]["network_required"] is True
        assert result["provider_checks"]["network_enabled"] is False
        assert result["provider_checks"]["allow_commit_to_repo"] is False
        assert result["provider_checks"]["field_mapping_ready"] is True
        assert result["provider_checks"]["cache_policy_ready"] is True
        assert result["provider_checks"]["failure_policy_ready"] is True
        assert result["warnings"]
        assert validate_cn_quote_dry_run_result(result) == []


def test_fund_company_industry_theme_and_computed_indicator_are_unsupported():
    cases = [
        ({**DEMO_STOCK, "type": "fund"}, "场外基金应使用 fund_nav_provider"),
        ({**DEMO_STOCK, "type": "company"}, "企业本身不是可直接报价对象"),
        ({**DEMO_STOCK, "type": "industry"}, "行业 / 主题后续通过指数或系统计算指标实现"),
        ({**DEMO_STOCK, "type": "theme"}, "行业 / 主题后续通过指数或系统计算指标实现"),
        ({**DEMO_STOCK, "type": "index", "item_type": "computed_indicator"}, "系统计算指标由市场广度模块生成"),
    ]

    for item, reason in cases:
        result = fetch_cn_quote_dry_run(item)
        assert result["data_status"] == "unsupported"
        assert reason in result["reason"]
        assert result["has_real_market_data"] is False


def test_unknown_is_invalid_and_non_cn_market_is_unsupported():
    unknown = fetch_cn_quote_dry_run({**DEMO_STOCK, "type": "unknown"})
    us_stock = fetch_cn_quote_dry_run({**DEMO_STOCK, "market": "US"})

    assert unknown["data_status"] == "invalid_request"
    assert us_stock["data_status"] == "unsupported"


def test_provider_not_registered_and_registry_backed_candidates():
    missing = fetch_cn_quote_dry_run(DEMO_STOCK, provider_name="missing_provider")
    assert missing["data_status"] == "provider_not_registered"
    assert missing["provider_checks"]["provider_registered"] is False

    for provider_name in ("akshare", "eastmoney"):
        provider = get_provider_evaluation(provider_name)
        result = fetch_cn_quote_dry_run(DEMO_STOCK, provider_name=provider_name)
        assert result["provider_name"] == provider["provider_name"]
        assert result["source"]["provider_type"] == provider["provider_type"]
        assert result["provider_checks"]["default_enabled"] is False
        assert result["provider_checks"]["network_required"] is True
        assert result["provider_checks"]["field_mapping_ready"] is True


def test_quote_request_compatibility_and_batch_plan_summary():
    provider = CnQuoteDryRunProvider("akshare")
    request = QuoteRequest(symbol="000001", asset_type="stock", market="CN", name="示例股票A", request_id="demo_stock_001")
    result = provider.fetch_quote(request)
    batch = provider.fetch_quotes([request])
    plan = build_cn_quote_dry_run_plan([DEMO_STOCK, DEMO_ETF])
    summary = summarize_cn_quote_dry_run_results(fetch_cn_quotes_dry_run([DEMO_STOCK, DEMO_ETF]))

    assert result["data_status"] == "dry_run_only"
    assert batch[0]["request_id"] == "demo_stock_001"
    assert plan["will_fetch_real_data"] is False
    assert plan["network_enabled"] is False
    assert len(plan["requests"]) == 2
    assert summary["status_counts"] == {"dry_run_only": 2}
    assert summary["has_real_market_data"] is False


def test_markdown_does_not_claim_real_provider_or_include_forbidden_values():
    markdown = render_cn_quote_dry_run_markdown(fetch_cn_quote_dry_run(DEMO_STOCK))
    lower_markdown = markdown.lower()

    assert "# A股 / ETF Provider Dry-run Demo" in markdown
    assert "本阶段仅做 dry-run，不请求真实行情。" in markdown
    assert "真实 provider 默认关闭，必须显式启用 network_enabled。" in markdown
    assert "本结果不包含真实价格、涨跌幅或成交额。" in markdown
    assert "已接入真实行情" not in markdown
    assert "last_price" not in markdown
    assert "change_pct" not in markdown
    assert "turnover" not in markdown
    assert "token" not in lower_markdown
    assert "api key" not in lower_markdown
    assert "webhook" not in lower_markdown


def test_rendered_result_contains_no_real_market_values_or_sensitive_terms():
    rendered = json.dumps(fetch_cn_quote_dry_run(DEMO_STOCK), ensure_ascii=False).lower()

    assert '"data_status": "available"' not in rendered
    assert '"has_real_market_data": true' not in rendered
    assert '"source_status": "real_provider"' not in rendered
    assert "api_key" not in rendered
    assert "webhook" not in rendered
    assert "authorization" not in rendered
    assert "bearer" not in rendered
    assert "cookie" not in rendered
