from copy import deepcopy
import json

from src.account_cn_quote_provider_integration import (
    audit_account_cn_quote_provider_results,
    build_account_cn_quote_display_models,
    build_account_cn_quote_provider_summary,
    fetch_account_cn_quote_provider_results,
    render_account_cn_quote_provider_summary_markdown,
    split_account_assets_for_cn_quote_provider,
    validate_account_cn_quote_provider_summary,
)


def demo_group():
    return {
        "account_id": "demo_account",
        "account_name": "示例账户",
        "assets": [
            {"asset_id": "stock_cn", "type": "stock", "code": "000001", "name": "示例股票", "market": "CN", "status": "holding"},
            {"asset_id": "etf_cn", "type": "etf", "code": "510300", "name": "示例ETF", "market": "CN", "status": "watching"},
            {"asset_id": "index_cn", "type": "index", "code": "000300", "name": "示例指数", "market": "CN", "status": "watching", "item_type": "official_index"},
            {"asset_id": "fund_cn", "type": "fund", "code": "000001", "name": "示例基金", "market": "CN", "status": "holding"},
            {"asset_id": "company_cn", "type": "company", "code": "demo", "name": "示例公司", "market": "CN", "status": "watching"},
            {"asset_id": "industry_cn", "type": "industry", "code": "industry", "name": "示例行业", "market": "CN", "status": "holding"},
            {"asset_id": "theme_cn", "type": "theme", "code": "theme", "name": "示例主题", "market": "CN", "status": "watching"},
            {"asset_id": "computed_cn", "type": "index", "code": "breadth", "name": "示例指标", "market": "CN", "status": "watching", "item_type": "computed_indicator"},
            {"asset_id": "unknown_cn", "type": "unknown", "code": "?", "name": "未知", "market": "CN", "status": "watching"},
            {"asset_id": "stock_us", "type": "stock", "code": "AAPL", "name": "示例美股", "market": "US", "status": "watching"},
            {"asset_id": "cleared_cn", "type": "stock", "code": "000002", "name": "已清仓", "market": "CN", "status": "cleared"},
            {"asset_id": "archived_cn", "type": "etf", "code": "159919", "name": "已归档", "market": "CN", "status": "archived"},
            {"asset_id": "deleted_cn", "type": "stock", "code": "000003", "name": "已删除", "market": "CN", "status": "deleted"},
        ],
    }


def by_id(results):
    return {item["asset_id"]: item for item in results}


def test_default_dry_run_reads_active_assets_and_does_not_mutate_group():
    group = demo_group()
    original = deepcopy(group)
    summary = build_account_cn_quote_provider_summary(group)

    assert group == original
    assert summary["provider_mode"] == "dry_run"
    assert summary["data_mode"] == "dry_run"
    assert summary["has_real_market_data"] is False
    assert summary["display_mode"] == "redacted"
    assert summary["asset_counts"]["total"] == 13
    assert summary["asset_counts"]["active"] == 10
    assert len(summary["results"]) == 10
    assert "cleared_cn" not in by_id(summary["results"])
    assert "archived_cn" not in by_id(summary["results"])
    assert "deleted_cn" not in by_id(summary["results"])
    assert validate_account_cn_quote_provider_summary(summary) == []


def test_holding_and_watching_are_summarized_separately():
    summary = build_account_cn_quote_provider_summary(demo_group())

    assert summary["holding"]["summary"]["total"] == 3
    assert summary["watching"]["summary"]["total"] == 7
    assert all(model["asset_status"] == "holding" for model in summary["holding"]["display_models"])
    assert all(model["asset_status"] == "watching" for model in summary["watching"]["display_models"])


def test_asset_routing_rules_for_supported_unsupported_and_invalid_assets():
    results = by_id(fetch_account_cn_quote_provider_results(demo_group()))

    assert results["stock_cn"]["data_status"] == "dry_run_only"
    assert results["stock_cn"]["data_mode"] == "dry_run"
    assert results["stock_cn"]["will_fetch_real_data"] is False
    assert results["stock_cn"]["has_real_market_data"] is False
    assert results["etf_cn"]["data_status"] == "dry_run_only"
    assert results["index_cn"]["data_status"] == "dry_run_only"
    assert results["index_cn"]["type"] == "official_index"
    assert results["fund_cn"]["data_status"] == "unsupported"
    assert "fund_nav_provider" in results["fund_cn"]["reason"]
    assert results["company_cn"]["data_status"] == "unsupported"
    assert results["industry_cn"]["data_status"] == "unsupported"
    assert results["theme_cn"]["data_status"] == "unsupported"
    assert results["computed_cn"]["data_status"] == "unsupported"
    assert results["unknown_cn"]["data_status"] == "invalid_request"
    assert results["stock_us"]["data_status"] == "unsupported"


