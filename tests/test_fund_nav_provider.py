import json

import pytest

from src.fund_nav_provider import (
    FixtureFundNavProvider,
    FundNavRequest,
    MockFundNavProvider,
    build_fund_nav_request,
    fetch_fund_nav,
    fetch_fund_navs,
    is_fund_nav_supported,
    render_fund_nav_result_markdown,
    summarize_fund_nav_results,
    validate_fund_nav_result,
)
from src.quote_capability import get_quote_capability


def asset(asset_type, code="000000", asset_id="demo_fund_001", name="示例场外基金A"):
    return {"asset_id": asset_id, "type": asset_type, "code": code, "name": name, "market": "CN"}


def test_fund_can_build_request_and_is_not_realtime():
    request = build_fund_nav_request(asset("fund"))
    assert isinstance(request, FundNavRequest)
    assert request.type == "fund"
    assert request.price_mode == "estimated_nav_or_daily_nav"
    assert request.requires_realtime is False
    capability = get_quote_capability(asset("fund"))
    assert capability["realtime_supported"] is False


@pytest.mark.parametrize(
    ("asset_type", "reason"),
    [
        ("etf", "股票 / ETF 实时行情框架"),
        ("stock", "实时行情框架"),
        ("index", "index_quote"),
        ("company", "企业本身不是基金净值对象"),
        ("industry", "行业 / 主题"),
        ("theme", "行业 / 主题"),
    ],
)
def test_non_fund_assets_return_unsupported(asset_type, reason):
    result = fetch_fund_nav(asset(asset_type)).to_dict()
    assert result["data_status"] == "unsupported"
    assert reason in result["reason"]


def test_unknown_returns_invalid_request():
    result = fetch_fund_nav(asset("unknown", code="", asset_id="unknown_demo", name="")).to_dict()
    assert result["data_status"] == "invalid_request"


def test_result_contains_source_evidence_fields():
    result = fetch_fund_nav(asset("fund")).to_dict()
    assert result["source"]["provider"] == "mock_fund_nav"
    assert result["source"]["checked_at"]
    assert result["source"]["source_status"] == "fixture_only"
    assert validate_fund_nav_result(result)


def test_mock_provider_is_fixture_only_and_offline_placeholder():
    provider = MockFundNavProvider({"000000": "available"})
    result = provider.fetch_one(build_fund_nav_request(asset("fund"))).to_dict()
    assert result["source"]["source_status"] == "fixture_only"
    assert "fixture" in result["source"]["delay_note"]
    assert result["disclaimer"].startswith("场外基金不支持")


def test_fixture_provider_supports_unavailable_daily_only_estimate_only():
    provider = FixtureFundNavProvider({"000000": "daily_nav_only", "000001": "estimate_only", "000002": "unavailable"})
    daily = provider.fetch_one(build_fund_nav_request(asset("fund", "000000"))).to_dict()
    estimate = provider.fetch_one(build_fund_nav_request(asset("fund", "000001", "demo_fund_002", "示例场外基金B"))).to_dict()
    unavailable = provider.fetch_one(build_fund_nav_request(asset("fund", "000002", "demo_fund_002", "示例场外基金B"))).to_dict()
    assert daily["data_status"] == "daily_nav_only"
    assert estimate["data_status"] == "estimate_only"
    assert unavailable["data_status"] == "unavailable"


def test_fetch_many_supports_partial_success_and_summary_counts():
    provider = FixtureFundNavProvider({"000000": "available", "000001": "estimate_only"})
    payload = fetch_fund_navs([
        asset("fund", "000000"),
        asset("fund", "000001", "demo_fund_002", "示例场外基金B"),
        asset("etf"),
        asset("unknown", code="", asset_id="unknown_demo", name=""),
    ], provider)
    summary = payload["summary"]
    assert payload["status"] == "partial_available"
    assert summary["total"] == 4
    assert summary["available_count"] == 1
    assert summary["estimate_only_count"] == 1
    assert summary["unsupported_count"] == 1
    assert summary["invalid_request_count"] == 1
    assert summary["has_real_nav_data"] is False
    assert summary["data_mode"] == "fixture_only"


def test_empty_batch_returns_empty_summary():
    payload = fetch_fund_navs([])
    assert payload["status"] == "empty"
    assert payload["summary"]["total"] == 0


def test_provider_error_is_captured_without_breaking_batch():
    provider = FixtureFundNavProvider({"000000": "provider_error", "000001": "available"})
    payload = fetch_fund_navs([
        asset("fund", "000000"),
        asset("fund", "000001", "demo_fund_002", "示例场外基金B"),
    ], provider)
    statuses = [item["data_status"] for item in payload["results"]]
    assert statuses == ["provider_error", "available"]
    assert payload["summary"]["provider_error_count"] == 1


def test_is_fund_nav_supported_only_for_fund():
    assert is_fund_nav_supported(asset("fund")) is True
    assert is_fund_nav_supported(asset("etf")) is False
    assert is_fund_nav_supported(asset("stock")) is False


def test_markdown_contains_required_disclaimer_and_not_forbidden_actions():
    result = fetch_fund_nav(asset("fund"))
    markdown = render_fund_nav_result_markdown(result)
    assert "最终以基金公司公布净值为准" in markdown
    assert "实时涨跌" not in markdown
    assert "实时净值" not in markdown
    for forbidden in ["买入", "卖出", "加仓", "减仓"]:
        assert forbidden not in markdown


def test_output_contains_no_real_sensitive_or_account_values():
    provider = FixtureFundNavProvider({"000000": "available"})
    output = json.dumps(fetch_fund_navs([asset("fund")], provider), ensure_ascii=False)
    forbidden = [
        "真实净值",
        "真实估算净值",
        "真实涨跌幅",
        "真实成交额",
        "金额",
        "成本价",
        "账户资产",
        "webhook",
        "Token",
        "API Key",
    ]
    for word in forbidden:
        assert word not in output
    assert "fixture_only" in output


def test_summary_direct_helper_counts_daily_nav_only():
    provider = FixtureFundNavProvider({"000000": "daily_nav_only"})
    result = provider.fetch_one(build_fund_nav_request(asset("fund")))
    assert summarize_fund_nav_results([result])["daily_nav_only_count"] == 1
