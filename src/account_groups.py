"""Public-safe account group helpers.

An account group is not a real-name user account. It is a lightweight
watch group / portfolio container with a unified ``assets`` list. This module
loads only example configuration by default and intentionally does not identify
codes, enrich names, persist private holdings, or read real user config.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.user_config import EXAMPLE_CONFIG_DIR, RISK_PROFILES, UserConfigError

EXAMPLE_ACCOUNT_GROUPS_PATH = EXAMPLE_CONFIG_DIR / "account_groups.example.json"
EMPTY_ACCOUNT_GROUP_CONFIG = {"config_version": 1, "account_groups": []}

ASSET_TYPES = {"fund", "stock", "company", "industry", "theme", "index"}
ACTIVE_ASSET_STATUSES = {"holding", "watching"}
ASSET_STATUSES = {"holding", "watching", "cleared", "archived"}
MARKETS = {"CN", "HK", "US", "unknown"}
SOURCE_STATUSES = {"manual_user_input", "verified", "unknown", "pending_confirmation", "conflict"}
SUMMARY_ASSET_TYPES = ("fund", "stock", "company", "industry", "theme", "index")
SUMMARY_STATUSES = ("holding", "watching", "cleared", "archived")

SENSITIVE_KEY_NAMES = {
    "email",
    "phone",
    "id_card",
    "身份证",
    "手机号",
    "amount",
    "cost_price",
    "account_value",
    "balance",
    "profit",
    "holding_amount",
    "position_amount",
    "webhook_url",
    "webhook",
    "token",
    "api_key",
    "apikey",
}
SENSITIVE_VALUE_PATTERNS = [
    ("webhook URL", re.compile(r"https?://[^\s\"']*webhook[^\s\"']*", re.IGNORECASE)),
    ("Token", re.compile(r"\b(?:token|secret)[=:][A-Za-z0-9_\-]{16,}\b", re.IGNORECASE)),
    ("API Key", re.compile(r"\bapi[_-]?key[=:][A-Za-z0-9_\-]{16,}\b", re.IGNORECASE)),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")),
    ("id_card", re.compile(r"(?<!\d)\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)")),
]


class AccountGroupConfigError(UserConfigError):
    """Raised when account group example/config data is malformed or unsafe."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return dict(EMPTY_ACCOUNT_GROUP_CONFIG)
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise AccountGroupConfigError(f"Invalid JSON in {path}: {exc.msg} at line {exc.lineno}") from exc
    if not isinstance(data, dict):
        raise AccountGroupConfigError(f"Configuration file {path} must contain a JSON object.")
    return data


