# -*- coding: utf-8 -*-
"""Lightweight public-market history snapshots for daily market reports.

The store intentionally persists only a whitelisted public-market summary.  It
never serializes user holdings, account amounts, credentials, webhooks, tokens,
or arbitrary runtime configuration.
"""
from __future__ import annotations

import csv
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

logger = logging.getLogger(__name__)

HISTORY_DIR = Path("data/history")
SNAPSHOT_VERSION = 1
SNAPSHOT_PREFIX = "market_snapshot_"
SNAPSHOT_SUFFIX = ".json"
CSV_FILENAME = "market_history.csv"

CSV_COLUMNS = [
    "date",
    "report_date",
    "data_mode",
    "coverage_percent",
    "market_status",
    "market_score",
    "rise_ratio",
    "rising_count",
    "falling_count",
    "flat_count",
    "turnover",
    "limit_up_count",
    "limit_down_count",
    "limit_diff",
    "top_leading_industry",
    "top_lagging_industry",
    "top_leading_concept",
    "top_lagging_concept",
]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ALLOWED_DATA_MODES = {"realtime", "recent_trading_day", "history_fallback", "insufficient_data"}


def save_market_history(
    payload: Mapping[str, Any],
    *,
    history_dir: Path | str = HISTORY_DIR,
    report_date: Optional[str] = None,
    run_info: Optional[Mapping[str, Any]] = None,
) -> bool:
    """Persist a JSON snapshot and upsert its CSV summary without raising.

    Returns ``True`` only when both JSON and CSV writes complete successfully.
    Any write or serialization failure is logged with ``[HISTORY_STORE]`` and
    swallowed so report generation and notifications can continue.
    """
    store_dir = Path(history_dir)
    logger.info("[HISTORY_STORE] history_dir=%s", store_dir.as_posix())
    try:
        snapshot = build_market_snapshot(payload, report_date=report_date, run_info=run_info)
        data_date = str(snapshot.get("data_date") or "")
        if not _is_valid_past_or_today_date(data_date):
            logger.info("[HISTORY_STORE] skipped_non_trading_day=true date=%s", data_date or "unknown")
            return False

        store_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = store_dir / f"{SNAPSHOT_PREFIX}{data_date}{SNAPSHOT_SUFFIX}"
        _assert_json_serializable(snapshot)
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        logger.info(
            "[HISTORY_STORE] snapshot_saved=true date=%s path=%s",
            data_date,
            snapshot_path.as_posix(),
        )
        rows = _upsert_market_history_csv(store_dir / CSV_FILENAME, snapshot)
        logger.info(
            "[HISTORY_STORE] csv_updated=true path=%s rows=%d",
            (store_dir / CSV_FILENAME).as_posix(),
            rows,
        )
        logger.info("[HISTORY_STORE] skipped_non_trading_day=false")
        return True
    except Exception as exc:  # pragma: no cover - exact failures depend on FS permissions
        logger.warning("[HISTORY_STORE] snapshot_saved=false reason=%s", exc)
        logger.warning("[HISTORY_STORE] csv_updated=false reason=%s", exc)
        return False


