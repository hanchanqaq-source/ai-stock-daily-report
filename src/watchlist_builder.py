# -*- coding: utf-8 -*-
"""Structured public-market watchlist builder.

The builder only consumes public market aggregates already produced by trend,
sector persistence, risk radar, and data-quality modules. It intentionally uses
observation wording and strips direct trading verbs.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

from src.report_sections import sanitize_observation_text

logger = logging.getLogger(__name__)

_FORBIDDEN = ("买入", "卖出", "加仓", "减仓", "必须买", "必须卖")


def build_watchlist(
    *,
    trend: Mapping[str, Any] | None = None,
    persistence: Mapping[str, Any] | None = None,
    risk_radar: Mapping[str, Any] | None = None,
    data_quality: Mapping[str, Any] | None = None,
    latest_snapshot: Mapping[str, Any] | None = None,
    period: str = "daily",
) -> dict[str, Any]:
    """Build a stable structured public-market observation watchlist."""
    try:
        result = _build_watchlist(
            trend=trend or {},
            persistence=persistence or {},
            risk_radar=risk_radar or {},
            data_quality=data_quality or {},
            latest_snapshot=latest_snapshot or {},
            period=period,
        )
    except Exception as exc:  # pragma: no cover - report paths must fail open
        logger.warning("[WATCHLIST_BUILDER] skipped_reason=%s", type(exc).__name__)
        return _empty("观察清单生成失败，暂不生成完整观察重点。")

    logger.info("[WATCHLIST_BUILDER] status=%s", result["status"])
    logger.info("[WATCHLIST_BUILDER] market_watch_count=%s", len(result["market_watch"]))
    logger.info("[WATCHLIST_BUILDER] sector_watch_count=%s", len(result["sector_watch"]))
    logger.info("[WATCHLIST_BUILDER] risk_watch_count=%s", len(result["risk_watch"]))
    logger.info("[WATCHLIST_BUILDER] data_quality_watch_count=%s", len(result["data_quality_watch"]))
    if result["status"] != "available":
        logger.info("[WATCHLIST_BUILDER] skipped_reason=insufficient_data")
    return result


def render_watchlist_markdown(watchlist: Mapping[str, Any] | None, *, title: str = "## 今日观察清单") -> str:
    """Render structured watchlist data into compact Markdown."""
    data = watchlist if isinstance(watchlist, Mapping) else {}
    lines = [title, ""]
    if data.get("status") != "available":
        lines.append("- 历史样本不足，暂不生成完整观察清单。")
        logger.info("[WATCHLIST_BUILDER] markdown_rendered=true")
        return "\n".join(lines)
    rows = []
    for key in ("market_watch", "sector_watch", "risk_watch"):
        rows.extend(x for x in data.get(key, []) if isinstance(x, Mapping))
    rows.extend(x for x in data.get("data_quality_watch", []) if isinstance(x, Mapping))
    if not rows:
        lines.append("- 暂无明确观察项，继续观察市场温度、成交额和风险雷达变化。")
    for row in rows[:8]:
        prefix = "数据观察" if row in data.get("data_quality_watch", []) else f"{row.get('priority', '中')}优先级"
        lines.append(f"- {prefix}：{_clean(row.get('item'))}。")
    pending = data.get("pending_watch") or []
    for item in pending[:2]:
        lines.append(f"- 暂不判断项：{_clean(item)}")
    logger.info("[WATCHLIST_BUILDER] markdown_rendered=true")
    return "\n".join(lines)


def _build_watchlist(*, trend, persistence, risk_radar, data_quality, latest_snapshot, period):
    five = _window(trend, "5") or trend
    status = "available" if _status(five) == "available" or _status(risk_radar) == "available" else "insufficient_data"
    market_watch: list[dict[str, str]] = []
    sector_watch: list[dict[str, str]] = []
    risk_watch: list[dict[str, str]] = []
    data_watch: list[dict[str, str]] = []
    pending: list[str] = []

    if status != "available":
        return _insufficient_watchlist()

    temp = _metric_dir(five, "market_temperature")
    if temp == "升温":
        market_watch.append(_item("高", "观察市场热度是否继续扩散", "市场温度升温", "trend_analyzer"))
    elif temp == "降温":
        market_watch.append(_item("高", "观察市场降温是否延续", "市场温度降温", "trend_analyzer"))

    turnover = _metric_dir(five, "turnover")
    if turnover == "放量":
        market_watch.append(_item("高", "观察成交额是否继续放大", "近 5 日成交额趋势显示放量", "trend_analyzer"))
    elif turnover == "缩量":
        market_watch.append(_item("高", "观察成交额缩量是否缓解", "近 5 日成交额趋势显示缩量", "trend_analyzer"))

    rise = _metric_dir(five, "rise_ratio")
    if rise == "上升":
        market_watch.append(_item("中", "观察上涨占比是否继续修复", "近 5 日上涨占比改善", "trend_analyzer"))
    elif rise == "下降":
        market_watch.append(_item("中", "观察上涨占比是否继续回落", "近 5 日上涨占比走弱", "trend_analyzer"))

    p = _combined_persistence(persistence or _mapping(five).get("sector_persistence") or {})
    if p["persistent_leaders"]:
        sector_watch.append(_item("中", f"观察{_names(p['persistent_leaders'])}等持续强势方向是否继续扩散", "近 5 日多次进入领涨方向", "sector_persistence"))
    if p["short_term_breakouts"]:
        sector_watch.append(_item("中", "观察短线爆发方向是否具备持续性", f"{_names(p['short_term_breakouts'])}短线进入强势方向", "sector_persistence"))
    if p["pullback_risks"]:
        risk_watch.append(_item("高", "观察冲高回落方向是否继续走弱", "板块 / 概念持续性识别到冲高回落风险", "sector_persistence"))
    if p["persistent_laggers"]:
        risk_watch.append(_item("高", "观察持续走弱方向是否收敛", "板块 / 概念持续性识别到持续走弱方向", "sector_persistence"))

    for risk in risk_radar.get("risks", []) if isinstance(risk_radar, Mapping) else []:
        if isinstance(risk, Mapping) and risk.get("observation"):
            risk_watch.append(_item(str(risk.get("level") or "中"), risk["observation"], str(risk.get("reason") or "风险雷达识别到风险项"), "risk_radar"))

    quality = _mapping(data_quality) or _mapping(five.get("data_quality"))
    coverage = _num(quality.get("coverage_percent") or quality.get("average_coverage_percent"))
    if coverage is not None and coverage < 70 or quality.get("impact") == "是" or latest_snapshot.get("data_mode") == "insufficient_data":
        data_watch.append(_item("中", "观察后续数据覆盖率是否恢复", "当前数据覆盖率偏低或存在字段缺失", "data_quality"))
    if _mapping(trend).get("20", {}).get("status") == "insufficient_data":
        pending.append("历史样本不足，暂不做长期趋势判断。")

    next_items = [_clean(x.get("item")) for x in (market_watch + sector_watch + risk_watch + data_watch)[:5]]
    summary = "今日重点观察成交额、市场温度和冲高回落方向。" if period == "daily" else "下周重点观察趋势延续、主线扩散和风险收敛。"
    return {"status": status, "summary": _clean(summary), "market_watch": _dedupe(market_watch), "sector_watch": _dedupe(sector_watch), "risk_watch": _dedupe(risk_watch), "data_quality_watch": _dedupe(data_watch), "next_period_watch": next_items, "pending_watch": list(dict.fromkeys(pending))}


def _empty(reason):
    return {"status": "insufficient_data", "summary": _clean(reason), "market_watch": [], "sector_watch": [], "risk_watch": [], "data_quality_watch": [], "next_period_watch": [], "pending_watch": [reason]}


def _insufficient_watchlist():
    reason = "历史样本不足，暂不生成完整观察清单。"
    return {
        "status": "insufficient_data",
        "summary": _clean(reason),
        "market_watch": [],
        "sector_watch": [],
        "risk_watch": [],
        "data_quality_watch": [
            _item("中", "历史样本不足，暂不生成完整观察清单", "缺少足够历史数据", "watchlist_builder")
        ],
        "next_period_watch": [],
        "pending_watch": [reason],
    }

def _item(priority, item, reason, source): return {"priority": priority if priority in {"高", "中", "低"} else "中", "item": _clean(item), "reason": _clean(reason), "source": source}
def _clean(text):
    value = sanitize_observation_text(text).rstrip("。")
    for word in _FORBIDDEN: value = value.replace(word, "观察")
    return value

def _mapping(v): return v if isinstance(v, Mapping) else {}
def _window(v, key): return _mapping(_mapping(v).get(key))
def _status(v): return str(_mapping(v).get("status") or "insufficient_data")
def _metric_dir(item, key): return str(_mapping(_mapping(item).get(key)).get("direction") or "")
def _num(v):
    try: return None if v in (None, "") else float(v)
    except (TypeError, ValueError): return None

def _combined_persistence(persistence):
    source = _window(persistence, "5") or _mapping(persistence)
    out = {k: [] for k in ("persistent_leaders", "short_term_breakouts", "pullback_risks", "persistent_laggers")}
    for group in ("industries", "concepts"):
        g = _mapping(source.get(group))
        for key in out:
            for x in g.get(key, []) or []:
                name = x.get("name") if isinstance(x, Mapping) else x
                if name and str(name) not in out[key]: out[key].append(str(name))
    return out

def _names(names): return "、".join(names[:3])
def _dedupe(items):
    seen = set(); out = []
    for item in items:
        key = item["item"]
        if key not in seen:
            seen.add(key); out.append(item)
    return out[:6]
