"""Audit helpers for off-exchange fund NAV provider results.

The audit module is intentionally local and side-effect free: it never fetches
provider data, never reads user configuration, and never writes result files.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

ESTIMATE_DISCLAIMER = "盘中估算仅供观察，最终以基金公司公布净值为准。"
REAL_NAV_REPO_WARNING = "真实基金净值仅允许本地内存使用，不得提交到 public 仓库。"
REDACTION_WARNING = "审计输出会脱敏单位净值、累计净值、估算净值和涨跌幅等字段。"
CI_NO_REAL_NAV_WARNING = "CI 测试不会请求真实基金净值。"
REDACTED = "<redacted>"
NAV_VALUE_FIELDS = ("unit_nav", "accumulated_nav", "daily_change_pct")
ESTIMATE_VALUE_FIELDS = ("estimated_nav", "estimated_change_pct", "estimated_change_amount")
SECRET_FIELDS = (
    "token", "api_key", "apikey", "secret", "password", "webhook", "cookie",
    "authorization", "bearer", "client_secret", "private_key",
)
VALID_STATUSES = {"passed", "passed_with_warnings", "failed", "blocked"}
VALID_SEVERITIES = {"info", "low", "medium", "high", "blocker"}


def build_fund_nav_audit_policy() -> dict[str, Any]:
    return {
        "policy_name": "fund_nav_result_audit_policy",
        "market": "CN",
        "data_kinds": ["daily_nav", "estimated_nav"],
        "allow_real_values_in_memory": True,
        "allow_real_values_in_repo": False,
        "allow_commit_to_repo_required": False,
        "required_source_fields": ["provider", "source_status", "checked_at"],
        "required_provider_checks": ["allow_commit_to_repo", "cache_scope"],
        "allowed_cache_scopes": ["local_only"],
        "daily_nav_max_age_seconds": 86400,
        "estimated_nav_max_age_seconds": 300,
        "redact_real_nav_values": True,
        "requires_estimate_disclaimer": True,
        "forbidden_secret_fields": list(SECRET_FIELDS),
    }


def validate_fund_nav_audit_policy(policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if policy.get("allow_real_values_in_repo") is not False:
        errors.append("allow_real_values_in_repo must be false")
    if policy.get("redact_real_nav_values") is not True:
        errors.append("redact_real_nav_values must be true")
    if "local_only" not in (policy.get("allowed_cache_scopes") or []):
        errors.append("allowed_cache_scopes must include local_only")
    if int(policy.get("estimated_nav_max_age_seconds", 0)) >= int(policy.get("daily_nav_max_age_seconds", 0)):
        errors.append("estimated_nav_max_age_seconds must be shorter than daily_nav_max_age_seconds")
    return errors


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(value or {})


def _lower_key(key: Any) -> str:
    return str(key).lower().replace("-", "_")


def _is_secret_key(key: Any, policy: Mapping[str, Any] | None = None) -> bool:
    forbidden = tuple((policy or build_fund_nav_audit_policy()).get("forbidden_secret_fields") or SECRET_FIELDS)
    normalized = _lower_key(key)
    return any(secret in normalized for secret in forbidden)


def _redact_nested(value: Any, policy: Mapping[str, Any] | None = None) -> Any:
    if isinstance(value, Mapping):
        return {str(k): (REDACTED if _is_secret_key(k, policy) else _redact_nested(v, policy)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_nested(item, policy) for item in value]
    return value


def redact_fund_nav_result_for_audit(result: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    redacted = _redact_nested(deepcopy(_as_dict(result)), policy)
    nav = dict(redacted.get("nav") or {})
    for field in NAV_VALUE_FIELDS:
        if field in nav and nav.get(field) is not None:
            nav[field] = REDACTED
    redacted["nav"] = nav
    estimate = dict(redacted.get("estimate") or {})
    for field in ESTIMATE_VALUE_FIELDS:
        if field in estimate and estimate.get(field) is not None:
            estimate[field] = REDACTED
    redacted["estimate"] = estimate
    return redacted


def scan_fund_nav_result_for_sensitive_fields(result: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                next_path = f"{path}.{key}" if path else str(key)
                if _is_secret_key(key, policy):
                    found.append({"field": next_path, "code": "secret_field_present"})
                walk(nested, next_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
    walk(_as_dict(result), "")
    return found


def is_real_nav_value_present(result: Mapping[str, Any]) -> bool:
    data = _as_dict(result)
    nav = data.get("nav") or {}
    estimate = data.get("estimate") or {}
    return any(nav.get(field) is not None for field in NAV_VALUE_FIELDS) or any(estimate.get(field) is not None for field in ESTIMATE_VALUE_FIELDS)


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def check_fund_nav_source_metadata(result: Mapping[str, Any]) -> dict[str, Any]:
    data = _as_dict(result); source = data.get("source") or {}
    issues = [f"missing_source_{field}" for field in ("provider", "source_status", "checked_at") if not source.get(field)]
    return {"ok": not issues, "issues": issues, "provider": source.get("provider") or data.get("provider_name") or data.get("provider"), "source_status": source.get("source_status"), "checked_at": source.get("checked_at")}


def check_fund_nav_result_freshness(result: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> dict[str, str]:
    policy = dict(policy or build_fund_nav_audit_policy())
    data = _as_dict(result); source = data.get("source") or {}; checked_at = source.get("checked_at")
    nav = data.get("nav") or {}; estimate = data.get("estimate") or {}
    if not checked_at:
        daily = "missing_checked_at"
        estimated = "missing_checked_at" if estimate else "unknown"
        return {"daily_nav_freshness_status": daily, "estimated_nav_freshness_status": estimated}
    checked = _parse_time(checked_at)
    if checked is None:
        return {"daily_nav_freshness_status": "unknown", "estimated_nav_freshness_status": "unknown"}
    age = (datetime.now(timezone.utc) - checked.astimezone(timezone.utc)).total_seconds()
    daily = "missing_nav_date" if nav and not nav.get("nav_date") else ("stale" if age > int(policy["daily_nav_max_age_seconds"]) else "fresh")
    if not estimate or str(data.get("data_status") or "") == "estimate_unavailable":
        estimated = "estimate_unavailable" if str(data.get("data_status") or "") == "estimate_unavailable" else "unknown"
    elif not estimate.get("estimate_time"):
        estimated = "missing_estimate_time"
    else:
        estimated = "stale" if age > int(policy["estimated_nav_max_age_seconds"]) else "fresh"
    return {"daily_nav_freshness_status": daily, "estimated_nav_freshness_status": estimated}


def check_fund_nav_result_repository_safety(result: Mapping[str, Any]) -> dict[str, Any]:
    data = _as_dict(result); checks = data.get("provider_checks") or {}
    has_real = bool(data.get("has_real_nav_data")) or data.get("data_mode") == "real_provider"
    contains_values = is_real_nav_value_present(data)
    commit_safe = not has_real and data.get("data_mode") in {"fixture_only", "model_only", "dry_run", "local_only_fixture"}
    issues: list[str] = [] ; warnings: list[str] = []
    if checks.get("allow_commit_to_repo") is True and (has_real or contains_values):
        issues.append("real_fund_nav_result_must_not_be_committed")
    cache_scope = checks.get("cache_scope") or data.get("cache_scope")
    if cache_scope != "local_only" and has_real:
        warnings.append("cache_scope_must_be_local_only")
    return {"commit_safe": bool(commit_safe), "allow_commit_to_repo": checks.get("allow_commit_to_repo", data.get("allow_commit_to_repo")), "cache_scope": cache_scope, "issues": issues, "warnings": warnings}


def check_fund_nav_result_data_status(result: Mapping[str, Any]) -> dict[str, Any]:
    status = str(_as_dict(result).get("data_status") or "")
    ok = bool(status)
    return {"ok": ok, "issues": [] if ok else ["missing_data_status"], "data_status": status}


def build_fund_nav_audit_warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def normalize_audit_severity(severity: str) -> str:
    return severity if severity in VALID_SEVERITIES else "info"


def audit_fund_nav_result(result: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    policy = dict(policy or build_fund_nav_audit_policy())
    validate_fund_nav_audit_policy(policy)
    data = _as_dict(result); source = check_fund_nav_source_metadata(data); freshness = check_fund_nav_result_freshness(data, policy)
    repo = check_fund_nav_result_repository_safety(data); status = check_fund_nav_result_data_status(data)
    secrets = scan_fund_nav_result_for_sensitive_fields(data, policy)
    issues = source["issues"] + repo["issues"] + status["issues"]
    warnings = [REAL_NAV_REPO_WARNING, REDACTION_WARNING]
    warnings.extend(repo["warnings"])
    if any(v == "stale" for v in freshness.values()):
        warnings.append("stale_fund_nav_data_must_not_be_marked_fresh")
    estimate = data.get("estimate") or {}
    disclaimer_text = " ".join(str(x) for x in (data.get("warnings") or [])) + " " + str(data.get("disclaimer") or "")
    if estimate and any(estimate.get(field) is not None for field in ESTIMATE_VALUE_FIELDS):
        if "最终以基金公司公布净值为准" not in disclaimer_text:
            warnings.append("estimated_nav_requires_final_company_nav_disclaimer")
        warnings.append(ESTIMATE_DISCLAIMER)
    if secrets:
        issues.extend(f"secret_field_present:{item['field']}" for item in secrets)
    severity = "blocker" if secrets or repo["issues"] else ("medium" if issues else ("low" if len(warnings) > 2 else "info"))
    audit_status = "blocked" if severity == "blocker" else ("failed" if issues else ("passed_with_warnings" if len(warnings) > 2 else "passed"))
    display_safe = audit_status != "blocked" and "stale" not in freshness.values()
    provider = source.get("provider") or data.get("provider_name") or data.get("provider")
    return {
        "asset_id": data.get("asset_id"), "code": data.get("code"), "type": data.get("type"), "market": data.get("market"), "provider": provider,
        "audit_status": audit_status, "severity": normalize_audit_severity(severity),
        "has_real_nav_data": bool(data.get("has_real_nav_data")), "contains_real_nav_values": is_real_nav_value_present(data),
        "real_values_redacted": True, "commit_safe": repo["commit_safe"], "display_safe": display_safe,
        "source_metadata_ok": source["ok"], **freshness, "cache_scope": repo["cache_scope"], "allow_commit_to_repo": repo["allow_commit_to_repo"],
        "secret_fields_found": [item["field"] for item in secrets], "issues": issues, "warnings": warnings,
        "redacted_result": redact_fund_nav_result_for_audit(data, policy),
    }


def audit_fund_nav_results(results: Sequence[Mapping[str, Any]], policy: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    return [audit_fund_nav_result(result, policy) for result in results]


def build_fund_nav_audit_summary(audit_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for audit in audit_results:
        key = str(audit.get("audit_status") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return {"summary_type": "fund_nav_result_audit_summary", "total": len(audit_results), "status_counts": counts, "audit_results": list(audit_results), "warnings": [REAL_NAV_REPO_WARNING, REDACTION_WARNING, ESTIMATE_DISCLAIMER, CI_NO_REAL_NAV_WARNING]}


def validate_fund_nav_audit_result(audit: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if audit.get("audit_status") not in VALID_STATUSES: errors.append("invalid audit_status")
    if audit.get("severity") not in VALID_SEVERITIES: errors.append("invalid severity")
    if audit.get("contains_real_nav_values") and audit.get("real_values_redacted") is not True: errors.append("real values must be redacted")
    if audit.get("has_real_nav_data") and audit.get("commit_safe") is True: errors.append("real fund NAV result cannot be commit_safe")
    return errors


def render_fund_nav_audit_markdown(audit_or_summary: Mapping[str, Any]) -> str:
    if audit_or_summary.get("summary_type") == "fund_nav_result_audit_summary":
        audit = (audit_or_summary.get("audit_results") or [{}])[0]
        counts = audit_or_summary.get("status_counts") or {}
    else:
        audit = audit_or_summary
        counts = {str(audit.get("audit_status") or "unknown"): 1}
    redacted = audit.get("redacted_result") or {}; source = redacted.get("source") or {}
    lines = [
        "# 场外基金净值 Provider 结果审计 Demo", "", "## 1. 审计概览",
        f"- audit_status：{audit.get('audit_status', '')}", f"- severity：{audit.get('severity', '')}", f"- provider：{audit.get('provider', '')}", f"- market：{audit.get('market', '')}",
        f"- 是否含真实基金净值：{str(audit.get('has_real_nav_data', False)).lower()}", f"- 是否可提交仓库：{str(audit.get('commit_safe', False)).lower()}", f"- 是否可本地展示：{str(audit.get('display_safe', False)).lower()}", f"- 状态统计：{counts}", "", "## 2. 来源检查",
        f"- provider：{source.get('provider') or audit.get('provider', '')}", f"- source_status：{source.get('source_status', '')}", f"- checked_at：{source.get('checked_at', '')}",
        f"- daily_nav_freshness_status：{audit.get('daily_nav_freshness_status', '')}", f"- estimated_nav_freshness_status：{audit.get('estimated_nav_freshness_status', '')}", "", "## 3. 安全检查",
        f"- allow_commit_to_repo：{str(audit.get('allow_commit_to_repo', False)).lower()}", f"- cache_scope：{audit.get('cache_scope', '')}", f"- 是否发现 secret：{str(bool(audit.get('secret_fields_found'))).lower()}", f"- 是否已脱敏：{str(audit.get('real_values_redacted', False)).lower()}", "", "## 4. 数据说明",
        REAL_NAV_REPO_WARNING, REDACTION_WARNING, ESTIMATE_DISCLAIMER, CI_NO_REAL_NAV_WARNING,
    ]
    return "\n".join(lines) + "\n"


def is_fund_nav_result_commit_safe(result: Mapping[str, Any]) -> bool:
    return check_fund_nav_result_repository_safety(result)["commit_safe"]
