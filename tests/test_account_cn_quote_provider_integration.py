from __future__ import annotations

from copy import deepcopy

from src.account_cn_quote_provider_integration import (
    audit_account_cn_quote_provider_results,
    build_account_cn_quote_display_models,
    build_account_cn_quote_provider_summary,
    fetch_account_cn_quote_provider_results,
    render_account_cn_quote_provider_summary_markdown,
    split_account_assets_for_cn_quote_provider,
    validate_account_cn_quote_provider_summary,
)


class FakeRealProvider:
    def __init__(self) -> None:
        self.calls = []

    def fetch_quote(self, asset):
        self.calls.append(dict(asset))
        return {
            "asset_id": asset["asset_id"],
            "code": asset["code"],
            "symbol": asset["symbol"],
            "name": asset["name"],
            "type": asset["type"],
            "market": asset["market"],
            "provider_name": "fake",
            "data_status": "disabled_by_default",
            "data_mode": "real_provider",
            "has_real_market_data": False,
            "will_fetch_real_data": False,
            "allow_commit_to_repo": False,
            "quote": {"last_price": None, "change_pct": None, "change_amount": None, "volume": None, "turnover": None, "open": None, "high": None, "low": None, "previous_close": None},
            "source": {"provider": "fake", "source_status": "disabled_by_default", "checked_at": "2026-01-01T00:00:00+00:00"},
            "provider_checks": {"allow_commit_to_repo": False, "cache_scope": "local_only", "network_enabled": False},
            "warnings": ["fake provider only"],
            "reason": "fake provider only",
            "disclaimer": "fake",
        }


def demo_group():
    return {
        "account_id": "demo_account",
        "account_name": "示例账户",
        "assets": [
            {"asset_id": "cn_stock", "code": "000001", "name": "示例股票", "type": "stock", "market": "CN", "status": "holding"},
            {"asset_id": "cn_etf", "code": "510300", "name": "示例ETF", "type": "etf", "market": "CN", "status": "watching"},
            {"asset_id": "cn_index", "code": "000300", "name": "示例指数", "type": "index", "market": "CN", "status": "holding", "is_official_index": True},
            {"asset_id": "fund", "code": "000001", "name": "示例基金", "type": "fund", "market": "CN", "status": "watching"},
            {"asset_id": "company", "code": "demo", "name": "示例企业", "type": "company", "market": "CN", "status": "holding"},
            {"asset_id": "industry", "code": "industry", "name": "示例行业", "type": "industry", "market": "CN", "status": "watching"},
            {"asset_id": "theme", "code": "theme", "name": "示例主题", "type": "theme", "market": "CN", "status": "holding"},
            {"asset_id": "computed", "code": "breadth", "name": "计算指标", "type": "index", "item_type": "computed_indicator", "market": "CN", "status": "watching"},
            {"asset_id": "unknown", "code": "???", "name": "未知", "type": "unknown", "market": "CN", "status": "holding"},
            {"asset_id": "us_stock", "code": "AAPL", "name": "Apple", "type": "stock", "market": "US", "status": "watching"},
            {"asset_id": "cleared", "code": "600000", "name": "已清仓", "type": "stock", "market": "CN", "status": "cleared"},
            {"asset_id": "archived", "code": "600001", "name": "已归档", "type": "stock", "market": "CN", "status": "archived"},
            {"asset_id": "deleted", "code": "600002", "name": "已删除", "type": "stock", "market": "CN", "status": "deleted"},
        ],
    }


def test_default_summary_is_dry_run_and_does_not_mutate_group():
    group = demo_group()
    original = deepcopy(group)
    summary = build_account_cn_quote_provider_summary(group)
    assert group == original
    assert summary["provider_mode"] == "dry_run"
    assert summary["data_mode"] == "dry_run"
    assert summary["has_real_market_data"] is False
    assert summary["display_mode"] == "redacted"
    assert validate_account_cn_quote_provider_summary(summary) is True


def test_reads_active_assets_and_excludes_inactive_statuses():
    split = split_account_assets_for_cn_quote_provider(demo_group())
    assert split["asset_counts"]["total"] == 13
    assert split["asset_counts"]["active"] == 10
    assert {asset["asset_id"] for asset in split["inactive"]} == {"cleared", "archived", "deleted"}
    assert all(asset["status"] in {"holding", "watching"} for asset in split["active"])


