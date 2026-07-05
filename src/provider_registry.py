"""Provider registry evaluation for future CN stock / ETF quote adapters.

This module is intentionally offline-only. It records candidate provider metadata,
field-mapping plans, enablement policies, cache policies and dry-run plans before
any real CN stock / ETF provider is wired into runtime quote fetching.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_ALLOWED_STATUSES = {"candidate_only", "supported_for_tests", "disabled_by_default", "pending_review"}
_ALLOWED_PROVIDER_TYPES = {"fixture", "mock", "public_web", "api", "public_web_or_library"}
_REAL_PROVIDERS = {"akshare", "eastmoney", "sina_finance", "tencent_finance"}
_REQUIRED_QUOTE_FIELDS = ["last_price", "change_pct", "volume", "turnover", "checked_at"]
_OPTIONAL_QUOTE_FIELDS = ["open", "high", "low", "previous_close", "change_amount"]
_UNIFIED_QUOTE_RESULT_TEMPLATE = {
    "last_price": None,
    "change_pct": None,
    "change_amount": None,
    "volume": None,
    "turnover": None,
    "open": None,
    "high": None,
    "low": None,
    "previous_close": None,
    "checked_at": None,
    "source_provider": None,
    "source_status": None,
}

_BASE_FAILURE_POLICY = {
    "timeout": "provider_timeout",
    "network_error": "provider_error",
    "rate_limit": "rate_limited",
    "invalid_schema": "invalid_response",
    "old_cache": "stale_data",
    "provider_conflict": "conflict",
    "unsupported_asset": "unsupported",
}

_PROVIDER_BASE: dict[str, dict[str, Any]] = {
    "akshare": {
        "provider_name": "akshare",
        "display_name": "AKShare",
        "provider_type": "public_web_or_library",
        "markets": ["CN"],
        "asset_types": ["stock", "etf", "index"],
        "data_kinds": ["realtime_quote", "index_quote"],
        "network_required": True,
        "token_required": False,
        "default_enabled": False,
        "status": "candidate_only",
        "risk_level": "medium",
        "data_mode_if_enabled": "real_provider",
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
        "requires_provider_safety_check": True,
        "requires_field_mapping_check": True,
        "requires_timeout": True,
        "requires_rate_limit": True,
        "requires_source_metadata": True,
        "notes": ["候选 provider，仅用于后续评估，本阶段不接入真实请求。"],
    },
    "eastmoney": {
        "provider_name": "eastmoney",
        "display_name": "东方财富",
        "provider_type": "public_web",
        "markets": ["CN"],
        "asset_types": ["stock", "etf", "index"],
        "data_kinds": ["realtime_quote", "index_quote"],
        "network_required": True,
        "token_required": "unknown",
        "default_enabled": False,
        "status": "candidate_only",
        "risk_level": "medium",
        "data_mode_if_enabled": "real_provider",
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
        "requires_provider_safety_check": True,
        "requires_field_mapping_check": True,
        "requires_timeout": True,
        "requires_rate_limit": True,
        "requires_source_metadata": True,
        "notes": ["候选 provider，仅用于后续评估，本阶段不接入真实请求。"],
    },
    "sina_finance": {
        "provider_name": "sina_finance",
        "display_name": "新浪财经",
        "provider_type": "public_web",
        "markets": ["CN"],
        "asset_types": ["stock", "etf"],
        "data_kinds": ["realtime_quote"],
        "network_required": True,
        "token_required": "unknown",
        "default_enabled": False,
        "status": "candidate_only",
        "risk_level": "medium",
        "data_mode_if_enabled": "real_provider",
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
        "requires_provider_safety_check": True,
        "requires_field_mapping_check": True,
        "requires_timeout": True,
        "requires_rate_limit": True,
        "requires_source_metadata": True,
        "notes": ["候选 provider，仅用于后续评估，本阶段不接入真实请求。"],
    },
    "tencent_finance": {
        "provider_name": "tencent_finance",
        "display_name": "腾讯财经",
        "provider_type": "public_web",
        "markets": ["CN"],
        "asset_types": ["stock", "etf"],
        "data_kinds": ["realtime_quote"],
        "network_required": True,
        "token_required": "unknown",
        "default_enabled": False,
        "status": "candidate_only",
        "risk_level": "medium",
        "data_mode_if_enabled": "real_provider",
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
        "requires_provider_safety_check": True,
        "requires_field_mapping_check": True,
        "requires_timeout": True,
        "requires_rate_limit": True,
        "requires_source_metadata": True,
        "notes": ["候选 provider，仅用于后续评估，本阶段不接入真实请求。"],
    },
    "local_fixture": {
        "provider_name": "local_fixture",
        "display_name": "本地 fixture",
        "provider_type": "fixture",
        "markets": ["CN"],
        "asset_types": ["stock", "etf", "index"],
        "data_kinds": ["realtime_quote", "index_quote"],
        "network_required": False,
        "token_required": False,
        "default_enabled": True,
        "status": "supported_for_tests",
        "risk_level": "low",
        "data_mode_if_enabled": "fixture_only",
        "allow_commit_to_repo": True,
        "cache_scope": "repo_fixture_only",
        "requires_provider_safety_check": False,
        "requires_field_mapping_check": True,
        "requires_timeout": False,
        "requires_rate_limit": False,
        "requires_source_metadata": True,
        "notes": ["仅用于离线测试和结构验证，不代表真实行情。"],
    },
}


def classify_provider_risk(candidate: dict[str, Any]) -> str:
    if candidate.get("provider_type") == "fixture":
        return "low"
    if candidate.get("network_required") and candidate.get("provider_type") in {"public_web", "public_web_or_library"}:
        return "medium"
    return "pending_review"


def build_provider_field_mapping(provider_name: str) -> dict[str, Any]:
    status = "planned" if provider_name in _PROVIDER_BASE else "pending_review"
    return {
        "provider_name": provider_name,
        "mapping_status": status,
        "quote_result_template": deepcopy(_UNIFIED_QUOTE_RESULT_TEMPLATE),
        "required_fields": list(_REQUIRED_QUOTE_FIELDS),
        "optional_fields": list(_OPTIONAL_QUOTE_FIELDS),
        "unsupported_fields": [],
        "notes": ["本阶段仅定义字段映射计划，不读取真实 provider 输出。"],
    }


def build_provider_enablement_policy(provider_name: str) -> dict[str, Any]:
    base = _PROVIDER_BASE[provider_name]
    is_fixture = base["provider_type"] == "fixture"
    return {
        "provider_name": provider_name,
        "default_enabled": bool(base["default_enabled"]),
        "requires_explicit_config": not is_fixture,
        "requires_network_enabled": bool(base["network_required"]),
        "requires_provider_safety": not is_fixture,
        "requires_cache_policy": True,
        "requires_timeout_seconds": 10 if not is_fixture else None,
        "requires_retry_limit": 1 if not is_fixture else 0,
        "allow_public_repo_write": bool(base["allow_commit_to_repo"]),
        "allow_real_data_in_tests": False,
        "allowed_modes": ["fixture_only"] if is_fixture else ["dry_run", "local_only"],
    }


def _build_provider_cache_policy(provider_name: str) -> dict[str, Any]:
    base = _PROVIDER_BASE[provider_name]
    is_fixture = base["provider_type"] == "fixture"
    return {
        "provider_name": provider_name,
        "data_kind": "realtime_quote",
        "cache_enabled_by_default": False,
        "cache_scope": base["cache_scope"],
        "allow_commit_to_repo": bool(base["allow_commit_to_repo"]),
        "ttl_seconds": 60,
        "requires_checked_at": True,
        "requires_expires_at": not is_fixture,
        "stale_policy": "mark_stale_not_available",
    }


def _build_provider_failure_policy(provider_name: str) -> dict[str, Any]:
    is_fixture = _PROVIDER_BASE[provider_name]["provider_type"] == "fixture"
    return {
        "provider_name": provider_name,
        "failure_policy": deepcopy(_BASE_FAILURE_POLICY),
        "fallback": {
            "allow_fixture_fallback": False,
            "allow_stale_cache": False,
            "mark_unavailable": not is_fixture,
            "preserve_conflict_warning": True,
            "single_asset_failure_isolated": True,
        },
    }


def build_provider_dry_run_plan(provider_name: str) -> dict[str, Any]:
    return {
        "provider_name": provider_name,
        "stages": [
            "validate_registry_candidate",
            "validate_provider_safety_policy",
            "validate_field_mapping_without_provider_payload",
            "run_fixture_only_contract_tests",
            "run_dry_run_without_network_request",
            "run_local_only_adapter_after_explicit_review",
            "run_real_provider_minimal_gated_adapter_after_explicit_review",
        ],
        "entry_criteria": ["no real quote persistence", "no secrets in config", "explicit network gate for real providers"],
        "exit_criteria": ["source metadata preserved", "timeouts and retry limits defined", "conflicts marked with warning"],
    }


def _build_candidate(provider_name: str) -> dict[str, Any]:
    candidate = deepcopy(_PROVIDER_BASE[provider_name])
    candidate["risk_level"] = classify_provider_risk(candidate)
    candidate["field_mapping"] = build_provider_field_mapping(provider_name)
    candidate["enablement_policy"] = build_provider_enablement_policy(provider_name)
    candidate["cache_policy"] = _build_provider_cache_policy(provider_name)
    candidate["failure_policy"] = _build_provider_failure_policy(provider_name)
    candidate["dry_run_plan"] = build_provider_dry_run_plan(provider_name)
    validate_provider_candidate(candidate)
    return candidate


def build_provider_registry() -> dict[str, Any]:
    registry = {
        "registry_name": "cn_quote_provider_registry",
        "status": "evaluation_only",
        "scope": {"markets": ["CN"], "asset_types": ["stock", "etf", "index"]},
        "disclaimer": "候选 provider 不代表已接入或已验证；真实 provider 默认关闭。",
        "providers": [_build_candidate(name) for name in _PROVIDER_BASE],
    }
    validate_provider_registry(registry)
    return registry


def get_provider_candidates(market: str | None = None, asset_type: str | None = None) -> list[dict[str, Any]]:
    candidates = build_provider_registry()["providers"]
    if market:
        candidates = [item for item in candidates if market in item.get("markets", [])]
    if asset_type:
        candidates = [item for item in candidates if asset_type in item.get("asset_types", [])]
    return candidates


def get_provider_evaluation(provider_name: str) -> dict[str, Any]:
    if provider_name not in _PROVIDER_BASE:
        raise KeyError(f"unknown provider candidate: {provider_name}")
    return _build_candidate(provider_name)


def validate_provider_candidate(candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    name = candidate.get("provider_name")
    is_fixture = candidate.get("provider_type") == "fixture"
    if not name:
        errors.append("provider_name is required")
    if candidate.get("provider_type") not in _ALLOWED_PROVIDER_TYPES:
        errors.append("provider_type is not allowed")
    if candidate.get("status") not in _ALLOWED_STATUSES:
        errors.append("status is not allowed")
    if candidate.get("status") == "verified":
        errors.append("candidate must not be marked verified")
    if not isinstance(candidate.get("network_required"), bool):
        errors.append("network_required must be explicit")
    if not is_fixture and candidate.get("default_enabled") is not False:
        errors.append("real provider candidates must be disabled by default")
    if not is_fixture and candidate.get("allow_commit_to_repo") is not False:
        errors.append("real provider candidates must not write public repo")
    if not candidate.get("cache_scope"):
        errors.append("cache_scope is required")
    if not candidate.get("risk_level"):
        errors.append("risk_level is required")
    if not candidate.get("notes") and not candidate.get("warnings"):
        errors.append("notes or warnings are required")
    for key in ("field_mapping", "enablement_policy", "cache_policy", "failure_policy", "dry_run_plan"):
        if key not in candidate:
            errors.append(f"{key} is required")
    if not is_fixture and candidate.get("enablement_policy", {}).get("requires_network_enabled") is not True:
        errors.append("real provider candidates require network gate")
    if candidate.get("provider_type") == "fixture" and candidate.get("data_mode_if_enabled") == "real_provider":
        errors.append("fixture cannot be marked real_provider")
    if errors:
        raise ValueError("; ".join(errors))
    return errors


def validate_provider_registry(registry: dict[str, Any]) -> list[str]:
    providers = registry.get("providers")
    if not isinstance(providers, list) or not providers:
        raise ValueError("providers must be a non-empty list")
    names = [item.get("provider_name") for item in providers]
    if len(names) != len(set(names)):
        raise ValueError("provider_name values must be unique")
    for item in providers:
        validate_provider_candidate(item)
    return []


def build_cn_quote_provider_evaluation() -> dict[str, Any]:
    registry = build_provider_registry()
    evaluation = {
        "evaluation_name": "p5_q_cn_quote_provider_evaluation",
        "status": "evaluation_only",
        "registry": registry,
        "preflight_checks": [
            "provider_safety",
            "field_mapping",
            "timeout",
            "retry",
            "cache_policy",
            "source_metadata",
        ],
        "conflict_policy": {
            "status": "conflict",
            "preserve_warning": True,
            "do_not_pick_silent_winner": True,
        },
        "future_route": [
            "P5-Q1: A股 / ETF provider dry-run adapter",
            "P5-Q2: A股 / ETF provider local-only 测试",
            "P5-Q3: A股 / ETF provider real-provider minimal gated adapter",
            "P5-Q4: A股 / ETF provider 本地手动试跑脚本",
            "P5-R: 场外基金真实净值 provider 接入评估",
        ],
    }
    validate_cn_quote_provider_evaluation(evaluation)
    return evaluation


def validate_cn_quote_provider_evaluation(evaluation: dict[str, Any]) -> list[str]:
    if evaluation.get("status") != "evaluation_only":
        raise ValueError("evaluation must remain evaluation_only")
    validate_provider_registry(evaluation.get("registry", {}))
    required = {"provider_safety", "field_mapping", "timeout", "retry", "cache_policy", "source_metadata"}
    if not required.issubset(set(evaluation.get("preflight_checks", []))):
        raise ValueError("missing required preflight checks")
    return []


def render_provider_registry_markdown(registry: dict[str, Any]) -> str:
    validate_provider_registry(registry)
    lines = [
        "# Provider Registry 说明",
        "",
        "> 本 registry 仅登记候选数据源，不代表已经接入或验证真实 provider。",
        "",
        "| Provider | 类型 | 市场 | 资产 | 状态 | 默认启用 | 网络 | 仓库写入 | 风险 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in registry["providers"]:
        lines.append(
            "| {display} (`{name}`) | {ptype} | {markets} | {assets} | {status} | {enabled} | {network} | {repo} | {risk} |".format(
                display=item["display_name"],
                name=item["provider_name"],
                ptype=item["provider_type"],
                markets=", ".join(item["markets"]),
                assets=", ".join(item["asset_types"]),
                status=item["status"],
                enabled=str(item["default_enabled"]).lower(),
                network=str(item["network_required"]).lower(),
                repo=str(item["allow_commit_to_repo"]).lower(),
                risk=item["risk_level"],
            )
        )
    lines.extend([
        "",
        "真实 provider 默认关闭，必须显式配置网络开关和 provider 配置后，才允许进入后续 dry-run / local_only 阶段。",
        "字段映射仅记录统一 QuoteResult 计划，不包含 provider 原始返回样本或真实行情值。",
        "失败兜底统一标记 provider_timeout、provider_error、rate_limited、invalid_response、stale_data、conflict 或 unsupported。",
    ])
    return "\n".join(lines) + "\n"
