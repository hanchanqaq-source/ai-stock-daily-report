import pytest

from src.personal_wording_policy import (
    build_personal_wording_policy,
    classify_personal_wording,
    is_allowed_personal_wording,
    render_personal_wording_policy_markdown,
)


def test_policy_modes_document_public_safe_and_personal_local_boundaries():
    public = build_personal_wording_policy("public_safe")
    local = build_personal_wording_policy("personal_local")
    assert public["allow_personal_observation_labels"] is True
    assert public["allow_stock_realtime_wording"] is True
    assert public["allow_fund_realtime_wording"] is False
    assert public["require_redacted_demo_values"] is True
    assert local["require_redacted_demo_values"] is False
    assert public["disclaimer"] == "仅作为个人观察和记录，需用户自行判断。"


@pytest.mark.parametrize("text", ["买入观察", "加仓观察", "减仓观察", "卖出观察", "清仓观察", "止盈观察", "止损观察"])
def test_personal_observation_labels_are_allowed(text):
    result = classify_personal_wording(text)
    assert result["allowed"] is True
    assert result["classification"] == "allowed_personal_wording"
    assert result["disclaimer_required"] is True


@pytest.mark.parametrize("text", ["资金看板", "账户首页资金看板", "仓位看板", "仓位观察", "成本观察", "盈亏观察", "交易记录", "操作记录"])
def test_personal_workspace_page_labels_are_allowed(text):
    assert is_allowed_personal_wording(text)


@pytest.mark.parametrize("text", ["股票实时涨跌", "ETF 实时涨跌", "指数实时涨跌", "A股实时涨跌", "港股实时涨跌", "美股实时涨跌", "韩股实时涨跌"])
def test_stock_etf_and_index_realtime_wording_is_allowed(text):
    assert classify_personal_wording(text)["classification"] == "allowed_personal_wording"


@pytest.mark.parametrize("text", ["场外基金实时涨跌", "普通基金实时涨跌", "基金实时价格", "场外基金实时价格", "实时净值"])
def test_off_exchange_fund_realtime_wording_is_blocked(text):
    result = classify_personal_wording(text)
    assert result["blocked"] is True
    assert result["classification"] == "blocked_fund_realtime_wording"
    assert "估算净值" in result["allowed_alternatives"]


@pytest.mark.parametrize("text", ["场外基金估算涨跌", "基金净值涨跌", "估算净值", "日净值", "最终以基金公司公布净值为准"])
def test_off_exchange_fund_alternative_wording_is_allowed(text):
    assert classify_personal_wording(text)["allowed"] is True


@pytest.mark.parametrize("text", ["必须买入", "必须卖出", "立刻买入", "立刻卖出", "全仓买入", "梭哈", "自动下单执行", "替我买入", "替我卖出", "保证收益", "必赚", "稳赚", "必涨", "无风险收益"])
def test_forced_trading_and_guaranteed_return_wording_is_blocked(text):
    assert classify_personal_wording(text)["blocked"] is True


@pytest.mark.parametrize("text", ["真实金额", "成本价", "账户资产", "Token", "API Key", "Webhook"])
def test_public_demo_privacy_fields_are_blocked(text):
    result = classify_personal_wording(text, context="public_demo", mode="public_safe")
    assert result["blocked"] is True
    assert result["classification"] == "blocked_public_privacy_field"


def test_rendered_markdown_contains_required_sections():
    markdown = render_personal_wording_policy_markdown()
    assert "# 个人使用场景文案策略说明" in markdown
    assert "股票 / ETF / 指数可以写实时涨跌" in markdown
    assert "场外基金不能写实时涨跌" in markdown
    assert "资金看板" in markdown
    assert "仅作为个人观察和记录，需用户自行判断。" in markdown