def load_account_groups(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate account groups from an explicit path or the example file."""

    path = Path(config_path) if config_path is not None else EXAMPLE_ACCOUNT_GROUPS_PATH
    config = _read_json(path)
    validate_account_group_config(config)
    findings = scan_account_group_for_sensitive_values(config)
    if findings:
        raise AccountGroupConfigError("Sensitive values are not allowed in account groups: " + "; ".join(findings))
    return config


def load_example_account_groups() -> dict[str, Any]:
    """Load the committed public-safe account group example configuration."""

    return load_account_groups(EXAMPLE_ACCOUNT_GROUPS_PATH)


def validate_account_group_config(config: dict[str, Any]) -> None:
    if not isinstance(config.get("config_version"), int):
        raise AccountGroupConfigError("config_version must be an integer.")
    groups = config.get("account_groups", [])
    if not isinstance(groups, list):
        raise AccountGroupConfigError("account_groups must be a list.")
    seen: set[str] = set()
    for group in groups:
        validate_account_group(group)
        account_id = group["account_id"]
        if account_id in seen:
            raise AccountGroupConfigError(f"Duplicate account_id: {account_id}")
        seen.add(account_id)


def validate_account_group(group: dict[str, Any]) -> None:
    if not isinstance(group, dict):
        raise AccountGroupConfigError("Each account group must be an object.")
    account_id = group.get("account_id")
    if not isinstance(account_id, str) or not account_id:
        raise AccountGroupConfigError("Each account group requires a non-empty account_id.")
    if not isinstance(group.get("account_name"), str) or not group.get("account_name"):
        raise AccountGroupConfigError(f"account_name is required for account_id {account_id}.")
    if not isinstance(group.get("enabled", False), bool):
        raise AccountGroupConfigError(f"enabled must be boolean for account_id {account_id}.")
    if group.get("risk_profile") not in RISK_PROFILES:
        raise AccountGroupConfigError(f"Invalid risk_profile for account_id {account_id}.")
    if "description" in group and not isinstance(group["description"], str):
        raise AccountGroupConfigError(f"description must be string for account_id {account_id}.")
    assets = group.get("assets", [])
    if not isinstance(assets, list):
        raise AccountGroupConfigError(f"assets must be a list for account_id {account_id}.")
    seen: set[str] = set()
    for asset in assets:
        validate_asset(asset)
        asset_id = asset["asset_id"]
        if asset_id in seen:
            raise AccountGroupConfigError(f"Duplicate asset_id {asset_id} in account_id {account_id}.")
        seen.add(asset_id)


def validate_asset(asset: dict[str, Any]) -> None:
    if not isinstance(asset, dict):
        raise AccountGroupConfigError("Each asset must be an object.")
    asset_id = asset.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id:
        raise AccountGroupConfigError("Each asset requires a non-empty asset_id.")
    if asset.get("type") not in ASSET_TYPES:
        raise AccountGroupConfigError(f"Invalid type for asset_id {asset_id}.")
    if not isinstance(asset.get("code"), str) or not asset.get("code"):
        raise AccountGroupConfigError(f"code is required for asset_id {asset_id}.")
    if not isinstance(asset.get("name"), str) or not asset.get("name"):
        raise AccountGroupConfigError(f"name is required for asset_id {asset_id}.")
    if asset.get("market") not in MARKETS:
        raise AccountGroupConfigError(f"Invalid market for asset_id {asset_id}.")
    if not isinstance(asset.get("tags", []), list) or not all(isinstance(tag, str) for tag in asset.get("tags", [])):
        raise AccountGroupConfigError(f"tags must be a list of strings for asset_id {asset_id}.")
    if asset.get("status") not in ASSET_STATUSES:
        raise AccountGroupConfigError(f"Invalid status for asset_id {asset_id}.")
    weight_level = asset.get("weight_level")
    if not isinstance(weight_level, int) or not 1 <= weight_level <= 5:
        raise AccountGroupConfigError(f"weight_level must be an integer from 1 to 5 for asset_id {asset_id}.")
    if asset.get("source_status") not in SOURCE_STATUSES:
        raise AccountGroupConfigError(f"Invalid source_status for asset_id {asset_id}.")


def get_enabled_account_groups(config: dict[str, Any]) -> list[dict[str, Any]]:
    validate_account_group_config(config)
    return [group for group in config.get("account_groups", []) if group.get("enabled") is True]


def get_account_group_by_id(config: dict[str, Any], account_id: str) -> dict[str, Any] | None:
    validate_account_group_config(config)
    return next((group for group in config.get("account_groups", []) if group.get("account_id") == account_id), None)


def get_assets_by_type(group: dict[str, Any], asset_type: str) -> list[dict[str, Any]]:
    if asset_type not in ASSET_TYPES:
        raise AccountGroupConfigError(f"Invalid asset_type: {asset_type}")
    validate_account_group(group)
    return [asset for asset in group.get("assets", []) if asset.get("type") == asset_type]


def get_assets_by_status(group: dict[str, Any], status: str) -> list[dict[str, Any]]:
    if status not in ASSET_STATUSES:
        raise AccountGroupConfigError(f"Invalid status: {status}")
    validate_account_group(group)
    return [asset for asset in group.get("assets", []) if asset.get("status") == status]


def split_assets_by_type(group: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    validate_account_group(group)
    buckets = {asset_type: [] for asset_type in SUMMARY_ASSET_TYPES}
    for asset in group.get("assets", []):
        buckets[asset["type"]].append(asset)
    return buckets


def _active_assets(group: dict[str, Any]) -> list[dict[str, Any]]:
    validate_account_group(group)
    return [asset for asset in group.get("assets", []) if asset.get("status") in ACTIVE_ASSET_STATUSES]


def get_visible_sections_for_account(group: dict[str, Any]) -> list[str]:
    active_assets = _active_assets(group)
    active_types = {asset.get("type") for asset in active_assets}
    sections: list[str] = []
    if "fund" in active_types or "stock" in active_types or "company" in active_types:
        sections.append("overview")
    if "fund" in active_types:
        sections.append("funds")
    if "stock" in active_types:
        sections.append("stocks")
    if "company" in active_types:
        sections.append("companies")
    return sections or ["empty_state"]


def build_account_group_summary(group: dict[str, Any]) -> dict[str, Any]:
    validate_account_group(group)
    assets = list(group.get("assets", []))
    counts: dict[str, int] = {"total": len(assets)}
    for asset_type in SUMMARY_ASSET_TYPES:
        counts[asset_type] = sum(1 for asset in assets if asset.get("type") == asset_type)
    for status in SUMMARY_STATUSES:
        counts[status] = sum(1 for asset in assets if asset.get("status") == status)
    active_types = {asset.get("type") for asset in _active_assets(group)}
    return {
        "account_id": group.get("account_id"),
        "account_name": group.get("account_name"),
        "enabled": group.get("enabled"),
        "asset_counts": counts,
        "visible_sections": get_visible_sections_for_account(group),
        "has_funds": "fund" in active_types,
        "has_stocks": "stock" in active_types,
        "has_active_assets": bool(active_types),
        "warnings": scan_account_group_for_sensitive_values(group),
    }


def scan_account_group_for_sensitive_values(config: Any) -> list[str]:
    """Return redacted sensitive-field findings without treating weight_level as money."""

    findings: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                normalized_key = str(key).lower()
                if normalized_key in SENSITIVE_KEY_NAMES:
                    findings.append(f"sensitive field at {child_path}")
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str):
            for label, pattern in SENSITIVE_VALUE_PATTERNS:
                if pattern.search(value):
                    findings.append(f"{label} at {path}")

    walk(config, "")
    return findings
