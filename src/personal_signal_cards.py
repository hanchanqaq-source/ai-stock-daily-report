"""Model-only personal observation signal cards and UI layout references.

This module intentionally does not connect to market providers, does not read
user configuration, and does not persist real prices, returns, NAVs, turnover,
or account assets. Values in the demo builders are fixture/model examples only.
"""

from __future__ import annotations

from typing import Any

ALLOWED_DATA_MODES = {"model_only", "fixture_only"}
CARD_TYPE = "personal_observation_points"
PAGE_DISCLAIMER = "本卡片仅用于个人观察和记录，不会自动执行任何操作。"
CARD_DISCLAIMER = "仅用于个人观察和记录，不代表系统要求你执行操作。"
RECORD_SCOPE_DISCLAIMER = "这些记录入口仅用于更新你的个人资产状态，不代表系统要求你执行对应操作。"
MODEL_DATA_DISCLAIMER = "本阶段为 model_only / fixture_only 数据，不代表真实行情。"

ALLOWED_RECORD_ACTIONS = {"记录买入", "记录卖出", "记录加仓", "记录减仓", "标记清仓", "记录减仓 / 标记清仓"}
FORBIDDEN_DIRECTIVE_TRADING_PHRASES = [
    "建议买入",
    "建议卖出",
    "推荐买入",
    "推荐卖出",
    "应该加仓",
    "应该减仓",
    "必须买入",
    "必须卖出",
    "立即清仓",
]

REQUIRED_CARD_KEYS = ("buy_watch_zone", "add_watch_zone", "risk_control_zone", "target_watch_zone")

_DEMO_CARD_DEFINITIONS = [
    {
        "key": "buy_watch_zone",
        "label": "观察买入区",
        "display_value": "69–72",
        "explanation": "接近示例均线支撑，可作为个人记录买入参考区。",
        "record_action": "记录买入",
        "tone": "positive_watch",
    },
    {
        "key": "add_watch_zone",
        "label": "二次关注区",
        "display_value": "65–67",
        "explanation": "若回到该区间，可作为二次观察区；如果你已完成操作，可记录加仓。",
        "record_action": "记录加仓",
        "tone": "secondary_watch",
    },
    {
        "key": "risk_control_zone",
        "label": "风险控制位",
        "display_value": "跌破 63.9",
        "explanation": "跌破后可标记为高风险观察区域，并支持个人记录减仓或标记清仓。",
        "record_action": "记录减仓 / 标记清仓",
        "tone": "risk",
    },
    {
        "key": "target_watch_zone",
        "label": "目标观察区",
        "display_value": "第一目标 84.61，第二目标 90+",
        "explanation": "到达目标区后观察是否放量突破或冲高回落；如果你已完成操作，可记录卖出。",
        "record_action": "记录卖出",
        "tone": "target",
    },
]


def assert_no_directive_trading_language(text: str) -> None:
    """Raise ValueError when text contains direct trading directive phrases."""
    for phrase in FORBIDDEN_DIRECTIVE_TRADING_PHRASES:
        if phrase in text:
            raise ValueError(f"directive trading language is not allowed: {phrase}")


def is_allowed_record_action(text: str) -> bool:
    """Return whether a record action is allowed for personal records."""
    return text in ALLOWED_RECORD_ACTIONS


def build_signal_card_item(
    *,
    key: str,
    label: str,
    display_value: str,
    explanation: str,
    record_action: str,
    tone: str,
    disclaimer: str = CARD_DISCLAIMER,
) -> dict[str, Any]:
    """Build one model-only personal observation point card."""
    payload = {
        "key": key,
        "label": label,
        "display_value": display_value,
        "explanation": explanation,
        "record_action": record_action,
        "tone": tone,
        "disclaimer": disclaimer,
    }
    assert_no_directive_trading_language("\n".join(str(value) for value in payload.values()))
    if not is_allowed_record_action(record_action):
        raise ValueError(f"unsupported record action: {record_action}")
    return payload


