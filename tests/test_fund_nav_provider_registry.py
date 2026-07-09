import json

from src.fund_nav_provider import FixtureFundNavProvider
from src.fund_nav_provider_registry import (
    build_fund_nav_field_mapping,
    build_fund_nav_provider_evaluation,
    build_fund_nav_provider_registry,
    get_fund_nav_provider_candidates,
    get_fund_nav_provider_evaluation,
    render_fund_nav_provider_registry_markdown,
    validate_fund_nav_provider_registry,
)
from src.provider_safety import validate_provider_config


def _providers_by_name():
    return {item["provider_name"]: item for item in build_fund_nav_provider_registry()["providers"]}


def test_registry_builds_and_contains_expected_candidates():
    registry = build_fund_nav_provider_registry()
    validate_fund_nav_provider_registry(registry)
    providers = _providers_by_name()
    assert set(providers) == {
        "eastmoney_fund",
        "tiantian_fund",
        "fund_company_official",
        "ant_fund_manual",
        "local_fund_nav_fixture",
    }


def test_real_provider_defaults_are_closed_network_gated_and_local_only():
    providers = _providers_by_name()
    for name in ("eastmoney_fund", "tiantian_fund", "fund_company_official"):
        candidate = providers[name]
        assert candidate["default_enabled"] is False
        assert candidate["network_required"] is True
        assert candidate["allow_commit_to_repo"] is False
        assert candidate["cache_scope"] == "local_only"
        assert candidate["status"] != "verified"
        assert candidate["risk_level"]
        assert candidate["enablement_policy"]["requires_network_enabled"] is True
        assert candidate["enablement_policy"]["allow_public_repo_write"] is False
        assert candidate["enablement_policy"]["allow_real_data_in_tests"] is False
        assert candidate["enablement_policy"]["allowed_modes"] == ["dry_run", "local_only"]


def test_manual_provider_requires_review_and_public_repo_is_closed():
    candidate = _providers_by_name()["ant_fund_manual"]
    assert candidate["status"] == "manual_review_only"
    assert candidate["default_enabled"] is False
    assert candidate["allow_commit_to_repo"] is False
    assert candidate["cache_scope"] == "local_only"
    assert "不抓取个人支付宝数据" in candidate["notes"]


def test_local_fixture_is_supported_for_tests_without_network_and_not_real_provider():
    candidate = _providers_by_name()["local_fund_nav_fixture"]
    assert candidate["network_required"] is False
    assert candidate["status"] == "supported_for_tests"
    assert candidate["default_enabled"] is True
    assert candidate["data_mode_if_enabled"] != "real_provider"
    assert candidate["enablement_policy"]["allowed_modes"] == ["fixture_only"]


def test_candidates_include_required_plans_and_policies():
    for candidate in build_fund_nav_provider_registry()["providers"]:
        assert candidate["risk_level"]
        assert candidate["field_mapping"]
        assert candidate["enablement_policy"]
        assert candidate["cache_policy"]
        assert candidate["failure_policy"]
        assert candidate["requires_source_metadata"] is True
        assert candidate["requires_final_nav_disclaimer"] is True


def test_field_mapping_contains_daily_and_estimated_nav_plans():
    mapping = build_fund_nav_field_mapping("eastmoney_fund")
    assert {"unit_nav", "accumulated_nav", "daily_change_pct", "nav_date"}.issubset(mapping["daily_nav_fields"])
    assert {"estimated_nav", "estimated_change_pct", "estimated_change_amount", "estimate_time"}.issubset(mapping["estimated_nav_fields"])
    assert "本阶段仅定义字段映射计划" in mapping["notes"][0]


def test_cache_policy_defines_daily_and_estimated_nav_ttl_and_stale_policy():
    candidate = _providers_by_name()["eastmoney_fund"]
    policies = {item["data_kind"]: item for item in candidate["cache_policy"]["policies"]}
    assert policies["daily_nav"]["ttl_seconds"] == 86400
    assert policies["estimated_nav"]["ttl_seconds"] == 300
    assert policies["daily_nav"]["cache_scope"] == "local_only"
    assert policies["estimated_nav"]["allow_commit_to_repo"] is False
    assert policies["daily_nav"]["stale_policy"] == "mark_stale_not_available"


def test_failure_policy_preserves_unavailable_and_conflict_semantics():
    policy = _providers_by_name()["eastmoney_fund"]["failure_policy"]
    assert policy["failure_policy"]["timeout"] == "provider_timeout"
    assert policy["failure_policy"]["network_error"] == "provider_error"
    assert policy["failure_policy"]["rate_limit"] == "rate_limited"
    assert policy["failure_policy"]["old_cache"] == "stale_data"
    assert policy["failure_policy"]["provider_conflict"] == "conflict"
    assert policy["failure_policy"]["estimate_missing"] == "estimate_unavailable"
    assert policy["failure_policy"]["daily_nav_missing"] == "daily_nav_unavailable"
    assert policy["fallback"]["allow_fixture_fallback"] is False
    assert policy["fallback"]["allow_stale_cache"] is False
    assert policy["fallback"]["preserve_conflict_warning"] is True
    assert policy["fallback"]["estimate_unavailable_keeps_daily_nav"] is True


def test_registry_filters_by_market_and_nav_type():
    cn_candidates = get_fund_nav_provider_candidates(market="CN")
    estimated_candidates = get_fund_nav_provider_candidates(nav_type="estimated_nav")
    assert len(cn_candidates) == 5
    assert "fund_company_official" not in {item["provider_name"] for item in estimated_candidates}
    assert get_fund_nav_provider_evaluation("eastmoney_fund")["provider_name"] == "eastmoney_fund"


def test_evaluation_has_required_preflight_checks_and_route():
    evaluation = build_fund_nav_provider_evaluation()
    assert evaluation["status"] == "evaluation_only"
    assert {"provider_safety", "field_mapping", "timeout", "retry", "cache_policy", "source_metadata", "fund_disclaimer"}.issubset(evaluation["preflight_checks"])
    assert "P5-R1" in evaluation["future_route"][0]


def test_registry_json_does_not_include_secret_fields_or_real_samples():
    rendered = json.dumps(build_fund_nav_provider_registry(), ensure_ascii=False).lower()
    for forbidden in ("api_key", "webhook", "cookie", "authorization", "bearer"):
        assert forbidden not in rendered
    # No real provider payload sample or numeric NAV sample should be stored.
    assert "provider_payload" not in rendered
    assert "real_nav_sample" not in rendered


def test_markdown_demo_is_safe_and_does_not_claim_real_provider_connected():
    markdown = render_fund_nav_provider_registry_markdown(build_fund_nav_provider_registry())
    assert "本阶段仅做 provider 接入评估，不请求真实基金净值。" in markdown
    assert "场外基金不支持真正实时价格。" in markdown
    assert "最终以基金公司公布净值为准" in markdown
    assert "真实净值和估算净值不得写入 public 仓库" in markdown
    assert "已接入" not in markdown
    assert "已验证" not in markdown
    assert "实时涨跌" not in markdown
    for forbidden in ("api_key", "webhook", "cookie", "authorization", "bearer"):
        assert forbidden not in markdown.lower()


def test_provider_safety_still_blocks_fixture_marked_real_provider():
    errors = validate_provider_config({"provider_type": "fixture", "data_mode": "real_provider"})
    assert "fixture provider cannot be marked real_provider" in errors


def test_fund_nav_provider_fixture_still_uses_fixture_values_only():
    provider = FixtureFundNavProvider()
    assert provider.name == "fixture_fund_nav"
    assert provider.provider_type == "fixture"
