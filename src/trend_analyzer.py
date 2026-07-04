# -*- coding: utf-8 -*-
"""Recent public-market trend analysis based on persisted history snapshots."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from src.history_store import HISTORY_DIR, SNAPSHOT_PREFIX, SNAPSHOT_SUFFIX, load_market_history_csv

logger = logging.getLogger(__name__)

MIN_WINDOW_DAYS = 5



def analyze_sector_persistence(window_days: int = 5, *, history_dir: Path | str = HISTORY_DIR) -> Dict[str, Any]:
    """Analyze industry persistence from public market history."""
    return _analyze_persistence(window_days, history_dir=history_dir)["industries"]


def analyze_concept_persistence(window_days: int = 5, *, history_dir: Path | str = HISTORY_DIR) -> Dict[str, Any]:
    """Analyze concept persistence from public market history."""
    return _analyze_persistence(window_days, history_dir=history_dir)["concepts"]


def analyze_multi_window_persistence(
    windows: list[int] | None = None, *, history_dir: Path | str = HISTORY_DIR
) -> Dict[str, Any]:
    """Analyze sector/concept persistence for several windows without raising."""
    windows = windows or [5, 20]
    return {str(window): _analyze_persistence(window, history_dir=history_dir) for window in windows}


def classify_persistence_state(item_history: Mapping[str, Any]) -> Dict[str, str]:
    """Classify one industry/concept history with explainable stable rules."""
    name = str(item_history.get("name") or "").strip()
    days = list(item_history.get("dates") or [])
    leading_dates = list(item_history.get("leading_dates") or [])
    lagging_dates = list(item_history.get("lagging_dates") or [])
    window_days = int(item_history.get("window_days") or max(len(days), 0) or 0)
    data_points = int(item_history.get("data_points") or len(days))
    latest_date = str(item_history.get("latest_date") or (days[-1] if days else ""))
    leading_count = len(leading_dates)
    lagging_count = len(lagging_dates)
    recent_leading = latest_date in leading_dates
    recent_lagging = latest_date in lagging_dates
    leading_streak = _tail_streak(days, set(leading_dates))
    lagging_streak = _tail_streak(days, set(lagging_dates))
    only_latest_leader = leading_count == 1 and recent_leading
    if data_points < 3 or not name:
        return {"state": "数据不足", "confidence": "数据不足", "bucket": "insufficient", "reason": "历史样本少于 3 条或名称缺失，暂不判断。"}
    if leading_count and lagging_count and recent_lagging and _first_index(days, leading_dates) < _first_index(days, lagging_dates):
        return {"state": "冲高回落", "confidence": "中", "bucket": "pullback_risks", "reason": f"前期进入领涨榜，最近转入领跌榜，需观察热度回落风险。"}
    recent_lagging_stage = _last_index(days, lagging_dates) >= max(0, data_points - 3)
    if lagging_count >= max(2, data_points // 2) and recent_lagging_stage and leading_count <= 1:
        return {"state": "持续走弱", "confidence": "高" if lagging_count >= 3 else "中", "bucket": "persistent_laggers", "reason": f"近 {window_days} 日 {lagging_count} 次进入领跌榜，最近阶段仍偏弱。"}
    if leading_count >= max(2, data_points // 2) and leading_streak >= 2 and lagging_count <= 1:
        return {"state": "持续走强", "confidence": "高" if leading_count >= 3 else "中", "bucket": "persistent_leaders", "reason": f"近 {window_days} 日 {leading_count} 次进入领涨榜，最近连续 {leading_streak} 日保持强势。"}
    if only_latest_leader:
        return {"state": "短线爆发", "confidence": "中", "bucket": "short_term_breakouts", "reason": "仅在最近 1 日突然进入领涨榜，属于短线爆发观察。"}
    if leading_count >= 2 and leading_streak < 2 and lagging_count <= 1:
        return {"state": "轮动扩散", "confidence": "中", "bucket": "rotation_candidates", "reason": f"近 {window_days} 日 {leading_count} 次进入领涨榜但不连续，显示轮动扩散迹象。"}
    if leading_count and not recent_leading:
        return {"state": "冲高回落", "confidence": "低", "bucket": "pullback_risks", "reason": "前期进入领涨榜但最近未延续，需观察冲高回落风险。"}
    return {"state": "数据不足", "confidence": "数据不足", "bucket": "insufficient", "reason": "有效领涨/领跌记录不足，暂不判断。"}


def render_persistence_summary_text(result: Mapping[str, Any]) -> str:
    """Render a compact Markdown section for sector/concept persistence."""
    results = result if all(isinstance(v, Mapping) for v in result.values()) else {str(result.get("window_days", 5)): result}
    lines = ["## 板块 / 概念持续性观察", ""]
    for key in sorted(results, key=lambda k: int(k) if str(k).isdigit() else 999):
        item = results[key]
        window = item.get("window_days", key)
        if item.get("status") != "available":
            msg = "近 20 日历史数据不足，暂不判断长期持续性。" if int(window) >= 20 else f"近 {window} 日历史数据不足，暂不判断。"
            lines.append(f"- {msg}")
            continue
        combined = _combine_persistence_names(item)
        lines.extend([
            f"- 近 {window} 日持续走强方向：{combined['persistent_leaders'] or '暂无'}",
            f"- 近 {window} 日短线爆发方向：{combined['short_term_breakouts'] or '暂无'}",
            f"- 近 {window} 日轮动扩散方向：{combined['rotation_candidates'] or '暂无'}",
            f"- 近 {window} 日冲高回落风险：{combined['pullback_risks'] or '暂无'}",
            f"- 近 {window} 日持续走弱方向：{combined['persistent_laggers'] or '暂无'}",
        ])
    logger.info("[SECTOR_PERSISTENCE] summary_rendered=true")
    return "\n".join(lines).rstrip() + "\n"

def analyze_multi_window_trends(
    windows: list[int] | None = None, *, history_dir: Path | str = HISTORY_DIR
) -> Dict[str, Any]:
    """Analyze multiple recent windows and return stable structured results."""
    windows = windows or [5, 20]
    return {str(window): analyze_recent_trends(window, history_dir=history_dir) for window in windows}


def analyze_recent_trends(days: int = 5, *, history_dir: Path | str = HISTORY_DIR) -> Dict[str, Any]:
    """Analyze recent public-market trends for one window without raising."""
    try:
        rows = load_recent_market_history(days, history_dir=history_dir)
        data_points = len(rows)
        if data_points < days or data_points < MIN_WINDOW_DAYS:
            result = _empty_result(
                days, data_points, f"历史数据不足，暂不生成趋势判断（需要 {days} 日，当前 {data_points} 日）。"
            )
            logger.info("[TREND_ANALYZER] window=%s status=%s data_points=%s", days, result["status"], data_points)
            return result

        result = _build_result(days, rows)
        result["sectors"] = calculate_sector_persistence(days, history_dir=history_dir)
        result["sector_persistence"] = _analyze_persistence(days, history_dir=history_dir)
        logger.info("[TREND_ANALYZER] window=%s status=%s data_points=%s", days, result["status"], data_points)
        logger.info("[TREND_ANALYZER] market_temperature=%s", result["market_temperature"].get("direction"))
        return result
    except Exception as exc:  # defensive: trend analysis must never block reporting
        logger.warning("[TREND_ANALYZER] skipped_reason=%s", exc)
        return _empty_result(days, 0, "趋势分析失败，暂不生成趋势判断。")


def load_recent_market_history(days: int, *, history_dir: Path | str = HISTORY_DIR) -> List[Dict[str, Any]]:
    """Load up to ``days`` non-future CSV rows in ascending date order."""
    if days <= 0:
        return []
    rows = load_market_history_csv(history_dir=history_dir)
    today = date.today().isoformat()
    valid_rows = [row for row in rows if str(row.get("date") or "") <= today]
    return valid_rows[-days:]


def calculate_trend_direction(
    values: list[float],
    *,
    up_label: str = "上升",
    down_label: str = "下降",
    flat_label: str = "震荡",
    threshold: float = 0.03,
) -> str:
    """Compare the latest value with the previous average using a small threshold."""
    clean = [float(v) for v in values if v is not None]
    if len(clean) < 2:
        return "数据不足"
    latest = clean[-1]
    previous = clean[:-1]
    average = sum(previous) / len(previous)
    baseline = abs(average) if average != 0 else 1.0
    if latest > average + baseline * threshold:
        return up_label
    if latest < average - baseline * threshold:
        return down_label
    return flat_label


def calculate_sector_persistence(
    days: int, *, history_dir: Path | str = HISTORY_DIR
) -> Dict[str, List[Dict[str, Any]]]:
    """Count repeated leading/lagging industries and concepts from CSV plus JSON snapshots."""
    rows = load_recent_market_history(days, history_dir=history_dir)
    if len(rows) < days or len(rows) < MIN_WINDOW_DAYS:
        return _empty_sectors()
    buckets = {
        "persistent_leading_industries": Counter(),
        "persistent_lagging_industries": Counter(),
        "persistent_leading_concepts": Counter(),
        "persistent_lagging_concepts": Counter(),
    }
    csv_fields = {
        "persistent_leading_industries": "top_leading_industry",
        "persistent_lagging_industries": "top_lagging_industry",
        "persistent_leading_concepts": "top_leading_concept",
        "persistent_lagging_concepts": "top_lagging_concept",
    }
    for row in rows:
        for bucket, field in csv_fields.items():
            name = str(row.get(field) or "").strip()
            if name:
                buckets[bucket][name] += 1
        snapshot = _load_snapshot_for_row(row, history_dir=history_dir)
        sectors = snapshot.get("sectors", {}) if isinstance(snapshot, dict) else {}
        for bucket, key in (
            ("persistent_leading_industries", "leading_industries"),
            ("persistent_lagging_industries", "lagging_industries"),
            ("persistent_leading_concepts", "leading_concepts"),
            ("persistent_lagging_concepts", "lagging_concepts"),
        ):
            for item in sectors.get(key, []) if isinstance(sectors, dict) else []:
                name = str(item.get("name") if isinstance(item, Mapping) else item).strip()
                if name:
                    buckets[bucket][name] += 1
    return {key: _counter_to_persistence(counter, days) for key, counter in buckets.items()}


def render_trend_summary_text(trend_result: Mapping[str, Any]) -> str:
    """Render a compact Markdown section for daily reports."""
    results = (
        trend_result
        if all(isinstance(v, Mapping) for v in trend_result.values())
        else {str(trend_result.get("window_days", 5)): trend_result}
    )
    lines = ["## 近 5 日 / 20 日趋势观察", ""]
    for key in sorted(results, key=lambda k: int(k) if str(k).isdigit() else 999):
        item = results[key]
        window = item.get("window_days", key)
        if item.get("status") != "available":
            lines.append(f"- 近 {window} 日：历史数据不足，暂不生成趋势判断。")
            continue
        temp = item.get("market_temperature", {})
        rise = item.get("rise_ratio", {})
        turnover = item.get("turnover", {})
        sectors = item.get("sectors", {})
        strong = [x.get("name") for x in sectors.get("persistent_leading_industries", [])[:3] if x.get("name")]
        strong_text = "、".join(strong) if strong else "暂无稳定方向"
        lines.extend(
            [
                f"- 近 {window} 日市场温度：{temp.get('direction', '数据不足')}",
                f"- 近 {window} 日上涨占比：当前 {_fmt(rise.get('latest'))}%，均值 {_fmt(rise.get('average'))}%，趋势：{rise.get('direction', '数据不足')}",
                f"- 近 {window} 日成交额：当前 {_fmt(turnover.get('latest'))} 亿元，均值 {_fmt(turnover.get('average'))} 亿元，趋势：{turnover.get('direction', '数据不足')}",
                f"- 近 {window} 日强势持续方向：{strong_text}",
                f"- 数据质量：近 {window} 日平均覆盖率 {_fmt(item.get('data_quality', {}).get('average_coverage_percent'))}%",
            ]
        )
    logger.info("[TREND_ANALYZER] trend_summary_rendered=true")
    persistence_text = render_persistence_summary_text({str(k): v.get("sector_persistence", _empty_persistence_result(int(k), 0)) for k, v in results.items() if isinstance(v, Mapping)})
    return ("\n".join(lines).rstrip() + "\n\n" + persistence_text).rstrip() + "\n"


def _build_result(days: int, rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rise_values = _numbers(rows, "rise_ratio")
    turnover_values = _numbers(rows, "turnover")
    limit_values = _numbers(rows, "limit_diff")
    score_values = _numbers(rows, "market_score")
    quality_values = _numbers(rows, "coverage_percent")
    temp_direction = _market_temperature(rise_values, turnover_values, score_values)
    return {
        "window_days": days,
        "data_points": len(rows),
        "status": "available",
        "market_temperature": {"direction": temp_direction, "reason": "上涨占比、成交额、市场评分综合判断"},
        "rise_ratio": _metric(rise_values, "上升", "下降", "震荡"),
        "turnover": _metric(turnover_values, "放量", "缩量", "平稳"),
        "limit_diff": _metric(limit_values, "改善", "走弱", "平稳"),
        "market_score": _metric(score_values, "改善", "走弱", "平稳"),
        "data_quality": {
            "average_coverage_percent": _average(quality_values),
            "low_quality_days": [
                str(r.get("date"))
                for r in rows
                if (_to_float(r.get("coverage_percent")) is not None and _to_float(r.get("coverage_percent")) < 60)
            ],
        },
        "sectors": _empty_sectors(),
        "sector_persistence": _empty_persistence_result(days, len(rows)),
    }


# helpers


def _empty_result(days: int, data_points: int, reason: str) -> Dict[str, Any]:
    return {
        "window_days": days,
        "data_points": data_points,
        "status": "insufficient_data",
        "reason": reason,
        "market_temperature": {"direction": "数据不足", "reason": reason},
        "rise_ratio": {"latest": None, "average": None, "direction": "数据不足"},
        "turnover": {"latest": None, "average": None, "direction": "数据不足"},
        "limit_diff": {"latest": None, "average": None, "direction": "数据不足"},
        "market_score": {"latest": None, "average": None, "direction": "数据不足"},
        "data_quality": {"average_coverage_percent": None, "low_quality_days": []},
        "sectors": _empty_sectors(),
    }


def _empty_sectors():
    return {
        "persistent_leading_industries": [],
        "persistent_lagging_industries": [],
        "persistent_leading_concepts": [],
        "persistent_lagging_concepts": [],
    }


def _numbers(rows, key):
    return [v for v in (_to_float(r.get(key)) for r in rows) if v is not None]


def _to_float(v):
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


def _average(vals):
    return round(sum(vals) / len(vals), 2) if vals else None


def _metric(vals, up, down, flat):
    return {
        "latest": round(vals[-1], 2) if vals else None,
        "average": _average(vals[:-1] or vals),
        "direction": calculate_trend_direction(vals, up_label=up, down_label=down, flat_label=flat),
    }


def _market_temperature(r, t, s):
    dirs = [calculate_trend_direction(r), calculate_trend_direction(t), calculate_trend_direction(s)]
    if dirs.count("上升") + dirs.count("放量") >= 2 or dirs.count("上升") + dirs.count("改善") >= 2:
        return "升温"
    if dirs.count("下降") + dirs.count("缩量") >= 2 or dirs.count("下降") + dirs.count("走弱") >= 2:
        return "降温"
    return "震荡" if "数据不足" not in dirs else "数据不足"


def _counter_to_persistence(counter, days):
    high, mid = (4, 2) if days <= 5 else (10, 5)
    out = []
    for name, count in counter.most_common():
        level = "高" if count >= high else "中" if count >= mid else "低"
        out.append({"name": name, "count": count, "window_days": days, "persistence_level": level})
    return out


def _load_snapshot_for_row(row, *, history_dir):
    d = str(row.get("date") or "")
    if not d:
        return None
    path = Path(history_dir) / f"{SNAPSHOT_PREFIX}{d}{SNAPSHOT_SUFFIX}"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[TREND_ANALYZER] skipped_reason=bad_json date=%s reason=%s", d, exc)
        logger.warning("[SECTOR_PERSISTENCE] skipped_reason=bad_json date=%s", d)
        return None


def _fmt(value):
    return "--" if value is None else f"{float(value):.1f}"


def _analyze_persistence(window_days: int, *, history_dir: Path | str = HISTORY_DIR) -> Dict[str, Any]:
    try:
        rows = load_recent_market_history(window_days, history_dir=history_dir)
        data_points = len(rows)
        if data_points < 3 or data_points < window_days:
            result = _empty_persistence_result(window_days, data_points)
            logger.info("[SECTOR_PERSISTENCE] window=%s status=%s data_points=%s", window_days, result["status"], data_points)
            logger.info("[SECTOR_PERSISTENCE] skipped_reason=insufficient_data")
            return result
        dates = [str(r.get("date") or "") for r in rows]
        stats = {
            "industries": defaultdict(lambda: {"leading_dates": [], "lagging_dates": []}),
            "concepts": defaultdict(lambda: {"leading_dates": [], "lagging_dates": []}),
        }
        for row in rows:
            d = str(row.get("date") or "")
            _add_name(stats["industries"], row.get("top_leading_industry"), "leading_dates", d)
            _add_name(stats["industries"], row.get("top_lagging_industry"), "lagging_dates", d)
            _add_name(stats["concepts"], row.get("top_leading_concept"), "leading_dates", d)
            _add_name(stats["concepts"], row.get("top_lagging_concept"), "lagging_dates", d)
            snapshot = _load_snapshot_for_row(row, history_dir=history_dir)
            sectors = snapshot.get("sectors", {}) if isinstance(snapshot, dict) else {}
            if isinstance(sectors, Mapping):
                for item in sectors.get("leading_industries", []) or []:
                    _add_name(stats["industries"], _item_name(item), "leading_dates", d)
                for item in sectors.get("lagging_industries", []) or []:
                    _add_name(stats["industries"], _item_name(item), "lagging_dates", d)
                for item in sectors.get("leading_concepts", []) or []:
                    _add_name(stats["concepts"], _item_name(item), "leading_dates", d)
                for item in sectors.get("lagging_concepts", []) or []:
                    _add_name(stats["concepts"], _item_name(item), "lagging_dates", d)
        result = {
            "window_days": window_days,
            "data_points": data_points,
            "status": "available",
            "industries": _classify_group(stats["industries"], dates, window_days, data_points),
            "concepts": _classify_group(stats["concepts"], dates, window_days, data_points),
        }
        logger.info("[SECTOR_PERSISTENCE] window=%s status=available data_points=%s", window_days, data_points)
        logger.info("[SECTOR_PERSISTENCE] persistent_leaders=%s", _combine_persistence_names(result)["persistent_leaders"])
        logger.info("[SECTOR_PERSISTENCE] pullback_risks=%s", _combine_persistence_names(result)["pullback_risks"])
        return result
    except Exception as exc:
        logger.warning("[SECTOR_PERSISTENCE] skipped_reason=%s", exc)
        return _empty_persistence_result(window_days, 0)


def _empty_persistence_result(window_days: int, data_points: int) -> Dict[str, Any]:
    return {
        "window_days": window_days,
        "data_points": data_points,
        "status": "insufficient_data",
        "industries": _empty_persistence_buckets(),
        "concepts": _empty_persistence_buckets(),
        "reason": f"历史数据不足，暂不判断（需要 {window_days} 日，当前 {data_points} 日）。",
    }


def _empty_persistence_buckets() -> Dict[str, List[Dict[str, Any]]]:
    return {"persistent_leaders": [], "short_term_breakouts": [], "rotation_candidates": [], "pullback_risks": [], "persistent_laggers": []}


def _add_name(group: Dict[str, Any], raw: Any, bucket: str, d: str) -> None:
    name = str(raw or "").strip()
    if name and d and d not in group[name][bucket]:
        group[name][bucket].append(d)


def _item_name(item: Any) -> str:
    return str(item.get("name") if isinstance(item, Mapping) else item).strip()


def _classify_group(group: Mapping[str, Any], dates: List[str], window_days: int, data_points: int) -> Dict[str, List[Dict[str, Any]]]:
    buckets = _empty_persistence_buckets()
    for name, values in group.items():
        item_history = {"name": name, "dates": dates, "leading_dates": values["leading_dates"], "lagging_dates": values["lagging_dates"], "latest_date": dates[-1] if dates else "", "window_days": window_days, "data_points": data_points}
        classified = classify_persistence_state(item_history)
        bucket = classified.get("bucket")
        if bucket not in buckets:
            continue
        buckets[bucket].append({
            "name": name,
            "leading_count": len(values["leading_dates"]),
            "lagging_count": len(values["lagging_dates"]),
            "recent_dates": sorted(set(values["leading_dates"] + values["lagging_dates"]))[-3:],
            "state": classified["state"],
            "confidence": classified["confidence"],
            "reason": classified["reason"],
        })
    for items in buckets.values():
        items.sort(key=lambda x: (x["confidence"] != "高", -(x["leading_count"] + x["lagging_count"]), x["name"]))
    return buckets


def _tail_streak(dates: List[str], hit_dates: set[str]) -> int:
    streak = 0
    for d in reversed(dates):
        if d in hit_dates:
            streak += 1
        else:
            break
    return streak


def _first_index(dates: List[str], selected: List[str]) -> int:
    return min((dates.index(d) for d in selected if d in dates), default=10**6)


def _last_index(dates: List[str], selected: List[str]) -> int:
    return max((dates.index(d) for d in selected if d in dates), default=-1)


def _combine_persistence_names(item: Mapping[str, Any]) -> Dict[str, str]:
    out = {}
    for bucket in _empty_persistence_buckets():
        names = []
        for group_key in ("industries", "concepts"):
            group = item.get(group_key) if isinstance(item, Mapping) else None
            if isinstance(group, Mapping):
                names.extend(str(x.get("name")) for x in group.get(bucket, [])[:3] if isinstance(x, Mapping) and x.get("name"))
        out[bucket] = "、".join(dict.fromkeys(names))
    return out
