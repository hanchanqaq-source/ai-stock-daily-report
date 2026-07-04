# -*- coding: utf-8 -*-
"""Lightweight monthly archive summaries for public market history data."""
from __future__ import annotations

import csv
import json
import logging
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

HISTORY_DIR = Path("data/history")
ARCHIVE_DIR = Path("data/archive_summaries")
HISTORY_CSV = "market_history.csv"
MANIFEST_NAME = "cleanup_manifest.json"
SCAN_DIRS = ("data/reports", "output", "logs", "cache", "tmp")
SENSITIVE_PATTERNS = re.compile(
    r"(webhook|token|api[_-]?key|secret|authorization|cookie|cost[_-]?price|amount|asset|email|phone|身份证|手机号|邮箱)",
    re.IGNORECASE,
)


def generate_monthly_archive(
    month: str,
    *,
    history_dir: str | Path = HISTORY_DIR,
    archive_dir: str | Path = ARCHIVE_DIR,
    today: Optional[date] = None,
) -> dict[str, str]:
    """Generate Markdown, JSON and CSV summaries for one month without deleting files."""
    _validate_month(month)
    logger.info("[HISTORY_ARCHIVE] month=%s", month)
    markdown_path = generate_monthly_markdown_summary(month, history_dir=history_dir, archive_dir=archive_dir, today=today)
    json_path = generate_monthly_json_summary(month, history_dir=history_dir, archive_dir=archive_dir, today=today)
    csv_path = generate_monthly_sector_stats(month, history_dir=history_dir, archive_dir=archive_dir, today=today)
    summary = _build_monthly_summary(month, Path(history_dir), today=today)
    manifest = load_archive_manifest(archive_dir=archive_dir)
    update_archive_manifest(
        manifest,
        archive_dir=archive_dir,
        monthly_summary={
            "month": month,
            "markdown_summary": _rel(markdown_path),
            "json_summary": _rel(json_path),
            "sector_stats_csv": _rel(csv_path),
            "source_snapshot_count": summary["source"]["snapshot_count"],
        },
    )
    logger.info("[HISTORY_ARCHIVE] delete_performed=false reason=manual_confirm_required")
    return {"markdown_summary": str(markdown_path), "json_summary": str(json_path), "sector_stats_csv": str(csv_path)}


def generate_monthly_markdown_summary(
    month: str,
    *,
    history_dir: str | Path = HISTORY_DIR,
    archive_dir: str | Path = ARCHIVE_DIR,
    today: Optional[date] = None,
) -> Path:
    summary = _build_monthly_summary(month, Path(history_dir), today=today)
    path = Path(archive_dir) / f"monthly_summary_{month}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown(summary), encoding="utf-8")
    logger.info("[HISTORY_ARCHIVE] markdown_summary_saved=true path=%s", path)
    return path


def generate_monthly_json_summary(
    month: str,
    *,
    history_dir: str | Path = HISTORY_DIR,
    archive_dir: str | Path = ARCHIVE_DIR,
    today: Optional[date] = None,
) -> Path:
    summary = _build_monthly_summary(month, Path(history_dir), today=today)
    path = Path(archive_dir) / f"monthly_summary_{month}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[HISTORY_ARCHIVE] json_summary_saved=true path=%s", path)
    return path


def generate_monthly_sector_stats(
    month: str,
    *,
    history_dir: str | Path = HISTORY_DIR,
    archive_dir: str | Path = ARCHIVE_DIR,
    today: Optional[date] = None,
) -> Path:
    summary = _build_monthly_summary(month, Path(history_dir), today=today)
    path = Path(archive_dir) / f"monthly_sector_stats_{month}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    sector_map = summary["sectors"]
    specs = [
        ("industry", "leading", sector_map["leading_industries_frequency"]),
        ("industry", "lagging", sector_map["lagging_industries_frequency"]),
        ("concept", "leading", sector_map["leading_concepts_frequency"]),
        ("concept", "lagging", sector_map["lagging_concepts_frequency"]),
    ]
    for category, direction, counts in specs:
        for rank, (name, count) in enumerate(sorted(counts.items(), key=lambda x: (-x[1], x[0])), start=1):
            rows.append({"month": month, "category": category, "name": name, "direction": direction, "count": count, "rank": rank})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["month", "category", "name", "direction", "count", "rank"])
        writer.writeheader()
        writer.writerows(rows)
    logger.info("[HISTORY_ARCHIVE] sector_stats_saved=true path=%s", path)
    return path


