import json

import pytest

from src.provider_safety import (
    build_provider_cache_policy,
    build_provider_failure_policy,
    build_provider_safety_policy,
    build_provider_source_metadata,
    classify_provider_data_mode,
    is_network_provider_enabled,
    is_sensitive_field_name,
    scan_provider_config_for_secrets,
    validate_cache_policy,
    validate_failure_result,
    validate_provider_config,
    validate_provider_result,
    validate_source_metadata,
    assert_fixture_not_marked_real,
)


def test_fixture_and_mock_providers_do_not_need_network():
    assert is_network_provider_enabled({"provider_type": "fixture", "enabled": True}) is False
    assert is_network_provider_enabled({"provider_type": "mock", "enabled": True}) is False


def test_public_web_and_api_providers_are_disabled_by_default():
    assert is_network_provider_enabled({"provider_type": "public_web"}) is False
    assert is_network_provider_enabled({"provider_type": "api"}) is False


def test_api_provider_rejects_plaintext_token_and_sensitive_names():
    config = {"provider_type": "api", "token": "plain-token"}
    assert "api provider config contains plaintext secret fields" in validate_provider_config(config)
    assert scan_provider_config_for_secrets(config) == ["token"]
    for field in ["webhook", "api_key", "password", "secret"]:
        assert is_sensitive_field_name(field)


def test_provider_type_to_data_mode_classification():
    assert classify_provider_data_mode({"provider_type": "fixture"}) == "fixture_only"
    assert classify_provider_data_mode({"provider_type": "mock"}) == "mock_only"
    assert classify_provider_data_mode({"provider_type": "public_web"}) == "real_provider"
    assert classify_provider_data_mode({"provider_type": "api"}) == "real_provider"
    assert classify_provider_data_mode({"provider_type": "local_cache"}) == "real_provider_cached"


def test_fixture_and_mock_cannot_be_marked_real_provider():
    assert "fixture provider cannot be marked real_provider" in validate_provider_config({"provider_type": "fixture", "data_mode": "real_provider"})
    assert "mock provider cannot be marked real_provider" in validate_provider_config({"provider_type": "mock", "data_mode": "real_provider"})
    assert "fixture_only cannot be marked real_provider" in validate_provider_result({"provider_type": "fixture", "data_mode": "real_provider"})
    assert "mock_only cannot be marked real_provider" in validate_provider_result({"provider_type": "mock", "data_mode": "real_provider"})


def test_real_provider_requires_provider_checked_at_and_source_status():
    errors = validate_provider_result({"data_mode": "real_provider", "provider": "p", "source_status": "real_provider"})
    assert "real_provider requires checked_at" in errors
    errors = validate_provider_result({"data_mode": "real_provider", "checked_at": "2026-01-01T00:00:00+00:00", "source_status": "real_provider"})
    assert "real_provider requires provider" in errors


def test_real_provider_cached_requires_cache_expires_at():
    errors = validate_provider_result({"data_mode": "real_provider_cached", "cache_checked_at": "2026-01-01T00:00:00+00:00"})
    assert "real_provider_cached requires cache_expires_at" in errors


def test_cache_defaults_local_only_and_public_repo_commit_is_forbidden():
    quote_policy = build_provider_cache_policy("example", "realtime_quote")
    fund_policy = build_provider_cache_policy("example", "fund_nav")
    assert quote_policy["cache_scope"] == "local_only"
    assert quote_policy["allow_commit_to_repo"] is False
    assert fund_policy["allow_commit_to_repo"] is False
    assert validate_cache_policy(quote_policy) == []


def test_failure_results_require_reason_checked_at_and_conflict_warning():
    assert "failure result requires reason" in validate_failure_result({"source_status": "provider_error"})
    assert "stale_data requires checked_at" in validate_failure_result({"source_status": "stale_data", "reason": "old cache"})
    assert "conflict requires warning" in validate_failure_result({"source_status": "conflict", "reason": "two providers disagree"})
    policy = build_provider_failure_policy("example")
    assert policy["fail_whole_account_page"] is False
    assert policy["fail_other_assets"] is False


def test_fund_nav_result_cannot_use_realtime_quote_wording_or_mode():
    assert "fund_nav result cannot use realtime_quote" in validate_provider_result({"data_kind": "fund_nav", "price_mode": "realtime_quote"})
    safe_text = "单位净值、累计净值、日涨跌幅、估算净值、估算涨跌、净值日期、估算更新时间"
    assert "实时基金涨跌" not in safe_text


def test_fixture_data_cannot_claim_real_market_data():
    with pytest.raises(ValueError):
        assert_fixture_not_marked_real({"provider_type": "fixture", "has_real_market_data": True})


def test_source_metadata_validation_and_mixed_warning():
    source = build_provider_source_metadata("fixture_provider", "fixture", "fixture_only")
    assert validate_source_metadata(source) == []
    assert "mixed_real_and_fixture source metadata requires warning" in validate_source_metadata(
        {"provider": "mixed", "provider_type": "public_web", "data_mode": "mixed_real_and_fixture", "source_status": "conflict"}
    )


def test_safety_policy_output_contains_no_secret_labels():
    rendered = json.dumps(build_provider_safety_policy(), ensure_ascii=False)
    assert "Token" not in rendered
    assert "API Key" not in rendered
    assert "Webhook" not in rendered
