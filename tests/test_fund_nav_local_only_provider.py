import json

from src.fund_nav_dry_run_provider import fetch_fund_nav_dry_run
from src.fund_nav_local_only_provider import (
    ESTIMATE_FIELDS,
    NAV_FIELDS,
    FundNavLocalOnlyProvider,
    build_fund_nav_local_only_config,
    build_fund_nav_local_only_fixture,
    fetch_fund_nav_local_only,
    render_fund_nav_local_only_markdown,
    summarize_fund_nav_local_only_results,
    validate_fund_nav_local_only_config,
    validate_fund_nav_local_only_result,
)
from src.fund_nav_provider import FixtureFundNavProvider, build_fund_nav_request, fetch_fund_nav
from src.fund_nav_provider_registry import build_fund_nav_provider_registry, validate_fund_nav_provider_registry
from src.provider_safety import validate_provider_config

DEMO_FUND = {"asset_id": "demo_fund_001", "code": "000000", "name": "示例场外基金A", "type": "fund", "market": "CN"}


def _assert_local_only_available(result):
    assert validate_fund_nav_local_only_result(result) == []
    assert result["data_status"] == "local_only_available"
    assert result["data_status"] != "available"
    assert result["has_real_nav_data"] is False
    assert result["will_fetch_real_data"] is False
    assert result["source"]["source_status"] == "local_fixture_only"
    assert result["source"]["checked_at"]
    assert set(NAV_FIELDS) == set(result["nav"])
    assert set(ESTIMATE_FIELDS) == set(result["estimate"])
    assert all(result["nav"][field] is None for field in NAV_FIELDS)
    assert all(result["estimate"][field] is None for field in ESTIMATE_FIELDS)
    assert result["provider_checks"]
    assert result["provider_checks"]["network_enabled"] is False
    assert result["provider_checks"]["will_fetch_real_data"] is False
    assert result["provider_checks"]["has_real_nav_data"] is False
    assert result["provider_checks"]["allow_commit_to_repo"] is False
    assert result["provider_checks"]["allow_fixture_definition_in_repo"] is True
    assert result["warnings"]


def test_generates_cn_fund_local_only_result_without_real_nav_values():
    result = fetch_fund_nav_local_only(DEMO_FUND)
    _assert_local_only_available(result)
    assert result["type"] == "fund"


def test_config_is_local_only_and_safety_checked():
    config = build_fund_nav_local_only_config()

    assert validate_fund_nav_local_only_config(config) == []
    assert validate_provider_config(config) == []
    assert config["network_enabled"] is False
    assert config["will_fetch_real_data"] is False
    assert config["has_real_nav_data"] is False
    assert config["allow_commit_to_repo"] is False
    assert config["allow_fixture_definition_in_repo"] is True
    assert config["source_status"] == "local_fixture_only"
    rendered = json.dumps(config, ensure_ascii=False).lower()
    assert not any(term in rendered for term in ["tok" + "en", "api" + "_key", "web" + "hook", "coo" + "kie", "author" + "ization", "bear" + "er"])


def test_unsupported_and_invalid_request_boundaries():
    cases = [
        ({**DEMO_FUND, "type": "stock"}, "unsupported", "股票应使用 A股 / ETF quote provider"),
        ({**DEMO_FUND, "type": "etf"}, "unsupported", "ETF 属于交易所交易品种"),
        ({**DEMO_FUND, "type": "index"}, "unsupported", "指数应使用 index quote"),
        ({**DEMO_FUND, "type": "company"}, "unsupported", "企业本身不是基金净值对象"),
        ({**DEMO_FUND, "type": "industry"}, "unsupported", "行业 / 主题不直接获取基金净值"),
        ({**DEMO_FUND, "type": "theme"}, "unsupported", "行业 / 主题不直接获取基金净值"),
        ({**DEMO_FUND, "type": "computed_indicator"}, "unsupported", "系统计算指标由市场广度模块生成"),
        ({**DEMO_FUND, "type": "unknown"}, "invalid_request", "unknown"),
        ({**DEMO_FUND, "market": "US"}, "unsupported", "非 CN 市场基金"),
    ]
    for item, status, reason in cases:
        result = fetch_fund_nav_local_only(item)
        assert result["data_status"] == status
        assert reason in result["reason"]
        assert result["has_real_nav_data"] is False


def test_fixture_row_missing_nav_or_estimate_returns_invalid_response():
    for field in ["nav", "estimate"]:
        fixture = build_fund_nav_local_only_fixture()
        fixture["rows"][0].pop(field)

        result = FundNavLocalOnlyProvider(fixture=fixture).fetch_one(DEMO_FUND)

        assert result["data_status"] == "invalid_response"
        assert "missing fields" in result["reason"]


def test_provider_status_error_stale_conflict_and_missing_paths_are_preserved():
    for provider_status, expected in [
        ("error", "provider_error"),
        ("stale", "stale_data"),
        ("conflict", "conflict"),
        ("estimate_missing", "estimate_unavailable"),
        ("daily_nav_missing", "daily_nav_unavailable"),
    ]:
        fixture = build_fund_nav_local_only_fixture()
        fixture["rows"][0]["provider_status"] = provider_status
        fixture["rows"][0]["warning"] = "示例场外基金A"
        fixture["rows"][0]["stale_reason"] = "示例场外基金A"

        result = FundNavLocalOnlyProvider(fixture=fixture).fetch_one(DEMO_FUND)

        assert result["data_status"] == expected
        assert result["source"]["checked_at"]
        assert any("示例场外基金A" in item for item in result["warnings"])


def test_markdown_is_local_only_and_contains_no_real_values_or_secrets():
    markdown = render_fund_nav_local_only_markdown(fetch_fund_nav_local_only(DEMO_FUND))

    assert "# 场外基金净值 Provider Local-only Demo" in markdown
    assert "本阶段仅做 local-only fixture 测试，不请求真实基金净值。" in markdown
    assert "本结果不包含真实单位净值、估算净值或涨跌幅。" in markdown
    assert "场外基金不支持真正实时价格。" in markdown
    assert "最终以基金公司公布净值为准" in markdown
    assert "local-only 结果不得被当作 real_provider 数据。" in markdown
    assert "已接入真实基金净值" not in markdown
    forbidden = ["真实单位净值：", "真实累计净值：", "真实估算净值：", "真实涨跌幅：", "Tok" + "en", "API " + "Key", "Web" + "hook", "api" + "_key"]
    assert not any(term in markdown for term in forbidden)


def test_summary_keeps_local_only_boundaries():
    summary = summarize_fund_nav_local_only_results([fetch_fund_nav_local_only(DEMO_FUND), fetch_fund_nav_local_only({**DEMO_FUND, "asset_id": "demo_fund_002", "code": "000001", "name": "示例场外基金B"})])

    assert summary["summary_type"] == "fund_nav_local_only_summary"
    assert summary["has_real_nav_data"] is False
    assert summary["will_fetch_real_data"] is False
    assert summary["status_counts"]["local_only_available"] == 2


def test_related_fund_nav_modules_still_behave():
    dry_run = fetch_fund_nav_dry_run(DEMO_FUND)
    registry = build_fund_nav_provider_registry()
    fixture_result = fetch_fund_nav(DEMO_FUND, FixtureFundNavProvider())
    request = build_fund_nav_request(DEMO_FUND)

    assert dry_run["data_mode"] == "dry_run"
    assert dry_run["will_fetch_real_data"] is False
    assert validate_fund_nav_provider_registry(registry) == []
    assert fixture_result.source["source_status"] == "fixture_only"
    assert request.type == "fund"
