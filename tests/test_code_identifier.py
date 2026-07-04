from src.asset_model import scan_asset_for_sensitive_values, validate_asset
from src.code_identifier import convert_identification_to_asset, identify_code, identify_codes
from src.source_verification import validate_asset_identification_result, validate_source_evidence


def candidate_types(result):
    return {candidate["type"] for candidate in result["candidates"]}


def candidate_markets(result):
    return {candidate["market"] for candidate in result["candidates"]}


def test_257070_returns_pending_without_name_or_tags():
    result = identify_code("257070")
    assert result["status"] == "pending_confirmation"
    assert result["name"]["value"] is None
    assert result["tags"] == []
    assert validate_asset_identification_result(result)


def test_002463_returns_cn_candidate_and_six_digit_types():
    result = identify_code("002463")
    assert "CN" in candidate_markets(result)
    assert {"fund", "stock"}.issubset(candidate_types(result))


def test_hk_suffix_returns_hk_candidate():
    result = identify_code("00700.HK")
    assert result["status"] == "pending_confirmation"
    assert result["candidates"] == [
        {"type": "stock", "market": "HK", "confidence": "medium", "reason": ".HK 后缀可能为港股代码格式。"}
    ]


def test_aapl_returns_us_candidate_without_company_name():
    result = identify_code("AAPL")
    assert "US" in candidate_markets(result)
    assert result["name"]["value"] is None
    assert result["tags"] == []


def test_us_jp_kr_suffixes_return_expected_markets():
    assert candidate_markets(identify_code("ABC.US")) == {"US"}
    assert "JP" in candidate_markets(identify_code("1234.JP"))
    assert "KR" in candidate_markets(identify_code("1234.KR"))


def test_empty_and_illegal_codes_are_unknown():
    assert identify_code("")["status"] == "unknown"
    assert identify_code(None)["status"] == "unknown"
    assert identify_code("ABC-123")["status"] == "unknown"
    assert identify_code("ABC-123")["candidates"] == []


def test_multi_candidate_requires_confirmation_and_is_not_formal():
    result = identify_code("257070")
    assert len(result["candidates"]) > 1
    assert result["needs_user_confirmation"] is True
    assert result["usable_for_formal_analysis"] is False


def test_sources_are_internal_rule_without_fabricated_url():
    result = identify_code("AAPL")
    sources = result["asset_type"]["sources"] + result["market"]["sources"]
    assert sources
    for source in sources:
        assert source["source_name"] == "code_format_rule"
        assert source["source_type"] == "internal_history"
        assert source["source_url"] is None
        assert validate_source_evidence(source)


def test_batch_identification_preserves_order():
    results = identify_codes(["257070", "AAPL", ""])
    assert [result["normalized_code"] for result in results] == ["257070", "AAPL", ""]
    assert [result["status"] for result in results] == ["pending_confirmation", "pending_confirmation", "unknown"]


def test_convert_identification_to_asset_generates_valid_public_safe_draft():
    asset = convert_identification_to_asset(identify_code("257070"))
    validate_asset(asset)
    assert asset["type"] == "unknown"
    assert asset["market"] == "CN"
    assert asset["name"] == ""
    assert asset["tags"] == []
    assert asset["status"] == "watching"
    assert asset["weight_level"] == 1
    assert asset["source_status"] == "pending_confirmation"
    assert scan_asset_for_sensitive_values(asset) == []
    for forbidden in ("amount", "cost_price", "account_value"):
        assert forbidden not in asset
