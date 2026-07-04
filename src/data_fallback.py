# -*- coding: utf-8 -*-
"""Helpers for market data mode labels and historical snapshot fallback."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DATA_MODE_LABELS = {
    "realtime": "实时数据",
    "recent_trading_day": "最近交易日数据",
    "history_fallback": "历史快照兜底",
    "insufficient_data": "数据不足",
    "skipped_non_trading_day": "非交易日跳过",
    "unknown": "未知",
}

_SNAPSHOT_RE = re.compile(r"^market_snapshot_(\d{4}-\d{2}-\d{2})\.json$")


@dataclass(frozen=True)
class MarketSnapshotFallback:
    snapshot_date: Optional[str]
    snapshot_data: Optional[Dict[str, Any]]
    data_mode: str
    reason: str = ""


def data_mode_label(data_mode: Any) -> str:
    """Return the shared Chinese display label for a data_mode enum value."""
    key = str(data_mode or "unknown").strip()
    return DATA_MODE_LABELS.get(key, DATA_MODE_LABELS["unknown"])


def find_latest_market_snapshot(
    history_dir: str | Path = "data/history",
    *,
    as_of: date | datetime | str | None = None,
) -> MarketSnapshotFallback:
    """Load the latest valid ``market_snapshot_YYYY-MM-DD.json`` not after ``as_of``.

    Corrupt JSON and future snapshots are skipped fail-open with concise logs.
    """
    base = Path(history_dir)
    cutoff = _normalize_date(as_of) or date.today()
    logger.info("[DATA_FALLBACK] history_dir=%s", base.as_posix())
    if not base.exists() or not base.is_dir():
        logger.info("[DATA_FALLBACK] using_history_snapshot=false reason=no_history_dir")
        return MarketSnapshotFallback(None, None, "insufficient_data", "no_history_dir")

    candidates: list[tuple[date, Path]] = []
    for path in base.iterdir():
        if not path.is_file():
            continue
        match = _SNAPSHOT_RE.match(path.name)
        if not match:
            continue
        snap_date = _parse_date(match.group(1))
        if snap_date is None:
            continue
        if snap_date > cutoff:
            logger.info("[DATA_FALLBACK] skipped_future_snapshot=%s", path.name)
            continue
        candidates.append((snap_date, path))

    for snap_date, path in sorted(candidates, key=lambda item: item[0], reverse=True):
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except json.JSONDecodeError:
            logger.warning("[DATA_FALLBACK] skipped_corrupt_snapshot=%s", path.name)
            continue
        except OSError as exc:
            logger.warning("[DATA_FALLBACK] skipped_unreadable_snapshot=%s reason=%s", path.name, type(exc).__name__)
            continue
        if not isinstance(payload, dict) or not payload:
            logger.info("[DATA_FALLBACK] skipped_empty_snapshot=%s", path.name)
            continue
        logger.info("[DATA_FALLBACK] latest_snapshot=%s", path.name)
        logger.info("[DATA_FALLBACK] using_history_snapshot=true date=%s", snap_date.isoformat())
        return MarketSnapshotFallback(snap_date.isoformat(), payload, "history_fallback")

    logger.info("[DATA_FALLBACK] using_history_snapshot=false reason=no_valid_snapshot")
    return MarketSnapshotFallback(None, None, "insufficient_data", "no_valid_snapshot")


def _normalize_date(value: date | datetime | str | None) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return _parse_date(str(value))


def _parse_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
