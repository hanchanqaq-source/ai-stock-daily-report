from copy import deepcopy

from src.account_real_data_final_gate import (
    FUND_ESTIMATE_DISCLAIMER,
    build_account_real_data_final_gate_policy,
    check_unified_summary_field_boundaries,
    render_account_real_data_final_gate_markdown,
    run_account_real_data_final_gate,
    validate_account_real_data_final_gate_policy,
)
from src.account_real_data_unified_summary import build_account_real_data_unified_summary


def demo_group():
    return {
        "account_id": "demo_account",
        "account_name": "示例账户",
        "assets": [
            {"asset_id": "stock_h", "code": "DEMOS", "name": "演示股票", "type": "stock", "market": "CN", "status": "holding"},
            {"asset_id": "fund_h", "code": "DEMOF1", "name": "演示基金", "type": "fund", "market": "CN", "status": "watching"},
        ],
    }


def safe_summary():
    return build_account_real_data_unified_summary(demo_group())


def assert_no_forbidden_values(rendered):
    for word in ["demo-price", "demo-turnover", "demo-unit-nav", "demo-est-nav", "demo-change-pct", "demo-amount", "Token", "API Key", "Webhook"]:
        assert word not in rendered


def test_can_build_final_gate_policy_and_validate_default_block_logic():
    policy = build_account_real_data_final_gate_policy()
    assert validate_account_real_data_final_gate_policy(policy)
    assert policy["default_decision"] == "block"
    assert policy["allow_local_real_display"] is False
    assert "token" in policy["forbidden_secret_fields"]


def test_compliant_redacted_unified_summary_returns_allowed_and_redacted_payload():
    result = run_account_real_data_final_gate(safe_summary())
    assert result["decision"] == "allowed"
    assert result["can_enter_account_page_model"] is True
    assert result["final_page_payload"]["display_mode"] == "redacted"
    assert result["final_page_payload"]["payload_status"] == "safe_for_account_page"
    assert result["can_write_to_public_repo"] is False


def test_warning_summary_returns_allowed_with_warnings_when_no_real_data():
    summary = safe_summary()
    summary["safety_summary"]["default_redacted"] = False
    result = run_account_real_data_final_gate(summary)
    assert result["decision"] == "allowed_with_warnings"
    assert result["default_redacted"] is False
    assert result["warnings"]


def test_all_results_audited_false_is_blocked():
    summary = safe_summary()
    summary["safety_summary"]["all_results_audited"] = False
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_all_display_models_checked_false_is_blocked():
    summary = safe_summary()
    summary["safety_summary"]["all_display_models_checked"] = False
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_default_redacted_false_with_real_data_is_blocked():
    summary = safe_summary()
    summary["safety_summary"]["default_redacted"] = False
    summary["has_real_market_data"] = True
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_real_data_written_to_repo_true_is_blocked():
    summary = safe_summary()
    summary["safety_summary"]["real_data_written_to_repo"] = True
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_secrets_detected_true_is_blocked():
    summary = safe_summary()
    summary["safety_summary"]["secrets_detected"] = True
    result = run_account_real_data_final_gate(summary)
    assert result["decision"] == "blocked"
    assert result["secrets_detected"] is True


def test_token_field_is_blocked():
    summary = safe_summary()
    summary["sections"]["stock_etf"]["token"] = "redacted-test-token"
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_api_key_field_is_blocked():
    summary = safe_summary()
    summary["api_key"] = "redacted-test-key"
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_webhook_field_is_blocked():
    summary = safe_summary()
    summary["sections"]["fund_nav"]["webhook"] = "redacted-test-hook"
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_amount_field_is_blocked():
    summary = safe_summary()
    summary["sections"]["stock_etf"]["display_models"].append({"amount": "demo-amount"})
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_cost_price_field_is_blocked():
    summary = safe_summary()
    summary["sections"]["stock_etf"]["display_models"].append({"cost_price": "demo-cost"})
    assert run_account_real_data_final_gate(summary)["decision"] == "blocked"


def test_personal_money_checker_does_not_false_positive_safe_similar_fields():
    summary = safe_summary()
    summary["weight_level"] = "balanced"
    summary["balanced"] = True
    summary["source_status"] = "fixture_only"
    summary["allow_commit_to_repo"] = False
    assert run_account_real_data_final_gate(summary)["decision"] == "allowed"


def test_fund_realtime_wording_in_display_models_blocks_or_warns():
    summary = safe_summary()
    summary["sections"]["fund_nav"]["display_models"].append({"label": "实时涨跌"})
    result = run_account_real_data_final_gate(summary)
    assert result["decision"] in {"blocked", "allowed_with_warnings"}
    assert result["warnings"] or result["issues"]


def test_missing_fund_estimate_disclaimer_warns():
    summary = safe_summary()
    summary["warnings"] = []
    summary["sections"]["fund_nav"].pop("estimate_warning", None)
    for model in summary["sections"]["fund_nav"].get("display_models", []):
        model.pop("estimate_warning", None)
        model.pop("warnings", None)
    result = run_account_real_data_final_gate(summary)
    assert result["decision"] == "allowed_with_warnings"
    assert FUND_ESTIMATE_DISCLAIMER in result["warnings"]


def test_stock_etf_and_fund_field_boundaries_pass():
    checked = check_unified_summary_field_boundaries(safe_summary())
    assert checked["ok"] is True
    assert checked["issues"] == []


def test_mixed_field_boundaries_create_issue():
    summary = safe_summary()
    summary["sections"]["stock_etf"]["field_boundary"].append("单位净值")
    summary["sections"]["fund_nav"]["field_boundary"].append("成交额")
    result = run_account_real_data_final_gate(summary)
    assert result["decision"] == "blocked"
    assert result["field_boundary_ok"] is False


def test_blocked_payload_does_not_contain_real_values():
    summary = safe_summary()
    summary["safety_summary"]["all_results_audited"] = False
    summary["sections"]["stock_etf"]["display_models"].append({"quote_display": {"最新价": "demo-price", "成交额": "demo-turnover"}})
    summary["sections"]["fund_nav"]["display_models"].append({"nav_display": {"单位净值": "demo-unit-nav"}, "estimate_display": {"估算净值": "demo-est-nav", "涨跌幅": "demo-change-pct"}, "amount": "demo-amount"})
    rendered = repr(run_account_real_data_final_gate(summary)["final_page_payload"])
    assert_no_forbidden_values(rendered)


def test_input_summary_is_not_mutated():
    summary = safe_summary()
    before = deepcopy(summary)
    run_account_real_data_final_gate(summary)
    assert summary == before


def test_markdown_is_safe_and_contains_required_disclaimers():
    result = run_account_real_data_final_gate(safe_summary())
    markdown = render_account_real_data_final_gate_markdown(result)
    assert_no_forbidden_values(markdown)
    assert "最终以基金公司公布净值为准" in markdown
    assert "不构成交易建议" in markdown
    assert "最终安全闸门通过后，数据才允许进入账户页面模型" in markdown
