import pytest

from src.asset_model import scan_asset_for_sensitive_values, validate_asset
from src.asset_enrichment import (
    build_enriched_asset_draft,
    detect_enrichment_conflicts,
    enrich_asset,
    enrich_identification_result,
    example_enrichment_provider,
    load_example_enrichment_records,
    merge_enrichment_results,
    validate_provider_result,
)
from src.code_identifier import identify_code


def provider_result(**overrides):
    payload = {
        "provider_name": "fixture_a",
        "provider_type": "fixture",
        "code": "000000",
        "fields": {
            "name": {"value": "示例基金A", "status": "manual_user_input", "confidence": "medium", "reason": "测试 fixture", "sources": []},
            "type": {"value": "fund", "status": "manual_user_input", "confidence": "medium", "reason": "测试 fixture", "sources": []},
            "market": {"value": "CN", "status": "manual_user_input", "confidence": "medium", "reason": "测试 fixture", "sources": []},
            "tags": [{"value": "示例标签", "status": "manual_user_input", "confidence": "medium", "reason": "测试 fixture", "sources": []}],
        },
        "sources": [],
    }
    payload.update(overrides)
    return payload


def test_provider_result_requires_provider_name():
    payload = provider_result(provider_name="")
    with pytest.raises(ValueError):
        validate_provider_result(payload)


def test_provider_result_requires_provider_type():
    payload = provider_result(provider_type="")
    with pytest.raises(ValueError):
        validate_provider_result(payload)


def test_provider_fields_require_status_confidence_reason():
    payload = provider_result()
    assert validate_provider_result(payload)
    for field in [payload["fields"]["name"], payload["fields"]["type"], payload["fields"]["market"], payload["fields"]["tags"][0]]:
        assert field["status"]
        assert field["confidence"]
        assert field["reason"]


def test_no_provider_match_returns_unknown():
    result = enrich_asset("NO_MATCH", providers=[])
    assert result["status"] == "unknown"
    assert result["fields"]["tags"] == []


def test_code_identifier_pending_input_can_generate_pending_enrichment():
    result = enrich_identification_result(identify_code("257070"), providers=[])
    assert result["status"] == "pending_confirmation"
    assert result["needs_user_confirmation"] is True


def test_example_fixture_can_fill_example_name():
    result = enrich_asset("000000")
    assert result["fields"]["name"]["value"] == "示例基金A"


def test_example_fixture_does_not_masquerade_as_official_source():
    provider = example_enrichment_provider("000000")
    assert provider["provider_type"] == "fixture"
    assert provider["provider_type"] != "official"
    assert provider["provider_type"] != "public_web"


def test_example_fixture_is_not_usable_for_formal_analysis():
    result = enrich_asset("000000")
    assert result["usable_for_formal_analysis"] is False


def test_multi_provider_different_field_value_returns_conflict():
    other = provider_result(provider_name="fixture_b")
    other["fields"]["name"]["value"] = "示例基金B"
    merged = merge_enrichment_results([provider_result(), other])
    assert merged["status"] == "conflict"
    assert detect_enrichment_conflicts([provider_result(), other])[0]["field"] == "name"


def test_conflict_requires_user_confirmation():
    other = provider_result(provider_name="fixture_b")
    other["fields"]["market"]["value"] = "US"
    merged = merge_enrichment_results([provider_result(), other])
    assert merged["needs_user_confirmation"] is True


def test_unknown_does_not_generate_tags():
    result = enrich_asset("UNKNOWN", providers=[])
    assert result["fields"]["tags"] == []


def test_enrichment_does_not_fabricate_source_url():
    result = enrich_asset("000000")
    assert result["sources"] == []
    for field in (result["fields"]["name"], result["fields"]["type"], result["fields"]["market"], *result["fields"]["tags"]):
        for source in field["sources"]:
            assert source.get("source_url") in (None, "")


def test_build_enriched_asset_draft_generates_valid_asset():
    identification = identify_code("000000")
    enrichment = enrich_identification_result(identification)
    draft = build_enriched_asset_draft(identification, enrichment)
    validate_asset(draft)
    assert draft["code"] == "000000"
    assert draft["name"] == "示例基金A"


def test_asset_draft_defaults_to_watching():
    draft = build_enriched_asset_draft(identify_code("000000"), enrich_asset("000000"))
    assert draft["status"] == "watching"


def test_asset_draft_defaults_weight_level_to_one():
    draft = build_enriched_asset_draft(identify_code("000000"), enrich_asset("000000"))
    assert draft["weight_level"] == 1


@pytest.mark.parametrize("forbidden", ["amount", "cost_price", "account_value", "webhook", "token", "api_key"])
def test_outputs_do_not_include_sensitive_keys(forbidden):
    result = enrich_asset("000000")
    draft = build_enriched_asset_draft(identify_code("000000"), result)
    assert forbidden not in str(result).lower()
    assert forbidden not in draft
    assert scan_asset_for_sensitive_values(draft) == []


def test_example_records_do_not_include_sensitive_account_data():
    records = load_example_enrichment_records()
    text = str(records).lower()
    for forbidden in ("amount", "cost_price", "account_value", "webhook", "token", "api_key"):
        assert forbidden not in text
