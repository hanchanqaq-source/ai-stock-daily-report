"""Deterministic code-format identification framework.

This module does not perform network lookups, read user configuration, or enrich
real asset names/tags. Format matches are only internal-rule evidence and remain
pending until a verifiable source or user confirmation is provided.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.asset_model import normalize_market, normalize_source_status, validate_asset
from src.source_verification import is_result_usable_for_formal_analysis, validate_asset_identification_result

ALLOWED_IDENTIFIER_TYPES = {"fund", "stock", "etf", "index", "unknown"}
ALLOWED_IDENTIFIER_MARKETS = {"CN", "HK", "US", "JP", "KR", "GLOBAL", "unknown"}
FORMAT_RULE_SOURCE_NAME = "code_format_rule"
FORMAT_RULE_SOURCE_TYPE = "internal_history"


def normalize_code_input(code: str | None) -> str:
    """Normalize a user-entered code without inferring real identity."""

    if code is None:
        return ""
    return str(code).strip().upper()


def _checked_at() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _format_source(evidence_text: str, confidence: str = "medium") -> dict[str, Any]:
    return {
        "source_name": FORMAT_RULE_SOURCE_NAME,
        "source_type": FORMAT_RULE_SOURCE_TYPE,
        "source_url": None,
        "checked_at": _checked_at(),
        "evidence_text": evidence_text,
        "confidence": confidence,
    }


def build_identification_candidate(asset_type: str, market: str, confidence: str, reason: str) -> dict[str, str]:
    """Build one possible type/market candidate from a format rule."""

    normalized_type = asset_type if asset_type in ALLOWED_IDENTIFIER_TYPES else "unknown"
    normalized_market = market if market in ALLOWED_IDENTIFIER_MARKETS else "unknown"
    normalized_confidence = confidence if confidence in {"high", "medium", "low"} else "low"
    return {
        "type": normalized_type,
        "market": normalized_market,
        "confidence": normalized_confidence,
        "reason": reason,
    }


def detect_code_format(code: str | None) -> dict[str, Any]:
    """Return conservative candidates inferred from code shape only."""

    normalized = normalize_code_input(code)
    if not normalized:
        return {"format": "empty", "candidates": [], "reason": "代码为空，无法根据格式识别。", "confidence": "low"}
    if not re.fullmatch(r"[A-Z0-9.]+", normalized):
        return {"format": "invalid", "candidates": [], "reason": "代码包含非法字符，无法根据格式识别。", "confidence": "low"}
    if re.fullmatch(r"\d{6}", normalized):
        return {
            "format": "cn_six_digit",
            "candidates": [
                build_identification_candidate("stock", "CN", "medium", "6 位数字可能为 A 股股票代码。"),
                build_identification_candidate("fund", "CN", "medium", "6 位数字也可能为中国基金代码。"),
                build_identification_candidate("etf", "CN", "medium", "6 位数字也可能为中国 ETF 代码。"),
            ],
            "reason": "根据 6 位数字格式，可能是中国股票、基金或 ETF 代码，需要进一步确认。",
            "confidence": "medium",
        }
    suffix_rules = {
        ".HK": ("hk_suffix", [build_identification_candidate("stock", "HK", "medium", ".HK 后缀可能为港股代码格式。")], ".HK 后缀常见于港股代码格式，需要进一步确认。"),
        ".US": ("us_suffix", [build_identification_candidate("stock", "US", "medium", ".US 后缀可能为美股代码格式。")], ".US 后缀常见于美股代码格式，需要进一步确认。"),
        ".JP": ("jp_suffix", [build_identification_candidate("stock", "JP", "medium", ".JP 后缀可能为日本股票代码格式。"), build_identification_candidate("index", "JP", "medium", ".JP 后缀也可能为日本指数代码格式。")], ".JP 后缀可能对应日本股票或指数，需要进一步确认。"),
        ".KR": ("kr_suffix", [build_identification_candidate("stock", "KR", "medium", ".KR 后缀可能为韩国股票代码格式。"), build_identification_candidate("index", "KR", "medium", ".KR 后缀也可能为韩国指数代码格式。")], ".KR 后缀可能对应韩国股票或指数，需要进一步确认。"),
    }
    for suffix, (fmt, candidates, reason) in suffix_rules.items():
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            return {"format": fmt, "candidates": candidates, "reason": reason, "confidence": "medium"}
    if re.fullmatch(r"[A-Z]{1,5}", normalized):
        return {
            "format": "us_letters",
            "candidates": [build_identification_candidate("stock", "US", "medium", "1-5 位纯英文字母可能为美股代码格式。")],
            "reason": "1-5 位纯英文字母常见于美股代码格式，需要进一步确认。",
            "confidence": "medium",
        }
    return {"format": "unrecognized", "candidates": [], "reason": "无法根据当前基础格式规则识别代码。", "confidence": "low"}


def _field(value: Any, status: str, confidence: str, reason: str, sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"value": value, "status": status, "confidence": confidence, "reason": reason, "sources": sources or []}


def build_unknown_result(code: str | None, reason: str) -> dict[str, Any]:
    normalized = normalize_code_input(code)
    result = {
        "code": "" if code is None else str(code),
        "normalized_code": normalized,
        "status": "unknown",
        "confidence": "low",
        "needs_user_confirmation": True,
        "asset_type": _field(None, "unknown", "low", reason),
        "market": _field(None, "unknown", "low", reason),
        "name": _field(None, "unknown", "low", "本次未接入公开名称数据源，不能编造名称。"),
        "tags": [],
        "candidates": [],
        "usable_for_formal_analysis": False,
    }
    validate_asset_identification_result(result)
    return result


def build_pending_confirmation_result(code: str | None, format_result: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_code_input(code)
    candidates = list(format_result.get("candidates") or [])
    markets = {candidate["market"] for candidate in candidates if candidate.get("market") != "unknown"}
    types = {candidate["type"] for candidate in candidates if candidate.get("type") != "unknown"}
    source = _format_source(format_result.get("reason", "代码格式规则。"), format_result.get("confidence", "medium"))
    market_value = next(iter(markets)) if len(markets) == 1 else None
    type_value = next(iter(types)) if len(types) == 1 else None
    result = {
        "code": "" if code is None else str(code),
        "normalized_code": normalized,
        "status": "pending_confirmation",
        "confidence": format_result.get("confidence", "medium"),
        "needs_user_confirmation": True,
        "asset_type": _field(type_value, "pending_confirmation", format_result.get("confidence", "medium"), format_result.get("reason", "需要进一步确认资产类型。"), [source]),
        "market": _field(market_value, "pending_confirmation", format_result.get("confidence", "medium"), format_result.get("reason", "需要进一步确认市场。"), [source]),
        "name": _field(None, "unknown", "low", "本次未接入公开名称数据源，不能编造名称。"),
        "tags": [],
        "candidates": candidates,
        "usable_for_formal_analysis": False,
    }
    validate_asset_identification_result(result)
    return result


def build_conflict_result(code: str | None, candidates: list[dict[str, str]], reason: str) -> dict[str, Any]:
    result = build_pending_confirmation_result(code, {"candidates": candidates, "reason": reason, "confidence": "low"})
    result["status"] = "conflict"
    result["asset_type"]["status"] = "conflict"
    result["market"]["status"] = "conflict"
    result["confidence"] = "low"
    result["usable_for_formal_analysis"] = False
    validate_asset_identification_result(result)
    return result


def identify_code(code: str | None) -> dict[str, Any]:
    """Identify one code using format-only candidates."""

    format_result = detect_code_format(code)
    if not format_result["candidates"]:
        return build_unknown_result(code, format_result["reason"])
    return build_pending_confirmation_result(code, format_result)


def identify_codes(codes: list[str | None]) -> list[dict[str, Any]]:
    """Identify multiple codes while preserving input order."""

    return [identify_code(code) for code in codes]


def convert_identification_to_asset(result: dict[str, Any]) -> dict[str, Any]:
    """Convert an identification result into a public-safe asset draft."""

    candidates = list(result.get("candidates") or [])
    candidate_types = {candidate.get("type") for candidate in candidates if candidate.get("type") != "unknown"}
    candidate_markets = {candidate.get("market") for candidate in candidates if candidate.get("market") != "unknown"}
    asset_type = "unknown"
    if len(candidates) == 1 and candidates[0].get("confidence") == "high":
        asset_type = candidates[0].get("type", "unknown")
    market = result.get("market", {}).get("value") or (next(iter(candidate_markets)) if len(candidate_markets) == 1 else "unknown")
    source_status = normalize_source_status(result.get("status", "unknown"))
    if source_status == "verified" and not is_result_usable_for_formal_analysis(result):
        source_status = "pending_confirmation"
    asset = {
        "asset_id": f"draft_{normalize_code_input(result.get('code')) or 'unknown'}",
        "type": asset_type if asset_type in ALLOWED_IDENTIFIER_TYPES else "unknown",
        "code": normalize_code_input(result.get("code")),
        "name": "",
        "market": normalize_market(market),
        "tags": [],
        "status": "watching",
        "weight_level": 1,
        "source_status": source_status,
        "notes": None,
    }
    validate_asset(asset)
    return asset
