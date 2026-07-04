# -*- coding: utf-8 -*-
"""Shared Markdown section renderers for public daily and weekly market reports.

The helpers in this module only render text from already prepared data.  They do
not fetch data, persist files, or send notifications, so report generation can
reuse the same wording without coupling to runtime side effects.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

NO_DATA_MESSAGE = "当前数据缺失，暂不展示该项。"
INSUFFICIENT_HISTORY_MESSAGE = "历史样本不足，暂不生成趋势判断。"
LOW_QUALITY_MESSAGE = "本期部分数据覆盖率较低，趋势判断仅供观察。"
NON_TRADING_DAY_MESSAGE = "当前为非交易日，使用最近可用交易日数据或历史快照。"
FORBIDDEN_ADVICE_WORDS = ("买入", "卖出", "加仓", "减仓", "必须买", "必须卖")


def sanitize_observation_text(text: Any) -> str:
    """Remove direct trading verbs from observation-oriented report text."""
    value = str(text or "").strip()
    for word in FORBIDDEN_ADVICE_WORDS:
        value = value.replace(word, "观察")
    return value


def render_one_line_summary(summary: Any, *, title: str) -> str:
    body = sanitize_observation_text(summary) or NO_DATA_MESSAGE
    return f"{title}\n\n{body}"


def render_market_temperature_section(
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    title: str,
) -> str:
    return _render_bullets(title, rows)


def render_trend_observation_section(
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]] | str | None,
    *,
    title: str,
    insufficient: bool = False,
) -> str:
    if insufficient:
        return f"{title}\n\n{INSUFFICIENT_HISTORY_MESSAGE}"
    if isinstance(rows, str):
        body = sanitize_observation_text(rows) or INSUFFICIENT_HISTORY_MESSAGE
        return f"{title}\n\n{body}"
    return _render_bullets(title, rows or {"趋势判断": INSUFFICIENT_HISTORY_MESSAGE})


def render_sector_persistence_section(
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]] | None,
    *,
    title: str,
) -> str:
    return _render_bullets(title, rows or {"持续性观察": NO_DATA_MESSAGE})


def render_data_quality_section(
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]] | None,
    *,
    title: str,
    low_quality: bool = False,
) -> str:
    body = _render_bullets(title, rows or {"覆盖率": NO_DATA_MESSAGE})
    if low_quality:
        body = f"{body}\n\n{LOW_QUALITY_MESSAGE}"
    return body


def render_watchlist_section(items: Iterable[Any] | None, *, title: str) -> str:
    cleaned = [sanitize_observation_text(item) for item in (items or [])]
    cleaned = [item if item.startswith("观察") else f"观察{item}" for item in cleaned if item]
    if not cleaned:
        cleaned = ["观察市场温度、成交额和主线持续性是否出现一致变化。"]
    return f"{title}\n\n" + "\n".join(f"- {item}" for item in cleaned[:6])


def _render_bullets(title: str, rows: Mapping[str, Any] | Sequence[tuple[str, Any]]) -> str:
    pairs = rows.items() if isinstance(rows, Mapping) else rows
    lines = [title, ""]
    any_line = False
    for label, value in pairs:
        text = _format_value(value)
        lines.append(f"- {label}：{sanitize_observation_text(text)}")
        any_line = True
    if not any_line:
        lines.append(f"- 说明：{NO_DATA_MESSAGE}")
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return NO_DATA_MESSAGE
    if isinstance(value, (list, tuple, set)):
        return "、".join(str(x) for x in value if x) or "无"
    return str(value)
