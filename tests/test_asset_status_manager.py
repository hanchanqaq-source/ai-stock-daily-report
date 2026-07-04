from __future__ import annotations

from copy import deepcopy
import json

from src.account_groups import validate_account_group
from src.asset_model import validate_asset
from src.asset_status_manager import (
    apply_asset_status_change,
    find_asset_for_status_change,
    get_status_change_risk_level,
    preview_asset_status_change,
)


def asset(asset_id, code, status="watching", name="示例基金A"):
    return {
        "asset_id": asset_id,
        "type": "fund",
        "code": code,
        "name": name,
        "market": "CN",
        "tags": ["示例"],
        "status": status,
        "weight_level": 3,
        "source_status": "manual_user_input",
    }


def group(*assets):
    return {
        "account_id": "demo_group",
        "account_name": "示例分组",
        "enabled": True,
        "risk_profile": "balanced",
        "description": "仅用于测试的公开安全示例分组",
        "assets": list(assets),
    }


def assert_no_sensitive_payload(payload):
    text = json.dumps(payload, ensure_ascii=False).lower()
    blocked = ["amount", "cost_price", "account_value", "webhook", "token", "api_key", "apikey", "成本价", "账户资产"]
    for word in blocked:
        assert word not in text


def test_preview_does_not_modify_group():
    original = group(asset("demo_fund_001", "000000", "holding"))
    before = deepcopy(original)
    preview = preview_asset_status_change(original, asset_id="demo_fund_001", to_status="cleared", reason="用户准备清仓")
    assert preview["status"] == "preview"
    assert preview["will_apply"] is False
    assert preview["risk_level"] == "medium"
    assert original == before


def test_confirm_false_does_not_apply_status_change():
    original = group(asset("demo_fund_001", "000000", "holding"))
    result = apply_asset_status_change(original, asset_id="demo_fund_001", to_status="cleared", confirm=False)
    assert result["status"] == "blocked"
    assert result["will_apply"] is False
    assert original["assets"][0]["status"] == "holding"


def test_confirm_true_applies_status_change_with_structured_result():
    original = group(asset("demo_fund_001", "000000", "holding"))
    result = apply_asset_status_change(original, asset_id="demo_fund_001", to_status="cleared", reason="用户准备清仓", confirm=True)
    assert result["status"] == "applied"
    assert result["will_apply"] is True
    assert result["from_status"] == "holding"
    assert result["to_status"] == "cleared"
    assert result["changed_at"]
    assert result["reason"] == "用户准备清仓"
    assert result["updated_asset"]["status"] == "cleared"
    assert result["updated_group"]["assets"][0]["status"] == "cleared"
    validate_asset(result["updated_asset"])
    validate_account_group(result["updated_group"])


def test_allowed_status_transitions():
    cases = [
        ("watching", "holding"),
        ("holding", "watching"),
        ("holding", "cleared"),
        ("cleared", "watching"),
        ("watching", "archived"),
        ("archived", "watching"),
    ]
    for from_status, to_status in cases:
        original = group(asset("demo_fund_001", "000000", from_status))
        result = apply_asset_status_change(original, asset_id="demo_fund_001", to_status=to_status, confirm=True)
        assert result["status"] == "applied"
        assert result["from_status"] == from_status
        assert result["to_status"] == to_status


def test_deleted_transitions_are_high_risk_and_do_not_remove_asset():
    original = group(asset("demo_watch_001", "000001", "watching"), asset("demo_hold_001", "000002", "holding"))
    preview = preview_asset_status_change(original, asset_id="demo_watch_001", to_status="deleted")
    assert preview["risk_level"] == "high"
    assert "不会物理删除文件" in "".join(preview["impact"])

    applied = apply_asset_status_change(original, asset_id="demo_watch_001", to_status="deleted", confirm=True)
    assert applied["status"] == "applied"
    assert len(applied["updated_group"]["assets"]) == 2
    assert applied["updated_group"]["assets"][0]["status"] == "deleted"

    holding_preview = preview_asset_status_change(original, asset_id="demo_hold_001", to_status="deleted")
    assert holding_preview["risk_level"] == "high"
    assert holding_preview["requires_double_confirm"] is True
    assert holding_preview["status"] == "blocked"


def test_asset_id_exact_match_and_code_single_match():
    original = group(asset("demo_fund_001", "000000", "watching"), asset("demo_fund_002", "000002", "holding"))
    by_id = find_asset_for_status_change(original, asset_id="demo_fund_002")
    assert by_id["status"] == "found"
    assert by_id["asset"]["asset_id"] == "demo_fund_002"

    by_code = find_asset_for_status_change(original, code="000000")
    assert by_code["status"] == "found"
    assert by_code["asset"]["asset_id"] == "demo_fund_001"


def test_code_conflict_requires_asset_id():
    original = group(asset("demo_fund_001", "000000"), asset("demo_fund_002", "000000", name="示例基金B"))
    result = find_asset_for_status_change(original, code="000000")
    assert result["status"] == "conflict"
    assert len(result["matches"]) == 2


def test_not_found_and_invalid_request():
    original = group(asset("demo_fund_001", "000000"))
    assert find_asset_for_status_change(original, asset_id="missing")["status"] == "not_found"
    assert find_asset_for_status_change(original, code="111111")["status"] == "not_found"
    assert find_asset_for_status_change(original)["status"] == "invalid_request"


def test_risk_levels():
    assert get_status_change_risk_level("watching", "holding") == "low"
    assert get_status_change_risk_level("holding", "cleared") == "medium"
    assert get_status_change_risk_level("watching", "deleted") == "high"
    assert get_status_change_risk_level("holding", "deleted") == "high"


def test_output_contains_no_sensitive_money_or_secret_fields():
    original = group(asset("demo_fund_001", "000000", "holding"))
    preview = preview_asset_status_change(original, asset_id="demo_fund_001", to_status="cleared", reason="用户准备清仓")
    result = apply_asset_status_change(original, asset_id="demo_fund_001", to_status="cleared", reason="用户准备清仓", confirm=True)
    assert_no_sensitive_payload(preview)
    assert_no_sensitive_payload(result)