def build_market_snapshot(
    payload: Mapping[str, Any],
    *,
    report_date: Optional[str] = None,
    run_info: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the whitelisted public-market snapshot from a market-review payload."""
    report_date_value = _date_or_today(report_date or payload.get("report_date") or payload.get("date"))
    quality = _mapping(payload.get("data_quality"))
    data_date = _date_or_today(
        payload.get("data_date")
        or payload.get("latest_data_date")
        or quality.get("latest_data_date")
        or payload.get("date")
        or report_date_value
    )
    data_mode = str(payload.get("data_mode") or quality.get("data_mode") or "realtime")
    if data_mode not in _ALLOWED_DATA_MODES:
        data_mode = "realtime"

    markets = payload.get("markets")
    if isinstance(markets, Mapping):
        market_payloads = {str(k): v for k, v in markets.items() if isinstance(v, Mapping)}
    else:
        region = str(payload.get("region") or "cn")
        market_payloads = {region: payload}

    cn_payload = _mapping(market_payloads.get("cn")) or _mapping(next(iter(market_payloads.values()), {}))
    breadth = _mapping(cn_payload.get("breadth"))
    market_light = _mapping(cn_payload.get("market_light"))
    sectors_payload = _mapping(cn_payload.get("sectors"))
    concepts_payload = _mapping(cn_payload.get("concepts"))

    indices = {key: [] for key in ("cn", "hk", "us", "jp", "kr")}
    for region_key, market_payload in market_payloads.items():
        if region_key in indices:
            indices[region_key] = [_sanitize_index(item) for item in _list(_mapping(market_payload).get("indices"))]

    rising_count = _number(breadth.get("rising_count"), breadth.get("up_count"))
    falling_count = _number(breadth.get("falling_count"), breadth.get("down_count"))
    flat_count = _number(breadth.get("flat_count"))
    rise_ratio = _number(breadth.get("rise_ratio"))
    if rise_ratio is not None and rise_ratio <= 1:
        rise_ratio = round(rise_ratio * 100, 4)

    snapshot = {
        "snapshot_version": SNAPSHOT_VERSION,
        "report_date": report_date_value,
        "data_date": data_date,
        "data_mode": data_mode,
        "data_quality": {
            "coverage_percent": _number(quality.get("coverage_percent"), quality.get("overall_score")),
            "missing_fields": _string_list(quality.get("missing_fields"), quality.get("missing")),
            "partial_fields": _string_list(quality.get("partial_fields"), quality.get("partial")),
        },
        "a_share": {
            "market_status": _market_status_label(market_light),
            "market_score": _number(market_light.get("score")),
            "rise_ratio": rise_ratio,
            "rising_count": rising_count,
            "falling_count": falling_count,
            "flat_count": flat_count,
            "turnover": _number(breadth.get("turnover"), breadth.get("total_amount")),
            "limit_up_count": _number(breadth.get("limit_up_count")),
            "limit_down_count": _number(breadth.get("limit_down_count")),
            "limit_diff": _number(breadth.get("limit_diff")),
        },
        "indices": indices,
        "sectors": {
            "leading_industries": _sanitize_ranked_items(sectors_payload.get("top")),
            "lagging_industries": _sanitize_ranked_items(sectors_payload.get("bottom")),
            "leading_concepts": _sanitize_ranked_items(concepts_payload.get("top")),
            "lagging_concepts": _sanitize_ranked_items(concepts_payload.get("bottom")),
        },
        "run_info": _sanitize_run_info(run_info or payload.get("run_info") or {}),
    }
    return snapshot


def load_snapshot_by_date(target_date: str, *, history_dir: Path | str = HISTORY_DIR) -> Optional[Dict[str, Any]]:
    """Load one snapshot by market data date; returns ``None`` for missing/future/bad JSON."""
    if not _is_valid_past_or_today_date(target_date):
        return None
    path = Path(history_dir) / f"{SNAPSHOT_PREFIX}{target_date}{SNAPSHOT_SUFFIX}"
    return _read_snapshot(path)


def load_latest_snapshot(
    before_or_equal_date: Optional[str] = None,
    *,
    history_dir: Path | str = HISTORY_DIR,
) -> Optional[Dict[str, Any]]:
    """Load the newest valid snapshot not later than ``before_or_equal_date`` or today."""
    limit = _date_or_today(before_or_equal_date) if before_or_equal_date else date.today().isoformat()
    for path in _snapshot_paths(Path(history_dir), reverse=True):
        data_date = _date_from_snapshot_path(path)
        if data_date and data_date <= limit:
            snapshot = _read_snapshot(path)
            if snapshot is not None:
                logger.info("[HISTORY_STORE] latest_snapshot=%s", data_date)
                return snapshot
    return None


def load_recent_snapshots(limit: int = 5, *, history_dir: Path | str = HISTORY_DIR) -> List[Dict[str, Any]]:
    """Return up to ``limit`` valid snapshots in newest-first (descending date) order."""
    if limit <= 0:
        return []
    snapshots: List[Dict[str, Any]] = []
    today = date.today().isoformat()
    for path in _snapshot_paths(Path(history_dir), reverse=True):
        data_date = _date_from_snapshot_path(path)
        if not data_date or data_date > today:
            continue
        snapshot = _read_snapshot(path)
        if snapshot is not None:
            snapshots.append(snapshot)
        if len(snapshots) >= limit:
            break
    return snapshots


def load_market_history_csv(*, history_dir: Path | str = HISTORY_DIR) -> List[Dict[str, str]]:
    """Load CSV summary rows sorted by date ascending; missing file returns an empty list."""
    path = Path(history_dir) / CSV_FILENAME
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            rows = [dict(row) for row in csv.DictReader(fh)]
        today = date.today().isoformat()
        return sorted([row for row in rows if str(row.get("date") or "") <= today], key=lambda row: row.get("date") or "")
    except Exception as exc:
        logger.warning("[HISTORY_STORE] csv_read_failed path=%s reason=%s", path.as_posix(), exc)
        return []


def _upsert_market_history_csv(path: Path, snapshot: Mapping[str, Any]) -> int:
    existing = load_market_history_csv(history_dir=path.parent)
    by_date = {row.get("date", ""): row for row in existing if row.get("date")}
    row = _snapshot_to_csv_row(snapshot)
    by_date[str(row["date"])] = row
    rows = [by_date[key] for key in sorted(by_date)]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _snapshot_to_csv_row(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    a_share = _mapping(snapshot.get("a_share"))
    quality = _mapping(snapshot.get("data_quality"))
    sectors = _mapping(snapshot.get("sectors"))
    return {
        "date": snapshot.get("data_date") or "",
        "report_date": snapshot.get("report_date") or "",
        "data_mode": snapshot.get("data_mode") or "",
        "coverage_percent": _csv_value(quality.get("coverage_percent")),
        "market_status": _csv_value(a_share.get("market_status")),
        "market_score": _csv_value(a_share.get("market_score")),
        "rise_ratio": _csv_value(a_share.get("rise_ratio")),
        "rising_count": _csv_value(a_share.get("rising_count")),
        "falling_count": _csv_value(a_share.get("falling_count")),
        "flat_count": _csv_value(a_share.get("flat_count")),
        "turnover": _csv_value(a_share.get("turnover")),
        "limit_up_count": _csv_value(a_share.get("limit_up_count")),
        "limit_down_count": _csv_value(a_share.get("limit_down_count")),
        "limit_diff": _csv_value(a_share.get("limit_diff")),
        "top_leading_industry": _top_name(sectors.get("leading_industries")),
        "top_lagging_industry": _top_name(sectors.get("lagging_industries")),
        "top_leading_concept": _top_name(sectors.get("leading_concepts")),
        "top_lagging_concept": _top_name(sectors.get("lagging_concepts")),
    }


def _snapshot_paths(history_dir: Path, *, reverse: bool) -> List[Path]:
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob(f"{SNAPSHOT_PREFIX}*{SNAPSHOT_SUFFIX}"), key=lambda p: p.name, reverse=reverse)


def _read_snapshot(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        data_date = _date_from_snapshot_path(path)
        if not data_date or not _is_valid_past_or_today_date(data_date):
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        logger.warning("[HISTORY_STORE] invalid_snapshot_skipped path=%s reason=%s", path.as_posix(), exc)
        return None


def _date_from_snapshot_path(path: Path) -> str:
    name = path.name
    if not (name.startswith(SNAPSHOT_PREFIX) and name.endswith(SNAPSHOT_SUFFIX)):
        return ""
    value = name[len(SNAPSHOT_PREFIX):-len(SNAPSHOT_SUFFIX)]
    return value if _DATE_RE.match(value) else ""


def _is_valid_past_or_today_date(value: Any) -> bool:
    text = str(value or "")
    if not _DATE_RE.match(text):
        return False
    try:
        return datetime.strptime(text, "%Y-%m-%d").date() <= date.today()
    except ValueError:
        return False


def _date_or_today(value: Any) -> str:
    text = str(value or "")[:10]
    if _DATE_RE.match(text):
        return text
    return date.today().isoformat()


def _assert_json_serializable(value: Mapping[str, Any]) -> None:
    json.dumps(value, ensure_ascii=False)


def _mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


def _number(*values: Any) -> Optional[float | int]:
    for value in values:
        if value is None or value == "":
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        return int(number) if number.is_integer() else number
    return None


def _string_list(*values: Any) -> List[str]:
    for value in values:
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [str(item) for item in value if item is not None and str(item)]
    return []


def _market_status_label(market_light: Mapping[str, Any]) -> Optional[str]:
    label = market_light.get("label") or market_light.get("temperature_label")
    if label:
        return str(label)
    status = str(market_light.get("status") or "")
    return {"green": "偏强", "yellow": "震荡", "red": "偏弱"}.get(status) or None


def _sanitize_index(item: Any) -> Dict[str, Any]:
    src = _mapping(item)
    return {
        "code": src.get("code"),
        "name": src.get("name"),
        "current": _number(src.get("current")),
        "change": _number(src.get("change")),
        "change_pct": _number(src.get("change_pct")),
        "open": _number(src.get("open")),
        "high": _number(src.get("high")),
        "low": _number(src.get("low")),
        "volume": _number(src.get("volume")),
        "amount": _number(src.get("amount")),
        "data_date": src.get("data_date"),
        "data_source": src.get("data_source"),
        "data_status": src.get("data_status"),
    }


def _sanitize_ranked_items(value: Any) -> List[Dict[str, Any]]:
    items = []
    for item in _list(value):
        src = _mapping(item)
        name = src.get("name") or src.get("板块名称") or src.get("concept") or src.get("industry")
        items.append({"name": name, "change_pct": _number(src.get("change_pct"), src.get("涨跌幅"))})
    return items


def _sanitize_run_info(value: Mapping[str, Any]) -> Dict[str, Any]:
    src = _mapping(value)
    return {
        "request_id": src.get("request_id"),
        "trigger_source": src.get("trigger_source"),
        "run_mode": src.get("run_mode"),
        "model_profile": src.get("model_profile"),
    }


def _top_name(value: Any) -> str:
    items = _list(value)
    if not items:
        return ""
    first = _mapping(items[0])
    return str(first.get("name") or "")


def _csv_value(value: Any) -> Any:
    return "" if value is None else value