def build_personal_signal_cards(asset: dict[str, Any], signal_inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the personal observation card model without reading real market data."""
    data_mode = (signal_inputs or {}).get("data_mode", "model_only")
    if data_mode not in ALLOWED_DATA_MODES:
        raise ValueError("data_mode must be model_only or fixture_only")

    cards = [build_signal_card_item(**definition) for definition in _DEMO_CARD_DEFINITIONS]
    model = {
        "asset_id": asset.get("asset_id", "demo_stock_001"),
        "asset_name": asset.get("asset_name") or asset.get("name", "示例股票A"),
        "asset_type": asset.get("asset_type") or asset.get("type", "stock"),
        "card_type": CARD_TYPE,
        "data_mode": data_mode,
        "has_real_market_data": False,
        "cards": cards,
        "page_disclaimer": PAGE_DISCLAIMER,
    }
    validate_personal_signal_cards(model)
    return model


def build_empty_signal_cards(asset: dict[str, Any], reason: str) -> dict[str, Any]:
    """Build an empty model-only card payload for unavailable demo inputs."""
    assert_no_directive_trading_language(reason)
    model = {
        "asset_id": asset.get("asset_id", "demo_stock_001"),
        "asset_name": asset.get("asset_name") or asset.get("name", "示例股票A"),
        "asset_type": asset.get("asset_type") or asset.get("type", "stock"),
        "card_type": CARD_TYPE,
        "data_mode": "model_only",
        "has_real_market_data": False,
        "cards": [],
        "empty_reason": reason,
        "page_disclaimer": PAGE_DISCLAIMER,
    }
    validate_personal_signal_cards(model, allow_empty=True)
    return model


def build_demo_personal_signal_cards() -> dict[str, Any]:
    """Build a deterministic demo card payload for docs and tests."""
    return build_personal_signal_cards({"asset_id": "demo_stock_001", "asset_name": "示例股票A", "asset_type": "stock"})


def validate_personal_signal_cards(cards: dict[str, Any], *, allow_empty: bool = False) -> bool:
    """Validate personal observation card safety and structure."""
    if cards.get("data_mode") not in ALLOWED_DATA_MODES:
        raise ValueError("data_mode must be model_only or fixture_only")
    if cards.get("has_real_market_data") is not False:
        raise ValueError("has_real_market_data must be false")
    if cards.get("card_type") != CARD_TYPE:
        raise ValueError("unsupported card_type")
    card_items = cards.get("cards")
    if not isinstance(card_items, list):
        raise ValueError("cards must be a list")
    if not allow_empty and [item.get("key") for item in card_items] != list(REQUIRED_CARD_KEYS):
        raise ValueError("personal signal cards must contain the four required zones")
    for item in card_items:
        text = "\n".join(str(value) for value in item.values())
        assert_no_directive_trading_language(text)
        if not item.get("disclaimer"):
            raise ValueError("each card must include disclaimer")
        if not is_allowed_record_action(item.get("record_action", "")):
            raise ValueError("record_action is not allowed")
    assert_no_directive_trading_language(render_personal_signal_cards_markdown(cards))
    return True


def render_personal_signal_cards_markdown(cards: dict[str, Any]) -> str:
    """Render a safe Markdown demo for personal observation point cards."""
    card_lines = []
    for item in cards.get("cards", []):
        card_lines.extend(
            [
                f"### {item['label']}",
                f"- 区间：{item['display_value']}",
                f"- 说明：{item['explanation']}",
                f"- 记录入口：{item['record_action']}",
                f"- 免责声明：{item['disclaimer']}",
                "",
            ]
        )
    markdown = "\n".join(
        [
            "# 个人观察点位卡片 Demo",
            "",
            "## 1. 资产信息",
            "",
            f"- 资产：{cards.get('asset_name', '示例股票A')}",
            f"- 类型：{cards.get('asset_type', 'stock')}",
            f"- 数据模式：{cards.get('data_mode', 'model_only')}",
            f"- 是否真实行情：{str(cards.get('has_real_market_data', False)).lower()}",
            "",
            "## 2. 点位卡片",
            "",
            *card_lines,
            "## 3. 数据说明",
            "",
            f"- {MODEL_DATA_DISCLAIMER}",
            f"- {PAGE_DISCLAIMER}",
            f"- {RECORD_SCOPE_DISCLAIMER}",
        ]
    )
    assert_no_directive_trading_language(markdown)
    return markdown


def build_ui_layout_reference_model() -> dict[str, Any]:
    """Build the model-only Web layout reference for a future page."""
    model = {
        "layout_name": "personal_market_workspace",
        "data_mode": "model_only",
        "has_real_market_data": False,
        "left_navigation": [
            {"key": "home", "label": "首页"},
            {"key": "accounts", "label": "账户"},
            {"key": "watching", "label": "自选 / 观察"},
            {"key": "holding", "label": "持有"},
            {"key": "funds", "label": "基金"},
            {"key": "stocks", "label": "股票"},
            {"key": "market_index", "label": "市场指数"},
            {"key": "signal_cards", "label": "点位卡片"},
            {"key": "news", "label": "资讯"},
            {"key": "settings", "label": "设置"},
        ],
        "top_bar": {
            "search": True,
            "account_switcher": True,
            "market_switcher": ["全球", "A股", "港股", "美股", "韩股"],
            "data_status": True,
        },
        "main_sections": [
            {"key": "account_overview", "label": "账户总览"},
            {"key": "market_summary", "label": "行情 / 净值摘要"},
            {"key": "related_sectors", "label": "关联板块"},
            {"key": "personal_signal_cards", "label": "个人观察点位卡片"},
            {"key": "risk_radar", "label": "风险雷达"},
            {"key": "news", "label": "相关新闻 / 公告"},
            {"key": "personal_records", "label": "个人记录入口"},
        ],
        "enhancements": [
            "账户切换",
            "基金 / 股票分流",
            "市场指数矩阵",
            "行情 / 净值摘要",
            "持有 vs 收藏",
            "风险雷达",
            "数据来源状态",
            "个人记录入口",
        ],
        "disclaimer": "本布局仅为后续 Web 页面参考模型，不代表真实前端已实现。",
    }
    validate_ui_layout_reference_model(model)
    return model


def validate_ui_layout_reference_model(model: dict[str, Any]) -> bool:
    """Validate the layout reference model."""
    if model.get("data_mode") != "model_only":
        raise ValueError("layout data_mode must be model_only")
    if model.get("has_real_market_data") is not False:
        raise ValueError("layout has_real_market_data must be false")
    if not model.get("left_navigation"):
        raise ValueError("layout must include left navigation")
    top_bar = model.get("top_bar", {})
    if top_bar.get("search") is not True or not top_bar.get("market_switcher"):
        raise ValueError("layout must include search and market switcher")
    section_keys = {section.get("key") for section in model.get("main_sections", [])}
    if "personal_signal_cards" not in section_keys:
        raise ValueError("layout must include personal signal cards section")
    return True


def render_ui_layout_reference_markdown(model: dict[str, Any]) -> str:
    """Render the UI layout reference model as Markdown."""
    validate_ui_layout_reference_model(model)
    nav = "\n".join(f"- {item['label']}" for item in model["left_navigation"])
    sections = "\n".join(f"- {item['label']}" for item in model["main_sections"])
    enhancements = "\n".join(f"- {item}" for item in model.get("enhancements", []))
    market_switcher = " / ".join(model["top_bar"]["market_switcher"])
    markdown = f"""# Web 页面布局参考模型 Demo

## 1. 左侧导航

{nav}

## 2. 顶部区域

- 搜索框：{model['top_bar']['search']}
- 账户切换：{model['top_bar']['account_switcher']}
- 市场切换：{market_switcher}
- 数据来源状态：{model['top_bar']['data_status']}

## 3. 主区域

{sections}

## 4. 本项目增强点

{enhancements}

## 5. 说明

- {model['disclaimer']}
- 本阶段为 model_only 数据，不代表真实前端已实现。
"""
    assert_no_directive_trading_language(markdown)
    return markdown


__all__ = [
    "ALLOWED_DATA_MODES",
    "FORBIDDEN_DIRECTIVE_TRADING_PHRASES",
    "build_personal_signal_cards",
    "build_empty_signal_cards",
    "build_demo_personal_signal_cards",
    "validate_personal_signal_cards",
    "render_personal_signal_cards_markdown",
    "build_ui_layout_reference_model",
    "validate_ui_layout_reference_model",
    "render_ui_layout_reference_markdown",
    "is_allowed_record_action",
    "assert_no_directive_trading_language",
    "build_signal_card_item",
]
