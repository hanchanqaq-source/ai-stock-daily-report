import json

import pytest

from src.personal_signal_cards import (
    FORBIDDEN_DIRECTIVE_TRADING_PHRASES,
    assert_no_directive_trading_language,
    build_demo_personal_signal_cards,
    build_empty_signal_cards,
    build_personal_signal_cards,
    build_ui_layout_reference_model,
    is_allowed_record_action,
    render_personal_signal_cards_markdown,
    render_ui_layout_reference_markdown,
    validate_personal_signal_cards,
    validate_ui_layout_reference_model,
)


def _serialized(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def test_build_personal_signal_cards_contains_required_zones_and_labels():
    cards = build_personal_signal_cards(
        {"asset_id": "demo_stock_001", "asset_name": "示例股票A", "asset_type": "stock"}
    )

    assert cards["asset_id"] == "demo_stock_001"
    assert cards["asset_name"] == "示例股票A"
    assert cards["card_type"] == "personal_observation_points"
    assert cards["has_real_market_data"] is False
    assert cards["data_mode"] in {"model_only", "fixture_only"}
    assert validate_personal_signal_cards(cards) is True

    by_key = {item["key"]: item for item in cards["cards"]}
    assert "buy_watch_zone" in by_key
    assert "add_watch_zone" in by_key
    assert "risk_control_zone" in by_key
    assert "target_watch_zone" in by_key
    assert by_key["buy_watch_zone"]["label"] == "观察买入区"
    assert by_key["add_watch_zone"]["label"] == "二次关注区"
    assert by_key["risk_control_zone"]["label"] == "风险控制位"
    assert by_key["target_watch_zone"]["label"] == "目标观察区"
    assert all(item["disclaimer"] for item in cards["cards"])


def test_record_actions_are_allowed_for_personal_records():
    cards = build_demo_personal_signal_cards()
    rendered = _serialized(cards)

    assert is_allowed_record_action("记录买入")
    assert is_allowed_record_action("记录卖出")
    assert is_allowed_record_action("记录加仓")
    assert is_allowed_record_action("记录减仓")
    assert is_allowed_record_action("标记清仓")
    assert "记录买入" in rendered
    assert "记录卖出" in rendered
    assert "记录加仓" in rendered
    assert "记录减仓" in rendered
    assert "标记清仓" in rendered


def test_markdown_demo_has_safe_disclaimers_and_no_directive_trading_language():
    markdown = render_personal_signal_cards_markdown(build_demo_personal_signal_cards())

    assert "# 个人观察点位卡片 Demo" in markdown
    assert "本阶段为 model_only / fixture_only 数据，不代表真实行情。" in markdown
    assert "本卡片仅用于个人观察和记录，不会自动执行任何操作。" in markdown
    assert "这些记录入口仅用于更新你的个人资产状态，不代表系统要求你执行对应操作。" in markdown
    assert "实时基金涨跌" not in markdown
    for phrase in FORBIDDEN_DIRECTIVE_TRADING_PHRASES:
        assert phrase not in markdown


@pytest.mark.parametrize("phrase", FORBIDDEN_DIRECTIVE_TRADING_PHRASES)
def test_directive_trading_language_is_rejected(phrase):
    with pytest.raises(ValueError):
        assert_no_directive_trading_language(f"系统输出：{phrase}")


def test_model_does_not_store_real_market_values_or_secrets():
    cards = build_demo_personal_signal_cards()
    markdown = render_personal_signal_cards_markdown(cards)
    combined = _serialized(cards) + "\n" + markdown

    forbidden_fragments = [
        "真实价格",
        "真实涨跌幅",
        "真实净值",
        "真实估算净值",
        "真实成交额",
        "真实金额",
        "成本价",
        "账户资产",
        "Token",
        "API Key",
        "Webhook",
        "个人邮箱",
        "手机号",
        "身份证",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in combined


def test_empty_signal_cards_remain_model_only_and_safe():
    cards = build_empty_signal_cards({"asset_id": "demo_etf_001", "asset_name": "示例ETF", "asset_type": "etf"}, "仅展示空状态模型")

    assert cards["cards"] == []
    assert cards["has_real_market_data"] is False
    assert cards["data_mode"] == "model_only"
    assert validate_personal_signal_cards(cards, allow_empty=True) is True


def test_ui_layout_reference_model_contains_navigation_top_bar_and_signal_cards_section():
    model = build_ui_layout_reference_model()

    assert model["layout_name"] == "personal_market_workspace"
    assert model["has_real_market_data"] is False
    assert model["data_mode"] == "model_only"
    assert validate_ui_layout_reference_model(model) is True
    assert model["left_navigation"]
    assert model["top_bar"]["search"] is True
    assert "A股" in model["top_bar"]["market_switcher"]
    assert "港股" in model["top_bar"]["market_switcher"]
    assert "美股" in model["top_bar"]["market_switcher"]
    assert any(section["key"] == "personal_signal_cards" for section in model["main_sections"])
    assert "账户切换" in model["enhancements"]
    assert "基金 / 股票分流" in model["enhancements"]
    assert "风险雷达" in model["enhancements"]


def test_ui_layout_reference_markdown_is_safe_model_only_demo():
    markdown = render_ui_layout_reference_markdown(build_ui_layout_reference_model())

    assert "# Web 页面布局参考模型 Demo" in markdown
    assert "个人观察点位卡片" in markdown
    assert "市场切换" in markdown
    assert "本阶段为 model_only 数据，不代表真实前端已实现。" in markdown
    for phrase in FORBIDDEN_DIRECTIVE_TRADING_PHRASES:
        assert phrase not in markdown
