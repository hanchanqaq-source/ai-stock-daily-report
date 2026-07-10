"""Context-aware wording policy for personal local workbench copy.

This module intentionally validates wording only. It does not fetch market data,
fund NAV data, account configuration, or trigger any trading action.
"""

from __future__ import annotations

from typing import Any, Mapping

POLICY_NAME = "personal_wording_policy"
PERSONAL_WORDING_DISCLAIMER = "仅作为个人观察和记录，需用户自行判断。"
FUND_ESTIMATE_WORDING = "最终以基金公司公布净值为准"

WORDING_MODES = {
    "public_safe": {
        "wording_mode": "public_safe",
        "allow_personal_observation_labels": True,
        "allow_direct_page_labels": True,
        "allow_stock_realtime_wording": True,
        "allow_fund_realtime_wording": False,
        "block_forced_trading": True,
        "block_guaranteed_return": True,
        "block_secret_leak": True,
        "require_redacted_demo_values": True,
    },
    "personal_local": {
        "wording_mode": "personal_local",
        "allow_personal_observation_labels": True,
        "allow_direct_page_labels": True,
        "allow_stock_realtime_wording": True,
        "allow_fund_realtime_wording": False,
        "block_forced_trading": True,
        "block_guaranteed_return": True,
        "block_secret_leak": True,
        "require_redacted_demo_values": False,
    },
}

ALLOWED_PERSONAL_OBSERVATION_LABELS = [
    "买入观察", "加仓观察", "减仓观察", "卖出观察", "清仓观察", "止盈观察", "止损观察", "持有观察", "关注观察", "风险观察",
]
ALLOWED_PAGE_LABELS = ["资金看板", "账户首页资金看板", "仓位看板", "成本看板", "盈亏看板", "实时涨跌看板", "行情看板", "仓位观察", "成本观察", "盈亏观察", "交易记录", "操作记录"]
ALLOWED_STOCK_REALTIME_CONTEXTS = ["股票实时涨跌", "ETF 实时涨跌", "ETF实时涨跌", "指数实时涨跌", "A股实时涨跌", "港股实时涨跌", "美股实时涨跌", "韩股实时涨跌"]
ALLOWED_MARKET_WORDING = ["实时行情", "最新价", "涨跌幅", "涨跌额"]
FORBIDDEN_FUND_REALTIME_WORDING = ["场外基金实时涨跌", "普通基金实时涨跌", "基金实时价格", "场外基金实时价格", "实时净值"]
REQUIRED_FUND_ALTERNATIVES = ["场外基金估算涨跌", "基金净值涨跌", "估算净值", "日净值", FUND_ESTIMATE_WORDING]
FORBIDDEN_FORCED_TRADING = ["必须买入", "必须卖出", "立刻买入", "立刻卖出", "无脑买入", "无脑卖出", "全仓买入", "梭哈", "自动下单", "自动买入", "自动卖出", "替我买入", "替我卖出", "强制交易"]
FORBIDDEN_GUARANTEED_RETURN = ["保证收益", "必赚", "稳赚", "一定赚钱", "绝对上涨", "必涨", "翻倍保证", "无风险收益"]
FORBIDDEN_PRIVACY_FIELDS = ["真实金额", "成本价", "账户资产", "持仓金额", "Token", "API Key", "Webhook", "Secret", "密码", "身份证", "手机号"]


