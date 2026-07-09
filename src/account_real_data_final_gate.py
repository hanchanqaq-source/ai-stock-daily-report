"""Final safety gate before unified real data enters account page models.

The gate consumes the already-built ``account_real_data_unified_summary`` model
and performs one last structural safety pass.  It never calls providers, never
reads user config, never writes files, and always builds redacted / blocked page
payloads by default.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

GATE_NAME = "account_real_data_final_gate"
POLICY_NAME = "account_real_data_final_gate_policy"
FUND_ESTIMATE_DISCLAIMER = "盘中估算仅供观察，最终以基金公司公布净值为准。"
DEFAULT_WARNING = "本页面 payload 默认脱敏，不保存真实行情或真实基金净值。"
PAGE_DISCLAIMER = "本页面仅用于个人观察和记录，不构成交易建议。"
RESULT_DISCLAIMER = "本结果仅用于个人观察和记录，不构成交易建议。"

STOCK_FIELDS = {"最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "checked_at", "source_status"}
FUND_FIELDS = {"单位净值", "累计净值", "净值日期", "日涨跌幅", "估算净值", "估算涨跌", "估算更新时间", "checked_at", "source_status"}
FUND_REALTIME_WORDS = ("实时价格", "实时涨跌", "实时行情", "盘中实时净值")
SAFE_PERSONAL_KEY_EXCEPTIONS = {"weight_level", "balanced", "source_status", "allow_commit_to_repo"}


def build_account_real_data_final_gate_policy() -> dict[str, Any]:
    return {
        "policy_name": POLICY_NAME,
        "default_decision": "block",
        "allow_redacted_page_payload": True,
        "allow_local_real_display": False,
        "require_all_results_audited": True,
        "require_all_display_models_checked": True,
        "require_default_redacted": True,
        "allow_real_data_written_to_repo": False,
        "forbid_secrets": True,
        "forbid_personal_money_fields": True,
        "forbid_fund_realtime_wording": True,
        "require_fund_estimate_disclaimer": True,
        "require_stock_fund_field_boundary": True,
        "allowed_display_modes": ["redacted", "blocked", "unavailable"],
        "local_allowed_display_modes": ["redacted", "blocked", "unavailable", "local_real_allowed"],
        "forbidden_secret_fields": ["token", "api_key", "apikey", "secret", "password", "webhook", "cookie", "authorization", "bearer", "client_secret", "private_key"],
        "forbidden_personal_money_fields": ["amount", "cost_price", "cost", "position_value", "account_value", "balance", "real_amount", "real_cost"],
    }


def validate_account_real_data_final_gate_policy(policy: Mapping[str, Any]) -> bool:
    required = build_account_real_data_final_gate_policy()
    return all(key in policy for key in required) and policy.get("default_decision") == "block"


def _safety(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    return summary.get("safety_summary") or {}


def _walk(value: Any, path: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield child_path, str(key), child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _contains_text(value: Any, words: Iterable[str]) -> bool:
    rendered = str(value)
    return any(word in rendered for word in words)


def _issue(code: str, message: str, severity: str = "blocker") -> dict[str, str]:
    return {"code": code, "message": message, "severity": severity}


def check_unified_summary_audit_status(summary: Mapping[str, Any]) -> dict[str, Any]:
    ok = _safety(summary).get("all_results_audited") is True
    return {"ok": ok, "issues": [] if ok else [_issue("audit_not_complete", "统一汇总结果尚未全部审计。")], "warnings": []}


def check_unified_summary_display_status(summary: Mapping[str, Any]) -> dict[str, Any]:
    safety = _safety(summary)
    issues: list[dict[str, str]] = []
    warnings: list[str] = []
    if safety.get("all_display_models_checked") is not True:
        issues.append(_issue("display_not_checked", "展示模型尚未全部经过安全适配。"))
    if safety.get("default_redacted") is not True:
        msg = "统一汇总默认展示模式不是 redacted。"
        if summary.get("has_real_market_data") or summary.get("has_real_nav_data"):
            issues.append(_issue("real_data_not_redacted", msg))
        else:
            warnings.append(msg)
    return {"ok": not issues, "issues": issues, "warnings": warnings}


def check_unified_summary_repository_safety(summary: Mapping[str, Any]) -> dict[str, Any]:
    written = _safety(summary).get("real_data_written_to_repo") is True or summary.get("commit_safe") is True
    return {"ok": not written, "issues": [] if not written else [_issue("real_data_repo_write", "真实数据可能写入 public repo。")], "warnings": []}


def check_unified_summary_secret_safety(summary: Mapping[str, Any]) -> dict[str, Any]:
    policy = build_account_real_data_final_gate_policy()
    forbidden = {field.lower() for field in policy["forbidden_secret_fields"]}
    issues = []
    if _safety(summary).get("secrets_detected") is True:
        issues.append(_issue("secret_flag_detected", "统一汇总标记发现 secret。"))
    for path, key, _value in _walk(summary):
        if key.lower() in forbidden:
            issues.append(_issue("secret_field_detected", f"发现敏感字段：{path}"))
            break
    return {"ok": not issues, "issues": issues, "warnings": []}


def check_unified_summary_personal_money_fields(summary: Mapping[str, Any]) -> dict[str, Any]:
    policy = build_account_real_data_final_gate_policy()
    forbidden = {field.lower() for field in policy["forbidden_personal_money_fields"]}
    issues = []
    for path, key, _value in _walk(summary):
        lowered = key.lower()
        if lowered in SAFE_PERSONAL_KEY_EXCEPTIONS:
            continue
        if lowered in forbidden:
            issues.append(_issue("personal_money_field_detected", f"发现真实金额 / 成本价 / 账户资产字段：{path}"))
            break
    return {"ok": not issues, "issues": issues, "warnings": []}


def check_unified_summary_fund_wording(summary: Mapping[str, Any]) -> dict[str, Any]:
    sections = summary.get("sections") or {}
    fund = sections.get("fund_nav") or {}
    issues: list[dict[str, str]] = []
    warnings: list[str] = []
    if _contains_text(fund.get("display_models") or [], FUND_REALTIME_WORDS):
        issues.append(_issue("fund_realtime_wording", "场外基金正式展示字段包含实时价格 / 实时涨跌等措辞。", "high"))
    elif _contains_text(fund, FUND_REALTIME_WORDS):
        warnings.append("场外基金区域包含实时价格 / 实时涨跌等措辞，请改为净值或估算净值表达。")
    if FUND_ESTIMATE_DISCLAIMER not in str(fund) and FUND_ESTIMATE_DISCLAIMER not in str(summary.get("warnings") or []):
        warnings.append(FUND_ESTIMATE_DISCLAIMER)
    return {"ok": not issues, "issues": issues, "warnings": warnings}


def check_unified_summary_field_boundaries(summary: Mapping[str, Any]) -> dict[str, Any]:
    sections = summary.get("sections") or {}
    stock_boundary = set(sections.get("stock_etf", {}).get("field_boundary") or [])
    fund_boundary = set(sections.get("fund_nav", {}).get("field_boundary") or [])
    issues = []
    mixed_stock = sorted(stock_boundary & (FUND_FIELDS - {"checked_at", "source_status"}))
    mixed_fund = sorted(fund_boundary & (STOCK_FIELDS - {"checked_at", "source_status"}))
    if mixed_stock:
        issues.append(_issue("fund_fields_in_stock_section", f"股票 / ETF 区域混入基金字段：{', '.join(mixed_stock)}", "high"))
    if mixed_fund:
        issues.append(_issue("stock_fields_in_fund_section", f"场外基金区域混入股票行情字段：{', '.join(mixed_fund)}", "high"))
    return {"ok": not issues, "issues": issues, "warnings": []}


def summarize_final_gate_issues(issues: list[Mapping[str, Any]]) -> str:
    return "；".join(str(item.get("message") or item.get("code") or item) for item in issues)


def _sanitize(value: Any, policy: Mapping[str, Any]) -> Any:
    secret_keys = {k.lower() for k in policy["forbidden_secret_fields"]}
    money_keys = {k.lower() for k in policy["forbidden_personal_money_fields"]}
    value_keys = {"quote_display", "nav_display", "estimate_display", "raw_value", "real_value", "price", "nav", "change_pct", "turnover"}
    if isinstance(value, Mapping):
        cleaned = {}
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in secret_keys or lowered in money_keys or lowered in value_keys:
                continue
            cleaned[key] = _sanitize(child, policy)
        return cleaned
    if isinstance(value, list):
        return [_sanitize(item, policy) for item in value]
    return value


def redact_final_page_payload(payload: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    final_policy = dict(policy or build_account_real_data_final_gate_policy())
    redacted = _sanitize(deepcopy(dict(payload)), final_policy)
    redacted["display_mode"] = "redacted" if redacted.get("display_mode") != "blocked" else "blocked"
    redacted["can_write_to_public_repo"] = False
    return redacted


def build_allowed_final_page_payload(summary: Mapping[str, Any], gate_result: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    sections = summary.get("sections") or {}
    payload = {
        "account_id": summary.get("account_id") or "demo_account",
        "account_name": summary.get("account_name") or "示例账户",
        "payload_status": "safe_for_account_page",
        "display_mode": "redacted",
        "data_mode": summary.get("data_mode") or "dry_run",
        "can_write_to_public_repo": False,
        "sections": {
            "stock_etf": {"enabled": bool((sections.get("stock_etf") or {}).get("enabled", True)), "display_models": (sections.get("stock_etf") or {}).get("display_models") or []},
            "fund_nav": {"enabled": bool((sections.get("fund_nav") or {}).get("enabled", True)), "display_models": (sections.get("fund_nav") or {}).get("display_models") or []},
        },
        "safety_badges": ["已审计", "默认脱敏", "禁止写入真实数据"],
        "warnings": list(gate_result.get("warnings") or []),
        "disclaimer": PAGE_DISCLAIMER,
    }
    return redact_final_page_payload(payload, policy)


def build_blocked_final_page_payload(summary: Mapping[str, Any], gate_result: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {"payload_status": "blocked", "display_mode": "blocked", "sections": {}, "issues": list(gate_result.get("issues") or []), "warnings": ["最终安全闸门未通过，页面不显示真实数据。", reason]}


def run_account_real_data_final_gate(summary: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    final_policy = dict(policy or build_account_real_data_final_gate_policy())
    validate_account_real_data_final_gate_policy(final_policy)
    checks = [check_unified_summary_audit_status, check_unified_summary_display_status, check_unified_summary_repository_safety, check_unified_summary_secret_safety, check_unified_summary_personal_money_fields, check_unified_summary_fund_wording, check_unified_summary_field_boundaries]
    issues: list[dict[str, str]] = []
    warnings: list[str] = [DEFAULT_WARNING]
    for check in checks:
        checked = check(summary)
        issues.extend(checked.get("issues") or [])
        warnings.extend(checked.get("warnings") or [])
    safety = _safety(summary)
    blocked = any(item.get("severity") == "blocker" for item in issues) or any(item.get("code") in {"fund_fields_in_stock_section", "stock_fields_in_fund_section", "fund_realtime_wording"} for item in issues)
    decision = "blocked" if blocked else ("allowed_with_warnings" if issues or len(warnings) > 1 else "allowed")
    severity = "blocker" if decision == "blocked" else ("medium" if decision == "allowed_with_warnings" else "info")
    base_result = {
        "gate_name": GATE_NAME,
        "decision": decision,
        "severity": severity,
        "page_payload_mode": "blocked" if decision == "blocked" else "redacted",
        "can_enter_account_page_model": decision != "blocked",
        "can_write_to_public_repo": False,
        "has_real_market_data": summary.get("has_real_market_data") is True,
        "has_real_nav_data": summary.get("has_real_nav_data") is True,
        "all_results_audited": safety.get("all_results_audited") is True,
        "all_display_models_checked": safety.get("all_display_models_checked") is True,
        "default_redacted": safety.get("default_redacted") is True,
        "secrets_detected": bool(safety.get("secrets_detected")) or any(i.get("code", "").startswith("secret") for i in issues),
        "personal_money_fields_detected": any(i.get("code") == "personal_money_field_detected" for i in issues),
        "fund_wording_ok": not any(i.get("code") == "fund_realtime_wording" for i in issues),
        "fund_estimate_disclaimer_ok": not any(FUND_ESTIMATE_DISCLAIMER in w for w in warnings[1:]),
        "field_boundary_ok": not any(i.get("code") in {"fund_fields_in_stock_section", "stock_fields_in_fund_section"} for i in issues),
        "issues": issues,
        "warnings": list(dict.fromkeys(warnings)),
        "disclaimer": RESULT_DISCLAIMER,
    }
    if decision == "blocked":
        base_result["final_page_payload"] = build_blocked_final_page_payload(summary, base_result, summarize_final_gate_issues(issues) or "blocked")
    else:
        base_result["final_page_payload"] = build_allowed_final_page_payload(summary, base_result, final_policy)
    validate_account_real_data_final_gate_result(base_result)
    return base_result


def validate_account_real_data_final_gate_result(result: Mapping[str, Any]) -> bool:
    if result.get("decision") not in {"allowed", "allowed_with_warnings", "blocked"}:
        return False
    payload = result.get("final_page_payload") or {}
    if result.get("decision") == "blocked" and payload.get("sections"):
        return False
    return result.get("can_write_to_public_repo") is False and payload.get("can_write_to_public_repo", False) is False


def render_account_real_data_final_gate_markdown(gate_result: Mapping[str, Any]) -> str:
    payload = gate_result.get("final_page_payload") or {}
    lines = [
        "# 账户真实数据最终安全闸门 Demo", "", "## 1. 闸门结果",
        f"- decision：{gate_result.get('decision')}", f"- severity：{gate_result.get('severity')}", f"- can_enter_account_page_model：{gate_result.get('can_enter_account_page_model') is True}", f"- can_write_to_public_repo：{gate_result.get('can_write_to_public_repo') is True}", "", "## 2. 检查项",
        f"- 是否全部审计：{gate_result.get('all_results_audited') is True}", f"- 是否全部展示适配：{gate_result.get('all_display_models_checked') is True}", f"- 是否默认脱敏：{gate_result.get('default_redacted') is True}", f"- 是否发现 secret：{gate_result.get('secrets_detected') is True}", f"- 是否发现真实金额 / 成本价：{gate_result.get('personal_money_fields_detected') is True}", f"- 场外基金措辞是否合规：{gate_result.get('fund_wording_ok') is True}", "", "## 3. 页面 Payload",
        f"- payload_status：{payload.get('payload_status')}", f"- display_mode：{payload.get('display_mode')}", f"- sections：{list((payload.get('sections') or {}).keys())}", "", "## 4. 数据说明",
        "- 最终安全闸门通过后，数据才允许进入账户页面模型。", "- 默认展示脱敏结果，不保存真实行情或真实基金净值到仓库。", "- 场外基金不支持真正实时价格。", f"- {FUND_ESTIMATE_DISCLAIMER}", "- 本页面只用于个人观察和记录，不构成交易建议。",
    ]
    return "\n".join(lines) + "\n"
