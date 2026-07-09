import json

from src.fund_nav_dry_run_provider import (
    FundNavDryRunProvider,
    build_fund_nav_dry_run_plan,
    build_fund_nav_dry_run_request,
    fetch_fund_nav_dry_run,
    fetch_fund_navs_dry_run,
    render_fund_nav_dry_run_markdown,
    summarize_fund_nav_dry_run_results,
    validate_fund_nav_dry_run_request,
    validate_fund_nav_dry_run_result,
)

DEMO_FUND_A = {"asset_id": "demo_fund_001", "code": "000000", "name": "示例场外基金A", "type": "fund", "market": "CN"}
DEMO_FUND_B = {"asset_id": "demo_fund_002", "code": "000001", "name": "示例场外基金B", "type": "fund", "market": "CN"}


def asset(asset_type, market="CN"):
    return {**DEMO_FUND_A, "type": asset_type, "market": market}


def test_build_cn_fund_dry_run_request_is_public_safe_plan():
    request = build_fund_nav_dry_run_request(DEMO_FUND_A)
    assert request["request_id"] == "demo_fund_001"
    assert request["data_kind"] == "fund_nav"
    assert request["data_mode"] == "dry_run"
    assert request["requested_data"] == ["daily_nav", "estimated_nav"]
    assert request["will_fetch_real_data"] is False
    assert request["network_enabled"] is False
    assert request["allow_commit_to_repo"] is False
    assert validate_fund_nav_dry_run_request(request)


def test_eastmoney_and_tiantian_are_read_from_registry():
    eastmoney = fetch_fund_nav_dry_run(DEMO_FUND_A, "eastmoney_fund")
    tiantian = fetch_fund_nav_dry_run(DEMO_FUND_A, "tiantian_fund")
    assert eastmoney["provider_name"] == "eastmoney_fund"
    assert tiantian["provider_name"] == "tiantian_fund"
    assert eastmoney["provider_checks"]["provider_registered"] is True
    assert tiantian["provider_checks"]["provider_registered"] is True
    assert eastmoney["provider_checks"]["provider_candidate_only"] is True
    assert tiantian["provider_checks"]["provider_candidate_only"] is True


def test_provider_not_registered_result():
    result = fetch_fund_nav_dry_run(DEMO_FUND_A, "missing_provider")
    assert result["data_status"] == "provider_not_registered"
    assert result["provider_checks"]["provider_registered"] is False
    assert result["has_real_nav_data"] is False
    assert validate_fund_nav_dry_run_result(result)


def test_real_provider_gates_remain_closed_in_dry_run():
    result = fetch_fund_nav_dry_run(DEMO_FUND_A)
    checks = result["provider_checks"]
    assert result["data_status"] == "dry_run_only"
    assert result["data_mode"] == "dry_run"
    assert checks["default_enabled"] is False
    assert checks["network_required"] is True
    assert checks["network_enabled"] is False
    assert result["will_fetch_real_data"] is False
    assert checks["allow_commit_to_repo"] is False
    assert result["has_real_nav_data"] is False
    assert result["source"]["source_status"] == "dry_run_only"
    assert result["source"]["checked_at"]
    assert result["warnings"]
    assert "network_enabled" in " ".join(result["warnings"])


def test_result_has_no_real_nav_or_estimate_values_and_has_checks():
    result = fetch_fund_nav_dry_run(DEMO_FUND_A)
    assert all(value is None for value in result["nav"].values())
    assert all(value is None for value in result["estimate"].values())
    assert result["provider_checks"]["daily_nav_mapping_ready"] is True
    assert result["provider_checks"]["estimated_nav_mapping_ready"] is True
    assert result["provider_checks"]["cache_policy_ready"] is True
    assert result["provider_checks"]["failure_policy_ready"] is True
    assert validate_fund_nav_dry_run_result(result)


def test_unsupported_asset_types_and_unknown():
    expected = {
        "stock": "股票应使用 A股 / ETF quote provider。",
        "etf": "ETF 属于交易所交易品种，应使用股票 / ETF provider。",
        "index": "指数应使用 index quote 或市场指数模块。",
        "company": "企业本身不是基金净值对象。",
        "industry": "行业 / 主题不直接获取基金净值。",
        "theme": "行业 / 主题不直接获取基金净值。",
        "computed_indicator": "系统计算指标由市场广度模块生成，不直接请求基金净值 provider。",
    }
    for asset_type, reason in expected.items():
        result = fetch_fund_nav_dry_run(asset(asset_type))
        assert result["data_status"] == "unsupported"
        assert result["reason"] == reason
    unknown = fetch_fund_nav_dry_run(asset("unknown"))
    assert unknown["data_status"] == "invalid_request"


def test_non_cn_fund_is_unsupported():
    result = fetch_fund_nav_dry_run(asset("fund", market="US"))
    assert result["data_status"] == "unsupported"
    assert "非 CN" in result["reason"]


def test_plan_many_provider_class_and_summary_are_dry_run_only():
    plan = build_fund_nav_dry_run_plan([DEMO_FUND_A, DEMO_FUND_B])
    provider = FundNavDryRunProvider()
    payload = fetch_fund_navs_dry_run([DEMO_FUND_A, DEMO_FUND_B])
    summary = summarize_fund_nav_dry_run_results(payload["results"])
    assert len(plan["requests"]) == 2
    assert provider.fetch_many([]) == []
    assert payload["summary"]["dry_run_only_count"] == 2
    assert summary["has_real_nav_data"] is False


def test_markdown_contains_required_disclaimer_and_no_secret_terms_or_real_claims():
    result = fetch_fund_nav_dry_run(DEMO_FUND_A)
    markdown = render_fund_nav_dry_run_markdown(result)
    lowered = markdown.lower()
    assert "最终以基金公司公布净值为准" in markdown
    assert "本阶段仅做 dry-run，不请求真实基金净值" in markdown
    assert "场外基金不支持真正实时价格" in markdown
    assert "本结果不包含真实单位净值、估算净值或涨跌幅" in markdown
    assert "已接入真实基金净值" not in markdown
    assert "真实单位净值" in markdown and "真实单位净值：" not in markdown
    assert "真实估算净值" not in markdown
    assert "真实涨跌幅" not in markdown
    assert "token" not in lowered
    assert "api key" not in lowered
    assert "webhook" not in lowered


def test_serialized_result_does_not_contain_fixture_or_real_provider_status():
    output = json.dumps(fetch_fund_nav_dry_run(DEMO_FUND_A), ensure_ascii=False).lower()
    assert "fixture_unit_nav" not in output
    assert "fixture_estimated_nav" not in output
    assert "real_provider" not in output