def generate_delete_candidates(
    *,
    archive_dir: str | Path = ARCHIVE_DIR,
    scan_dirs: tuple[str, ...] = SCAN_DIRS,
    today: Optional[date] = None,
) -> Path:
    current = today or date.today()
    root = Path(archive_dir)
    root.mkdir(parents=True, exist_ok=True)
    scanned, files = [], []
    for name in scan_dirs:
        path = Path(name)
        if not path.exists():
            logger.info("[HISTORY_ARCHIVE] scan_skipped_missing_dir path=%s", path)
            scanned.append(f"{name}（不存在，已跳过）")
            continue
        scanned.append(name)
        for child in path.rglob("*"):
            if child.is_file() and not _path_looks_sensitive(child):
                try:
                    files.append((child, child.stat().st_size))
                except OSError:
                    continue
    path = root / f"delete_candidates_{current.isoformat()}.md"
    total_size = sum(size for _, size in files)
    lines = [
        "# 历史文件清理候选清单", "", "## 1. 本次扫描结果", "",
        f"- 扫描时间：{datetime.now().replace(microsecond=0).isoformat()}",
        f"- 扫描目录：{', '.join(scanned)}", f"- 总文件数：{len(files)}", f"- 估算总大小：{_human_size(total_size)}", "",
        "## 2. 建议保留", "", "必须长期保留：", "", "- data/history/market_history.csv", "- data/history/market_snapshot_YYYY-MM-DD.json", "- data/archive_summaries/*.json", "- data/archive_summaries/*.csv", "- data/archive_summaries/*.md", "",
        "## 3. 建议归档后清理", "", "可以列出但不要删除：", "", "- 旧 Markdown 日报", "- 旧完整 artifact", "- 旧图片卡片", "- 旧日志", "",
        "## 4. 可直接清理", "", "可以列出：", "", "- cache/", "- tmp/", "- __pycache__/", "- .pytest_cache/", "", "本次不会自动删除上述文件。", "",
        "## 5. 用户确认", "", "当前不会自动删除重要文件。", "如需删除，请后续手动运行 cleanup，并显式设置 confirm_cleanup=true。", "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    manifest = load_archive_manifest(archive_dir=root)
    update_archive_manifest(manifest, archive_dir=root, delete_candidate={"generated_at": datetime.now().replace(microsecond=0).isoformat(), "path": _rel(path), "manual_confirm_required": True})
    logger.info("[HISTORY_ARCHIVE] delete_candidates_saved=true path=%s", path)
    logger.info("[HISTORY_ARCHIVE] delete_performed=false reason=manual_confirm_required")
    return path


def load_archive_manifest(*, archive_dir: str | Path = ARCHIVE_DIR) -> dict[str, Any]:
    path = Path(archive_dir) / MANIFEST_NAME
    if not path.exists():
        return {"manifest_version": 1, "last_updated": None, "monthly_summaries": [], "delete_candidates": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[HISTORY_ARCHIVE] manifest_read_failed path=%s error=%s", path, exc)
        return {"manifest_version": 1, "last_updated": None, "monthly_summaries": [], "delete_candidates": []}
    return payload if isinstance(payload, dict) else {"manifest_version": 1, "last_updated": None, "monthly_summaries": [], "delete_candidates": []}


def update_archive_manifest(
    manifest: Mapping[str, Any] | None = None,
    *,
    archive_dir: str | Path = ARCHIVE_DIR,
    monthly_summary: Optional[dict[str, Any]] = None,
    delete_candidate: Optional[dict[str, Any]] = None,
) -> Path:
    root = Path(archive_dir); root.mkdir(parents=True, exist_ok=True)
    payload = dict(manifest or load_archive_manifest(archive_dir=root))
    payload.setdefault("manifest_version", 1)
    payload["last_updated"] = datetime.now().replace(microsecond=0).isoformat()
    summaries = [x for x in payload.get("monthly_summaries", []) if isinstance(x, dict)]
    if monthly_summary:
        summaries = [x for x in summaries if x.get("month") != monthly_summary.get("month")]
        summaries.append(monthly_summary)
        summaries.sort(key=lambda x: str(x.get("month", "")))
    payload["monthly_summaries"] = summaries
    candidates = [x for x in payload.get("delete_candidates", []) if isinstance(x, dict)]
    if delete_candidate and delete_candidate not in candidates:
        candidates.append(delete_candidate)
    payload["delete_candidates"] = candidates
    path = root / MANIFEST_NAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[HISTORY_ARCHIVE] manifest_updated=true")
    return path


def _build_monthly_summary(month: str, history_dir: Path, *, today: Optional[date] = None) -> dict[str, Any]:
    _validate_month(month)
    current = today or date.today()
    rows = _load_history_rows(history_dir / HISTORY_CSV, month, current)
    snapshots = _load_month_snapshots(history_dir, month, current)
    metrics = [_normalize_record(x) for x in rows]
    snap_metrics = [_normalize_record(x) for x in snapshots]
    by_date = {m["date"]: m for m in snap_metrics if m.get("date")}
    for m in metrics:
        if m.get("date") not in by_date:
            by_date[m.get("date")] = m
    items = [by_date[k] for k in sorted(by_date) if k]
    coverages = [x["coverage_percent"] for x in items if isinstance(x.get("coverage_percent"), (int, float))]
    turnovers = [x for x in items if isinstance(x.get("turnover"), (int, float))]
    risk_days = [x["date"] for x in items if _is_risk_day(x)]
    counters = _sector_counters(snapshots)
    return {
        "summary_version": 1,
        "month": month,
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "source": {"history_csv": _rel(history_dir / HISTORY_CSV), "snapshot_count": len(snapshots)},
        "trading_days": len(items),
        "data_quality": {
            "average_coverage_percent": _avg(coverages), "min_coverage_percent": min(coverages) if coverages else None, "max_coverage_percent": max(coverages) if coverages else None,
            "min_coverage_day": _min_day(items, "coverage_percent"), "missing_dates": [],
            "complete_days": len([x for x in items if _coverage_level(x) == "complete"]), "partial_missing_days": len([x for x in items if _coverage_level(x) == "partial"]),
            "insufficient_data_days": [x["date"] for x in items if _coverage_level(x) == "insufficient"], "history_fallback_days": [x["date"] for x in items if x.get("data_mode") == "history_fallback"],
        },
        "market": {"average_rise_ratio": _avg([x.get("rise_ratio") for x in items]), "average_turnover": _avg([x.get("turnover") for x in items]), "highest_turnover_day": _max_day(turnovers, "turnover"), "lowest_turnover_day": _min_day(turnovers, "turnover"), "average_limit_diff": _avg([x.get("limit_diff") for x in items]), "risk_days": risk_days},
        "sectors": {key: dict(counter) for key, counter in counters.items()},
        "cleanup": {"can_delete_after_summary": [], "keep_long_term": [_rel(history_dir / HISTORY_CSV), _rel(history_dir / "market_snapshot_YYYY-MM-DD.json")], "manual_confirm_required": True},
    }


def _load_history_rows(path: Path, month: str, today: date) -> list[dict[str, Any]]:
    if not path.exists():
        logger.info("[HISTORY_ARCHIVE] history_csv_missing path=%s", path)
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if _date_in_month(row.get("date"), month, today)]


def _load_month_snapshots(history_dir: Path, month: str, today: date) -> list[dict[str, Any]]:
    if not history_dir.exists():
        logger.info("[HISTORY_ARCHIVE] history_dir_missing path=%s", history_dir)
        return []
    out = []
    for path in sorted(history_dir.glob(f"market_snapshot_{month}-*.json")):
        if not _date_in_month(path.stem.removeprefix("market_snapshot_"), month, today):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[HISTORY_ARCHIVE] skip_damaged_snapshot path=%s error=%s", path, exc)
            continue
        if isinstance(payload, dict):
            out.append(payload)
    return out


def _normalize_record(raw: Mapping[str, Any]) -> dict[str, Any]:
    dq = _mapping(raw.get("data_quality")); breadth = _mapping(raw.get("breadth") or raw.get("a_share") or raw.get("market_breadth")); ml = _mapping(raw.get("market_light"))
    rise = _num(raw.get("rise_ratio") or breadth.get("rise_ratio") or breadth.get("up_ratio"))
    if rise is not None and rise <= 1:
        rise *= 100
    return {"date": str(raw.get("date") or raw.get("data_date") or raw.get("trade_date") or ""), "coverage_percent": _num(raw.get("coverage_percent") or dq.get("coverage_percent")), "rise_ratio": rise, "turnover": _num(raw.get("turnover") or breadth.get("turnover")), "limit_diff": _num(raw.get("limit_diff") or breadth.get("limit_diff")), "data_mode": raw.get("data_mode") or ml.get("data_mode")}


def _sector_counters(snapshots: list[Mapping[str, Any]]) -> dict[str, Counter]:
    counters = {"leading_industries_frequency": Counter(), "lagging_industries_frequency": Counter(), "leading_concepts_frequency": Counter(), "lagging_concepts_frequency": Counter()}
    for raw in snapshots:
        sectors = _mapping(raw.get("sectors")); concepts = _mapping(raw.get("concepts"))
        _count_names(counters["leading_industries_frequency"], raw.get("strong_sectors") or raw.get("leading_sectors") or sectors.get("top"))
        _count_names(counters["lagging_industries_frequency"], raw.get("weak_sectors") or raw.get("lagging_sectors") or sectors.get("bottom"))
        _count_names(counters["leading_concepts_frequency"], raw.get("leading_concepts") or concepts.get("top"))
        _count_names(counters["lagging_concepts_frequency"], raw.get("lagging_concepts") or concepts.get("bottom"))
    return counters


def _render_markdown(summary: Mapping[str, Any]) -> str:
    q = summary["data_quality"]; m = summary["market"]; s = summary["sectors"]
    return "\n".join([
        f"# {summary['month']} 历史数据归档摘要", "", "## 1. 数据范围", "", f"- 月份：{summary['month']}", f"- 交易日数量：{summary['trading_days']}", f"- 快照文件数量：{summary['source']['snapshot_count']}", f"- 数据覆盖率平均值：{_fmt(q['average_coverage_percent'], '%')}", f"- 数据覆盖率最低日期：{q.get('min_coverage_day') or '数据暂缺'}", f"- 数据缺失日期：{_join(q.get('missing_dates'))}", "",
        "## 2. 市场概况", "", f"- 平均上涨占比：{_fmt(m['average_rise_ratio'], '%')}", f"- 平均成交额：{_fmt(m['average_turnover'])}", f"- 最高成交额日期：{m.get('highest_turnover_day') or '数据暂缺'}", f"- 最低成交额日期：{m.get('lowest_turnover_day') or '数据暂缺'}", f"- 平均涨跌停差：{_fmt(m['average_limit_diff'])}", f"- 风险天数：{_join(m.get('risk_days'))}", "",
        "## 3. 强势方向", "", "- 领涨行业 Top 10", *_top_lines(s["leading_industries_frequency"]), "", "- 领涨概念 Top 10", *_top_lines(s["leading_concepts_frequency"]), "",
        "## 4. 弱势方向", "", "- 领跌行业 Top 10", *_top_lines(s["lagging_industries_frequency"]), "", "- 领跌概念 Top 10", *_top_lines(s["lagging_concepts_frequency"]), "",
        "## 5. 数据质量", "", f"- 完整天数：{q.get('complete_days', 0)}", f"- 部分缺失天数：{q.get('partial_missing_days', 0)}", f"- 数据不足天数：{len(q.get('insufficient_data_days') or [])}", f"- 历史兜底天数：{len(q.get('history_fallback_days') or [])}", "",
        "## 6. 文件归档建议", "", "- 可长期保留文件：data/history/market_history.csv、data/history/market_snapshot_YYYY-MM-DD.json、data/archive_summaries/*.json、*.csv、*.md", "- 可归档后清理文件：旧 Markdown 日报、旧完整 artifact、旧图片卡片、旧日志", "- 可直接清理文件：cache/、tmp/、__pycache__/、.pytest_cache/", "- 暂不建议删除文件：尚未生成摘要或仍需人工确认的重要历史文件", "", "当前不会自动删除重要文件；后续清理需要用户显式确认。", ""])


def _count_names(counter: Counter, value: Any) -> None:
    if not isinstance(value, list): return
    for item in value:
        name = item.get("name") if isinstance(item, Mapping) else str(item)
        if name and not SENSITIVE_PATTERNS.search(str(name)): counter[str(name)] += 1

def _mapping(v: Any) -> Mapping[str, Any]: return v if isinstance(v, Mapping) else {}
def _num(v: Any) -> Optional[float]:
    if v in (None, ""): return None
    if isinstance(v, str): v = re.sub(r"[^0-9.+-]", "", v)
    try: return float(v)
    except (TypeError, ValueError): return None
def _avg(vals: list[Any]) -> Optional[float]:
    nums = [x for x in vals if isinstance(x, (int, float))]
    return round(mean(nums), 2) if nums else None
def _min_day(items, key):
    vals = [x for x in items if isinstance(x.get(key), (int, float))]
    return min(vals, key=lambda x: x[key])["date"] if vals else None
def _max_day(items, key):
    vals = [x for x in items if isinstance(x.get(key), (int, float))]
    return max(vals, key=lambda x: x[key])["date"] if vals else None
def _coverage_level(x):
    c = x.get("coverage_percent")
    if not isinstance(c, (int, float)): return "insufficient"
    if c >= 80: return "complete"
    if c >= 50: return "partial"
    return "insufficient"
def _is_risk_day(x): return (isinstance(x.get("rise_ratio"), (int, float)) and x["rise_ratio"] < 35) or (isinstance(x.get("limit_diff"), (int, float)) and x["limit_diff"] < 0)
def _validate_month(month):
    if not re.fullmatch(r"\d{4}-\d{2}", month): raise ValueError("month must use YYYY-MM")
def _date_in_month(value, month, today):
    try: d = date.fromisoformat(str(value))
    except ValueError: return False
    return str(value).startswith(month) and d <= today
def _top_lines(counter):
    items = sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:10]
    return [f"  {i}. {name}：{count} 次" for i, (name, count) in enumerate(items, 1)] or ["  - 数据暂缺"]
def _join(v): return "、".join(v) if v else "无"
def _fmt(v, suffix=""): return "数据暂缺" if v is None else f"{v}{suffix}"
def _rel(path: Path) -> str:
    try: return str(path.relative_to(Path.cwd()))
    except ValueError: return str(path)
def _human_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024: return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"
def _path_looks_sensitive(path: Path) -> bool: return any(SENSITIVE_PATTERNS.search(part) for part in path.parts)
