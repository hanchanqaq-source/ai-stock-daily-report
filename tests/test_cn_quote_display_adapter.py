from __future__ import annotations

import copy
from datetime import datetime, timezone

from src.cn_quote_display_adapter import (
    build_cn_quote_display_model,
    build_cn_quote_display_models,
    build_cn_quote_display_policy,
    render_cn_quote_display_markdown,
    summarize_cn_quote_display_models,
    validate_cn_quote_display_model,
    validate_cn_quote_display_policy,
)
from src.cn_quote_result_audit import audit_cn_quote_result


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def demo_result(**updates):
    result = {
        "asset_id": "demo_stock_001",
        "code": "DEMO001",
        "symbol": "DEMO001",
        "name": "示例股票",
        "type": "stock",
        "market": "CN",
        "provider_name": "demo_provider",
        "data_status": "real_provider_available",
        "data_mode": "real_provider",
        "has_real_market_data": True,
        "quote": {
            "last_price": 1.23,
            "change_pct": 0.45,
            "change_amount": 0.01,
            "volume": 100,
            "turnover": 123.45,
            "open": 1.2,
            "high": 1.3,
            "low": 1.1,
            "previous_close": 1.22,
        },
        "source": {"provider": "demo_provider", "source_status": "real_provider", "checked_at": iso_now()},
        "provider_checks": {"allow_commit_to_repo": False, "cache_scope": "local_only"},
        "allow_commit_to_repo": False,
    }
    for key, value in updates.items():
        if key in {"quote", "source", "provider_checks"}:
            result[key].update(value)
        else:
            result[key] = value
    return result


def audit_for(result, **updates):
    audit = audit_cn_quote_result(result)
    audit.update(updates)
    return audit


def test_policy_defaults_are_safe():
    policy = build_cn_quote_display_policy()

    assert validate_cn_quote_display_policy(policy) == []
    assert policy["default_display_mode"] == "redacted"
    assert policy["allow_real_values_on_local_page"] is False
    assert policy["allow_commit_to_repo"] is False


def test_real_provider_result_defaults_to_redacted_without_mutating_input():
    result = demo_result()
    original = copy.deepcopy(result)

    model = build_cn_quote_display_model(result, audit_for(result))

    assert model["display_mode"] == "redacted"
    assert model["display_status"] == "displayable"
    assert model["quote_display"]["last_price"] == "<redacted>"
    assert model["quote_display"]["change_pct"] == "<redacted>"
    assert model["quote_display"]["turnover"] == "<redacted>"
    assert result == original
    assert validate_cn_quote_display_model(model) == []


def test_passed_and_passed_with_warnings_audits_can_render_redacted():
    result = demo_result()

    for status in ("passed", "passed_with_warnings"):
        model = build_cn_quote_display_model(result, audit_for(result, audit_status=status, display_safe=True))
        assert model["display_mode"] == "redacted"
        assert model["audit_status"] == status


def test_failed_and_blocked_audits_render_blocked_without_quote_values():
    result = demo_result()

    for status in ("failed", "blocked"):
        model = build_cn_quote_display_model(result, audit_for(result, audit_status=status, display_safe=False))
        assert model["display_status"] == "blocked"
        assert model["display_mode"] == "blocked"
        assert model["quote_display"] == {}
        assert "审计未通过" in model["warnings"][0]


def test_local_real_allowed_requires_display_safe_commit_safe_cache_and_checked_at():
    policy = {**build_cn_quote_display_policy(), "allow_real_values_on_local_page": True, "redact_by_default": False}
    result = demo_result()

    assert build_cn_quote_display_model(result, audit_for(result, display_safe=False), policy)["display_mode"] == "redacted"
    assert build_cn_quote_display_model(result, audit_for(result, commit_safe=True), policy)["display_mode"] == "blocked"
    assert build_cn_quote_display_model(demo_result(provider_checks={"cache_scope": "shared"}), audit_for(demo_result(provider_checks={"cache_scope": "shared"})), policy)["display_mode"] != "local_real_allowed"
    missing_checked_at = demo_result()
    missing_checked_at["source"].pop("checked_at")
    assert build_cn_quote_display_model(missing_checked_at, audit_for(missing_checked_at, audit_status="passed_with_warnings", display_safe=True), policy)["display_mode"] != "local_real_allowed"

    missing_source_status = demo_result()
    missing_source_status["source"].pop("source_status")
    assert build_cn_quote_display_model(missing_source_status, audit_for(missing_source_status, audit_status="passed_with_warnings", display_safe=True), policy)["display_mode"] != "local_real_allowed"


def test_secret_blocks_real_display_and_does_not_expose_secret_names():
    policy = {**build_cn_quote_display_policy(), "allow_real_values_on_local_page": True, "redact_by_default": False}
    result = demo_result()
    result["source"]["token"] = "DEMO_SECRET_VALUE"

    model = build_cn_quote_display_model(result, audit_for(result), policy)
    rendered = repr(model).lower()

    assert model["display_mode"] == "blocked"
    assert "demo_secret_value" not in rendered
    assert "token" not in rendered


def test_local_real_allowed_can_show_demo_values_only_when_explicitly_enabled():
    policy = {**build_cn_quote_display_policy(), "allow_real_values_on_local_page": True, "redact_by_default": False}
    result = demo_result()

    model = build_cn_quote_display_model(result, audit_for(result, audit_status="passed_with_warnings", display_safe=True), policy)

    assert model["display_mode"] == "local_real_allowed"
    assert model["quote_display"]["last_price"] == 1.23
    assert model["quote_display"]["change_pct"] == 0.45
    assert model["commit_safe"] is False


def test_markdown_default_is_redacted_and_secret_word_safe():
    result = demo_result()
    model = build_cn_quote_display_model(result, audit_for(result))

    markdown = render_cn_quote_display_markdown(model)

    assert "# A股 / ETF Provider 页面展示安全适配 Demo" in markdown
    assert "默认展示脱敏结果。" in markdown
    assert "真实行情值仅允许本地页面显式开启后展示。" in markdown
    assert "真实行情值不得提交到 public 仓库。" in markdown
    assert "审计未通过时页面不显示真实行情值。" in markdown
    assert "1.23" not in markdown
    assert "0.45" not in markdown
    assert "123.45" not in markdown
    assert "Token" not in markdown
    assert "API Key" not in markdown
    assert "Webhook" not in markdown


def test_display_model_keeps_required_metadata_badges_and_commit_safe_false():
    result = demo_result()
    model = build_cn_quote_display_model(result, audit_for(result))

    assert model["provider"] == "demo_provider"
    assert model["source"]["checked_at"]
    assert model["freshness_status"] in {"fresh", "stale", "unknown", "missing_checked_at"}
    assert model["badges"]
    assert model["has_real_market_data"] is True
    assert model["commit_safe"] is False


def test_models_summary_supports_multiple_results():
    models = build_cn_quote_display_models([demo_result(), demo_result(asset_id="demo_stock_002", code="DEMO002")])
    summary = summarize_cn_quote_display_models(models)

    assert len(models) == 2
    assert summary["summary_type"] == "cn_quote_display_summary"
    assert summary["total"] == 2
    assert summary["commit_safe"] is False
    assert render_cn_quote_display_markdown(summary)
