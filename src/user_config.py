"""Safe, example-first multi-user configuration helpers.

This module intentionally does not wire user configuration into the daily or
weekly report runtime.  It only provides loading, validation, lookup, and basic
sensitive-value scanning for future local/private user configuration layers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG_DIR = REPO_ROOT / "config" / "examples"
DEFAULT_USER_CONFIG_DIR = REPO_ROOT / "data" / "user_config"

RISK_PROFILES = {"conservative", "balanced", "aggressive"}
TASK_GROUP_TYPES = {
    "market_tracking",
    "fund_tracking",
    "stock_tracking",
    "industry_tracking",
    "company_tracking",
    "mixed",
}
OUTPUT_MODES = {"public_summary_only", "local_private_report", "private_discord_channel"}
REPORT_TYPES = {"daily", "weekly"}
WATCHLIST_ITEM_TYPES = {"stock", "fund", "company", "industry", "theme", "index"}

EMPTY_USER_CONFIG = {"config_version": 1, "users": []}
EMPTY_TASK_GROUPS_CONFIG = {"config_version": 1, "task_groups": []}
EMPTY_WATCHLISTS_CONFIG = {"config_version": 1, "watchlists": []}

SENSITIVE_KEY_PARTS = {
    "cost",
    "cost_price",
    "amount",
    "asset",
    "assets",
    "balance",
    "profit",
    "principal",
    "position_value",
    "market_value",
}

SENSITIVE_VALUE_PATTERNS = [
    ("webhook URL", re.compile(r"https?://[^\s\"']*webhook[^\s\"']*", re.IGNORECASE)),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("OpenAI API key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("API key", re.compile(r"\b(?:api[_-]?key|token|secret)[=:][A-Za-z0-9_\-]{16,}\b", re.IGNORECASE)),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone number", re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")),
    ("Chinese ID number", re.compile(r"(?<!\d)\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)")),
]


class UserConfigError(ValueError):
    """Raised when a user configuration file is malformed or unsafe."""


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise UserConfigError(f"Invalid JSON in {path}: {exc.msg} at line {exc.lineno}") from exc
    if not isinstance(data, dict):
        raise UserConfigError(f"Configuration file {path} must contain a JSON object.")
    return data


def load_user_config(config_dir: str | Path | None = None) -> dict[str, Any]:
    """Load users, task groups, and watchlists from a directory.

    By default this function loads only committed example files.  If a custom
    local/private directory is provided and does not exist, empty configuration
    sections are returned without raising.
    """

    base_dir = Path(config_dir) if config_dir is not None else EXAMPLE_CONFIG_DIR
    if not base_dir.exists():
        return {
            "users": dict(EMPTY_USER_CONFIG),
            "task_groups": dict(EMPTY_TASK_GROUPS_CONFIG),
            "watchlists": dict(EMPTY_WATCHLISTS_CONFIG),
        }

    suffix = ".example" if base_dir == EXAMPLE_CONFIG_DIR else ""
    config = {
        "users": _read_json(base_dir / f"users{suffix}.json", EMPTY_USER_CONFIG),
        "task_groups": _read_json(base_dir / f"task_groups{suffix}.json", EMPTY_TASK_GROUPS_CONFIG),
        "watchlists": _read_json(base_dir / f"watchlists{suffix}.json", EMPTY_WATCHLISTS_CONFIG),
    }
    validate_user_config(config["users"])
    validate_task_groups(config["task_groups"])
    validate_watchlists(config["watchlists"])
    findings = scan_config_for_sensitive_values(config)
    if findings:
        raise UserConfigError("Sensitive values are not allowed in user config: " + "; ".join(findings))
    return config


def load_example_user_config() -> dict[str, Any]:
    """Load the public-safe example configuration files."""

    return load_user_config(EXAMPLE_CONFIG_DIR)


def _ensure_list(config: dict[str, Any], key: str) -> list[Any]:
    value = config.get(key, [])
    if not isinstance(value, list):
        raise UserConfigError(f"{key} must be a list.")
    return value


def validate_user_config(config: dict[str, Any]) -> None:
    users = _ensure_list(config, "users")
    seen: set[str] = set()
    for user in users:
        if not isinstance(user, dict):
            raise UserConfigError("Each user must be an object.")
        user_id = user.get("user_id")
        if not isinstance(user_id, str) or not user_id:
            raise UserConfigError("Each user requires a non-empty user_id.")
        if user_id in seen:
            raise UserConfigError(f"Duplicate user_id: {user_id}")
        seen.add(user_id)
        if user.get("risk_profile") not in RISK_PROFILES:
            raise UserConfigError(f"Invalid risk_profile for user_id {user_id}.")
        if not isinstance(user.get("enabled", False), bool):
            raise UserConfigError(f"enabled must be boolean for user_id {user_id}.")
        if not isinstance(user.get("task_group_ids", []), list):
            raise UserConfigError(f"task_group_ids must be a list for user_id {user_id}.")
        secret_name = user.get("discord_webhook_secret_name")
        if secret_name is not None and (not isinstance(secret_name, str) or secret_name.startswith("http")):
            raise UserConfigError(f"discord_webhook_secret_name must be a secret name for user_id {user_id}.")


def validate_task_groups(config: dict[str, Any]) -> None:
    task_groups = _ensure_list(config, "task_groups")
    seen: set[str] = set()
    for group in task_groups:
        if not isinstance(group, dict):
            raise UserConfigError("Each task group must be an object.")
        group_id = group.get("task_group_id")
        if not isinstance(group_id, str) or not group_id:
            raise UserConfigError("Each task group requires a non-empty task_group_id.")
        if group_id in seen:
            raise UserConfigError(f"Duplicate task_group_id: {group_id}")
        seen.add(group_id)
        if group.get("type") not in TASK_GROUP_TYPES:
            raise UserConfigError(f"Invalid type for task_group_id {group_id}.")
        if group.get("output_mode") not in OUTPUT_MODES:
            raise UserConfigError(f"Invalid output_mode for task_group_id {group_id}.")
        if not isinstance(group.get("enabled", False), bool):
            raise UserConfigError(f"enabled must be boolean for task_group_id {group_id}.")
        if any(item not in REPORT_TYPES for item in group.get("report_types", [])):
            raise UserConfigError(f"Invalid report_types for task_group_id {group_id}.")


def validate_watchlists(config: dict[str, Any]) -> None:
    watchlists = _ensure_list(config, "watchlists")
    seen: set[str] = set()
    for watchlist in watchlists:
        if not isinstance(watchlist, dict):
            raise UserConfigError("Each watchlist must be an object.")
        watchlist_id = watchlist.get("watchlist_id")
        if not isinstance(watchlist_id, str) or not watchlist_id:
            raise UserConfigError("Each watchlist requires a non-empty watchlist_id.")
        if watchlist_id in seen:
            raise UserConfigError(f"Duplicate watchlist_id: {watchlist_id}")
        seen.add(watchlist_id)
        items = watchlist.get("items", [])
        if not isinstance(items, list):
            raise UserConfigError(f"items must be a list for watchlist_id {watchlist_id}.")
        for item in items:
            if not isinstance(item, dict):
                raise UserConfigError(f"Each watchlist item must be an object for watchlist_id {watchlist_id}.")
            if item.get("type") not in WATCHLIST_ITEM_TYPES:
                raise UserConfigError(f"Invalid item type in watchlist_id {watchlist_id}.")
            if "code" in item and item["code"] is not None and not isinstance(item["code"], str):
                raise UserConfigError(f"code must be string or null in watchlist_id {watchlist_id}.")
            if not isinstance(item.get("tags", []), list):
                raise UserConfigError(f"tags must be a list in watchlist_id {watchlist_id}.")


def get_enabled_users(config: dict[str, Any]) -> list[dict[str, Any]]:
    users_config = config.get("users", config)
    validate_user_config(users_config)
    return [user for user in users_config.get("users", []) if user.get("enabled") is True]


def get_task_group_by_id(config: dict[str, Any], task_group_id: str) -> dict[str, Any] | None:
    task_groups_config = config.get("task_groups", config)
    validate_task_groups(task_groups_config)
    return next((group for group in task_groups_config.get("task_groups", []) if group.get("task_group_id") == task_group_id), None)


def get_watchlist_by_id(config: dict[str, Any], watchlist_id: str) -> dict[str, Any] | None:
    watchlists_config = config.get("watchlists", config)
    validate_watchlists(watchlists_config)
    return next((item for item in watchlists_config.get("watchlists", []) if item.get("watchlist_id") == watchlist_id), None)


def scan_config_for_sensitive_values(config: Any) -> list[str]:
    """Return redacted findings for sensitive fields or values in config."""

    findings: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                normalized_key = str(key).lower()
                if normalized_key in SENSITIVE_KEY_PARTS or any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
                    findings.append(f"sensitive money/account field at {child_path}")
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
