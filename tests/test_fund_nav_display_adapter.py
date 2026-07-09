from copy import deepcopy
from datetime import datetime, timezone
import json

from src.fund_nav_display_adapter import (
    build_fund_nav_display_model,
    build_fund_nav_display_models,
    build_fund_nav_display_policy,
    render_fund_nav_display_markdown,
    summarize_fund_nav_display_models,
    validate_fund_nav_display_model,
    validate_fund_nav_display_policy,
)
from src.fund_nav_result_audit import ESTIMATE_DISCLAIMER, audit_fund_nav_result


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
        "nav": {
            "unit_nav": "DEMO_UNIT_NAV",
            "accumulated_nav": "DEMO_ACC_NAV",
            "daily_change_pct": "DEMO_DAILY_CHANGE",
            "nav_date": "2099-01-01",
        },
        "estimate": {
            "estimated_nav": "DEMO_EST_NAV",
            "estimated_change_pct": "DEMO_EST_CHANGE",
            "estimated_change_amount": "DEMO_EST_AMOUNT",
            "estimate_time": _now(),
        },
        "source": {"provider": "eastmoney_fund", "source_status": "real_provider", "checked_at": _now()},
        "provider_checks": {"allow_commit_to_repo": False, "cache_scope": "local_only"},
        "warnings": [ESTIMATE_DISCLAIMER],
        "disclaimer": ESTIMATE_DISCLAIMER,
    }
    for key, value in overrides.items():
        data[key] = value
    return data


def _audit(result=None, **overrides):
    data = audit_fund_nav_result(result or _result())
    data.update(overrides)
    return data


def _dump(value):
    return json.dumps(value, ensure_ascii=False)


def test_builds_default_policy_and_validates_safety_defaults():
    policy = build_fund_nav_display_policy()
    assert policy["default_display_mode"] == "redacted"
    assert policy["allow_real_values_on_local_page"] is False
    assert policy["allow_commit_to_repo"] is False
    assert validate_fund_nav_display_policy(policy) == []


def test_real_provider_result_defaults_to_redacted_without_mutating_result():
    result = _result()
    original = deepcopy(result)
    model = build_fund_nav_display_model(result, _audit(result))
    assert model["display_mode"] == "redacted"
    assert model["display_status"] == "displayable"
    assert model["nav_display"]["unit_nav"] == "<redacted>"
    assert model["nav_display"]["accumulated_nav"] == "<redacted>"
    assert model["nav_display"]["daily_change_pct"] == "<redacted>"
    assert model["estimate_display"]["estimated_nav"] == "<redacted>"
    assert model["estimate_display"]["estimated_change_pct"] == "<redacted>"
    assert model["has_real_nav_data"] is True
    assert model["commit_safe"] is False
    assert result == original
    assert validate_fund_nav_display_model(model) == []


def test_passed_and_passed_with_warnings_audits_can_generate_redacted_display():
    for status in ("passed", "passed_with_warnings"):
        model = build_fund_nav_display_model(_result(), _audit(audit_status=status, display_safe=True))
        assert model["audit_status"] == status
        assert model["display_mode"] == "redacted"


def test_failed_and_blocked_audits_generate_blocked_display():
    for status in ("failed", "blocked"):
        model = build_fund_nav_display_model(_result(), _audit(audit_status=status, display_safe=False))
        assert model["display_status"] == "blocked"
        assert model["display_mode"] == "blocked"
        assert model["nav_display"] == {}
        assert model["estimate_display"] == {}


def test_local_real_allowed_requires_display_safe_commit_safe_cache_scope_and_checked_at():
    policy = {"allow_real_values_on_local_page": True, "redact_by_default": False}
    cases = [
        (_result(), _audit(display_safe=False), "audit_status="),
        (_result(), _audit(commit_safe=True), "real_fund_nav_data_commit_safe_must_be_false"),
        (_result(provider_checks={"allow_commit_to_repo": False, "cache_scope": "repo_cache"}), None, "cache_scope_must_be_local_only"),
        (_result(source={"provider": "eastmoney_fund", "source_status": "real_provider"}), None, "missing_checked_at"),
    ]
    for result, audit, issue in cases:
        model = build_fund_nav_display_model(result, audit or _audit(result), policy)
        assert model["display_mode"] != "local_real_allowed"


def test_secret_fields_block_real_display_without_exposing_secret_values():
    result = _result(api_key="DEMO_SECRET_VALUE")
    model = build_fund_nav_display_model(result, audit_fund_nav_result(result), {"allow_real_values_on_local_page": True, "redact_by_default": False})
    dumped = _dump(model)
    assert model["display_mode"] == "blocked"
    assert "DEMO_SECRET_VALUE" not in dumped
    assert "api_key" not in dumped.lower()


def test_local_real_allowed_can_show_demo_values_only_when_explicitly_enabled():
    result = _result(
        nav={"unit_nav": 1.23, "accumulated_nav": 2.34, "daily_change_pct": 0.45, "nav_date": "2099-01-01"},
        estimate={"estimated_nav": 1.24, "estimated_change_pct": 0.46, "estimated_change_amount": 0.01, "estimate_time": _now()},
    )
    model = build_fund_nav_display_model(result, _audit(result), {"allow_real_values_on_local_page": True, "redact_by_default": False})
    assert model["display_mode"] == "local_real_allowed"
    assert model["nav_display"]["unit_nav"] == 1.23
    assert model["estimate_display"]["estimated_nav"] == 1.24
    assert model["commit_safe"] is False
    assert ESTIMATE_DISCLAIMER in " ".join(model["warnings"])


def test_markdown_default_is_redacted_contains_disclaimer_and_no_sensitive_labels():
    model = build_fund_nav_display_model(_result(), _audit())
    markdown = render_fund_nav_display_markdown(model)
    assert "DEMO_UNIT_NAV" not in markdown
    assert "DEMO_EST_NAV" not in markdown
    assert "DEMO_DAILY_CHANGE" not in markdown
    assert "<redacted>" in markdown
    assert "最终以基金公司公布净值为准" in markdown
    for forbidden in ("Token", "API Key", "Webhook"):
        assert forbidden not in markdown


def test_display_model_keeps_required_source_and_freshness_metadata_and_badges():
    model = build_fund_nav_display_model(_result(), _audit())
    assert model["provider"] == "eastmoney_fund"
    assert model["source"]["provider"] == "eastmoney_fund"
    assert model["source"]["checked_at"]
    assert model["source"]["source_status"] == "real_provider"
    assert model["daily_nav_freshness_status"] == "fresh"
    assert model["estimated_nav_freshness_status"] == "fresh"
    assert "禁止提交仓库" in model["badges"]


def test_unavailable_status_does_not_show_real_values():
    model = build_fund_nav_display_model(_result(data_status="provider_error"), _audit())
    assert model["display_mode"] == "unavailable"
    assert model["nav_display"] == {}
    assert model["estimate_display"] == {}


def test_build_models_and_summary():
    models = build_fund_nav_display_models([_result()], [_audit()])
    summary = summarize_fund_nav_display_models(models)
    assert summary["summary_type"] == "fund_nav_display_summary"
    assert summary["total"] == 1
    assert render_fund_nav_display_markdown(summary).startswith("# 场外基金净值页面展示安全适配 Demo")
