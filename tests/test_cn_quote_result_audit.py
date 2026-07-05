from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone

from src.cn_quote_result_audit import (
    QUOTE_VALUE_FIELDS,
    audit_cn_quote_result,
    audit_cn_quote_results,
    build_cn_quote_audit_summary,
    check_quote_result_freshness,
    redact_quote_result_for_audit,
    render_cn_quote_audit_markdown,
    scan_quote_result_for_sensitive_fields,
)


def iso_now(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).replace(microsecond=0).isoformat()


def real_result(**updates):
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
            "last_price": "DEMO_PRICE_VALUE",
            "change_pct": "DEMO_CHANGE_PCT_VALUE",
            "change_amount": "DEMO_CHANGE_AMOUNT_VALUE",
            "volume": "DEMO_VOLUME_VALUE",
            "turnover": "DEMO_TURNOVER_VALUE",
            "open": "DEMO_OPEN_VALUE",
            "high": "DEMO_HIGH_VALUE",
            "low": "DEMO_LOW_VALUE",
            "previous_close": "DEMO_PREVIOUS_CLOSE_VALUE",
        },
        "source": {"provider": "demo_provider", "source_status": "real_provider", "checked_at": iso_now()},
        "provider_checks": {
            "allow_commit_to_repo": False,
            "cache_scope": "local_only",
            "network_enabled": True,
            "allow_real_request": True,
        },
        "allow_commit_to_repo": False,
    }
    for key, value in updates.items():
        if key in {"quote", "source", "provider_checks"}:
            result[key].update(value)
        else:
            result[key] = value
    return result


def test_real_provider_result_is_audited_redacted_and_not_commit_safe():
    result = real_result()
    original = copy.deepcopy(result)

    audit = audit_cn_quote_result(result)

    assert audit["audit_status"] == "passed_with_warnings"
    assert audit["commit_safe"] is False
    assert audit["display_safe"] is True
    assert audit["has_real_market_data"] is True
    assert audit["contains_real_quote_values"] is True
    assert audit["redacted_result"]["quote"]["last_price"] == "<redacted>"
    assert audit["redacted_result"]["quote"]["change_pct"] == "<redacted>"
    assert audit["redacted_result"]["quote"]["turnover"] == "<redacted>"
    assert result == original


def test_redaction_covers_all_quote_fields_and_preserves_source_metadata():
    redacted = redact_quote_result_for_audit(real_result())

    for field in QUOTE_VALUE_FIELDS:
        assert redacted["quote"][field] == "<redacted>"
    assert redacted["asset_id"] == "demo_stock_001"
    assert redacted["code"] == "DEMO001"
    assert redacted["type"] == "stock"
    assert redacted["market"] == "CN"
    assert redacted["source"]["provider"] == "demo_provider"
    assert redacted["source"]["source_status"] == "real_provider"
    assert redacted["source"]["checked_at"]


def test_freshness_missing_stale_and_fresh():
    missing = real_result()
    missing["source"].pop("checked_at")
    stale = real_result(source={"checked_at": iso_now(-3600)})
    fresh = real_result(source={"checked_at": iso_now()})

    assert check_quote_result_freshness(missing)["freshness_status"] == "missing_checked_at"
    assert check_quote_result_freshness(stale)["freshness_status"] == "stale"
    assert check_quote_result_freshness(fresh)["freshness_status"] == "fresh"
    assert audit_cn_quote_result(stale)["freshness_status"] != "fresh"
    assert audit_cn_quote_result(stale)["display_safe"] is False


def test_invalid_checked_at_is_unknown():
    result = real_result(source={"checked_at": "not-a-time"})

    assert check_quote_result_freshness(result)["freshness_status"] == "unknown"


def test_missing_source_provider_and_status_are_issues():
    result = real_result()
    result["source"].pop("provider")
    result.pop("provider_name")
    result["source"].pop("source_status")

    audit = audit_cn_quote_result(result)

    assert audit["audit_status"] == "failed"
    assert "missing_source_provider" in audit["issues"]
    assert "missing_source_source_status" in audit["issues"]
    assert audit["source_metadata_ok"] is False