def test_split_counts_supported_unsupported_invalid_and_active_only():
    split = split_account_assets_for_cn_quote_provider(demo_group())

    assert split["asset_counts"] == {
        "total": 13,
        "active": 10,
        "cn_quote_supported": 3,
        "unsupported": 6,
        "invalid_request": 1,
    }
    assert {asset["asset_id"] for asset in split["cn_quote_supported"]} == {"stock_cn", "etf_cn", "index_cn"}


def test_each_result_is_audited_and_sent_through_display_adapter_with_redaction():
    results = fetch_account_cn_quote_provider_results(demo_group())
    audits = audit_account_cn_quote_provider_results(results)
    models = build_account_cn_quote_display_models(results, audits)

    assert len(audits) == len(results)
    assert len(models) == len(results)
    assert all(audit["audit_type"] == "cn_quote_result_audit" for audit in audits)
    assert all(model["display_mode"] in {"redacted", "unavailable"} for model in models)
    assert all(model["has_real_market_data"] is False for model in models)


def test_blocked_or_failed_audit_does_not_show_quote_values():
    result = fetch_account_cn_quote_provider_results(demo_group())[0]
    bad_audit = {
        "audit_type": "cn_quote_result_audit",
        "audit_status": "blocked",
        "display_safe": False,
        "contains_secret": False,
        "has_real_market_data": True,
        "commit_safe": False,
        "issues": ["forced_block"],
    }
    model = build_account_cn_quote_display_models([result], [bad_audit])[0]

    assert model["display_mode"] == "blocked"
    assert model["quote_display"] == {}


def test_summary_contains_result_summary_and_safe_flags():
    summary = build_account_cn_quote_provider_summary(demo_group())

    assert "result_summary" in summary
    assert "holding" in summary
    assert "watching" in summary
    assert summary["result_summary"]["dry_run_count"] == 3
    assert summary["result_summary"]["unsupported_count"] == 6
    assert summary["has_real_market_data"] is False


def test_markdown_contains_required_safety_text_and_no_forbidden_values_or_secret_words():
    summary = build_account_cn_quote_provider_summary(demo_group())
    markdown = render_account_cn_quote_provider_summary_markdown(summary)
    lowered = markdown.lower()

    assert markdown.startswith("# 账户 A股 / ETF Provider 汇总 Dry-run Demo")
    assert "本阶段为账户 provider dry-run 接入，不请求真实行情。" in markdown
    assert "所有 provider 结果进入页面前必须经过审计和展示安全适配。" in markdown
    assert "默认展示脱敏结果，不保存真实行情到仓库。" in markdown
    for forbidden in ["真实价格", "真实涨跌幅", "真实成交额", "token", "api key", "api_key", "webhook"]:
        assert forbidden not in lowered
    assert "12.34" not in markdown
    assert "+1.23%" not in markdown
    assert "123456789" not in markdown


def test_local_only_and_real_gated_are_offline_safe_with_fake_provider():
    local_summary = build_account_cn_quote_provider_summary(demo_group(), provider_mode="local_only")
    assert local_summary["provider_mode"] == "local_only"
    assert local_summary["has_real_market_data"] is False

    def fake_fetcher(request):
        return {"quote": {"last_price": None, "change_pct": None, "change_amount": None, "volume": None, "turnover": None, "open": None, "high": None, "low": None, "previous_close": None}}

    real_summary = build_account_cn_quote_provider_summary(demo_group(), provider_mode="real_gated", provider=fake_fetcher)
    assert real_summary["provider_mode"] == "real_gated"
    assert real_summary["has_real_market_data"] is False
    assert all(item.get("provider_checks", {}).get("network_enabled") is False for item in real_summary["results"] if item.get("data_mode") == "real_provider")


def test_summary_json_does_not_include_real_quote_values():
    summary = build_account_cn_quote_provider_summary(demo_group())
    rendered = json.dumps(summary, ensure_ascii=False).lower()

    assert "12.34" not in rendered
    assert "+1.23%" not in rendered
    assert "123456789" not in rendered
