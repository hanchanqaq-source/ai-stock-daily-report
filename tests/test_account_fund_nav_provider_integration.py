from copy import deepcopy

from src.account_fund_nav_provider_integration import (
    build_account_fund_nav_display_models,
    build_account_fund_nav_provider_summary,
    fetch_account_fund_nav_provider_results,
    render_account_fund_nav_provider_summary_markdown,
    split_account_assets_for_fund_nav_provider,
)


def demo_group():
    return {
        "account_id": "demo_account",
        "account_name": "示例账户",
        "assets": [
            {"asset_id": "fund_h", "code": "DEMOF1", "name": "演示持有基金", "type": "fund", "market": "CN", "status": "holding"},
            {"asset_id": "fund_w", "code": "DEMOF2", "name": "演示观察基金", "type": "fund", "market": "cn", "status": "watching"},
            {"asset_id": "stock_h", "code": "DEMOS", "name": "演示股票", "type": "stock", "market": "CN", "status": "holding"},
            {"asset_id": "etf_w", "code": "DEMOE", "name": "演示 ETF", "type": "etf", "market": "CN", "status": "watching"},
            {"asset_id": "idx", "code": "DEMOI", "name": "演示指数", "type": "index", "market": "CN", "status": "watching"},
            {"asset_id": "company", "code": "DEMOC", "name": "演示企业", "type": "company", "market": "CN", "status": "watching"},
            {"asset_id": "industry", "code": "DEMOIND", "name": "演示行业", "type": "industry", "market": "CN", "status": "watching"},
            {"asset_id": "theme", "code": "DEMOT", "name": "演示主题", "type": "theme", "market": "CN", "status": "watching"},
            {"asset_id": "computed", "code": "DEMOCALC", "name": "演示指标", "type": "index", "item_type": "computed_indicator", "market": "CN", "status": "watching"},
            {"asset_id": "unknown", "code": "DEMO?", "name": "演示未知", "type": "unknown", "market": "CN", "status": "watching"},
            {"asset_id": "fund_us", "code": "DEMOUS", "name": "演示海外基金", "type": "fund", "market": "US", "status": "watching"},
            {"asset_id": "cleared", "code": "DEMOCLEAR", "name": "已清仓", "type": "fund", "market": "CN", "status": "cleared"},
            {"asset_id": "archived", "code": "DEMOARCH", "name": "已归档", "type": "fund", "market": "CN", "status": "archived"},
            {"asset_id": "deleted", "code": "DEMODEL", "name": "已删除", "type": "fund", "market": "CN", "status": "deleted"},
        ],
    }


def test_default_summary_is_dry_run_and_does_not_mutate_group():
    group = demo_group()
    before = deepcopy(group)
    summary = build_account_fund_nav_provider_summary(group)
    assert group == before
    assert summary["provider_mode"] == "dry_run"
    assert summary["data_mode"] == "dry_run"
    assert summary["has_real_nav_data"] is False
    assert summary["display_mode"] == "redacted"
    assert summary["asset_counts"]["fund_nav_supported"] == 2
    assert summary["asset_counts"]["active"] == 11
    assert summary["result_summary"]["dry_run_count"] == 2
    assert "result_summary" in summary and "holding" in summary and "watching" in summary


def test_split_reads_active_assets_and_excludes_inactive_statuses():
    split = split_account_assets_for_fund_nav_provider(demo_group())
    active_ids = {asset["asset_id"] for asset in split["active"]}
    assert {"cleared", "archived", "deleted"}.isdisjoint(active_ids)
    assert {asset["asset_id"] for asset in split["fund_nav_supported"]} == {"fund_h", "fund_w"}
    assert split["asset_counts"]["holding"] == 2
    assert split["asset_counts"]["watching"] == 9


def test_routing_statuses_for_supported_unsupported_and_invalid_assets():
    results = fetch_account_fund_nav_provider_results(demo_group())
    by_id = {item["asset_id"]: item for item in results}
    assert by_id["fund_h"]["data_status"] == "dry_run_only"
    assert by_id["fund_h"]["will_fetch_real_data"] is False
    assert by_id["fund_w"]["has_real_nav_data"] is False
    for asset_id in ["stock_h", "etf_w", "idx", "company", "industry", "theme", "computed", "fund_us"]:
        assert by_id[asset_id]["data_status"] == "unsupported"
    assert "A股 / ETF quote provider" in by_id["stock_h"]["reason"]
    assert "股票 / ETF provider" in by_id["etf_w"]["reason"]
    assert "index quote" in by_id["idx"]["reason"]
    assert "企业本身不是基金净值对象" in by_id["company"]["reason"]
    assert "不直接请求基金净值 provider" in by_id["computed"]["reason"]
    assert by_id["unknown"]["data_status"] == "invalid_request"


