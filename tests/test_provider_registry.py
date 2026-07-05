import json

import pytest

from src.provider_registry import (
    build_cn_quote_provider_evaluation,
    build_provider_field_mapping,
    build_provider_registry,
    get_provider_candidates,
    render_provider_registry_markdown,
    validate_cn_quote_provider_evaluation,
    validate_provider_registry,
)

REAL_PROVIDERS = {"akshare", "eastmoney", "sina_finance", "tencent_finance"}
UNIFIED_FIELDS = {
    "last_price",
    "change_pct",
    "change_amount",
    "volume",
    "turnover",
    "open",
    "high",
    "low",
    "previous_close",
    "checked_at",
    "source_provider",
    "source_status",
}


def _by_name(registry):
    return {item["provider_name"]: item for item in registry["providers"]}


def test_provider_registry_generates_required_candidates():
    registry = build_provider_registry()
    validate_provider_registry(registry)
    providers = _by_name(registry)

    assert {"akshare", "eastmoney", "sina_finance", "tencent_finance", "local_fixture"}.issubset(providers)


def test_real_provider_safety_defaults_are_closed_and_local_only():
    providers = _by_name(build_provider_registry())

    for name in REAL_PROVIDERS:
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
        assert candidate["cache_policy"]["allow_commit_to_repo"] is False
        assert candidate["failure_policy"]["fallback"]["allow_fixture_fallback"] is False
        assert candidate["failure_policy"]["fallback"]["allow_stale_cache"] is False


def test_local_fixture_is_test_only_and_not_real_provider():
    fixture = _by_name(build_provider_registry())["local_fixture"]

    assert fixture["network_required"] is False
    assert fixture["status"] == "supported_for_tests"
    assert fixture["provider_type"] == "fixture"
    assert fixture["data_mode_if_enabled"] != "real_provider"
    assert fixture["enablement_policy"]["requires_network_enabled"] is False


def test_candidates_include_required_policy_sections():
    for candidate in build_provider_registry()["providers"]:
        assert candidate["risk_level"]
        assert candidate["enablement_policy"]
        assert candidate["cache_policy"]
        assert candidate["failure_policy"]
        assert candidate["field_mapping"]
        assert candidate["dry_run_plan"]


def test_get_provider_candidates_filters_by_market_and_asset_type():
    cn_etf = get_provider_candidates(market="CN", asset_type="etf")
    names = {item["provider_name"] for item in cn_etf}

    assert REAL_PROVIDERS.issubset(names)
    assert "local_fixture" in names
    assert get_provider_candidates(market="US") == []


def test_field_mapping_contains_only_unified_plan_without_market_payload():
    mapping = build_provider_field_mapping("akshare")

    assert mapping["mapping_status"] == "planned"
    assert set(mapping["quote_result_template"]) == UNIFIED_FIELDS
    assert set(mapping["required_fields"]).issubset(UNIFIED_FIELDS)
    assert set(mapping["optional_fields"]).issubset(UNIFIED_FIELDS)
    assert mapping["unsupported_fields"] == []

    rendered = json.dumps(mapping, ensure_ascii=False).lower()
    forbidden = ["provider payload", "sample", "成交额样本"]
    assert not any(term in rendered for term in forbidden)


@pytest.mark.parametrize("forbidden", ["api_key", "webhook", "authorization", "bearer", "cookie"])
def test_registry_does_not_include_secret_or_hook_fields(forbidden):
    rendered = json.dumps(build_provider_registry(), ensure_ascii=False).lower()

    assert forbidden not in rendered


def test_render_markdown_is_evaluation_only_and_has_no_real_market_values():
    markdown = render_provider_registry_markdown(build_provider_registry())

    assert "不代表已经接入或验证真实 provider" in markdown
    assert "已接入" not in markdown.replace("不代表已经接入", "")
    forbidden = ["真实价格", "真实涨跌幅", "真实成交额", "price: ", "change_pct: ", "turnover: "]
    assert not any(term in markdown for term in forbidden)


def test_cn_quote_provider_evaluation_validates_preflight_and_route():
    evaluation = build_cn_quote_provider_evaluation()

    validate_cn_quote_provider_evaluation(evaluation)
    assert evaluation["status"] == "evaluation_only"
    assert set(evaluation["preflight_checks"]) >= {
        "provider_safety",
        "field_mapping",
        "timeout",
        "retry",
        "cache_policy",
        "source_metadata",
    }
    assert evaluation["conflict_policy"]["status"] == "conflict"
    assert evaluation["conflict_policy"]["preserve_warning"] is True
