import pytest

from src.account_groups import validate_asset as validate_account_group_asset
from src.asset_model import (
    AssetModelError,
    build_asset_public_safe_view,
    build_asset_summary,
    get_allowed_asset_statuses,
    get_allowed_asset_types,
    get_allowed_markets,
    get_allowed_source_statuses,
    group_assets_by_status,
    group_assets_by_type,
    is_active_asset,
    normalize_asset,
    scan_asset_for_sensitive_values,
    validate_asset,
)


def asset(**overrides):
    base = {
        "asset_id": "demo_asset_001",
        "type": "fund",
        "code": "000000",
        "name": "示例基金A",
        "market": "CN",
        "tags": ["示例标签"],
        "status": "holding",
        "weight_level": 3,
        "source_status": "manual_user_input",
        "notes": None,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("asset_type", get_allowed_asset_types())
def test_allowed_asset_type_validation(asset_type):
    validate_asset(asset(type=asset_type))


def test_invalid_asset_type_fails():
    with pytest.raises(AssetModelError):
        validate_asset(asset(type="crypto"))


@pytest.mark.parametrize("market", get_allowed_markets())
def test_allowed_market_validation(market):
    validate_asset(asset(market=market))


def test_invalid_market_fails():
    with pytest.raises(AssetModelError):
        validate_asset(asset(market="TW"))


@pytest.mark.parametrize("status", get_allowed_asset_statuses())
def test_allowed_status_validation(status):
    validate_asset(asset(status=status))


def test_invalid_status_fails():
    with pytest.raises(AssetModelError):
        validate_asset(asset(status="sold"))


@pytest.mark.parametrize("source_status", get_allowed_source_statuses())
def test_allowed_source_status_validation(source_status):
    validate_asset(asset(source_status=source_status))


def test_invalid_source_status_fails():
    with pytest.raises(AssetModelError):
        validate_asset(asset(source_status="auto_verified"))


@pytest.mark.parametrize("weight_level", [1, 2, 3, 4, 5])
def test_weight_level_must_be_one_to_five(weight_level):
    validate_asset(asset(weight_level=weight_level))


@pytest.mark.parametrize("weight_level", [0, 6, "3"])
def test_invalid_weight_level_fails(weight_level):
    with pytest.raises(AssetModelError):
        validate_asset(asset(weight_level=weight_level))


def test_weight_level_is_not_misclassified_as_money():
    assert scan_asset_for_sensitive_values(asset(weight_level=5)) == []


def test_balanced_is_not_misclassified_as_balance():
    assert scan_asset_for_sensitive_values({"risk_profile": "balanced"}) == []


@pytest.mark.parametrize("field", ["amount", "cost_price", "account_value"])
def test_sensitive_money_fields_are_detected(field):
    assert scan_asset_for_sensitive_values(asset(**{field: 1000}))


def test_webhook_url_is_detected():
    assert scan_asset_for_sensitive_values(asset(notes="https://example.com/webhook/abc"))


@pytest.mark.parametrize("payload", [{"token": "token=abcdefghijklmnop123456"}, {"api_key": "api_key=abcdefghijklmnop123456"}])
def test_token_and_api_key_are_detected(payload):
    assert scan_asset_for_sensitive_values(asset(**payload))


@pytest.mark.parametrize("status, expected", [("holding", True), ("watching", True), ("cleared", False), ("archived", False), ("deleted", False)])
def test_active_status_rules(status, expected):
    assert is_active_asset(asset(status=status)) is expected


def test_group_assets_by_type_works():
    assets = [asset(asset_id="a1", type="fund"), asset(asset_id="a2", type="stock")]
    grouped = group_assets_by_type(assets)
    assert [item["asset_id"] for item in grouped["fund"]] == ["a1"]
    assert [item["asset_id"] for item in grouped["stock"]] == ["a2"]
    assert "etf" in grouped


def test_group_assets_by_status_works():
    assets = [asset(asset_id="a1", status="holding"), asset(asset_id="a2", status="watching")]
    grouped = group_assets_by_status(assets)
    assert [item["asset_id"] for item in grouped["holding"]] == ["a1"]
    assert [item["asset_id"] for item in grouped["watching"]] == ["a2"]


def test_build_asset_summary_outputs_stable_counts():
    assets = [
        asset(asset_id="a1", type="fund", status="holding"),
        asset(asset_id="a2", type="stock", status="watching"),
        asset(asset_id="a3", type="company", status="cleared"),
        asset(asset_id="a4", type="theme", status="deleted"),
    ]
    summary = build_asset_summary(assets)
    assert summary["total"] == 3
    assert summary["by_type"]["fund"] == 1
    assert summary["by_type"]["stock"] == 1
    assert summary["by_type"]["theme"] == 0
    assert summary["by_status"]["deleted"] == 1
    assert summary["active_count"] == 2
    assert summary["holding_count"] == 1
    assert summary["watching_count"] == 1
    assert summary["has_funds"] is True
    assert summary["has_stocks"] is True
    assert summary["warnings"] == []


def test_public_safe_view_excludes_sensitive_fields():
    view = build_asset_public_safe_view(asset(notes="public note"))
    assert set(view) == {"asset_id", "type", "code", "name", "market", "tags", "status", "weight_level", "source_status"}
    assert "notes" not in view


def test_public_safe_view_rejects_sensitive_fields():
    with pytest.raises(AssetModelError):
        build_asset_public_safe_view(asset(amount=1000))


def test_normalize_asset_keeps_required_fields_and_enums():
    normalized = normalize_asset({"asset_id": "a1", "type": " FUND ", "name": "示例", "market": "cn", "weight_level": 1})
    assert normalized["type"] == "fund"
    assert normalized["market"] == "CN"
    assert normalized["code"] == ""
    assert normalized["source_status"] == "manual_user_input"


def test_account_groups_reuse_asset_model_validation():
    validate_account_group_asset(asset(type="etf", market="GLOBAL", status="deleted"))
    with pytest.raises(Exception):
        validate_account_group_asset(asset(amount=1000))