def test_every_result_passes_audit_and_display_adapter_with_redacted_default():
    summary = build_account_fund_nav_provider_summary(demo_group())
    assert len(summary["audits"]) == len(summary["results"])
    assert len(summary["display_models"]) == len(summary["results"])
    assert all("audit_status" in audit for audit in summary["audits"])
    assert all("display_mode" in model for model in summary["display_models"])
    assert any(model["display_mode"] == "redacted" for model in summary["display_models"])


def test_holding_and_watching_are_separately_summarized():
    summary = build_account_fund_nav_provider_summary(demo_group())
    assert summary["holding"]["summary"]["total"] == 2
    assert summary["watching"]["summary"]["total"] == 9
    assert summary["holding"]["summary"]["unsupported_count"] == 1
    assert summary["watching"]["summary"]["unsupported_count"] == 7


def test_blocked_or_failed_display_does_not_expose_nav_values():
    result = fetch_account_fund_nav_provider_results(demo_group())[0]
    result = {**result, "has_real_nav_data": True, "nav": {"unit_nav": "demo-unit", "accumulated_nav": "demo-acc", "daily_change_pct": "demo-pct", "nav_date": "demo-date"}}
    models = build_account_fund_nav_display_models([result], audits=[{"audit_status": "blocked", "display_safe": False, "secret_fields_found": [], "issues": ["demo_block"]}])
    assert models[0]["display_status"] == "blocked"
    assert models[0]["nav_display"] == {}
    assert "demo-unit" not in repr(models[0])


def test_markdown_is_redacted_and_contains_required_disclaimer():
    summary = build_account_fund_nav_provider_summary(demo_group())
    markdown = render_account_fund_nav_provider_summary_markdown(summary)
    assert "最终以基金公司公布净值为准" in markdown
    assert "本阶段为账户基金净值 provider dry-run 接入，不请求真实基金净值。" in markdown
    assert "所有基金净值结果进入页面前必须经过审计和展示安全适配。" in markdown
    assert "默认展示脱敏结果，不保存真实基金净值到仓库。" in markdown
    assert "场外基金不支持真正实时价格。" in markdown
    forbidden = ["demo-unit", "demo-estimated", "demo-pct", "Token", "API Key", "Webhook"]
    assert all(text not in markdown for text in forbidden)


def test_local_only_and_real_gated_fake_do_not_fetch_network_or_mark_real_data():
    local_summary = build_account_fund_nav_provider_summary(demo_group(), provider_mode="local_only")
    assert local_summary["has_real_nav_data"] is False
    assert local_summary["result_summary"]["local_only_count"] == 2

    class FakeProvider:
        def fetch_one(self, asset):
            return {
                "request_id": asset["asset_id"], "asset_id": asset["asset_id"], "code": asset["code"], "name": asset["name"],
                "type": "fund", "market": "CN", "price_mode": "estimated_nav_or_daily_nav", "provider_name": "fake_fund_nav",
                "data_status": "disabled_by_default", "data_mode": "real_provider", "has_real_nav_data": False, "will_fetch_real_data": False,
                "nav": {"unit_nav": None, "accumulated_nav": None, "daily_change_pct": None, "nav_date": None},
                "estimate": {"estimated_nav": None, "estimated_change_pct": None, "estimated_change_amount": None, "estimate_time": None},
                "source": {"provider": "fake_fund_nav", "provider_type": "fake", "source_status": "fake", "checked_at": "demo"},
                "provider_checks": {"allow_commit_to_repo": False, "cache_scope": "local_only", "network_enabled": False},
                "warnings": ["盘中估算仅供观察，最终以基金公司公布净值为准。"], "disclaimer": "demo", "reason": "fake only",
            }

    real_summary = build_account_fund_nav_provider_summary(demo_group(), provider_mode="real_gated", provider=FakeProvider())
    assert real_summary["has_real_nav_data"] is False
    assert real_summary["result_summary"]["real_provider_count"] == 2
