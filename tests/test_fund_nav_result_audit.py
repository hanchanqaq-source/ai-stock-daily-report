from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

from src.fund_nav_result_audit import (
    ESTIMATE_DISCLAIMER,
    audit_fund_nav_result,
    audit_fund_nav_results,
    build_fund_nav_audit_summary,
    check_fund_nav_result_freshness,
    redact_fund_nav_result_for_audit,
    render_fund_nav_audit_markdown,
    scan_fund_nav_result_for_sensitive_fields,
    validate_fund_nav_audit_result,
)


def _now(delta_seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).replace(microsecond=0).isoformat()


def _result(**overrides):
    data = {
        "asset_id": "demo_fund_001",
        "code": "000000",
        "name": "示例场外基金A",
        "type": "fund",
        "market": "CN",
        "provider_name": "eastmoney_fund",
        "data_status": "real_provider_available",
        "data_mode": "real_provider",
        "has_real_nav_data": True,
        "nav": {"unit_nav": "DEMO_UNIT_NAV", "accumulated_nav": "DEMO_ACC_NAV", "daily_change_pct": "DEMO_DAILY_CHANGE", "nav_date": "2099-01-01"},
        "estimate": {"estimated_nav": "DEMO_EST_NAV", "estimated_change_pct": "DEMO_EST_CHANGE", "estimated_change_amount": "DEMO_EST_AMOUNT", "estimate_time": _now()},
        "source": {"provider": "eastmoney_fund", "source_status": "real_provider", "checked_at": _now()},
        "provider_checks": {"allow_commit_to_repo": False, "cache_scope": "local_only", "network_enabled": True, "allow_real_request": True},
        "warnings": [ESTIMATE_DISCLAIMER],
        "disclaimer": "本结果仅用于本地观察。" + ESTIMATE_DISCLAIMER,
    }
    for key, value in overrides.items():
        data[key] = value
    return data


def _dump(value):
    return json.dumps(value, ensure_ascii=False)


def test_audits_real_provider_result_and_redacts_values_without_mutation():
    result = _result()
    original = deepcopy(result)
    audit = audit_fund_nav_result(result)
    assert audit["audit_status"] in {"passed", "passed_with_warnings"}
    assert audit["commit_safe"] is False
    assert audit["display_safe"] is True
    assert audit["has_real_nav_data"] is True
    assert audit["contains_real_nav_values"] is True
    assert audit["redacted_result"]["nav"]["unit_nav"] == "<redacted>"
    assert audit["redacted_result"]["nav"]["accumulated_nav"] == "<redacted>"
    assert audit["redacted_result"]["nav"]["daily_change_pct"] == "<redacted>"
    assert audit["redacted_result"]["estimate"]["estimated_nav"] == "<redacted>"
    assert audit["redacted_result"]["estimate"]["estimated_change_pct"] == "<redacted>"
    assert audit["redacted_result"]["estimate"]["estimated_change_amount"] == "<redacted>"
    assert result == original
    assert validate_fund_nav_audit_result(audit) == []


def test_missing_checked_at_nav_date_and_estimate_time_freshness_statuses():
    missing_checked = _result(source={"provider": "eastmoney_fund", "source_status": "real_provider"})
    assert check_fund_nav_result_freshness(missing_checked)["daily_nav_freshness_status"] == "missing_checked_at"
    missing_nav_date = _result(nav={"unit_nav": "DEMO_UNIT_NAV"})
    assert check_fund_nav_result_freshness(missing_nav_date)["daily_nav_freshness_status"] == "missing_nav_date"
    missing_estimate_time = _result(estimate={"estimated_nav": "DEMO_EST_NAV"})
    assert check_fund_nav_result_freshness(missing_estimate_time)["estimated_nav_freshness_status"] == "missing_estimate_time"


def test_stale_and_fresh_statuses_use_different_thresholds():
    stale = _result(source={"provider": "eastmoney_fund", "source_status": "real_provider", "checked_at": _now(-90000)})
    audit = audit_fund_nav_result(stale)
    assert audit["daily_nav_freshness_status"] == "stale"
    assert audit["estimated_nav_freshness_status"] == "stale"
    assert audit["display_safe"] is False
    assert "fresh" not in {audit["daily_nav_freshness_status"], audit["estimated_nav_freshness_status"]}
    fresh = audit_fund_nav_result(_result())
    assert fresh["daily_nav_freshness_status"] == "fresh"
    assert fresh["estimated_nav_freshness_status"] == "fresh"


