from __future__ import annotations

from copy import deepcopy
import json

from src.account_market_page_adapter import (
    attach_market_summary_to_page_model,
    build_account_page_model_with_market_data,
    filter_market_results_for_page,
    render_account_market_page_demo_markdown,
    validate_account_market_page_model,
)
from src.account_page_model import build_account_page_model
from src.account_realtime_summary import build_account_realtime_summary


def asset(asset_id, type, status="holding", code="000001", name="示例股票A", **extra):
    data = {
        "asset_id": asset_id,
        "type": type,
        "code": code,
        "name": name,
        "market": "CN",
        "status": status,
        "tags": ["示例"],
        "weight_level": 1,
        "source_status": "manual_user_input",
    }
    data.update(extra)
    return data


def mixed_group():
    return {
        "account_id": "demo_mixed_group",
        "account_name": "示例混合账户",
        "enabled": True,
        "risk_profile": "balanced",
        "assets": [
            asset("demo_stock_001", "stock", "holding", "000001", "示例股票A"),
            asset("demo_etf_001", "etf", "holding", "DEMOA", "示例ETF"),
            asset("demo_index_001", "index", "watching", "000000", "示例指数", item_type="official_index"),
            asset("demo_fund_001", "fund", "watching", "000000", "示例场外基金A"),
            asset("demo_stock_002", "stock", "cleared", "000001", "示例股票A"),
            asset("demo_fund_002", "fund", "archived", "000000", "示例场外基金A"),
            asset("demo_etf_002", "etf", "deleted", "DEMOA", "示例ETF"),
        ],
    }



FORBIDDEN_DIRECTIVE_TRADING_PHRASES = [
    "建议买入", "建议卖出", "建议加仓", "建议减仓", "建议清仓",
    "推荐买入", "推荐卖出", "推荐加仓", "推荐减仓", "推荐清仓",
    "应该买入", "应该卖出", "应该加仓", "应该减仓", "应该清仓",
    "必须买入", "必须卖出", "必须加仓", "必须减仓", "必须清仓",
    "立即买入", "立即卖出", "立即加仓", "立即减仓", "立即清仓",
    "可以买入", "可以卖出", "可以加仓", "可以减仓", "可以清仓",
]

FORBIDDEN_FUND_REALTIME_PHRASES = [
    "实时基金涨跌",
    "实时基金净值",
    "基金实时涨跌",
    "基金实时净值",
]


def assert_no_directive_trading_phrases(text: str) -> None:
    for phrase in FORBIDDEN_DIRECTIVE_TRADING_PHRASES:
        assert phrase not in text, f"不应出现指挥性交易表达: {phrase}"
    for phrase in FORBIDDEN_FUND_REALTIME_PHRASES:
        assert phrase not in text, f"场外基金不应被写成实时行情: {phrase}"


def payload_text(value):
    return json.dumps(value, ensure_ascii=False) + "\n" + render_account_market_page_demo_markdown(value)


def test_builds_page_model_with_market_summary_without_changing_visible_pages():
    group = mixed_group()
    base = build_account_page_model(deepcopy(group))
    model = build_account_page_model_with_market_data(group)
    assert validate_account_market_page_model(model)
    assert model["visible_pages"] == base["visible_pages"]
    assert model["visible_pages"] == ["overview", "funds", "stocks", "themes", "watching", "holding_vs_watching", "history"]
    assert model["has_real_market_data"] is False
    assert model["data_mode"] in {"fixture_only", "model_only"}
    assert "market_summary" in model["pages"]["overview"]


def test_page_filters_are_kind_and_status_specific():
    summary = build_account_realtime_summary(mixed_group())
    funds = filter_market_results_for_page(summary, "funds")
    stocks = filter_market_results_for_page(summary, "stocks")
    watching = filter_market_results_for_page(summary, "watching")
    assert funds and all(item["result_kind"] == "fund_nav" and item["asset"]["type"] == "fund" for item in funds)
    assert stocks and all(item["result_kind"] == "realtime_quote" and item["asset"]["type"] in {"stock", "etf", "index"} for item in stocks)
    assert watching and all(item["asset"]["status"] == "watching" for item in watching)


def test_page_sections_match_required_filters_and_comparison_counts():
    model = build_account_page_model_with_market_data(mixed_group())
    funds = model["pages"]["funds"]["market_summary"]
    stocks = model["pages"]["stocks"]["market_summary"]
    watching = model["pages"]["watching"]["market_summary"]
    compare = model["pages"]["holding_vs_watching"]["market_summary"]
    assert funds["results"] and all(item["result_kind"] == "fund_nav" for item in funds["results"])
    assert stocks["results"] and all(item["result_kind"] == "realtime_quote" for item in stocks["results"])
    assert watching["results"] and all(item["asset"]["status"] == "watching" for item in watching["results"])
    assert compare["holding"]["available_count"] == 2
    assert compare["watching"]["available_count"] == 2
    assert_no_directive_trading_phrases(compare["disclaimer"])


def test_empty_and_history_pages_do_not_show_current_market_data():
    group = {**mixed_group(), "assets": [asset("demo_stock_001", "stock", "cleared", "000001", "示例股票A")]}
    model = build_account_page_model_with_market_data(group)
    assert model["visible_pages"] == ["empty_state", "history"]
    assert "market_summary" not in model["pages"]["empty_state"]
    assert "market_summary" not in model["pages"]["history"]
    assert "历史资产默认不参与当前行情 / 净值汇总。" == model["pages"]["history"]["market_note"]


def test_inactive_assets_are_not_in_market_page_results_and_input_is_not_mutated():
    group = mixed_group()
    before = deepcopy(group)
    model = build_account_page_model_with_market_data(group)
    assert group == before
    market_text = json.dumps(
        {key: page.get("market_summary") for key, page in model["pages"].items()},
        ensure_ascii=False,
    )
    assert "demo_stock_002" not in market_text
    assert "demo_fund_002" not in market_text
    assert "demo_etf_002" not in market_text
    assert {item["status"] for item in group["assets"]} == {item["status"] for item in before["assets"]}


def test_can_attach_prebuilt_summary_for_tests():
    group = mixed_group()
    page_model = build_account_page_model(group)
    summary = build_account_realtime_summary(group)
    model = attach_market_summary_to_page_model(page_model, summary)
    assert model["pages"]["overview"]["market_summary"]["has_real_market_data"] is False


def test_markdown_has_required_notes_and_no_forbidden_trading_or_fund_realtime_words():
    markdown = render_account_market_page_demo_markdown(build_account_page_model_with_market_data(mixed_group()))
    assert "最终以基金公司公布净值为准" in markdown
    assert "本阶段为 mock / fixture 数据，不代表真实行情。" in markdown
    assert "本页面内容不构成投资建议。" in markdown
    assert "本页面仅用于信息展示、风险观察和个人记录，不会自动执行任何操作。" in markdown
    assert "记录买入 / 记录卖出 / 记录加仓 / 记录减仓 / 标记清仓" in markdown
    assert "不代表系统建议你进行对应操作" in markdown
    assert_no_directive_trading_phrases(markdown)


def test_output_excludes_real_values_money_holdings_and_secrets():
    text = payload_text(build_account_page_model_with_market_data(mixed_group()))
    for forbidden in [
        "真实价格",
        "真实涨跌幅",
        "真实净值",
        "真实估算净值",
        "真实成交额",
        "金额",
        "成本价",
        "账户资产",
        "webhook",
        "Webhook",
        "Token",
        "API Key",
    ]:
        assert forbidden not in text
