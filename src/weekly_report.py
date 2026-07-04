# -*- coding: utf-8 -*-
"""Enhanced weekly market review report built from public market history."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Optional

from src.history_store import load_market_history_csv
from src.trend_analyzer import analyze_multi_window_trends, analyze_multi_window_persistence
from src.risk_radar import build_risk_radar
from src.report_sections import (
    INSUFFICIENT_HISTORY_MESSAGE as STANDARD_INSUFFICIENT_HISTORY_MESSAGE,
    NO_DATA_MESSAGE,
    render_data_quality_section,
    render_market_temperature_section,
    render_one_line_summary,
    render_risk_radar_section,
    render_sector_persistence_section,
    render_trend_observation_section,
    render_watchlist_section,
    sanitize_observation_text,
)

logger = logging.getLogger(__name__)

INSUFFICIENT_HISTORY_MESSAGE = STANDARD_INSUFFICIENT_HISTORY_MESSAGE
DATA_MISSING = NO_DATA_MESSAGE
FORBIDDEN_ADVICE_WORDS = ("买入", "卖出", "加仓", "减仓")


@dataclass(frozen=True)
class WeeklyReportResult:
    report: str
    discord_summary: str
    filename: str
    loaded_snapshots: int
    insufficient_history: bool
    week_start: date
    week_end: date
    structured_result: dict[str, Any]


def resolve_week_range(today: Optional[date] = None) -> tuple[date, date]:
    current = today or date.today()
    if current.weekday() >= 5:
        current = current - timedelta(days=current.weekday() - 4)
    start = current - timedelta(days=current.weekday())
    return start, min(start + timedelta(days=4), current)


def load_week_snapshots(
    history_dir: str | Path = "data/history",
    *,
    today: Optional[date] = None,
) -> tuple[list[dict[str, Any]], date, date]:
    """Load current-week public snapshots, falling back to CSV rows without future dates."""
    week_start, week_end = resolve_week_range(today)
    root = Path(history_dir)
    by_date: dict[str, dict[str, Any]] = {}
    current = week_start
    while current <= week_end:
        path = root / f"market_snapshot_{current.isoformat()}.json"
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("[WEEKLY_REPORT] skipped_reason=damaged_json date=%s error=%s", current.isoformat(), exc)
                current += timedelta(days=1)
                continue
            if isinstance(payload, dict):
                item = dict(payload)
                item.setdefault("date", current.isoformat())
                by_date[current.isoformat()] = item
        current += timedelta(days=1)

    for row in load_market_history_csv(history_dir=root):
        d = str(row.get("date") or row.get("data_date") or "")
        if week_start.isoformat() <= d <= week_end.isoformat() and d not in by_date:
            item = dict(row)
            item.setdefault("date", d)
            by_date[d] = item

    snapshots = [by_date[d] for d in sorted(by_date)]
    logger.info("[WEEKLY_REPORT] enhanced=true")
    logger.info("[WEEKLY_REPORT] week_start=%s week_end=%s", week_start.isoformat(), week_end.isoformat())
    logger.info("[WEEKLY_REPORT] trading_days=%s", len(snapshots))
    return snapshots, week_start, week_end


def generate_weekly_report(
    history_dir: str | Path = "data/history",
    *,
    today: Optional[date] = None,
) -> WeeklyReportResult:
    snapshots, week_start, week_end = load_week_snapshots(history_dir, today=today)
    items = [_normalize_snapshot(s) for s in snapshots]
    structured = _build_structured_result(items, week_start, week_end, history_dir)
    insufficient = structured["status"] == "insufficient_data"
    filename = f"AI股票基金每周复盘报告_{week_start.strftime('%Y')}-W{week_start.isocalendar().week:02d}.md"
    report = _render_markdown(structured)
    summary = _render_discord_summary(structured)
    logger.info("[WEEKLY_REPORT] trend_loaded=%s", str(bool(structured.get("trend"))).lower())
    logger.info("[WEEKLY_REPORT] persistence_loaded=%s", str(bool(structured.get("persistence"))).lower())
    logger.info("[WEEKLY_REPORT] markdown_rendered=true")
    return WeeklyReportResult(report, summary, filename, len(snapshots), insufficient, week_start, week_end, structured)


def save_weekly_report(result: WeeklyReportResult, reports_dir: str | Path = "reports") -> str:
    root = Path(reports_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / result.filename
    path.write_text(result.report, encoding="utf-8")
    return str(path)


def run_weekly_report(*, notifier: Any = None, send_notification: bool = True, history_dir: str | Path = "data/history") -> WeeklyReportResult:
    logger.info("[REPORT] type=weekly")
    result = generate_weekly_report(history_dir)
    save_weekly_report(result)
    status = "skipped"
    if send_notification and notifier is not None:
        try:
            status = "success" if notifier.send_to_discord(result.discord_summary) else "failed"
        except Exception as exc:  # pragma: no cover
            status = "failed"
            logger.warning("Discord weekly report send failed: %s", exc)
    logger.info("[DISCORD] weekly_send_status=%s", status)
    return result


def _build_structured_result(items: list[dict[str, Any]], week_start: date, week_end: date, history_dir: str | Path) -> dict[str, Any]:
    trend = analyze_multi_window_trends([5, 20], history_dir=history_dir)
    persistence = analyze_multi_window_persistence([5, 20], history_dir=history_dir)
    status = "available" if len(items) >= 3 else "insufficient_data"
    metrics = {
        "average_rise_ratio": _round(_avg([x["up_ratio"] for x in items])),
        "latest_rise_ratio": _round(_latest(items, "up_ratio")),
        "average_turnover": _round(_avg([x["turnover"] for x in items])),
        "latest_turnover": _round(_latest(items, "turnover")),
        "average_limit_diff": _round(_avg([x["limit_diff"] for x in items])),
        "latest_limit_diff": _round(_latest(items, "limit_diff")),
        "average_market_score": _round(_avg([x["market_score"] for x in items])),
        "latest_market_score": _round(_latest(items, "market_score")),
    }
    temperature = _weekly_temperature(items, trend)
    data_quality = _data_quality(items)
    result = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "status": status,
        "trading_days": len(items),
        "market_temperature": temperature,
        "summary": _summary(status, temperature, metrics, persistence),
        "metrics": metrics,
        "trend": trend,
        "persistence": persistence,
        "data_quality": data_quality,
        "risk_radar": build_risk_radar(latest_snapshot=items[-1] if items else {}, trend=trend, persistence=persistence, data_quality=data_quality, history_count=len(items)),
        "next_week_watchlist": _watchlist(temperature, trend, persistence, data_quality),
    }
    if status == "insufficient_data":
        logger.info("[WEEKLY_REPORT] skipped_reason=insufficient_weekly_history")
    return result


def _normalize_snapshot(raw: Mapping[str, Any]) -> dict[str, Any]:
    a_share = _mapping(raw.get("a_share"))
    quality = _mapping(raw.get("data_quality"))
    breadth = _mapping(raw.get("breadth") or raw.get("market_breadth"))
    ml = _mapping(raw.get("market_light") or raw.get("market_light_snapshot"))
    return {
        "date": str(raw.get("date") or raw.get("data_date") or raw.get("trade_date") or raw.get("report_date") or ""),
        "market_score": _num(raw.get("market_score") or raw.get("market_signal") or raw.get("signal") or a_share.get("market_score") or ml.get("score")),
        "up_ratio": _num(raw.get("rise_ratio") or raw.get("up_ratio") or raw.get("advance_ratio") or a_share.get("rise_ratio") or breadth.get("rise_ratio")),
        "turnover": _num(raw.get("turnover") or raw.get("amount") or raw.get("成交额") or a_share.get("turnover") or breadth.get("turnover")),
        "limit_diff": _num(raw.get("limit_diff") or raw.get("limit_up_down_diff") or a_share.get("limit_diff")),
        "coverage_percent": _num(raw.get("coverage_percent") or quality.get("coverage_percent")),
        "data_mode": str(raw.get("data_mode") or ""),
        "strong": _sector_items(raw.get("strong_sectors") or raw.get("leading_sectors") or raw.get("top_industries") or _mapping(raw.get("sectors")).get("leading_industries")),
        "weak": _sector_items(raw.get("weak_sectors") or raw.get("lagging_sectors") or raw.get("bottom_industries") or _mapping(raw.get("sectors")).get("lagging_industries")),
    }


def _render_markdown(r: Mapping[str, Any]) -> str:
    m = r["metrics"]
    trend = r.get("trend", {})
    quality = r.get("data_quality", {})
    p = _combined_persistence(r.get("persistence", {}), "5")
    low_quality = quality.get("impact") == "是"
    sections = [
        "# AI 股票基金市场周报",
        render_one_line_summary(r.get("summary"), title="## 1. 本周一句话总结"),
        render_market_temperature_section(
            {
                "本周交易日数量": r.get("trading_days"),
                "平均上涨占比": f"{_fmt(m['average_rise_ratio'])}%",
                "最新上涨占比": f"{_fmt(m['latest_rise_ratio'])}%",
                "平均成交额": f"{_fmt(m['average_turnover'])} 亿",
                "最新成交额": f"{_fmt(m['latest_turnover'])} 亿",
                "平均涨跌停差": _signed(m["average_limit_diff"]),
                "最新涨跌停差": _signed(m["latest_limit_diff"]),
                "市场评分变化": _change(m["average_market_score"], m["latest_market_score"]),
                "市场温度": r.get("market_temperature"),
            },
            title="## 2. 本周市场温度",
        ),
        render_trend_observation_section(
            {
                "近 5 日趋势": _trend_temp(trend, "5"),
                "近 20 日趋势": _trend_temp(trend, "20"),
                "上涨占比趋势": _trend_metric(trend, "5", "rise_ratio"),
                "成交额趋势": _trend_metric(trend, "5", "turnover"),
                "涨跌停差趋势": _trend_metric(trend, "5", "limit_diff"),
                "市场评分趋势": _trend_metric(trend, "5", "market_score"),
                "数据质量趋势": _quality_trend(trend),
            },
            title="## 3. 本周趋势观察",
            insufficient=r.get("status") == "insufficient_data",
        ),
        render_sector_persistence_section(
            {
                "持续走强方向": _names(p, "persistent_leaders"),
                "短线爆发方向": _names(p, "short_term_breakouts"),
                "轮动扩散方向": _names(p, "rotation_candidates"),
                "冲高回落风险": _names(p, "pullback_risks"),
                "持续走弱方向": _names(p, "persistent_laggers"),
            },
            title="## 4. 板块 / 概念持续性观察",
        ),
        render_data_quality_section(
            {
                "本周平均覆盖率": f"{_fmt(quality.get('average_coverage_percent'))}%",
                "最低覆盖率日期": quality.get("lowest_coverage_date") or DATA_MISSING,
                "数据不足日期": _join(quality.get("insufficient_data_days")),
                "历史兜底日期": _join(quality.get("fallback_days")),
                "是否影响结论": quality.get("impact"),
            },
            title="## 5. 数据质量说明",
            low_quality=low_quality,
        ),
        render_risk_radar_section(r.get("risk_radar", {}), title="## 本周风险雷达", weekly=True),
        render_watchlist_section(r.get("next_week_watchlist", []), title="## 6. 下周观察重点"),
    ]
    return "\n\n".join(section.strip() for section in sections if section).rstrip() + "\n"

def _render_discord_summary(r: Mapping[str, Any]) -> str:
    p = _combined_persistence(r.get("persistence", {}), "5")
    lines = [
        "📊 本周市场周报", "",
        "一句话总结：", str(r.get("summary") or DATA_MISSING), "",
        "趋势：",
        f"近 5 日市场温度：{_trend_temp(r.get('trend', {}), '5')}",
        f"近 20 日趋势：{_trend_temp(r.get('trend', {}), '20')}", "",
        "持续性：",
        f"持续走强：{_names(p, 'persistent_leaders', limit=3)}",
        f"冲高回落：{_names(p, 'pullback_risks', limit=3)}", "",
        "数据质量：",
        f"本周平均覆盖率：{_fmt(r.get('data_quality', {}).get('average_coverage_percent'))}%",
        _risk_discord_line(r.get("risk_radar", {})),
    ]
    return "\n".join(lines)

# helpers
_mapping = lambda v: v if isinstance(v, Mapping) else {}
def _num(v):
    if v is None: return None
    if isinstance(v, str): v = re.sub(r"[^0-9.+-]", "", v)
    try: return float(v)
    except (TypeError, ValueError): return None
def _avg(vals):
    nums=[v for v in vals if isinstance(v,(int,float))]
    return mean(nums) if nums else None
def _round(v): return None if v is None else round(float(v), 2)
def _latest(items, key): return items[-1].get(key) if items else None
def _fmt(v): return DATA_MISSING if v is None else f"{float(v):.1f}"
def _signed(v): return DATA_MISSING if v is None else f"{float(v):+.1f}"
def _change(a,b): return DATA_MISSING if a is None or b is None else f"{float(a):.1f} → {float(b):.1f}（{float(b)-float(a):+.1f}）"
def _join(v): return "、".join(v or []) if v else "无"
def _sector_items(v):
    if not isinstance(v, list): return []
    out=[]
    for x in v:
        name = x if isinstance(x, str) else x.get("name") if isinstance(x, Mapping) else ""
        if name: out.append(str(name))
    return out[:5]

def _weekly_temperature(items, trend):
    if len(items) < 3: return "数据不足"
    five = _mapping(trend.get("5")).get("market_temperature", {}) if isinstance(trend, Mapping) else {}
    direction = _mapping(five).get("direction")
    if direction in {"升温", "降温", "震荡"}: return direction
    first, last = items[0], items[-1]
    changes = [(_num(last.get(k)) or 0) - (_num(first.get(k)) or 0) for k in ("up_ratio", "turnover", "market_score") if first.get(k) is not None and last.get(k) is not None]
    if len(changes) < 2: return "震荡"
    positive = sum(1 for x in changes if x > 0)
    negative = sum(1 for x in changes if x < 0)
    return "升温" if positive >= 2 else "降温" if negative >= 2 else "震荡"

def _data_quality(items):
    qs=[x["coverage_percent"] for x in items if x.get("coverage_percent") is not None]
    low=[x["date"] for x in items if x.get("coverage_percent") is not None and x["coverage_percent"] < 60]
    insufficient=[x["date"] for x in items if x.get("data_mode") == "insufficient_data"]
    fallback=[x["date"] for x in items if x.get("data_mode") == "history_fallback"]
    lowest = min((x for x in items if x.get("coverage_percent") is not None), key=lambda x: x["coverage_percent"], default={}).get("date")
    return {"average_coverage_percent": _round(_avg(qs)), "lowest_coverage_date": lowest, "low_quality_days": low, "insufficient_data_days": insufficient, "fallback_days": fallback, "impact": "是" if low or insufficient or len(items) < 3 else "否"}

def _summary(status, temp, metrics, persistence):
    if status == "insufficient_data": return INSUFFICIENT_HISTORY_MESSAGE
    p = _combined_persistence(persistence, "5")
    strong = _names(p, "persistent_leaders", limit=2)
    risk = _names(p, "pullback_risks", limit=1)
    turnover = "成交额温和放大" if (metrics.get("latest_turnover") or 0) >= (metrics.get("average_turnover") or 10**18) else "成交额未明显放大"
    tail = f"，{strong} 等方向持续活跃" if strong != "暂无" else ""
    risk_text = f"，但 {risk} 出现冲高回落风险" if risk != "暂无" else ""
    return sanitize_observation_text(f"本周市场整体{temp}，{turnover}{tail}{risk_text}。")

def _trend_temp(trend, key):
    item=_mapping(_mapping(trend).get(key)); return _mapping(item.get("market_temperature")).get("direction") or "数据不足"
def _trend_metric(trend, key, metric):
    item=_mapping(_mapping(trend).get(key)); m=_mapping(item.get(metric)); return m.get("direction") or "数据不足"
def _quality_trend(trend):
    item=_mapping(_mapping(trend).get("5")); q=_mapping(item.get("data_quality")); avg=q.get("average_coverage_percent")
    return "数据不足" if avg is None else f"近 5 日平均覆盖率 {_fmt(avg)}%"
def _combined_persistence(persistence, window):
    item=_mapping(_mapping(persistence).get(window)); out={k: [] for k in ("persistent_leaders","short_term_breakouts","rotation_candidates","pullback_risks","persistent_laggers")}
    for group in ("industries", "concepts"):
        g=_mapping(item.get(group))
        for key in out:
            for x in g.get(key, [])[:5] if isinstance(g.get(key), list) else []:
                if isinstance(x, Mapping) and x.get("name") and x.get("name") not in out[key]: out[key].append(str(x["name"]))
    return out
def _names(p, key, limit=5):
    names=(p.get(key) or [])[:limit]
    return "、".join(names) if names else "暂无"
def _watchlist(temp, trend, persistence, quality):
    p=_combined_persistence(persistence, "5")
    items=["观察持续走强方向是否继续扩散。", "观察成交额是否继续放大。"]
    if p.get("pullback_risks"): items.append("观察冲高回落方向是否继续走弱。")
    if quality.get("impact") == "是": items.append("观察数据覆盖率是否恢复。")
    items.append(f"观察市场温度是否从{temp}转为升温。" if temp != "升温" else "观察市场温度是否维持升温。")
    clean=[]
    for item in items[:5]:
        for word in FORBIDDEN_ADVICE_WORDS: item=item.replace(word,"观察")
        clean.append(item)
    return clean


def _risk_discord_line(radar):
    if not isinstance(radar, Mapping) or radar.get("status") == "insufficient_data":
        return "风险雷达：历史样本不足，暂不生成完整风险判断。"
    risks = [str(x.get("risk_type", "")).replace("风险", "") for x in radar.get("risks", []) if isinstance(x, Mapping) and x.get("level") in {"中", "高"}]
    focus = "、".join(risks[:2]) if risks else "暂无明显中高风险"
    return f"风险雷达：综合风险{radar.get('overall_risk_level', '数据不足')}，主要关注{focus}。"
