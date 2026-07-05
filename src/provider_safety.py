"""Safety policies for future real market data providers.

This module intentionally does not connect to external providers, read user
configuration, persist market values, or include real tokens.  It only defines
preflight safety rules for later provider integrations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PROVIDER_TYPES = frozenset({"fixture", "mock", "public_web", "api", "local_cache"})
DATA_MODES = frozenset({
    "fixture_only",
    "mock_only",
    "model_only",
    "real_provider",
    "real_provider_cached",
    "mixed_real_and_fixture",
    "unsupported",
})
SENSITIVE_FIELD_NAMES = frozenset({
    "token",
    "api key",
    "apikey",
    "api_key",
    "secret",
    "password",
    "passwd",
    "webhook",
    "authorization",
    "bearer",
    "cookie",
    "session",
    "private_key",
    "client_secret",
})
ALLOWED_TOKEN_ENV_NAMES = frozenset({"AKSHARE_TOKEN_ENV", "YFINANCE_TOKEN_ENV", "EASTMONEY_TOKEN_ENV"})
FAILURE_REASONS = frozenset({
    "provider_timeout",
    "provider_error",
    "rate_limited",
    "invalid_response",
    "stale_data",
    "conflict",
    "unsupported",
})
FUND_NAV_ALLOWED_LABELS = frozenset({"单位净值", "累计净值", "日涨跌幅", "估算净值", "估算涨跌", "净值日期", "估算更新时间"})
FUND_ESTIMATE_WARNING = "盘中估算仅供观察，最终以基金公司公布净值为准。"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_sensitive_field_name(field_name: str) -> bool:
    normalized = str(field_name or "").strip().lower().replace("-", "_")
    compact = normalized.replace("_", " ")
    return normalized in SENSITIVE_FIELD_NAMES or compact in SENSITIVE_FIELD_NAMES


def _walk_config(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if is_sensitive_field_name(key_text):
                if not (isinstance(nested, str) and nested in ALLOWED_TOKEN_ENV_NAMES):
                    findings.append(child_path)
            findings.extend(_walk_config(nested, child_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            findings.extend(_walk_config(nested, f"{path}[{index}]"))
    return findings


def scan_provider_config_for_secrets(config: Mapping[str, Any]) -> list[str]:
    return _walk_config(config)


def classify_provider_data_mode(provider_config: Mapping[str, Any]) -> str:
    provider_type = str(provider_config.get("provider_type") or "").strip()
    data_mode = str(provider_config.get("data_mode") or "").strip()
    if data_mode:
        return data_mode if data_mode in DATA_MODES else "unsupported"
    return {
        "fixture": "fixture_only",
        "mock": "mock_only",
        "local_cache": "real_provider_cached",
        "public_web": "real_provider",
        "api": "real_provider",
    }.get(provider_type, "unsupported")


def is_network_provider_enabled(config: Mapping[str, Any]) -> bool:
    provider_type = config.get("provider_type")
    if provider_type in {"fixture", "mock", "local_cache"}:
        return False
    return bool(config.get("enabled") and config.get("network_enabled"))


def is_provider_allowed_in_public_repo(config: Mapping[str, Any]) -> bool:
    mode = classify_provider_data_mode(config)
    return mode in {"fixture_only", "mock_only", "model_only", "unsupported"} and not bool(config.get("has_real_market_data"))


def build_provider_safety_policy() -> dict[str, Any]:
    return {
        "provider_types": sorted(PROVIDER_TYPES),
        "data_modes": sorted(DATA_MODES),
        "real_providers_default_enabled": False,
        "requires_explicit_network_enabled": True,
        "allow_real_data_commit_to_public_repo": False,
        "allow_secrets_in_repo": False,
        "fund_nav_estimate_warning": FUND_ESTIMATE_WARNING,
    }


def validate_provider_config(config: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    provider_type = str(config.get("provider_type") or "")
    if provider_type not in PROVIDER_TYPES:
        errors.append("unsupported provider_type")
    if provider_type in {"public_web", "api"} and config.get("enabled") is True:
        if config.get("network_enabled") is not True:
            errors.append("network provider must explicitly set network_enabled=true")
    if provider_type == "public_web":
        for field in ("timeout_seconds", "retry", "rate_limit"):
            if field not in config:
                errors.append(f"public_web provider requires {field}")
    if provider_type == "api" and scan_provider_config_for_secrets(config):
        errors.append("api provider config contains plaintext secret fields")
    data_mode = classify_provider_data_mode(config)
    if provider_type == "fixture" and data_mode == "real_provider":
        errors.append("fixture provider cannot be marked real_provider")
    if provider_type == "mock" and data_mode == "real_provider":
        errors.append("mock provider cannot be marked real_provider")
    return errors


def build_provider_source_metadata(provider_name: str, provider_type: str, data_mode: str) -> dict[str, Any]:
    status = {"fixture": "fixture_only", "mock": "mock_only"}.get(provider_type, data_mode)
    return {"provider": provider_name, "provider_type": provider_type, "data_mode": data_mode, "source_status": status, "checked_at": _utc_now_iso()}


def validate_source_metadata(source: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("provider", "provider_type", "data_mode", "source_status"):
        if not source.get(field):
            errors.append(f"source metadata requires {field}")
    if source.get("data_mode") == "real_provider" and not source.get("checked_at"):
        errors.append("real_provider source metadata requires checked_at")
    if source.get("data_mode") == "real_provider_cached":
        if not source.get("cache_checked_at"):
            errors.append("real_provider_cached source metadata requires cache_checked_at")
        if not source.get("cache_expires_at"):
            errors.append("real_provider_cached source metadata requires cache_expires_at")
    if source.get("data_mode") == "mixed_real_and_fixture" and not source.get("warning"):
        errors.append("mixed_real_and_fixture source metadata requires warning")
    return errors


def validate_provider_result(result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    data_mode = str(result.get("data_mode") or result.get("source", {}).get("data_mode") or "")
    provider_type = str(result.get("provider_type") or result.get("source", {}).get("provider_type") or "")
    if provider_type == "fixture" and data_mode == "real_provider":
        errors.append("fixture_only cannot be marked real_provider")
    if provider_type == "mock" and data_mode == "real_provider":
        errors.append("mock_only cannot be marked real_provider")
    if data_mode == "real_provider":
        for field in ("provider", "checked_at", "source_status"):
            if not (result.get(field) or result.get("source", {}).get(field)):
                errors.append(f"real_provider requires {field}")
    if data_mode == "real_provider_cached":
        for field in ("cache_checked_at", "cache_expires_at"):
            if not (result.get(field) or result.get("source", {}).get(field)):
                errors.append(f"real_provider_cached requires {field}")
    if data_mode == "mixed_real_and_fixture" and not result.get("warning"):
        errors.append("mixed_real_and_fixture requires warning")
    if result.get("data_kind") == "fund_nav" and result.get("price_mode") == "realtime_quote":
        errors.append("fund_nav result cannot use realtime_quote")
    return errors


def assert_fixture_not_marked_real(result: Mapping[str, Any]) -> None:
    if result.get("provider_type") == "fixture" and (result.get("has_real_market_data") or result.get("data_mode") == "real_provider"):
        raise ValueError("fixture data cannot be marked as real market data")


def build_provider_cache_policy(provider_name: str, data_kind: str) -> dict[str, Any]:
    return {
        "provider": provider_name,
        "data_kind": data_kind,
        "cache_enabled": False,
        "cache_scope": "local_only",
        "allow_commit_to_repo": False,
        "ttl_seconds": 60,
        "requires_checked_at": True,
        "requires_expires_at": True,
    }


def validate_cache_policy(policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if policy.get("cache_scope") != "local_only":
        errors.append("provider cache must default to local_only")
    if policy.get("allow_commit_to_repo") is not False:
        errors.append("real provider cache cannot be committed to public repo")
    if policy.get("requires_checked_at") is not True:
        errors.append("cache policy requires checked_at")
    if policy.get("requires_expires_at") is not True:
        errors.append("cache policy requires expires_at")
    return errors


def assert_real_data_not_written_to_repo(path_or_policy: str | Path | Mapping[str, Any]) -> None:
    if isinstance(path_or_policy, Mapping):
        if path_or_policy.get("has_real_market_data") or path_or_policy.get("allow_commit_to_repo") is not False:
            raise ValueError("real provider data cannot be written to a public repository")
        return
    path_text = str(path_or_policy)
    if ".git" in Path(path_text).parts:
        raise ValueError("real provider data cannot be written inside a git repository")


def build_provider_failure_policy(provider_name: str) -> dict[str, Any]:
    return {
        "provider": provider_name,
        "failure_reasons": sorted(FAILURE_REASONS),
        "fail_whole_account_page": False,
        "fail_other_assets": False,
        "requires_reason": True,
        "stale_data_requires_checked_at": True,
        "conflict_requires_warning": True,
        "forbid_stale_as_fresh": True,
        "forbid_unavailable_as_available": True,
    }


def validate_failure_result(result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    reason = result.get("reason")
    status = result.get("status") or result.get("source_status")
    if status in FAILURE_REASONS and not reason:
        errors.append("failure result requires reason")
    if status == "stale_data" and not result.get("checked_at"):
        errors.append("stale_data requires checked_at")
    if status == "conflict" and not result.get("warning"):
        errors.append("conflict requires warning")
    if status == "unavailable" and result.get("available") is True:
        errors.append("unavailable cannot be marked available")
    return errors
