"""Unified public-safe asset model helpers.

The asset model is intentionally conservative: it validates user-provided demo
or local asset objects, but does not identify codes, enrich names, infer markets,
or fetch external data.
"""

from __future__ import annotations

import re
from typing import Any

ALLOWED_ASSET_TYPES = ("fund", "stock", "etf", "company", "industry", "theme", "index", "unknown")
ALLOWED_MARKETS = ("CN", "HK", "US", "JP", "KR", "GLOBAL", "unknown")
ALLOWED_ASSET_STATUSES = ("holding", "watching", "cleared", "archived", "deleted")
ALLOWED_SOURCE_STATUSES = ("manual_user_input", "verified", "unknown", "pending_confirmation", "conflict")
ACTIVE_ASSET_STATUSES = frozenset({"holding", "watching"})
PUBLIC_SAFE_ASSET_FIELDS = (
    "asset_id",
    "type",
    "code",
    "name",
    "market",
    "tags",
    "status",
    "weight_level",
    "source_status",
)

SENSITIVE_KEY_NAMES = frozenset(
    {
        "amount",
        "asset_amount",
        "holding_amount",
        "position_amount",
        "cost",
        "cost_price",
        "balance",
        "account_value",
        "profit",
        "real_amount",
        "账户资产",
        "成本价",
        "持仓金额",
        "收益金额",
        "webhook",
        "webhook_url",
        "token",
        "api_key",
        "apikey",
        "email",
        "phone",
        "id_card",
        "身份证",
        "手机号",
    }
)
SENSITIVE_VALUE_PATTERNS = (
    ("webhook URL", re.compile(r"https?://[^\s\"']*webhook[^\s\"']*", re.IGNORECASE)),
    ("Token", re.compile(r"\b(?:token|secret)[=:][A-Za-z0-9_\-]{16,}\b", re.IGNORECASE)),
    ("API Key", re.compile(r"\bapi[_-]?key[=:][A-Za-z0-9_\-]{16,}\b", re.IGNORECASE)),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")),
    ("id_card", re.compile(r"(?<!\d)\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)")),
)


class AssetModelError(ValueError):
    """Raised when an asset object is malformed or public-unsafe."""


def get_allowed_asset_types() -> tuple[str, ...]:
    return ALLOWED_ASSET_TYPES


def get_allowed_markets() -> tuple[str, ...]:
    return ALLOWED_MARKETS


def get_allowed_asset_statuses() -> tuple[str, ...]:
    return ALLOWED_ASSET_STATUSES


def get_allowed_source_statuses() -> tuple[str, ...]:
    return ALLOWED_SOURCE_STATUSES


def _normalize_enum(value: Any, allowed: tuple[str, ...], field: str) -> str:
    if value is None:
        return "unknown" if "unknown" in allowed else ""
    normalized = str(value).strip()
    if field == "market":
        normalized = normalized.upper() if normalized.lower() != "unknown" else "unknown"
    else:
        normalized = normalized.lower()
    return normalized if normalized in allowed else normalized


def normalize_asset_type(value: Any) -> str:
    return _normalize_enum(value, ALLOWED_ASSET_TYPES, "type")


def normalize_market(value: Any) -> str:
    return _normalize_enum(value, ALLOWED_MARKETS, "market")


def normalize_asset_status(value: Any) -> str:
    return _normalize_enum(value, ALLOWED_ASSET_STATUSES, "status")


def normalize_source_status(value: Any) -> str:
    return _normalize_enum(value, ALLOWED_SOURCE_STATUSES, "source_status")


