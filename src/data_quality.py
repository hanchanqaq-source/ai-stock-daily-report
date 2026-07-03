# -*- coding: utf-8 -*-
"""Lightweight report data coverage diagnostics.

This module only inspects already-available report/market payloads.  It does not
fetch data and must stay fail-open so report generation and notification delivery
are not blocked by diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

logger = logging.getLogger(__name__)

DATA_MODE_LABELS = {
    "realtime": "实时",
    "recent_trading_day": "最近交易日",
    "history_fallback": "历史快照兜底",
    "unknown": "未知",
}

_FIELD_LABELS = {
    "report_date": "报告日期",
    "latest_data_date": "数据日期",
    "market_status": "市场状态",
    "market_score": "市场评分",
    "rise_ratio": "上涨占比",
    "rising_count": "上涨家数",
    "falling_count": "下跌家数",
    "flat_count": "平盘家数",
    "turnover": "成交额",
    "limit_up_count": "涨停数量",
    "limit_down_count": "跌停数量",
    "limit_diff": "涨跌停差",
    "a_share_indices": "A股指数",
    "hk_indices": "港股指数",
    "us_indices": "美股指数",
    "jp_indices": "日股指数",
    "kr_indices": "韩股指数",
    "global_indices": "全球指数",
    "leading_industries": "领涨行业",
    "lagging_industries": "领跌行业",
    "leading_concepts": "领涨概念",
    "lagging_concepts": "领跌概念",
    "history_yesterday": "昨日快照",
    "history_5d": "近5日快照",
}

_REQUIRED_FIELDS = tuple(_FIELD_LABELS.keys())
_INDEX_GROUP_KEYWORDS = {
    "a_share_indices": ("上证", "深证", "创业", "科创", "沪深", "中证"),
    "hk_indices": ("恒生", "科技", "国企", "红筹"),
    "us_indices": ("纳斯达克", "标普", "道琼", "S&P", "NASDAQ", "DOW"),
    "jp_indices": ("日经", "TOPIX", "东证", "Nikkei"),
    "kr_indices": ("韩国", "KOSPI", "KOSDAQ"),
}

_MISSING_MARKERS = ("数据暂缺", "暂缺", "N/A", "None", "null", "历史样本不足", "--")


@dataclass(frozen=True)
class DataQualityResult:
    coverage_percent: int
    available_fields: List[str]
    missing_fields: List[str]
    partial_fields: List[str]
    data_mode: str
    latest_data_date: str
    human_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage_percent": self.coverage_percent,
            "available_fields": list(self.available_fields),
            "missing_fields": list(self.missing_fields),
            "partial_fields": list(self.partial_fields),
            "data_mode": self.data_mode,
            "latest_data_date": self.latest_data_date,
            "human_summary": self.human_summary,
        }


def assess_data_quality(payload: Any) -> Dict[str, Any]:
    """Return a stable data-quality dict for a report payload or report text."""
    try:
        if isinstance(payload, str):
            result = _assess_text(payload)
        elif isinstance(payload, Mapping):
            result = _assess_mapping(payload)
        else:
            result = _assess_mapping({})
        _log_result(result)
        return result.to_dict()
    except Exception as exc:  # pragma: no cover - defensive report fail-open
        logger.warning("[DATA_QUALITY] status=failed reason=%s", type(exc).__name__)
        return {
            "coverage_percent": 0,
            "available_fields": [],
            "missing_fields": list(_REQUIRED_FIELDS),
            "partial_fields": [],
            "data_mode": "unknown",
            "latest_data_date": "",
            "human_summary": "数据质量检查暂不可用。",
        }


def format_data_quality_block(quality: Mapping[str, Any]) -> str:
    """Format a compact mobile-friendly Chinese data-quality block."""
    if not quality:
        return "数据质量检查暂不可用。"
    coverage = quality.get("coverage_percent")
    data_mode = str(quality.get("data_mode") or "unknown")
    mode_label = DATA_MODE_LABELS.get(data_mode, DATA_MODE_LABELS["unknown"])
    latest = str(quality.get("latest_data_date") or "未知")
    missing_labels = [_FIELD_LABELS.get(str(name), str(name)) for name in list(quality.get("missing_fields") or [])[:4]]
    missing = "、".join(missing_labels) if missing_labels else "无重点缺失"
    return "\n".join([
        "数据质量：",
        f"• 数据覆盖率：{coverage if coverage is not None else 0}%",
        f"• 数据日期：{latest}",
        f"• 数据状态：{mode_label}",
        f"• 缺失重点：{missing}",
    ])


def _assess_mapping(payload: Mapping[str, Any]) -> DataQualityResult:
    flat = _flatten(payload)
    available: Set[str] = set()
    partial: Set[str] = set()

    aliases = {
        "report_date": ("report_date", "date"),
        "latest_data_date": ("latest_data_date", "data_date", "trading_date"),
        "market_status": ("market_status", "market_state", "status"),
        "market_score": ("market_score", "market_signal", "signal", "score"),
        "rise_ratio": ("rise_ratio", "up_ratio", "上涨占比"),
        "rising_count": ("rising_count", "up_count", "上涨家数"),
        "falling_count": ("falling_count", "down_count", "下跌家数"),
        "flat_count": ("flat_count", "平盘家数"),
        "turnover": ("turnover", "amount", "成交额"),
        "limit_up_count": ("limit_up_count", "limit_up", "涨停"),
        "limit_down_count": ("limit_down_count", "limit_down", "跌停"),
        "limit_diff": ("limit_diff", "limit_up_down_diff", "涨跌停差"),
        "leading_industries": ("leading_industries", "industry_top", "industry_top3", "top_industries", "top_sectors", "sectors.top"),
        "lagging_industries": ("lagging_industries", "industry_bottom", "industry_bottom3", "bottom_industries", "bottom_sectors", "sectors.bottom"),
        "leading_concepts": ("leading_concepts", "concept_top", "top_concepts", "concepts.top"),
        "lagging_concepts": ("lagging_concepts", "concept_bottom", "bottom_concepts", "concepts.bottom"),
        "history_yesterday": ("history_yesterday", "yesterday_snapshot"),
        "history_5d": ("history_5d", "last_5_days", "recent_5d"),
    }
    for field, names in aliases.items():
        if _has_any(flat, names):
            available.add(field)

    text_blob = " ".join(f"{k} {v}" for k, v in flat.items())
    for field, keywords in _INDEX_GROUP_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword.lower() in text_blob.lower())
        if hits:
            available.add(field)
            if hits < 2 and field in {"a_share_indices", "hk_indices", "us_indices"}:
                partial.add(field)
    _apply_global_indices_status(available, partial)

    latest = str(_first_value(flat, ("latest_data_date", "data_date", "trading_date", "report_date")) or "")
    data_mode = _normalize_data_mode(_first_value(flat, ("data_mode", "mode")))
    return _build_result(available, partial, latest, data_mode)


def _assess_text(content: str) -> DataQualityResult:
    text = str(content or "")
    available: Set[str] = set()
    partial: Set[str] = set()
    patterns = {
        "report_date": (r"报告日期[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",),
        "latest_data_date": (r"(?:数据日期|行情日期)[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",),
        "market_status": (r"市场状态[:：]\s*([^\n]+)", r"今日市场状态[:：]\s*([^\n]+)"),
        "market_score": (r"(?:盘面信号|市场信号)[:：]\s*([^\n]+)",),
        "rise_ratio": (r"上涨占比[:：]?\s*([+-]?[\d.]+%)",),
        "rising_count": (r"(?:上涨股票|上涨)[:：]\s*(\d+\s*家)",),
        "falling_count": (r"(?:下跌股票|下跌)[:：]\s*(\d+\s*家)",),
        "turnover": (r"(?:两市)?成交额[:：]\s*([^\n]+)",),
        "limit_up_count": (r"涨停(?:数量)?[:：]\s*(\d+)",),
        "limit_down_count": (r"跌停(?:数量)?[:：]\s*(\d+)",),
        "limit_diff": (r"涨跌停差[:：]?\s*([+-]?\d+)",),
        "leading_industries": (r"行业板块领涨", r"领涨行业"),
        "lagging_industries": (r"行业板块领跌", r"领跌行业"),
        "leading_concepts": (r"概念板块领涨", r"领涨概念"),
        "lagging_concepts": (r"概念板块领跌", r"领跌概念"),
        "history_yesterday": (r"昨日[:：]", r"昨日快照"),
        "history_5d": (r"近\s*5\s*日",),
    }
    for field, field_patterns in patterns.items():
        if any(_regex_has_real_value(text, pattern) for pattern in field_patterns):
            available.add(field)
    for field, keywords in _INDEX_GROUP_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword.lower() in text.lower())
        if hits:
            available.add(field)
            if hits < 2 and field in {"a_share_indices", "hk_indices", "us_indices"}:
                partial.add(field)
    _apply_global_indices_status(available, partial)
    latest = _first_regex_value(text, [r"(?:数据日期|行情日期)[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", r"报告日期[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})"])
    data_mode = _normalize_data_mode(_first_regex_value(text, [r"(?:数据状态|数据模式)[:：]\s*([^\n]+)"]))
    return _build_result(available, partial, latest, data_mode)



def _apply_global_indices_status(available: Set[str], partial: Set[str]) -> None:
    groups = {"a_share_indices", "hk_indices", "us_indices", "jp_indices", "kr_indices"}
    hits = groups & available
    if not hits:
        return
    available.add("global_indices")
    if hits != groups or bool(groups & partial):
        partial.add("global_indices")

def _build_result(available: Set[str], partial: Set[str], latest: str, data_mode: str) -> DataQualityResult:
    missing = [field for field in _REQUIRED_FIELDS if field not in available]
    available_list = [field for field in _REQUIRED_FIELDS if field in available]
    partial_list = [field for field in _REQUIRED_FIELDS if field in partial]
    coverage = int(round((len(available_list) / len(_REQUIRED_FIELDS)) * 100)) if _REQUIRED_FIELDS else 0
    if coverage >= 80:
        summary = f"数据覆盖率 {coverage}%，核心数据较完整。"
    elif coverage >= 50:
        summary = f"数据覆盖率 {coverage}%，部分字段缺失。"
    else:
        summary = f"数据覆盖率 {coverage}%，数据质量偏低。"
    return DataQualityResult(coverage, available_list, missing, partial_list, data_mode, latest or "", summary)


def _flatten(value: Any, prefix: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            out[name] = item
            out.update(_flatten(item, name))
    elif isinstance(value, list):
        for idx, item in enumerate(value[:20]):
            out.update(_flatten(item, f"{prefix}.{idx}" if prefix else str(idx)))
    return out


def _is_present(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    text = str(value).strip()
    return bool(text) and not any(marker.lower() == text.lower() for marker in _MISSING_MARKERS)


def _matches_field_key(key: str, names: Sequence[str]) -> bool:
    last = key.lower().split(".")[-1]
    full = key.lower()
    lowered = tuple(name.lower() for name in names)
    return any(name == last or name == full for name in lowered)


def _has_any(flat: Mapping[str, Any], names: Sequence[str]) -> bool:
    return any(_matches_field_key(key, names) and _is_present(value) for key, value in flat.items())


def _first_value(flat: Mapping[str, Any], names: Sequence[str]) -> Any:
    for key, value in flat.items():
        if _matches_field_key(key, names) and _is_present(value):
            return value
    return None


def _regex_has_real_value(text: str, pattern: str) -> bool:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return False
    value = match.group(1) if match.groups() else match.group(0)
    return _is_present(value)


def _first_regex_value(text: str, patterns: Iterable[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match and _is_present(match.group(1)):
            return str(match.group(1)).strip()
    return ""


def _normalize_data_mode(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    if "history" in text or "历史" in text:
        return "history_fallback"
    if "recent" in text or "最近交易日" in text:
        return "recent_trading_day"
    if "real" in text or "实时" in text:
        return "realtime"
    return text if text in DATA_MODE_LABELS else "unknown"


def _log_result(result: DataQualityResult) -> None:
    logger.info("[DATA_QUALITY] coverage=%s%%", result.coverage_percent)
    logger.info("[DATA_QUALITY] available=%s", ",".join(result.available_fields[:20]) or "none")
    logger.info("[DATA_QUALITY] missing=%s", ",".join(result.missing_fields[:20]) or "none")
    logger.info("[DATA_QUALITY] latest_data_date=%s", result.latest_data_date or "unknown")
    logger.info("[DATA_QUALITY] data_mode=%s", result.data_mode)
    for field in ("rise_ratio", "turnover", "limit_diff", "a_share_indices", "hk_indices", "us_indices", "jp_indices", "kr_indices", "global_indices"):
        if field in result.partial_fields:
            status = "partial"
        elif field in result.available_fields:
            status = "ok"
        else:
            status = "missing"
        logger.info("[DATA_QUALITY] field=%s status=%s", field, status)
    industry_hits = sum(
        1 for field in ("leading_industries", "lagging_industries") if field in result.available_fields
    )
    industry_status = "ok" if industry_hits == 2 else "partial" if industry_hits == 1 else "missing"
    logger.info("[DATA_QUALITY] field=industry_top status=%s", industry_status)
