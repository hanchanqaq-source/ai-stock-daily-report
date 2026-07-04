"""Validation helpers for source-verifiable asset identification results.

This module only defines structures and deterministic validation rules. It does
not perform network lookups, infer real asset identities, or enrich labels.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

CONFIDENCE_LEVELS = {"high", "medium", "low"}
VERIFICATION_STATUSES = {"verified", "unknown", "pending_confirmation", "conflict"}
SOURCE_TYPES = {
    "official",
    "public_web",
    "market_data",
    "fund_data",
    "manual_user_input",
    "internal_history",
}
FORMAL_REQUIRED_FIELDS = ("asset_type", "name", "market")
SENSITIVE_KEYWORDS = (
    "webhook",
    "token",
    "api_key",
    "apikey",
    "secret",
    "amount",
    "cost",
    "cost_price",
    "balance",
    "asset_value",
    "account_value",
    "holding_amount",
    "position_amount",
    "用户金额",
    "金额",
    "成本价",
    "账户资产",
)


def normalize_confidence(value: Any) -> str:
    """Return a supported confidence level, defaulting invalid input to ``low``."""

    if isinstance(value, str) and value.strip().lower() in CONFIDENCE_LEVELS:
        return value.strip().lower()
    return "low"


def validate_source_evidence(source: Mapping[str, Any]) -> bool:
    """Validate one source evidence object.

    The function verifies shape only; callers must not use it as proof that a
    lookup happened. ``checked_at`` must be supplied by the actual lookup or
    manual-confirmation workflow.
    """

    if not isinstance(source, Mapping):
        return False
    if not str(source.get("source_name") or "").strip():
        return False
    if source.get("source_type") not in SOURCE_TYPES:
        return False
    if normalize_confidence(source.get("confidence")) != source.get("confidence"):
        return False
    checked_at = source.get("checked_at")
    if not isinstance(checked_at, str) or not checked_at.strip():
        return False
    try:
        datetime.fromisoformat(checked_at)
    except ValueError:
        return False
    return not _contains_sensitive_data(source)


def validate_verified_field(field: Mapping[str, Any]) -> bool:
    """Validate an auto-completed field with status, confidence and evidence."""

    if not isinstance(field, Mapping):
        return False
    status = field.get("status")
    if status not in VERIFICATION_STATUSES:
        return False
    if normalize_confidence(field.get("confidence")) != field.get("confidence"):
        return False
    sources = field.get("sources", [])
    if sources is None:
        sources = []
    if not isinstance(sources, list):
        return False
    if any(not validate_source_evidence(source) for source in sources):
        return False
    reason = str(field.get("reason") or "").strip()
    if status == "verified":
        return bool(sources) and field.get("value") is not None
    if status in {"unknown", "pending_confirmation"}:
        return bool(reason)
    if status == "conflict":
        return bool(reason) or len(sources) >= 2
    return False


def validate_asset_identification_result(result: Mapping[str, Any]) -> bool:
    """Validate an asset identification result without performing enrichment."""

    if not isinstance(result, Mapping):
        return False
    if result.get("status") not in VERIFICATION_STATUSES:
        return False
    for field_name in FORMAL_REQUIRED_FIELDS:
        if not validate_verified_field(result.get(field_name, {})):
            return False
    tags = result.get("tags", [])
    if not isinstance(tags, list):
        return False
    if any(not validate_verified_field(tag) for tag in tags):
        return False
    return not _contains_sensitive_data(result)


def mark_unknown(reason: str) -> dict[str, Any]:
    """Build a standard unknown field/result fragment."""

    return {
        "value": None,
        "status": "unknown",
        "confidence": "low",
        "sources": [],
        "reason": reason,
    }


def mark_conflict(reason: str, sources: list[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Build a standard conflict field/result fragment."""

    return {
        "value": None,
        "status": "conflict",
        "confidence": "low",
        "sources": list(sources or []),
        "reason": reason,
    }


def is_result_usable_for_formal_analysis(result: Mapping[str, Any]) -> bool:
    """Return whether a result may enter formal analysis conclusions."""

    if not validate_asset_identification_result(result):
        return False
    if result.get("status") != "verified":
        return False
    for field_name in FORMAL_REQUIRED_FIELDS:
        if result[field_name].get("status") != "verified":
            return False
    return True


def is_tag_usable_for_formal_analysis(tag: Mapping[str, Any]) -> bool:
    """Return whether a single tag may be used in formal analysis."""

    if not validate_verified_field(tag):
        return False
    if tag.get("status") != "verified":
        return False
    sources = tag.get("sources") or []
    return any(source.get("source_type") == "manual_user_input" or validate_source_evidence(source) for source in sources)


def _contains_sensitive_data(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(keyword in normalized_key for keyword in SENSITIVE_KEYWORDS):
                return True
            if _contains_sensitive_data(item):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_data(item) for item in value)
    elif isinstance(value, str):
        lowered = value.lower()
        if "discord.com/api/webhooks/" in lowered or "discordapp.com/api/webhooks/" in lowered:
            return True
        if "ghp_" in value or "github_pat_" in value or "sk-" in value:
            return True
    return False