def normalize_asset(asset: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(asset, dict):
        raise AssetModelError("Each asset must be an object.")
    normalized = dict(asset)
    normalized.setdefault("code", "")
    normalized.setdefault("tags", [])
    normalized.setdefault("notes", None)
    normalized["type"] = normalize_asset_type(normalized.get("type", "unknown"))
    normalized["market"] = normalize_market(normalized.get("market", "unknown"))
    normalized["status"] = normalize_asset_status(normalized.get("status", "watching"))
    normalized["source_status"] = normalize_source_status(normalized.get("source_status", "manual_user_input"))
    if normalized.get("code") is None:
        normalized["code"] = ""
    return normalized


def validate_asset(asset: dict[str, Any]) -> None:
    if not isinstance(asset, dict):
        raise AssetModelError("Each asset must be an object.")
    findings = scan_asset_for_sensitive_values(asset)
    if findings:
        raise AssetModelError("Sensitive values are not allowed in asset: " + "; ".join(findings))
    asset_id = asset.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id:
        raise AssetModelError("Each asset requires a non-empty asset_id.")
    if asset.get("type") not in ALLOWED_ASSET_TYPES:
        raise AssetModelError(f"Invalid type for asset_id {asset_id}.")
    if not isinstance(asset.get("code"), str):
        raise AssetModelError(f"code must be a string for asset_id {asset_id}.")
    if not isinstance(asset.get("name"), str) or not asset.get("name"):
        raise AssetModelError(f"name is required for asset_id {asset_id}.")
    if asset.get("market") not in ALLOWED_MARKETS:
        raise AssetModelError(f"Invalid market for asset_id {asset_id}.")
    if not isinstance(asset.get("tags", []), list) or not all(isinstance(tag, str) for tag in asset.get("tags", [])):
        raise AssetModelError(f"tags must be a list of strings for asset_id {asset_id}.")
    if asset.get("status") not in ALLOWED_ASSET_STATUSES:
        raise AssetModelError(f"Invalid status for asset_id {asset_id}.")
    weight_level = asset.get("weight_level")
    if not isinstance(weight_level, int) or not 1 <= weight_level <= 5:
        raise AssetModelError(f"weight_level must be an integer from 1 to 5 for asset_id {asset_id}.")
    if asset.get("source_status") not in ALLOWED_SOURCE_STATUSES:
        raise AssetModelError(f"Invalid source_status for asset_id {asset_id}.")
    if "notes" in asset and asset["notes"] is not None and not isinstance(asset["notes"], str):
        raise AssetModelError(f"notes must be string or null for asset_id {asset_id}.")


def validate_assets(assets: list[dict[str, Any]]) -> None:
    if not isinstance(assets, list):
        raise AssetModelError("assets must be a list.")
    seen: set[str] = set()
    for asset in assets:
        validate_asset(asset)
        asset_id = asset["asset_id"]
        if asset_id in seen:
            raise AssetModelError(f"Duplicate asset_id: {asset_id}")
        seen.add(asset_id)


def is_active_asset(asset: dict[str, Any]) -> bool:
    return asset.get("status") in ACTIVE_ASSET_STATUSES


def is_holding_asset(asset: dict[str, Any]) -> bool:
    return asset.get("status") == "holding"


def is_watching_asset(asset: dict[str, Any]) -> bool:
    return asset.get("status") == "watching"


def is_cleared_asset(asset: dict[str, Any]) -> bool:
    return asset.get("status") == "cleared"


def is_archived_asset(asset: dict[str, Any]) -> bool:
    return asset.get("status") == "archived"


def group_assets_by_type(assets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    validate_assets(assets)
    buckets = {asset_type: [] for asset_type in ALLOWED_ASSET_TYPES}
    for asset in assets:
        buckets[asset["type"]].append(asset)
    return buckets


def group_assets_by_status(assets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    validate_assets(assets)
    buckets = {status: [] for status in ALLOWED_ASSET_STATUSES}
    for asset in assets:
        buckets[asset["status"]].append(asset)
    return buckets


def build_asset_summary(assets: list[dict[str, Any]]) -> dict[str, Any]:
    validate_assets(assets)
    active_assets = [asset for asset in assets if is_active_asset(asset)]
    by_type = {asset_type: 0 for asset_type in ALLOWED_ASSET_TYPES}
    by_status = {status: 0 for status in ALLOWED_ASSET_STATUSES}
    for asset in assets:
        if asset["status"] != "deleted":
            by_type[asset["type"]] += 1
        by_status[asset["status"]] += 1
    active_types = {asset["type"] for asset in active_assets}
    return {
        "total": sum(1 for asset in assets if asset["status"] != "deleted"),
        "by_type": by_type,
        "by_status": by_status,
        "active_count": len(active_assets),
        "holding_count": sum(1 for asset in assets if is_holding_asset(asset)),
        "watching_count": sum(1 for asset in assets if is_watching_asset(asset)),
        "has_funds": "fund" in active_types,
        "has_stocks": "stock" in active_types,
        "warnings": [],
    }


def build_asset_public_safe_view(asset: dict[str, Any]) -> dict[str, Any]:
    validate_asset(asset)
    return {field: asset[field] for field in PUBLIC_SAFE_ASSET_FIELDS if field in asset}


def scan_asset_for_sensitive_values(asset: Any) -> list[str]:
    findings: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if str(key).lower() in SENSITIVE_KEY_NAMES:
                    findings.append(f"sensitive field at {child_path}")
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str):
            for label, pattern in SENSITIVE_VALUE_PATTERNS:
                if pattern.search(value):
                    findings.append(f"{label} at {path}")

    walk(asset, "")
    return findings