def test_holding_and_watching_are_summarized_separately():
    summary = build_account_cn_quote_provider_summary(demo_group())
    assert summary["holding"]["summary"]["total"] == 5
    assert summary["watching"]["summary"]["total"] == 5
    assert "display_models" in summary["holding"]
    assert "display_models" in summary["watching"]


def test_supported_cn_stock_etf_and_official_index_enter_dry_run_provider():
    results = fetch_account_cn_quote_provider_results(demo_group())
    by_id = {item["asset"]["asset_id"]: item for item in results}
    for asset_id in ["cn_stock", "cn_etf", "cn_index"]:
        assert by_id[asset_id]["data_mode"] == "dry_run"
        assert by_id[asset_id]["data_status"] == "dry_run_only"
        assert by_id[asset_id]["will_fetch_real_data"] is False


def test_unsupported_and_invalid_asset_routing():
    results = fetch_account_cn_quote_provider_results(demo_group())
    by_id = {item["asset"]["asset_id"]: item for item in results}
    for asset_id in ["fund", "company", "industry", "theme", "computed", "us_stock"]:
        assert by_id[asset_id]["data_status"] == "unsupported"
        assert by_id[asset_id]["has_real_market_data"] is False
    assert "fund_nav_provider" in by_id["fund"]["reason"]
    assert by_id["unknown"]["data_status"] == "invalid_request"


def test_every_result_is_audited_and_display_adapted_redacted_by_default():
    results = fetch_account_cn_quote_provider_results(demo_group())
    audits = audit_account_cn_quote_provider_results(results)
    models = build_account_cn_quote_display_models(results, audits)
    assert len(audits) == len(results)
    assert len(models) == len(results)
    assert all("audit_status" in audit for audit in audits)
    assert all(model["display_mode"] in {"redacted", "unavailable"} for model in models)


def test_blocked_audit_does_not_display_real_quote_values():
    result = fetch_account_cn_quote_provider_results(demo_group())[0]
    result = {**result, "has_real_market_data": True, "data_mode": "real_provider", "quote": {"last_price": "12.34", "change_pct": "5.67%", "turnover": "999999"}}
    audit = {"audit_status": "blocked", "display_safe": False, "contains_secret": False, "has_real_market_data": True, "commit_safe": False, "issues": ["blocked_for_test"], "market": "CN"}
    model = build_account_cn_quote_display_models([result], [audit])[0]
    assert model["display_mode"] == "blocked"
    assert "12.34" not in repr(model)
    assert "5.67%" not in repr(model)
    assert "999999" not in repr(model)


def test_summary_contains_result_summary_holding_watching_and_counts():
    summary = build_account_cn_quote_provider_summary(demo_group())
    assert summary["asset_counts"]["cn_quote_supported"] == 3
    assert summary["asset_counts"]["unsupported"] == 6
    assert summary["asset_counts"]["invalid_request"] == 1
    assert summary["result_summary"]["dry_run_count"] == 3
    assert summary["result_summary"]["unsupported_count"] == 6
    assert summary["result_summary"]["invalid_request_count"] == 1
    assert "holding" in summary
    assert "watching" in summary


def test_markdown_is_safe_and_contains_required_demo_copy():
    markdown = render_account_cn_quote_provider_summary_markdown(build_account_cn_quote_provider_summary(demo_group()))
    assert markdown.startswith("# 账户 A股 / ETF Provider 汇总 Dry-run Demo")
    assert "本阶段为账户 provider dry-run 接入，不请求真实行情。" in markdown
    assert "所有 provider 结果进入页面前必须经过审计和展示安全适配。" in markdown
    assert "默认展示脱敏结果，不保存真实行情到仓库。" in markdown
    forbidden = ["12.34", "5.67%", "999999", "Token", "API Key", "Webhook"]
    assert all(value not in markdown for value in forbidden)


def test_real_gated_uses_only_injected_fake_provider_without_network():
    provider = FakeRealProvider()
    summary = build_account_cn_quote_provider_summary(demo_group(), provider_mode="real_gated", provider=provider)
    assert len(provider.calls) == 3
    assert summary["has_real_market_data"] is False
    assert summary["result_summary"]["real_provider_count"] == 3
    assert all(item.get("will_fetch_real_data") is not True for item in summary["results"])
