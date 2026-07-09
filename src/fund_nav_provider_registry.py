"""Evaluation registry for future off-exchange fund NAV providers.

This module is intentionally offline-only. It defines candidate metadata,
field-mapping plans, enablement policies, cache policies and failure policies
for later fund NAV provider work. It does not connect to external providers,
read user configuration, persist real NAV values, or include real provider
payload samples.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.provider_safety import FUND_ESTIMATE_WARNING, scan_provider_config_for_secrets

_ALLOWED_STATUSES = {"candidate_only", "manual_review_only", "supported_for_tests", "pending_review"}
_ALLOWED_PROVIDER_TYPES = {"fixture", "public_web", "manual_or_app_only"}
_REAL_PROVIDER_TYPES = {"public_web", "manual_or_app_only"}
_DAILY_NAV_FIELDS = ["unit_nav", "accumulated_nav", "daily_change_pct", "nav_date"]
_ESTIMATED_NAV_FIELDS = ["estimated_nav", "estimated_change_pct", "estimated_change_amount", "estimate_time"]
_REQUIRED_FIELDS = ["fund_code", "fund_name", "checked_at", "source_status"]
_SOURCE_FIELDS = ["provider", "provider_type", "source_status", "checked_at", "delay_note"]
_SECRET_TERMS = ("api_key", "token", "webhook", "cookie", "authorization", "bearer")

_BASE_FAILURE_POLICY = {
    "timeout": "provider_timeout",
    "network_error": "provider_error",
    "rate_limit": "rate_limited",
    "invalid_schema": "invalid_response",
    "old_cache": "stale_data",
    "provider_conflict": "conflict",
    "unsupported_asset": "unsupported",
    "estimate_missing": "estimate_unavailable",
    "daily_nav_missing": "daily_nav_unavailable",
}

_PROVIDER_BASE: dict[str, dict[str, Any]] = {
    "eastmoney_fund": {
        "provider_name": "eastmoney_fund",
        "display_name": "东方财富基金 / 天天基金",
        "provider_type": "public_web",
        "markets": ["CN"],
        "asset_types": ["fund"],
        "data_kinds": ["daily_nav", "estimated_nav"],
        "network_required": True,
        "default_enabled": False,
        "status": "candidate_only",
        "data_mode_if_enabled": "real_provider",
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
    },
    "tiantian_fund": {
        "provider_name": "tiantian_fund",
        "display_name": "天天基金",
        "provider_type": "public_web",
        "markets": ["CN"],
        "asset_types": ["fund"],
        "data_kinds": ["daily_nav", "estimated_nav"],
        "network_required": True,
        "default_enabled": False,
        "status": "candidate_only",
        "data_mode_if_enabled": "real_provider",
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
    },
    "fund_company_official": {
        "provider_name": "fund_company_official",
        "display_name": "基金公司官网",
        "provider_type": "public_web",
        "markets": ["CN"],
        "asset_types": ["fund"],
        "data_kinds": ["daily_nav"],
        "network_required": True,
        "default_enabled": False,
        "status": "candidate_only",
        "data_mode_if_enabled": "real_provider",
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
    },
    "ant_fund_manual": {
        "provider_name": "ant_fund_manual",
        "display_name": "支付宝 / 蚂蚁基金手动来源",
        "provider_type": "manual_or_app_only",
        "markets": ["CN"],
        "asset_types": ["fund"],
        "data_kinds": ["daily_nav", "estimated_nav"],
        "network_required": "unknown",
        "default_enabled": False,
        "status": "manual_review_only",
        "data_mode_if_enabled": "manual_review_only",
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
        "notes": ["不默认接入", "不抓取个人支付宝数据", "不读取真实账户"],
    },
    "local_fund_nav_fixture": {
        "provider_name": "local_fund_nav_fixture",
        "display_name": "本地基金净值 fixture",
        "provider_type": "fixture",
        "markets": ["CN"],
        "asset_types": ["fund"],
        "data_kinds": ["daily_nav", "estimated_nav"],
        "network_required": False,
        "default_enabled": True,
        "status": "supported_for_tests",
        "data_mode_if_enabled": "fixture_only",
        "allow_commit_to_repo": True,
        "cache_scope": "repo_fixture_only",
    },
}


def classify_fund_nav_provider_risk(candidate: dict[str, Any]) -> str:
    if candidate.get("provider_type") == "fixture":
        return "low"
    if candidate.get("provider_type") == "manual_or_app_only":
        return "high"
    if candidate.get("network_required") is True:
        return "medium"
    return "pending_review"


def build_fund_nav_field_mapping(provider_name: str) -> dict[str, Any]:
    data_kinds = _PROVIDER_BASE.get(provider_name, {}).get("data_kinds", [])
    return {
        "provider_name": provider_name,
        "mapping_status": "planned" if provider_name in _PROVIDER_BASE else "pending_review",
        "required_fields": list(_REQUIRED_FIELDS),
        "daily_nav_fields": list(_DAILY_NAV_FIELDS),
        "estimated_nav_fields": list(_ESTIMATED_NAV_FIELDS) if "estimated_nav" in data_kinds or provider_name not in _PROVIDER_BASE else [],
        "source_fields": list(_SOURCE_FIELDS),
        "optional_fields": [],
        "unknown_fields": [] if provider_name in _PROVIDER_BASE else ["pending_review"],
        "notes": ["本阶段仅定义字段映射计划，不读取真实 provider 输出。", "估算净值不等于最终净值。"],
    }


def build_fund_nav_enablement_policy(provider_name: str) -> dict[str, Any]:
    base = _PROVIDER_BASE[provider_name]
    is_fixture = base["provider_type"] == "fixture"
    return {
        "provider_name": provider_name,
        "default_enabled": bool(base["default_enabled"]),
        "requires_explicit_config": not is_fixture,
        "requires_network_enabled": bool(base["network_required"] is True),
        "requires_provider_enabled": not is_fixture,
        "requires_allow_real_request": not is_fixture,
        "requires_provider_safety": not is_fixture,
        "requires_cache_policy": True,
        "requires_timeout_seconds": 10 if not is_fixture else None,
        "requires_retry_limit": 0,
        "allow_public_repo_write": bool(base["allow_commit_to_repo"]),
        "allow_real_data_in_tests": False,
        "allowed_modes": ["fixture_only"] if is_fixture else ["dry_run", "local_only"],
    }


def build_fund_nav_cache_policy(provider_name: str) -> dict[str, Any]:
    base = _PROVIDER_BASE[provider_name]
    return {
        "provider_name": provider_name,
        "policies": [
            {"data_kind": "daily_nav", "cache_enabled_by_default": False, "cache_scope": base["cache_scope"], "allow_commit_to_repo": bool(base["allow_commit_to_repo"]), "ttl_seconds": 86400, "requires_checked_at": True, "requires_nav_date": True, "stale_policy": "mark_stale_not_available"},
            {"data_kind": "estimated_nav", "cache_enabled_by_default": False, "cache_scope": base["cache_scope"], "allow_commit_to_repo": bool(base["allow_commit_to_repo"]), "ttl_seconds": 300, "requires_checked_at": True, "requires_estimate_time": True, "stale_policy": "mark_stale_not_available"},
        ],
    }


def build_fund_nav_failure_policy(provider_name: str) -> dict[str, Any]:
    return {
        "provider_name": provider_name,
        "failure_policy": deepcopy(_BASE_FAILURE_POLICY),
        "fallback": {"allow_fixture_fallback": False, "allow_stale_cache": False, "mark_unavailable": True, "preserve_conflict_warning": True, "single_fund_failure_isolated": True, "estimate_unavailable_keeps_daily_nav": True},
    }


def _build_candidate(provider_name: str) -> dict[str, Any]:
    candidate = deepcopy(_PROVIDER_BASE[provider_name])
    candidate["risk_level"] = classify_fund_nav_provider_risk(candidate)
    candidate.setdefault("notes", [])
    candidate["notes"].extend(["候选 provider，仅用于后续评估，本阶段不接入真实请求。", FUND_ESTIMATE_WARNING])
    candidate.update({
        "requires_provider_safety_check": candidate["provider_type"] != "fixture",
        "requires_field_mapping_check": True,
        "requires_timeout": candidate["provider_type"] != "fixture",
        "requires_rate_limit": candidate["provider_type"] != "fixture",
        "requires_source_metadata": True,
        "requires_final_nav_disclaimer": True,
        "field_mapping": build_fund_nav_field_mapping(provider_name),
        "enablement_policy": build_fund_nav_enablement_policy(provider_name),
        "cache_policy": build_fund_nav_cache_policy(provider_name),
        "failure_policy": build_fund_nav_failure_policy(provider_name),
    })
    validate_fund_nav_provider_candidate(candidate)
    return candidate


def build_fund_nav_provider_registry() -> dict[str, Any]:
    registry = {"registry_name": "fund_nav_provider_registry", "status": "evaluation_only", "scope": {"markets": ["CN"], "asset_types": ["fund"], "data_kinds": ["daily_nav", "estimated_nav"]}, "disclaimer": "本阶段仅做 provider 接入评估，不请求真实基金净值。", "providers": [_build_candidate(name) for name in _PROVIDER_BASE]}
    validate_fund_nav_provider_registry(registry)
    return registry


def get_fund_nav_provider_candidates(market: str | None = None, nav_type: str | None = None) -> list[dict[str, Any]]:
    candidates = build_fund_nav_provider_registry()["providers"]
    if market:
        candidates = [item for item in candidates if market in item.get("markets", [])]
    if nav_type:
        candidates = [item for item in candidates if nav_type in item.get("data_kinds", [])]
    return candidates


def get_fund_nav_provider_evaluation(provider_name: str) -> dict[str, Any]:
    if provider_name not in _PROVIDER_BASE:
        raise KeyError(f"unknown fund NAV provider candidate: {provider_name}")
    return _build_candidate(provider_name)


def validate_fund_nav_provider_candidate(candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    is_fixture = candidate.get("provider_type") == "fixture"
    if not candidate.get("provider_name"):
        errors.append("provider_name is required")
    if candidate.get("provider_type") not in _ALLOWED_PROVIDER_TYPES:
        errors.append("provider_type is not allowed")
    if candidate.get("status") not in _ALLOWED_STATUSES or candidate.get("status") == "verified":
        errors.append("candidate must not be marked verified")
    if not is_fixture and candidate.get("default_enabled") is not False:
        errors.append("real provider candidates must be disabled by default")
    if not is_fixture and candidate.get("allow_commit_to_repo") is not False:
        errors.append("real provider candidates must not write public repo")
    if candidate.get("provider_type") == "public_web" and candidate.get("network_required") is not True:
        errors.append("public_web fund NAV providers require network gate")
    if candidate.get("provider_type") == "fixture" and candidate.get("data_mode_if_enabled") == "real_provider":
        errors.append("fixture cannot be marked real_provider")
    if not candidate.get("risk_level"):
        errors.append("risk_level is required")
    for key in ("field_mapping", "enablement_policy", "cache_policy", "failure_policy"):
        if key not in candidate:
            errors.append(f"{key} is required")
    if not is_fixture and candidate.get("enablement_policy", {}).get("allow_public_repo_write") is not False:
        errors.append("real provider policy must forbid public repo writes")
    if scan_provider_config_for_secrets(candidate):
        errors.append("candidate contains secret-like fields")
    if errors:
        raise ValueError("; ".join(errors))
    return []


def validate_fund_nav_provider_registry(registry: dict[str, Any]) -> list[str]:
    providers = registry.get("providers")
    if not isinstance(providers, list) or not providers:
        raise ValueError("providers must be a non-empty list")
    names = [item.get("provider_name") for item in providers]
    if len(names) != len(set(names)):
        raise ValueError("provider_name values must be unique")
    for item in providers:
        validate_fund_nav_provider_candidate(item)
    return []


def build_fund_nav_provider_evaluation() -> dict[str, Any]:
    evaluation = {"evaluation_name": "p5_r_fund_nav_provider_evaluation", "status": "evaluation_only", "registry": build_fund_nav_provider_registry(), "preflight_checks": ["provider_safety", "field_mapping", "timeout", "retry", "cache_policy", "source_metadata", "fund_disclaimer"], "future_route": ["P5-R1: 场外基金净值 provider dry-run adapter", "P5-R2: 场外基金净值 provider local-only 测试", "P5-R3: 场外基金净值真实请求最小闭环"]}
    validate_fund_nav_provider_evaluation(evaluation)
    return evaluation


def validate_fund_nav_provider_evaluation(evaluation: dict[str, Any]) -> list[str]:
    if evaluation.get("status") != "evaluation_only":
        raise ValueError("evaluation must remain evaluation_only")
    validate_fund_nav_provider_registry(evaluation.get("registry", {}))
    required = {"provider_safety", "field_mapping", "timeout", "retry", "cache_policy", "source_metadata", "fund_disclaimer"}
    if not required.issubset(set(evaluation.get("preflight_checks", []))):
        raise ValueError("missing required preflight checks")
    return []


def render_fund_nav_provider_registry_markdown(registry: dict[str, Any]) -> str:
    validate_fund_nav_provider_registry(registry)
    by_kind = {kind: [p["display_name"] for p in registry["providers"] if kind in p.get("data_kinds", [])] for kind in ("daily_nav", "estimated_nav")}
    lines = [
        "# 场外基金净值 Provider 接入评估 Demo",
        "",
        "## 1. 候选 Provider",
    ]
    for item in registry["providers"]:
        lines.append(f"- {item['display_name']}：{item['status']}，默认启用={str(item['default_enabled']).lower()}，网络={str(item['network_required']).lower()}。")
    lines.extend([
        "",
        "## 2. 支持数据",
        f"- 每日净值：{', '.join(by_kind['daily_nav'])}",
        f"- 估算净值：{', '.join(by_kind['estimated_nav'])}",
        "",
        "## 3. 启用条件",
        "- network_enabled：真实 public_web provider 必须显式开启。",
        "- provider_enabled：真实 provider 必须显式开启。",
        "- allow_real_request：后续真实请求前必须显式允许。",
        "- allow_commit_to_repo：真实净值和估算净值不得写入 public 仓库。",
        "",
        "## 4. 缓存策略",
        "- daily_nav：local_only，TTL 86400 秒，stale 数据标记为不可用。",
        "- estimated_nav：local_only，TTL 300 秒，stale 数据标记为不可用。",
        "",
        "## 5. 数据说明",
        "本阶段仅做 provider 接入评估，不请求真实基金净值。",
        "场外基金不支持真正实时价格。",
        FUND_ESTIMATE_WARNING,
        "真实净值和估算净值不得写入 public 仓库。",
    ])
    rendered = "\n".join(lines) + "\n"
    lowered = rendered.lower()
    if any(term in lowered for term in _SECRET_TERMS):
        raise ValueError("rendered markdown contains forbidden secret term")
    return rendered
