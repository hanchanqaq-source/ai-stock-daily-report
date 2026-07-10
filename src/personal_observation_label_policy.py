"""Policy for personal observation labels and direct wording.

The policy treats words such as 买入 / 加仓 / 减仓 as context-sensitive:
they are allowed when used as personal observation labels, but blocked when
combined with forced trading, guaranteed return, or auto-execution wording.
"""

from __future__ import annotations

from typing import Any, Mapping

POLICY_NAME = "personal_observation_label_policy"
OBSERVATION_LABEL_DISCLAIMER = "本页面标签仅作为个人观察和记录，不自动下单，不构成强制交易指令。"

ALLOWED_PERSONAL_OBSERVATION_LABELS = [
    "买入观察", "分批买入", "低吸区", "加仓观察", "继续持有", "持有观察", "关注观察", "等待回调", "减仓观察", "冲高减仓",
    "卖出观察", "止盈观察", "止损观察", "清仓观察", "风险观察", "风险位", "目标区", "压力位", "支撑位", "暂不操作",
    "仅记录", "个人观察", "个人计划", "观察结论", "风险提醒", "下一步关注",
]

ALLOWED_SHORT_LABELS = ["买入区", "加仓区", "持有区", "减仓区", "止盈区", "止损区", "清仓区", "等待区", "风险区", "目标区"]

FORCED_TRADING_EXPRESSIONS = [
    "必须买入", "必须卖出", "必须加仓", "必须清仓", "立刻买入", "立刻卖出", "立即买入", "立即卖出", "立即满仓", "马上满仓", "无脑买入", "无脑卖出", "全仓买入", "梭哈",
    "系统建议你买入", "系统建议你卖出", "替我买入", "替我卖出", "强制交易",
]
GUARANTEED_RETURN_EXPRESSIONS = ["稳赚", "保证收益", "无风险", "一定涨", "一定翻倍", "必赚", "一定赚钱", "绝对上涨", "必涨", "翻倍保证", "无风险收益"]
AUTO_EXECUTION_EXPRESSIONS = ["系统替你下单", "自动下单", "自动买入", "自动卖出", "代替用户操作", "替我买入", "替我卖出"]


def build_personal_observation_label_policy() -> dict[str, Any]:
    return {
        "policy_name": POLICY_NAME,
        "allowed_personal_observation_labels": list(ALLOWED_PERSONAL_OBSERVATION_LABELS),
        "allowed_short_labels": list(ALLOWED_SHORT_LABELS),
        "forbidden_forced_trading_expressions": list(FORCED_TRADING_EXPRESSIONS),
        "forbidden_guaranteed_return_expressions": list(GUARANTEED_RETURN_EXPRESSIONS),
        "forbidden_auto_execution_expressions": list(AUTO_EXECUTION_EXPRESSIONS),
        "disclaimer": OBSERVATION_LABEL_DISCLAIMER,
    }


def validate_personal_observation_label_policy(policy: Mapping[str, Any]) -> bool:
    required = build_personal_observation_label_policy()
    return all(key in policy for key in required) and bool(policy.get("disclaimer"))


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def is_forbidden_forced_trading_expression(text: str, policy: Mapping[str, Any] | None = None) -> bool:
    final_policy = policy or build_personal_observation_label_policy()
    return _contains_any(str(text), list(final_policy["forbidden_forced_trading_expressions"]))


def is_forbidden_guaranteed_return_expression(text: str, policy: Mapping[str, Any] | None = None) -> bool:
    final_policy = policy or build_personal_observation_label_policy()
    return _contains_any(str(text), list(final_policy["forbidden_guaranteed_return_expressions"]))


def is_forbidden_auto_execution_expression(text: str, policy: Mapping[str, Any] | None = None) -> bool:
    final_policy = policy or build_personal_observation_label_policy()
    return _contains_any(str(text), list(final_policy["forbidden_auto_execution_expressions"]))


def is_allowed_personal_observation_label(text: str, policy: Mapping[str, Any] | None = None) -> bool:
    final_policy = policy or build_personal_observation_label_policy()
    labels = list(final_policy["allowed_personal_observation_labels"]) + list(final_policy["allowed_short_labels"])
    return _contains_any(str(text), labels) and not (
        is_forbidden_forced_trading_expression(text, final_policy)
        or is_forbidden_guaranteed_return_expression(text, final_policy)
        or is_forbidden_auto_execution_expression(text, final_policy)
    )


def classify_observation_label_text(text: str, policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    final_policy = policy or build_personal_observation_label_policy()
    rendered = str(text)
    if is_forbidden_forced_trading_expression(rendered, final_policy):
        return {"text": rendered, "classification": "blocked_forced_trading_instruction", "severity": "blocker", "allowed": False, "blocked": True, "reason": "该表达属于强制交易指令。"}
    if is_forbidden_guaranteed_return_expression(rendered, final_policy):
        return {"text": rendered, "classification": "blocked_guaranteed_return", "severity": "blocker", "allowed": False, "blocked": True, "reason": "该表达属于保证收益或无风险承诺。"}
    if is_forbidden_auto_execution_expression(rendered, final_policy):
        return {"text": rendered, "classification": "blocked_auto_execution", "severity": "blocker", "allowed": False, "blocked": True, "reason": "该表达暗示自动下单或替用户操作。"}
    if is_allowed_personal_observation_label(rendered, final_policy):
        return {
            "text": rendered,
            "classification": "allowed_personal_observation_label",
            "severity": "info",
            "allowed": True,
            "blocked": False,
            "reason": "该表达用于个人观察标签，不代表强制交易指令。",
            "disclaimer_required": True,
            "disclaimer": final_policy["disclaimer"],
        }
    return {"text": rendered, "classification": "neutral", "severity": "info", "allowed": True, "blocked": False, "reason": "未命中个人观察标签或禁止表达。", "disclaimer_required": False}


def render_personal_observation_label_policy_markdown(policy: Mapping[str, Any] | None = None) -> str:
    final_policy = policy or build_personal_observation_label_policy()
    lines = [
        "# 个人观察标签与直接表达规则", "", "## 允许标签",
        *[f"- {label}" for label in final_policy["allowed_personal_observation_labels"]],
        *[f"- {label}" for label in final_policy["allowed_short_labels"]],
        "", "## 禁止表达",
        *[f"- {label}" for label in final_policy["forbidden_forced_trading_expressions"]],
        *[f"- {label}" for label in final_policy["forbidden_guaranteed_return_expressions"]],
        *[f"- {label}" for label in final_policy["forbidden_auto_execution_expressions"]],
        "", "## 安全说明", f"- {final_policy['disclaimer']}",
    ]
    return "\n".join(lines) + "\n"
