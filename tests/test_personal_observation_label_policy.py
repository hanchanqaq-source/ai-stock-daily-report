from src.personal_observation_label_policy import (
    OBSERVATION_LABEL_DISCLAIMER,
    build_personal_observation_label_policy,
    classify_observation_label_text,
    is_allowed_personal_observation_label,
    is_forbidden_auto_execution_expression,
    is_forbidden_forced_trading_expression,
    is_forbidden_guaranteed_return_expression,
    render_personal_observation_label_policy_markdown,
    validate_personal_observation_label_policy,
)


def test_policy_can_be_built_and_validated():
    policy = build_personal_observation_label_policy()
    assert validate_personal_observation_label_policy(policy)
    assert "买入观察" in policy["allowed_personal_observation_labels"]
    assert "自动下单" in policy["forbidden_auto_execution_expressions"]


import pytest


@pytest.mark.parametrize("label", ["买入观察", "分批买入", "加仓观察", "减仓观察", "卖出观察", "止盈观察", "止损观察", "清仓观察", "持有观察", "关注观察", "风险观察", "低吸区", "目标区", "风险位", "继续持有", "暂不操作"])
def test_allowed_personal_observation_labels(label):
    result = classify_observation_label_text(label)
    assert result["classification"] == "allowed_personal_observation_label"
    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["severity"] == "info"
    assert result["disclaimer_required"] is True
    assert OBSERVATION_LABEL_DISCLAIMER == result["disclaimer"]
    assert is_allowed_personal_observation_label(label)


@pytest.mark.parametrize("text", ["必须买入", "必须卖出", "立刻买入", "立即满仓", "稳赚", "保证收益", "必涨", "无风险", "自动下单", "替我买入", "系统替你下单"])
def test_forbidden_expressions_are_blocked_with_high_or_blocker_severity(text):
    result = classify_observation_label_text(text)
    assert result["allowed"] is False
    assert result["blocked"] is True
    assert result["severity"] in {"high", "blocker"}


def test_forbidden_helpers_detect_each_category():
    assert is_forbidden_forced_trading_expression("必须买入")
    assert is_forbidden_guaranteed_return_expression("保证收益")
    assert is_forbidden_auto_execution_expression("自动下单")


def test_allowed_words_are_context_sensitive_not_absolute_block_words():
    assert classify_observation_label_text("买入观察")["classification"] == "allowed_personal_observation_label"
    assert classify_observation_label_text("加仓观察")["classification"] == "allowed_personal_observation_label"
    assert classify_observation_label_text("减仓观察")["classification"] == "allowed_personal_observation_label"
    assert classify_observation_label_text("必须买入")["classification"] == "blocked_forced_trading_instruction"


def test_policy_markdown_contains_allowed_and_forbidden_examples():
    markdown = render_personal_observation_label_policy_markdown()
    assert "买入观察" in markdown
    assert "必须买入" in markdown
    assert OBSERVATION_LABEL_DISCLAIMER in markdown
