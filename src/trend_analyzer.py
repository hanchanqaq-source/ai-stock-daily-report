# -*- coding: utf-8 -*-
"""Recent public-market trend analysis based on persisted history snapshots."""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from src.history_store import HISTORY_DIR, SNAPSHOT_PREFIX, SNAPSHOT_SUFFIX, load_market_history_csv

logger = logging.getLogger(__name__)

MIN_WINDOW_DAYS = 5


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
    return "\n".join(lines).rstrip() + "\n"


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
        return None


def _fmt(value):
    return "--" if value is None else f"{float(value):.1f}"