def test_source_metadata_missing_fields_create_issues():
    audit = audit_fund_nav_result(_result(source={"checked_at": _now()}))
    assert audit["source_metadata_ok"] is False
    assert "missing_source_provider" in audit["issues"]
    assert "missing_source_source_status" in audit["issues"]
    assert audit["audit_status"] in {"failed", "passed_with_warnings"}


def test_allow_commit_to_repo_with_real_nav_blocks_audit():
    audit = audit_fund_nav_result(_result(provider_checks={"allow_commit_to_repo": True, "cache_scope": "local_only"}))
    assert audit["audit_status"] == "blocked"
    assert audit["severity"] == "blocker"
    assert "real_fund_nav_result_must_not_be_committed" in audit["issues"]


def test_non_local_cache_scope_warns_for_real_result():
    audit = audit_fund_nav_result(_result(provider_checks={"allow_commit_to_repo": False, "cache_scope": "repo_cache"}))
    assert "cache_scope_must_be_local_only" in audit["warnings"]
    assert audit["cache_scope"] == "repo_cache"


def test_secret_fields_are_detected_and_redacted_without_values():
    result = _result(token="DEMO_TOKEN_VALUE", api_key="DEMO_API_KEY_VALUE", nested={"webhook": "DEMO_WEBHOOK_VALUE"})
    found = scan_fund_nav_result_for_sensitive_fields(result)
    assert {item["field"] for item in found} >= {"token", "api_key", "nested.webhook"}
    audit = audit_fund_nav_result(result)
    assert audit["audit_status"] == "blocked"
    assert audit["severity"] == "blocker"
    dumped = _dump(audit["redacted_result"])
    assert "DEMO_TOKEN_VALUE" not in dumped
    assert "DEMO_API_KEY_VALUE" not in dumped
    assert "DEMO_WEBHOOK_VALUE" not in dumped
    assert "token" in " ".join(audit["secret_fields_found"])


def test_fixture_and_model_only_results_can_be_commit_safe_without_secrets():
    for mode in ("fixture_only", "model_only"):
        audit = audit_fund_nav_result(_result(data_mode=mode, has_real_nav_data=False, nav={}, estimate={}, provider_checks={"allow_commit_to_repo": False, "cache_scope": "local_only"}))
        assert audit["commit_safe"] is True
        assert audit["audit_status"] in {"passed", "passed_with_warnings"}


def test_estimated_nav_missing_disclaimer_produces_warning():
    audit = audit_fund_nav_result(_result(warnings=[], disclaimer="本结果仅用于本地观察。"))
    assert "estimated_nav_requires_final_company_nav_disclaimer" in audit["warnings"]
    assert ESTIMATE_DISCLAIMER in audit["warnings"]


def test_summary_counts_passed_and_blocked():
    passed = audit_fund_nav_result(_result())
    blocked = audit_fund_nav_result(_result(token="DEMO_TOKEN_VALUE"))
    summary = build_fund_nav_audit_summary(audit_fund_nav_results([_result(), _result(token="DEMO_TOKEN_VALUE")]))
    assert summary["total"] == 2
    assert summary["status_counts"][passed["audit_status"]] >= 1
    assert summary["status_counts"][blocked["audit_status"]] == 1


def test_markdown_is_redacted_and_contains_required_disclaimers():
    audit = audit_fund_nav_result(_result(token="DEMO_TOKEN_VALUE"))
    markdown = render_fund_nav_audit_markdown(audit)
    assert "最终以基金公司公布净值为准" in markdown
    assert "真实基金净值仅允许本地内存使用" in markdown
    assert "CI 测试不会请求真实基金净值" in markdown
    for forbidden in ("DEMO_UNIT_NAV", "DEMO_EST_NAV", "DEMO_DAILY_CHANGE", "DEMO_TOKEN_VALUE", "API Key", "Webhook", "Token"):
        assert forbidden not in markdown


def test_redact_helper_keeps_metadata_and_redacts_values():
    redacted = redact_fund_nav_result_for_audit(_result(private_key="DEMO_PRIVATE_KEY"))
    assert redacted["asset_id"] == "demo_fund_001"
    assert redacted["code"] == "000000"
    assert redacted["type"] == "fund"
    assert redacted["market"] == "CN"
    assert redacted["source"]["provider"] == "eastmoney_fund"
    assert redacted["source"]["checked_at"]
    assert redacted["nav"]["nav_date"] == "2099-01-01"
    assert redacted["estimate"]["estimate_time"]
    assert "DEMO_PRIVATE_KEY" not in _dump(redacted)
