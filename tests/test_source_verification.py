from src.source_verification import (
    is_result_usable_for_formal_analysis,
    is_tag_usable_for_formal_analysis,
    mark_conflict,
    mark_unknown,
    normalize_confidence,
    validate_asset_identification_result,
    validate_source_evidence,
    validate_verified_field,
)

CHECKED_AT = "2026-07-04T00:00:00"


def source(source_type="market_data", **overrides):
    payload = {
        "source_name": "示例公开来源",
        "source_type": source_type,
        "source_url": None,
        "checked_at": CHECKED_AT,
        "evidence_text": "仅用于结构校验的示例证据，不代表真实联网查询。",
        "confidence": "high",
    }
    payload.update(overrides)
    return payload


def field(status="verified", value="示例值", sources=None, **overrides):
    payload = {
        "value": value,
        "status": status,
        "confidence": "high" if status == "verified" else "low",
        "sources": [source()] if sources is None and status == "verified" else (sources or []),
        "reason": "结构校验原因",
    }
    payload.update(overrides)
    return payload


def result(**overrides):
    payload = {
        "code": "000000",
        "status": "verified",
        "asset_type": field(value="stock"),
        "name": field(value="示例资产"),
        "market": field(value="CN"),
        "tags": [field(value="示例标签")],
        "needs_user_confirmation": False,
        "usable_for_formal_analysis": True,
    }
    payload.update(overrides)
    return payload


def test_verified_field_requires_source():
    assert not validate_verified_field(field(sources=[]))


def test_unknown_field_can_skip_source_but_requires_reason():
    assert validate_verified_field(mark_unknown("未能确认"))
    assert not validate_verified_field(field(status="unknown", value=None, reason=""))


def test_pending_confirmation_requires_reason():
    assert validate_verified_field(field(status="pending_confirmation", value="候选", reason="需要用户确认"))
    assert not validate_verified_field(field(status="pending_confirmation", value="候选", reason=""))


def test_conflict_requires_reason_or_conflict_sources():
    assert validate_verified_field(mark_conflict("来源冲突", [source(), source(source_name="另一个来源")]))
    assert not validate_verified_field(field(status="conflict", value=None, sources=[], reason=""))


def test_confidence_only_allows_known_levels():
    assert normalize_confidence("medium") == "medium"
    assert normalize_confidence("certain") == "low"
    assert not validate_verified_field(field(confidence="certain"))


def test_source_type_must_be_allowed():
    assert validate_source_evidence(source("official"))
    assert not validate_source_evidence(source("rumor"))


def test_source_name_is_required():
    assert not validate_source_evidence(source(source_name=""))


def test_checked_at_is_required():
    assert not validate_source_evidence(source(checked_at=""))


def test_verified_asset_type_name_market_are_usable():
    payload = result()
    assert validate_asset_identification_result(payload)
    assert is_result_usable_for_formal_analysis(payload)


def test_asset_type_unknown_is_not_usable():
    payload = result(asset_type=mark_unknown("未能确认类型"), status="unknown")
    assert validate_asset_identification_result(payload)
    assert not is_result_usable_for_formal_analysis(payload)


def test_name_pending_confirmation_is_not_usable():
    payload = result(name=field(status="pending_confirmation", value="候选名称", reason="低置信度"))
    assert validate_asset_identification_result(payload)
    assert not is_result_usable_for_formal_analysis(payload)


def test_market_conflict_is_not_usable():
    payload = result(market=mark_conflict("市场归属来源冲突", [source(), source(source_name="另一个来源")]))
    assert validate_asset_identification_result(payload)
    assert not is_result_usable_for_formal_analysis(payload)


def test_unknown_tag_is_not_formal_analysis_input():
    tag = mark_unknown("未能确认标签")
    assert validate_verified_field(tag)
    assert not is_tag_usable_for_formal_analysis(tag)


def test_manual_user_input_tag_is_allowed_but_not_public_source():
    tag = field(value="用户自定义标签", sources=[source("manual_user_input", source_name="用户手动输入")])
    assert validate_verified_field(tag)
    assert is_tag_usable_for_formal_analysis(tag)
    assert tag["sources"][0]["source_type"] == "manual_user_input"


def test_auto_tag_without_source_cannot_be_verified():
    tag = field(value="自动标签", sources=[])
    assert not validate_verified_field(tag)
    assert not is_tag_usable_for_formal_analysis(tag)


def test_webhook_is_not_saved_in_evidence():
    bad = source(source_url="https://discord.com/api/webhooks/example/secret")
    assert not validate_source_evidence(bad)


def test_token_is_not_saved_in_evidence():
    bad = source(evidence_text="github_pat_example_token")
    assert not validate_source_evidence(bad)


def test_api_key_is_not_saved_in_evidence():
    bad = source(evidence_text="sk-example-api-key")
    assert not validate_source_evidence(bad)


def test_user_amount_is_not_saved_in_result():
    payload = result(user_amount=10000)
    assert not validate_asset_identification_result(payload)
