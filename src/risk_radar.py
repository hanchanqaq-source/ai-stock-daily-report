# -*- coding: utf-8 -*-
"""Public-market risk radar for daily and weekly reports.

The radar uses only already available public market snapshots, trend analysis and
sector/concept persistence signals. It returns stable structured data so Markdown,
Discord, web dashboards and future card renderers can reuse the same contract.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

from src.report_sections import sanitize_observation_text

logger = logging.getLogger(__name__)

RISK_LOW = "低"
RISK_MEDIUM = "中"
RISK_HIGH = "高"
RISK_INSUFFICIENT = "数据不足"
_FORBIDDEN = ("买入", "卖出", "加仓", "减仓", "必须买", "必须卖")


def build_risk_radar(
    *,
    latest_snapshot: Mapping[str, Any] | None = None,
    trend: Mapping[str, Any] | None = None,
    persistence: Mapping[str, Any] | None = None,
    data_quality: Mapping[str, Any] | None = None,
    history_count: int | None = None,
) -> dict[str, Any]:
    """Build a structured public-market risk radar without raising."""
    try:
        result = _build_risk_radar(
            latest_snapshot=latest_snapshot or {},
            trend=trend or {},
            persistence=persistence or {},
            data_quality=data_quality or {},
            history_count=history_count,
        )
    except Exception as exc:  # pragma: no cover - report path must fail open
        logger.warning("[RISK_RADAR] skipped_reason=%s", type(exc).__name__)
        return _empty_result("风险雷达暂不可用。")

    logger.info("[RISK_RADAR] status=%s", result["status"])
    logger.info("[RISK_RADAR] overall_risk_level=%s", result["overall_risk_level"])
    logger.info("[RISK_RADAR] risk_count=%s", result["risk_count"])
    logger.info("[RISK_RADAR] high_risk_count=%s", result["high_risk_count"])
    return result


def _build_risk_radar(*, latest_snapshot, trend, persistence, data_quality, history_count):
    risks: list[dict[str, Any]] = []
    warnings: list[str] = []
    five = _window(trend, "5")
    twenty = _window(trend, "20")
    quality = dict(data_quality or {})

    coverage = _num(quality.get("coverage_percent") or quality.get("average_coverage_percent"))
    missing = list(quality.get("missing_fields") or [])
    partial = list(quality.get("partial_fields") or [])
    data_mode = str(quality.get("data_mode") or latest_snapshot.get("data_mode") or "")
    if coverage is not None and coverage < 70 or missing or len(partial) >= 4 or data_mode == "insufficient_data":
        risks.append(_risk("数据质量风险", RISK_MEDIUM if data_mode != "insufficient_data" else RISK_HIGH,
                           "数据覆盖率偏低或存在重点字段缺失", {"coverage_percent": coverage, "missing_fields": missing, "partial_fields": partial, "data_mode": data_mode},
                           "观察数据覆盖率是否改善。"))

    if _status(five) != "available":
        risks.append(_risk("历史样本不足风险", RISK_INSUFFICIENT, "近 5 日历史数据不足，暂不生成完整风险判断。", {"history_count": history_count, "window_5d_status": _status(five)}, "观察历史快照数量是否补足。"))
    if _status(twenty) != "available":
        warnings.append("近 20 日历史样本不足。")

    if data_mode == "history_fallback" or _is_stale(latest_snapshot):
        risks.append(_risk("非交易日 / 历史兜底数据风险", RISK_MEDIUM, "当前使用历史兜底或非最新交易日数据", {"data_mode": data_mode, "latest_data_date": latest_snapshot.get("latest_data_date") or latest_snapshot.get("date")}, "观察后续交易日数据是否更新。"))

    if _status(five) == "available":
        if _metric_dir(five, "market_temperature") == "降温" or _below_avg(five, "rise_ratio") or _below_avg(five, "market_score"):
            risks.append(_risk("市场降温风险", RISK_MEDIUM, "近 5 日市场温度降温或上涨占比、市场评分低于均值", _metric_evidence(five, ["rise_ratio", "market_score", "market_temperature"]), "观察市场温度是否继续降温。"))
        if _below_avg(five, "turnover") or _metric_dir(five, "turnover") == "缩量":
            risks.append(_risk("成交额缩量风险", RISK_MEDIUM, "最新成交额低于近 5 日均值或近 5 日成交额方向为缩量", _metric_evidence(five, ["turnover"]), "观察成交额是否恢复。"))
        if _below_avg(five, "limit_diff") or _metric_dir(five, "limit_diff") == "走弱":
            risks.append(_risk("涨跌停差恶化风险", RISK_MEDIUM, "最新涨跌停差低于近 5 日均值或近 5 日方向走弱", _metric_evidence(five, ["limit_diff"]), "观察涨跌停差是否继续走弱。"))
        if _metric_dir(five, "market_score") == "走弱" or _below_avg(five, "market_score"):
            risks.append(_risk("市场评分走弱风险", RISK_MEDIUM, "市场评分走弱或最新评分低于近 5 日均值", _metric_evidence(five, ["market_score"]), "观察市场评分是否企稳。"))

    p = _combined_persistence(persistence or five.get("sector_persistence") or {})
    if p["pullback_risks"]:
        risks.append(_risk("板块 / 概念冲高回落风险", RISK_HIGH, "P3-B 持续性结果显示存在冲高回落方向", {"directions": p["pullback_risks"][:5]}, "观察冲高回落方向是否继续走弱。"))
    if p["persistent_laggers"]:
        risks.append(_risk("板块 / 概念持续走弱风险", RISK_HIGH, "P3-B 持续性结果显示存在持续走弱方向", {"directions": p["persistent_laggers"][:5]}, "观察持续走弱方向是否扩散。"))

    mid_high = [r for r in risks if r["level"] in {RISK_MEDIUM, RISK_HIGH}]
    if len(mid_high) >= 3:
        risks.append(_risk("多项风险叠加风险", RISK_HIGH, "同时出现 3 个及以上中高风险", {"medium_high_risk_count": len(mid_high)}, "观察多项风险是否同步缓和。"))

    high = sum(1 for r in risks if r["level"] == RISK_HIGH)
    medium = sum(1 for r in risks if r["level"] == RISK_MEDIUM)
    status = "available" if risks and any(r["level"] != RISK_INSUFFICIENT for r in risks) else "insufficient_data"
    overall = RISK_HIGH if high else RISK_MEDIUM if medium else RISK_INSUFFICIENT if status == "insufficient_data" else RISK_LOW
    return {"status": status, "overall_risk_level": overall, "risk_count": len(risks), "high_risk_count": high, "medium_risk_count": medium, "risks": risks, "watch_points": _watch_points(risks), "data_warnings": warnings}


def _empty_result(reason):
    return {"status": "insufficient_data", "overall_risk_level": RISK_INSUFFICIENT, "risk_count": 0, "high_risk_count": 0, "medium_risk_count": 0, "risks": [], "watch_points": [], "data_warnings": [reason]}

def _risk(t, level, reason, evidence, observation):
    return {"risk_type": t, "level": level, "reason": _clean(reason), "evidence": evidence or {}, "observation": _clean(observation)}
def _clean(s):
    text = sanitize_observation_text(s)
    for word in _FORBIDDEN: text = text.replace(word, "观察")
    return text

def _window(trend, key): return trend.get(key, {}) if isinstance(trend, Mapping) else {}
def _status(item): return str(item.get("status") or "insufficient_data") if isinstance(item, Mapping) else "insufficient_data"
def _num(v):
    try: return None if v in (None, "") else float(v)
    except (TypeError, ValueError): return None
def _metric(item, key): return item.get(key, {}) if isinstance(item.get(key), Mapping) else {}
def _metric_dir(item, key):
    if key == "market_temperature": return str(_metric(item, key).get("direction") or "")
    return str(_metric(item, key).get("direction") or "")
def _below_avg(item, key):
    m = _metric(item, key); latest = _num(m.get("latest")); avg = _num(m.get("average"))
    return latest is not None and avg is not None and latest < avg

def _metric_evidence(item, keys):
    out = {}
    for key in keys:
        m = _metric(item, key)
        out[key] = {"latest": m.get("latest"), "average": m.get("average"), "direction": m.get("direction")}
    return out

def _combined_persistence(persistence):
    buckets = {"pullback_risks": [], "persistent_laggers": []}
    source = _window(persistence, "5") or persistence
    for group in ("industries", "concepts"):
        g = source.get(group, {}) if isinstance(source, Mapping) else {}
        if isinstance(g, Mapping):
            for key in buckets:
                for item in g.get(key, []) or []:
                    name = item.get("name") if isinstance(item, Mapping) else item
                    if name and str(name) not in buckets[key]: buckets[key].append(str(name))
    for key in buckets:
        for item in source.get(key, []) or [] if isinstance(source, Mapping) else []:
            name = item.get("name") if isinstance(item, Mapping) else item
            if name and str(name) not in buckets[key]: buckets[key].append(str(name))
    return buckets

def _is_stale(snapshot):
    return bool(snapshot.get("is_history_fallback") or snapshot.get("is_non_trading_day")) if isinstance(snapshot, Mapping) else False

def _watch_points(risks):
    points=[]
    for r in risks:
        obs=r.get("observation")
        if obs and obs not in points: points.append(obs)
    return points[:6]
