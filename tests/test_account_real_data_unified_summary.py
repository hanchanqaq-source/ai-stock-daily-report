from copy import deepcopy

from src.account_real_data_unified_summary import (
    build_account_real_data_unified_summary,
    build_unified_fund_nav_section,
    build_unified_stock_etf_section,
    merge_account_real_data_sections,
    render_account_real_data_unified_summary_markdown,
    validate_account_real_data_unified_summary,
)
from src.account_cn_quote_provider_integration import build_account_cn_quote_provider_summary
from src.account_fund_nav_provider_integration import build_account_fund_nav_provider_summary


def demo_group():
    return {
        "account_id": "demo_account",
        "account_name": "示例账户",
        "assets": [
            {"asset_id": "stock_h", "code": "DEMOS", "name": "演示股票", "type": "stock", "market": "CN", "status": "holding"},
            {"asset_id": "etf_w", "code": "DEMOE", "name": "演示 ETF", "type": "etf", "market": "CN", "status": "watching"},
            {"asset_id": "fund_h", "code": "DEMOF1", "name": "演示持有基金", "type": "fund", "market": "CN", "status": "holding"},
            {"asset_id": "fund_w", "code": "DEMOF2", "name": "演示观察基金", "type": "fund", "market": "CN", "status": "watching"},
            {"asset_id": "unknown", "code": "DEMO?", "name": "演示未知", "type": "unknown", "market": "CN", "status": "watching"},
            {"asset_id": "cleared", "code": "DEMOC", "name": "已清仓", "type": "stock", "market": "CN", "status": "cleared"},
        ],
    }


def test_default_summary_is_dry_run_redacted_and_does_not_mutate_group():
    group = demo_group()
    before = deepcopy(group)
    summary = build_account_real_data_unified_summary(group)

    assert group == before
    assert summary["data_mode"] == "dry_run"
    assert summary["sections"]["stock_etf"]["provider_mode"] == "dry_run"
    assert summary["sections"]["fund_nav"]["provider_mode"] == "dry_run"
    assert summary["display_mode"] == "redacted"
    assert summary["has_real_market_data"] is False
    assert summary["has_real_nav_data"] is False
    assert summary["commit_safe"] is False
    assert validate_account_real_data_unified_summary(summary)


def test_summary_contains_required_sections_counts_and_safety_status():
    summary = build_account_real_data_unified_summary(demo_group())

    assert "stock_etf" in summary["sections"]
    assert "fund_nav" in summary["sections"]
    assert "combined_counts" in summary
    assert "safety_summary" in summary
    assert summary["combined_counts"]["stock_etf_supported"] == 2
    assert summary["combined_counts"]["fund_nav_supported"] == 2
    assert summary["combined_counts"]["total_assets"] == 6
    assert summary["combined_counts"]["active_assets"] == 5
    assert summary["safety_summary"]["all_results_audited"] is True
    assert summary["safety_summary"]["all_display_models_checked"] is True
    assert summary["safety_summary"]["default_redacted"] is True
    assert summary["safety_summary"]["real_data_written_to_repo"] is False
    assert summary["safety_summary"]["secrets_detected"] is False


def test_can_build_and_merge_stock_etf_and_fund_nav_sections():
    stock_summary = build_account_cn_quote_provider_summary(demo_group())
    fund_summary = build_account_fund_nav_provider_summary(demo_group())

    stock_section = build_unified_stock_etf_section(stock_summary)
    fund_section = build_unified_fund_nav_section(fund_summary)
    merged = merge_account_real_data_sections(stock_section, fund_section)

    assert stock_section["supported_count"] == 2
    assert fund_section["supported_count"] == 2
    assert merged["sections"]["stock_etf"]["enabled"] is True
    assert merged["sections"]["fund_nav"]["enabled"] is True
    assert merged["combined_counts"]["displayable_total"] >= 0
    assert merged["combined_counts"]["unsupported_total"] >= 0


def test_provider_fakes_are_not_called_by_default_so_no_real_requests_happen():
    class RaisingStockProvider:
        def fetch_quote(self, asset):
            raise AssertionError("stock provider should not be called in dry_run")

    class RaisingFundProvider:
        def fetch_one(self, asset):
            raise AssertionError("fund provider should not be called in dry_run")

    summary = build_account_real_data_unified_summary(
        demo_group(), providers={"stock_etf": RaisingStockProvider(), "fund_nav": RaisingFundProvider()}
    )

    assert summary["sections"]["stock_etf"]["provider_mode"] == "dry_run"
    assert summary["sections"]["fund_nav"]["provider_mode"] == "dry_run"
    assert summary["has_real_market_data"] is False
    assert summary["has_real_nav_data"] is False


def test_stock_and_fund_field_boundaries_do_not_mix_or_use_realtime_fund_wording():
    summary = build_account_real_data_unified_summary(demo_group())
    stock_boundary = summary["sections"]["stock_etf"]["field_boundary"]
    fund_boundary = summary["sections"]["fund_nav"]["field_boundary"]

    assert "最新价" in stock_boundary
    assert "成交额" in stock_boundary
    assert "单位净值" not in stock_boundary
    assert "估算净值" not in stock_boundary
    assert "单位净值" in fund_boundary
    assert "估算净值" in fund_boundary
    assert "最新价" not in fund_boundary
    assert "成交额" not in fund_boundary
    assert "实时涨跌" not in repr(summary)
    assert "最终以基金公司公布净值为准" in repr(summary)


def test_blocked_display_models_do_not_expose_values_in_unified_sections():
    stock_summary = build_account_cn_quote_provider_summary(demo_group())
    stock_summary["display_models"][0].update({"display_status": "blocked", "display_mode": "blocked", "quote_display": {"last_price": "demo-price"}})
    fund_summary = build_account_fund_nav_provider_summary(demo_group())
    fund_summary["display_models"][0].update({"display_status": "blocked", "display_mode": "blocked", "nav_display": {"unit_nav": "demo-unit"}, "estimate_display": {"estimated_nav": "demo-est"}})

    stock_section = build_unified_stock_etf_section(stock_summary)
    fund_section = build_unified_fund_nav_section(fund_summary)

    assert "demo-price" not in repr(stock_section)
    assert "demo-unit" not in repr(fund_section)
    assert "demo-est" not in repr(fund_section)


def test_markdown_is_safe_and_contains_required_disclaimers():
    summary = build_account_real_data_unified_summary(demo_group())
    markdown = render_account_real_data_unified_summary_markdown(summary)

    assert "# 账户股票 / ETF / 基金真实数据统一汇总 Demo" in markdown
    assert "本阶段为统一真实数据汇总安全适配，不请求真实行情或真实基金净值。" in markdown
    assert "默认展示脱敏结果，不保存真实数据到仓库。" in markdown
    assert "场外基金不支持真正实时价格。" in markdown
    assert "盘中估算仅供观察，最终以基金公司公布净值为准。" in markdown
    assert "本页面只用于个人观察和记录，不构成交易建议。" in markdown
    forbidden = ["demo-price", "demo-turnover", "demo-unit", "demo-est", "demo-pct", "Token", "API Key", "Webhook"]
    assert all(text not in markdown for text in forbidden)