def build_personal_wording_policy(mode: str = "public_safe") -> dict[str, Any]:
    if mode not in WORDING_MODES:
        raise ValueError(f"unsupported wording mode: {mode}")
    return {
        "policy_name": POLICY_NAME,
        **WORDING_MODES[mode],
        "allowed_personal_observation_labels": list(ALLOWED_PERSONAL_OBSERVATION_LABELS),
        "allowed_page_labels": list(ALLOWED_PAGE_LABELS),
        "allowed_stock_realtime_contexts": list(ALLOWED_STOCK_REALTIME_CONTEXTS),
        "allowed_market_wording": list(ALLOWED_MARKET_WORDING),
        "forbidden_fund_realtime_wording": list(FORBIDDEN_FUND_REALTIME_WORDING),
        "required_fund_alternatives": list(REQUIRED_FUND_ALTERNATIVES),
        "forbidden_forced_trading": list(FORBIDDEN_FORCED_TRADING),
        "forbidden_guaranteed_return": list(FORBIDDEN_GUARANTEED_RETURN),
        "forbidden_privacy_fields": list(FORBIDDEN_PRIVACY_FIELDS),
        "disclaimer": PERSONAL_WORDING_DISCLAIMER,
    }


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def classify_personal_wording(text: str, context: str = "personal_workspace", mode: str = "public_safe") -> dict[str, Any]:
    policy = build_personal_wording_policy(mode)
    rendered = str(text)
    if _contains_any(rendered, policy["forbidden_forced_trading"]):
        return {"allowed": False, "blocked": True, "classification": "blocked_forced_trading", "reason": "强制交易或自动执行表达。"}
    if _contains_any(rendered, policy["forbidden_guaranteed_return"]):
        return {"allowed": False, "blocked": True, "classification": "blocked_guaranteed_return", "reason": "收益承诺或无风险表达。"}
    if _contains_any(rendered, policy["forbidden_fund_realtime_wording"]):
        return {"allowed": False, "blocked": True, "classification": "blocked_fund_realtime_wording", "reason": "场外基金不能写成实时涨跌 / 实时价格 / 实时净值。", "allowed_alternatives": policy["required_fund_alternatives"]}
    if context in {"public_demo", "repo_example", "ci_fixture"} and _contains_any(rendered, policy["forbidden_privacy_fields"]):
        return {"allowed": False, "blocked": True, "classification": "blocked_public_privacy_field", "reason": "public demo / repo 示例不能出现真实隐私字段或 secret。"}
    if _contains_any(rendered, policy["allowed_personal_observation_labels"] + policy["allowed_page_labels"] + policy["allowed_stock_realtime_contexts"] + policy["allowed_market_wording"]):
        return {"allowed": True, "blocked": False, "classification": "allowed_personal_wording", "reason": "个人观察 / 页面 / 股票 ETF 指数行情上下文允许。", "disclaimer_required": True, "disclaimer": policy["disclaimer"]}
    return {"allowed": True, "blocked": False, "classification": "neutral", "reason": "未命中放宽或禁止表达。", "disclaimer_required": False}


def is_allowed_personal_wording(text: str, context: str = "personal_workspace", mode: str = "public_safe") -> bool:
    return classify_personal_wording(text, context=context, mode=mode)["allowed"]


def render_personal_wording_policy_markdown(mode: str = "public_safe") -> str:
    policy = build_personal_wording_policy(mode)
    lines = [
        "# 个人使用场景文案策略说明", "", "## 1. 设计目标", "- 个人工作台允许直观、易懂的个人观察词语，但不放宽自动交易、收益承诺或隐私数据边界。", "", "## 2. 允许词语",
        *[f"- {item}" for item in policy["allowed_personal_observation_labels"] + policy["allowed_page_labels"] + policy["allowed_stock_realtime_contexts"]],
        "", "## 3. 禁止词语", *[f"- {item}" for item in policy["forbidden_forced_trading"] + policy["forbidden_guaranteed_return"]],
        "", "## 4. 实时涨跌规则", "- 股票 / ETF / 指数可以写实时涨跌。", "- 场外基金不能写实时涨跌，只能写估算涨跌 / 净值涨跌。", "", "## 5. 资金看板规则", "- 本地个人工作台可以叫资金看板，public demo 只能展示脱敏值。", "", "## 6. 安全边界", f"- {policy['disclaimer']}", "- 词语放宽不代表真实金额、成本价、账户资产、Token、API Key 或 Webhook 可以进入仓库。",
    ]
    return "\n".join(lines) + "\n"