def test_real_result_with_allow_commit_to_repo_true_is_blocked():
    result = real_result(provider_checks={"allow_commit_to_repo": True}, allow_commit_to_repo=True)

    audit = audit_cn_quote_result(result)

    assert audit["audit_status"] == "blocked"
    assert audit["severity"] == "blocker"
    assert "real_provider_result_must_not_be_committed" in audit["issues"]


def test_real_result_with_non_local_cache_scope_warns():
    audit = audit_cn_quote_result(real_result(provider_checks={"cache_scope": "shared_cache"}))

    assert audit["audit_status"] in {"passed_with_warnings", "failed"}
    assert "real_provider_cache_scope_must_be_local_only" in audit["warnings"]


def test_secret_fields_are_detected_and_redacted_without_values():
    result = real_result()
    result["source"].update({"token": "DEMO_TOKEN_SECRET", "api_key": "DEMO_API_KEY_SECRET"})
    result["provider_checks"]["webhook"] = "DEMO_WEBHOOK_SECRET"

    audit = audit_cn_quote_result(result)
    serialized = json.dumps(audit["redacted_result"], ensure_ascii=False)

    assert audit["audit_status"] == "blocked"
    assert audit["severity"] == "blocker"
    assert scan_quote_result_for_sensitive_fields(result) == ["provider_checks.webhook", "source.api_key", "source.token"]
    assert "DEMO_TOKEN_SECRET" not in serialized
    assert "DEMO_API_KEY_SECRET" not in serialized
    assert "DEMO_WEBHOOK_SECRET" not in serialized
    assert serialized.count("<redacted>") >= 3


def test_fixture_and_model_only_results_can_be_commit_safe_without_secret():
    for mode in ["fixture_only", "model_only"]:
        result = real_result(
            data_status=mode,
            data_mode=mode,
            has_real_market_data=False,
            quote={field: None for field in QUOTE_VALUE_FIELDS},
            provider_checks={"allow_commit_to_repo": True, "cache_scope": "test_fixture_only"},
            allow_commit_to_repo=True,
        )
        audit = audit_cn_quote_result(result)
        assert audit["commit_safe"] is True
        assert audit["audit_status"] in {"passed", "passed_with_warnings"}


def test_audit_summary_counts_passed_and_blocked():
    clean_fixture = real_result(data_status="fixture_only", data_mode="fixture_only", has_real_market_data=False, quote={field: None for field in QUOTE_VALUE_FIELDS}, provider_checks={"allow_commit_to_repo": True, "cache_scope": "test_fixture_only"}, allow_commit_to_repo=True)
    blocked_real = real_result(provider_checks={"allow_commit_to_repo": True}, allow_commit_to_repo=True)

    summary = build_cn_quote_audit_summary(audit_cn_quote_results([clean_fixture, blocked_real]))

    assert summary["total"] == 2
    assert summary["status_counts"]["passed"] == 1
    assert summary["status_counts"]["blocked"] == 1
    assert summary["blocked"] == 1


def test_markdown_contains_only_redacted_audit_details():
    result = real_result()
    result["source"]["token"] = "DEMO_TOKEN_SECRET"
    audit = audit_cn_quote_result(result)
    markdown = render_cn_quote_audit_markdown(audit)

    assert "# A股 / ETF Provider 结果审计 Demo" in markdown
    assert "真实行情值仅允许本地内存使用，不得提交到 public 仓库。" in markdown
    assert "审计输出会脱敏价格、涨跌幅、成交额等字段。" in markdown
    assert "CI 测试不会请求真实行情。" in markdown
    assert "DEMO_PRICE_VALUE" not in markdown
    assert "DEMO_CHANGE_PCT_VALUE" not in markdown
    assert "DEMO_TURNOVER_VALUE" not in markdown
    assert "DEMO_TOKEN_SECRET" not in markdown
    assert "API Key" not in markdown
    assert "Webhook" not in markdown
