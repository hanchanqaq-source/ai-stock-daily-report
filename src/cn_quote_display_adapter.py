"""Safe local display adapter for audited CN A-share / ETF quote results.

This module does not fetch providers, read user config, or write files. It only
converts QuoteResult-like mappings plus audit output into page-display models.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from src.cn_quote_result_audit import QUOTE_VALUE_FIELDS, REDACTED, audit_cn_quote_result, scan_quote_result_for_sensitive_fields

BLOCKED = "<blocked>"
DISPLAY_ALLOWED_STATUSES = {"passed", "passed_with_warnings"}
BLOCKED_AUDIT_STATUSES = {"failed", "blocked"}
UNAVAILABLE_DATA_STATUSES = {"provider_error", "provider_timeout", "invalid_response", "stale_data", "conflict", "unsupported", "invalid_request", "provider_policy_blocked", "disabled_by_default"}
DISCLAIMER = "本展示模型仅用于本地页面查看，不会保存真实行情到仓库。"
LOCAL_REAL_WARNING = "真实行情值仅允许本地展示，不得提交到 public 仓库。"
BLOCKED_WARNING = "审计未通过，页面不显示真实行情值。"


def build_cn_quote_display_policy() -> dict[str, Any]:
    return {
        "policy_name": "cn_quote_display_policy",
        "market": "CN",
        "default_display_mode": "redacted",
        "allow_real_values_on_local_page": False,
        "requires_audit_passed": True,
        "allowed_audit_statuses": ["passed", "passed_with_warnings"],
        "blocked_audit_statuses": ["failed", "blocked"],
        "redact_by_default": True,
        "allow_commit_to_repo": False,
        "require_commit_safe_false_for_real_data": True,
        "require_cache_scope_local_only": True,
        "require_checked_at": True,
        "require_source_status": True,
        "forbid_secret_output": True,
    }


def validate_cn_quote_display_policy(policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if policy.get("policy_name") != "cn_quote_display_policy":
        errors.append("policy_name must be cn_quote_display_policy")
    if policy.get("default_display_mode") != "redacted":
        errors.append("default_display_mode must be redacted")
    if policy.get("allow_real_values_on_local_page") is not False and not isinstance(policy.get("allow_real_values_on_local_page"), bool):
        errors.append("allow_real_values_on_local_page must be boolean")
    if policy.get("redact_by_default") is not True:
        errors.append("redact_by_default must be true")
    if policy.get("allow_commit_to_repo") is not False:
        errors.append("allow_commit_to_repo must be false")
    if set(policy.get("allowed_audit_statuses") or []) != DISPLAY_ALLOWED_STATUSES:
        errors.append("allowed_audit_statuses must include passed and passed_with_warnings only")
    return errors


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _source(result: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(result.get("source"))


def _checks(result: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(result.get("provider_checks"))


def _provider(result: Mapping[str, Any], audit: Mapping[str, Any] | None = None) -> str:
    audit = audit or {}
    return str(audit.get("provider") or result.get("provider") or result.get("provider_name") or _source(result).get("provider") or "")


def extract_quote_source_metadata(result: Mapping[str, Any]) -> dict[str, Any]:
    source = _source(result)
    return {
        "provider": result.get("provider") or result.get("provider_name") or source.get("provider"),
        "source_status": result.get("source_status") or source.get("source_status"),
        "checked_at": result.get("checked_at") or source.get("checked_at"),
    }


def is_audit_display_allowed(audit: Mapping[str, Any]) -> bool:
    return audit.get("audit_status") in DISPLAY_ALLOWED_STATUSES and audit.get("display_safe") is True and not audit.get("contains_secret")


def _has_real(result: Mapping[str, Any], audit: Mapping[str, Any]) -> bool:
    return bool(audit.get("has_real_market_data") or result.get("has_real_market_data") is True or result.get("data_mode") == "real_provider")


def _cache_scope(result: Mapping[str, Any], audit: Mapping[str, Any]) -> Any:
    return audit.get("cache_scope") or _checks(result).get("cache_scope") or result.get("cache_scope")


def _real_display_issues(result: Mapping[str, Any], audit: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    metadata = extract_quote_source_metadata(result)
    issues: list[str] = []
    if policy.get("allow_real_values_on_local_page") is not True:
        issues.append("policy_disallows_real_values")
    if not is_audit_display_allowed(audit):
        issues.append(f"audit_status={audit.get('audit_status')}")
    if audit.get("commit_safe") is not False and _has_real(result, audit):
        issues.append("real_market_data_commit_safe_must_be_false")
    if _cache_scope(result, audit) != "local_only":
        issues.append("cache_scope_must_be_local_only")
    if not metadata.get("checked_at"):
        issues.append("missing_checked_at")
    if not metadata.get("source_status"):
        issues.append("missing_source_status")
    if audit.get("contains_secret") or scan_quote_result_for_sensitive_fields(result):
        issues.append("sensitive_field_detected")
    return issues


def should_redact_for_display(audit: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
    return policy.get("redact_by_default") is True or not policy.get("allow_real_values_on_local_page") or not is_audit_display_allowed(audit)


def redact_quote_for_display(quote: Mapping[str, Any]) -> dict[str, Any]:
    return {field: REDACTED for field in QUOTE_VALUE_FIELDS if field in quote or field in QUOTE_VALUE_FIELDS}


def _safe_issue(issue: Any) -> str:
    text = str(issue)
    lowered = text.lower()
    if any(secret in lowered for secret in ("token", "api_key", "apikey", "webhook", "authorization", "bearer", "cookie", "secret", "password")):
        return "sensitive_field_detected"
    return text


def _base_model(result: Mapping[str, Any], audit: Mapping[str, Any]) -> dict[str, Any]:
    metadata = extract_quote_source_metadata(result)
    return {
        "asset_id": result.get("asset_id"),
        "code": result.get("code") or result.get("symbol"),
        "name": result.get("name"),
        "type": result.get("type"),
        "market": result.get("market") or audit.get("market"),
        "provider": _provider(result, audit),
        "data_status": result.get("data_status"),
        "audit_status": audit.get("audit_status"),
        "has_real_market_data": _has_real(result, audit),
        "commit_safe": False if _has_real(result, audit) else bool(audit.get("commit_safe", False)),
        "display_safe": bool(audit.get("display_safe", False)),
        "freshness_status": audit.get("freshness_status"),
        "source": metadata,
        "badges": [],
        "warnings": [],
        "issues": [_safe_issue(issue) for issue in (audit.get("issues") or [])],
        "disclaimer": DISCLAIMER,
    }


def build_quote_display_warning(message: str) -> str:
    return message


def build_blocked_quote_display(result: Mapping[str, Any], audit: Mapping[str, Any], reason: str) -> dict[str, Any]:
    model = _base_model(result, audit)
    model.update({"display_status": "blocked", "display_mode": "blocked", "quote_display": {}, "badges": ["展示已阻断", "禁止提交仓库"]})
    model["issues"] = list(dict.fromkeys([*model.get("issues", []), reason]))
    model["warnings"] = [BLOCKED_WARNING]
    model["commit_safe"] = False
    return model


def build_redacted_quote_display(result: Mapping[str, Any], audit: Mapping[str, Any]) -> dict[str, Any]:
    model = _base_model(result, audit)
    data_status = str(result.get("data_status") or "")
    unavailable = data_status in UNAVAILABLE_DATA_STATUSES
    model.update({
        "display_status": "unavailable" if unavailable else "displayable",
        "display_mode": "unavailable" if unavailable else "redacted",
        "quote_display": {} if unavailable else redact_quote_for_display(_mapping(result.get("quote"))),
        "badges": ["本地真实数据" if model["has_real_market_data"] else "本地展示模型", "已审计", "禁止提交仓库"],
        "warnings": [LOCAL_REAL_WARNING, "默认展示脱敏结果。"],
    })
    model["commit_safe"] = False if model["has_real_market_data"] else model["commit_safe"]
    return model


def build_local_real_quote_display(result: Mapping[str, Any], audit: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    issues = _real_display_issues(result, audit, policy)
    if issues:
        return build_blocked_quote_display(result, audit, issues[0])
    model = _base_model(result, audit)
    quote = _mapping(result.get("quote"))
    model.update({
        "display_status": "displayable",
        "display_mode": "local_real_allowed",
        "quote_display": {field: quote.get(field) for field in QUOTE_VALUE_FIELDS if field in quote},
        "badges": ["本地真实数据", "已审计", "禁止提交仓库"],
        "warnings": [LOCAL_REAL_WARNING],
        "commit_safe": False,
        "display_safe": True,
    })
    return model


def build_cn_quote_display_model(result: Mapping[str, Any], audit: Mapping[str, Any] | None = None, policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    active_policy = {**build_cn_quote_display_policy(), **dict(policy or {})}
    active_audit = dict(audit or audit_cn_quote_result(result))
    if active_audit.get("audit_status") in BLOCKED_AUDIT_STATUSES or active_audit.get("contains_secret"):
        return build_blocked_quote_display(result, active_audit, f"audit_status={active_audit.get('audit_status')}")
    if active_policy.get("allow_real_values_on_local_page") is True and is_audit_display_allowed(active_audit):
        real_issues = _real_display_issues(result, active_audit, active_policy)
        if real_issues:
            return build_blocked_quote_display(result, active_audit, real_issues[0])
        return build_local_real_quote_display(result, active_audit, active_policy)
    return build_redacted_quote_display(result, active_audit)


def build_cn_quote_display_models(results: Sequence[Mapping[str, Any]], audits: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None, policy: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        audit = None
        if isinstance(audits, Sequence) and not isinstance(audits, (str, bytes, Mapping)):
            audit = audits[index] if index < len(audits) else None
        elif isinstance(audits, Mapping):
            audit = audits.get(str(result.get("asset_id") or result.get("code") or index))
        models.append(build_cn_quote_display_model(result, audit, policy))
    return models


def validate_cn_quote_display_model(model: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if model.get("display_mode") not in {"redacted", "local_real_allowed", "blocked", "unavailable"}:
        errors.append("unsupported display_mode")
    if model.get("has_real_market_data") is True and model.get("commit_safe") is not False:
        errors.append("real market data display model must be commit_safe=false")
    if model.get("display_mode") in {"blocked", "unavailable"} and any(value not in {BLOCKED, REDACTED, None} for value in _mapping(model.get("quote_display")).values()):
        errors.append("blocked or unavailable display must not expose quote values")
    rendered = repr(model).lower()
    if any(secret in rendered for secret in ("token", "api_key", "webhook", "authorization", "bearer", "cookie")):
        errors.append("display model must not contain secret field names")
    return errors


def validate_cn_quote_display_models(models: Sequence[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, model in enumerate(models):
        errors.extend([f"models[{index}]: {error}" for error in validate_cn_quote_display_model(model)])
    return errors


def summarize_cn_quote_display_models(models: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    mode_counts: dict[str, int] = {}
    for model in models:
        counts[str(model.get("display_status") or "unknown")] = counts.get(str(model.get("display_status") or "unknown"), 0) + 1
        mode_counts[str(model.get("display_mode") or "unknown")] = mode_counts.get(str(model.get("display_mode") or "unknown"), 0) + 1
    return {"summary_type": "cn_quote_display_summary", "total": len(models), "status_counts": counts, "mode_counts": mode_counts, "commit_safe": False, "models": list(models)}


def _markdown_for_model(model: Mapping[str, Any], index: int | None = None) -> list[str]:
    quote = _mapping(model.get("quote_display"))
    source = _mapping(model.get("source"))
    heading = "## 1. 展示概览" if index is None else f"## {index}. 展示概览"
    return [
        heading,
        "",
        f"- display_status：{model.get('display_status', '')}",
        f"- display_mode：{model.get('display_mode', '')}",
        f"- provider：{model.get('provider', '')}",
        f"- market：{model.get('market', '')}",
        f"- 是否真实行情：{str(model.get('has_real_market_data', False)).lower()}",
        f"- 是否可提交仓库：{str(model.get('commit_safe', False)).lower()}",
        "",
        "## 2. 行情展示字段",
        "",
        f"- 最新价：{quote.get('last_price', REDACTED if model.get('display_mode') == 'redacted' else '')}",
        f"- 涨跌幅：{quote.get('change_pct', REDACTED if model.get('display_mode') == 'redacted' else '')}",
        f"- 成交额：{quote.get('turnover', REDACTED if model.get('display_mode') == 'redacted' else '')}",
        "",
        "## 3. 来源信息",
        "",
        f"- provider：{source.get('provider', model.get('provider', ''))}",
        f"- source_status：{source.get('source_status', '')}",
        f"- checked_at：{source.get('checked_at', '')}",
        f"- freshness_status：{model.get('freshness_status', '')}",
    ]


def render_cn_quote_display_markdown(model_or_models: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> str:
    if isinstance(model_or_models, Mapping) and model_or_models.get("summary_type") == "cn_quote_display_summary":
        models = list(model_or_models.get("models") or [])
    elif isinstance(model_or_models, Mapping):
        models = [model_or_models]
    else:
        models = list(model_or_models)
    lines = ["# A股 / ETF Provider 页面展示安全适配 Demo", ""]
    if not models:
        lines.extend(["## 1. 展示概览", "", "- display_status：empty"])
    else:
        for index, model in enumerate(models, 1):
            lines.extend(_markdown_for_model(model, None if len(models) == 1 else index))
            lines.append("")
    lines.extend([
        "## 4. 安全说明",
        "",
        "- 默认展示脱敏结果。",
        "- 真实行情值仅允许本地页面显式开启后展示。",
        "- 真实行情值不得提交到 public 仓库。",
        "- 审计未通过时页面不显示真实行情值。",
    ])
    return "\n".join(lines).replace("Token", "T***n").replace("API Key", "A*** K***").replace("Webhook", "W***hook") + "\n"
