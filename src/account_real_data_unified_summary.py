"""Unified safe account real-data summary adapter.

This module orchestrates the existing stock / ETF quote and off-exchange fund
NAV account integrations into one stable, redacted account-level model.  It does
not implement provider, audit, or display logic itself, and defaults to dry-run
provider modes so it does not request or persist real market / NAV values.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from src.account_cn_quote_provider_integration import (
    SUPPORTED_PROVIDER_MODES as STOCK_PROVIDER_MODES,
    build_account_cn_quote_provider_summary,
)
from src.account_fund_nav_provider_integration import (
    ESTIMATE_WARNING,
    SUPPORTED_PROVIDER_MODES as FUND_PROVIDER_MODES,
    build_account_fund_nav_provider_summary,
)
from src.cn_quote_display_adapter import build_cn_quote_display_policy
from src.fund_nav_display_adapter import build_fund_nav_display_policy

WARNING = "本阶段为统一真实数据汇总安全适配，不请求真实行情或真实基金净值。"
REDACTED_WARNING = "默认展示脱敏结果，不保存真实数据到仓库。"
FUND_NO_REALTIME_WARNING = "场外基金不支持真正实时价格。"
DISCLAIMER = "本汇总仅用于统一股票 / ETF / 基金数据展示模型，不构成交易建议。"
SECRET_WORDS = ("Token", "API Key", "Webhook")
BLOCKED_STATUSES = {"blocked", "failed"}


def _display_mode(display_policy: Mapping[str, Any] | None = None) -> str:
    stock_policy = {**build_cn_quote_display_policy(), **dict(display_policy or {})}
    fund_policy = {**build_fund_nav_display_policy(), **dict(display_policy or {})}
    if stock_policy.get("default_display_mode") == fund_policy.get("default_display_mode"):
        return str(stock_policy.get("default_display_mode") or "redacted")
    return "redacted"


def _redacted_models(models: Sequence[Mapping[str, Any]], value_keys: Sequence[str]) -> list[dict[str, Any]]:
    safe_models: list[dict[str, Any]] = []
    for model in models:
        item = deepcopy(dict(model))
        status = str(item.get("display_status") or "")
        if status in BLOCKED_STATUSES or item.get("display_mode") in BLOCKED_STATUSES:
            for key in value_keys:
                item[key] = {}
        safe_models.append(item)
    return safe_models


def extract_unified_display_models(section: Mapping[str, Any]) -> list[dict[str, Any]]:
    return list(section.get("display_models") or [])


def count_unified_blocked_items(section: Mapping[str, Any]) -> int:
    return int(section.get("blocked_count") or 0)


def count_unified_redacted_items(section: Mapping[str, Any]) -> int:
    return sum(1 for model in extract_unified_display_models(section) if model.get("display_mode") == "redacted")


def build_unified_data_warning() -> list[str]:
    return [WARNING, REDACTED_WARNING, FUND_NO_REALTIME_WARNING, ESTIMATE_WARNING]


def _all_audited(provider_summary: Mapping[str, Any]) -> bool:
    return len(provider_summary.get("audits") or []) == len(provider_summary.get("results") or [])


def _all_display_checked(provider_summary: Mapping[str, Any]) -> bool:
    return len(provider_summary.get("display_models") or []) == len(provider_summary.get("results") or [])


def build_unified_stock_etf_section(cn_quote_summary: Mapping[str, Any]) -> dict[str, Any]:
    counts = cn_quote_summary.get("asset_counts") or {}
    result_summary = cn_quote_summary.get("result_summary") or {}
    models = _redacted_models(cn_quote_summary.get("display_models") or [], ("quote_display",))
    return {
        "enabled": True,
        "provider_mode": cn_quote_summary.get("provider_mode", "dry_run"),
        "supported_count": int(counts.get("cn_quote_supported") or 0),
        "displayable_count": int(result_summary.get("displayable_count") or 0),
        "blocked_count": int(result_summary.get("blocked_count") or 0),
        "unsupported_count": int(result_summary.get("unsupported_count") or 0),
        "invalid_request_count": int(result_summary.get("invalid_request_count") or 0),
        "display_models": models,
        "field_boundary": ["最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "checked_at", "source_status"],
        "all_results_audited": _all_audited(cn_quote_summary),
        "all_display_models_checked": _all_display_checked(cn_quote_summary),
    }


def build_unified_fund_nav_section(fund_nav_summary: Mapping[str, Any]) -> dict[str, Any]:
    counts = fund_nav_summary.get("asset_counts") or {}
    result_summary = fund_nav_summary.get("result_summary") or {}
    models = _redacted_models(fund_nav_summary.get("display_models") or [], ("nav_display", "estimate_display"))
    return {
        "enabled": True,
        "provider_mode": fund_nav_summary.get("provider_mode", "dry_run"),
        "supported_count": int(counts.get("fund_nav_supported") or 0),
        "displayable_count": int(result_summary.get("displayable_count") or 0),
        "blocked_count": int(result_summary.get("blocked_count") or 0),
        "unsupported_count": int(result_summary.get("unsupported_count") or 0),
        "invalid_request_count": int(result_summary.get("invalid_request_count") or 0),
        "display_models": models,
        "field_boundary": ["单位净值", "累计净值", "净值日期", "日涨跌幅", "估算净值", "估算涨跌", "估算更新时间", "checked_at", "source_status"],
        "estimate_warning": ESTIMATE_WARNING,
        "all_results_audited": _all_audited(fund_nav_summary),
        "all_display_models_checked": _all_display_checked(fund_nav_summary),
    }


def merge_account_real_data_sections(stock_section: Mapping[str, Any], fund_section: Mapping[str, Any]) -> dict[str, Any]:
    stock = dict(stock_section); fund = dict(fund_section)
    return {
        "sections": {"stock_etf": stock, "fund_nav": fund},
        "combined_counts": {
            "stock_etf_supported": int(stock.get("supported_count") or 0),
            "fund_nav_supported": int(fund.get("supported_count") or 0),
            "displayable_total": int(stock.get("displayable_count") or 0) + int(fund.get("displayable_count") or 0),
            "blocked_total": int(stock.get("blocked_count") or 0) + int(fund.get("blocked_count") or 0),
            "redacted_total": count_unified_redacted_items(stock) + count_unified_redacted_items(fund),
            "unsupported_total": int(stock.get("unsupported_count") or 0) + int(fund.get("unsupported_count") or 0),
            "invalid_request_total": int(stock.get("invalid_request_count") or 0) + int(fund.get("invalid_request_count") or 0),
        },
    }


def build_account_real_data_unified_summary(group: Mapping[str, Any], stock_provider_mode: str = "dry_run", fund_provider_mode: str = "dry_run", providers: Mapping[str, Any] | None = None, display_policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if stock_provider_mode not in STOCK_PROVIDER_MODES:
        raise ValueError(f"unsupported stock_provider_mode: {stock_provider_mode}")
    if fund_provider_mode not in FUND_PROVIDER_MODES:
        raise ValueError(f"unsupported fund_provider_mode: {fund_provider_mode}")
    snapshot = deepcopy(dict(group))
    provider_map = dict(providers or {})
    stock_summary = build_account_cn_quote_provider_summary(snapshot, stock_provider_mode, provider_map.get("stock_etf"), display_policy)
    fund_summary = build_account_fund_nav_provider_summary(snapshot, fund_provider_mode, provider_map.get("fund_nav"), display_policy)
    stock_section = build_unified_stock_etf_section(stock_summary)
    fund_section = build_unified_fund_nav_section(fund_summary)
    merged = merge_account_real_data_sections(stock_section, fund_section)
    total_assets = int((stock_summary.get("asset_counts") or {}).get("total") or 0)
    active_assets = int((stock_summary.get("asset_counts") or {}).get("active") or 0)
    merged["combined_counts"].update({"total_assets": total_assets, "active_assets": active_assets})
    summary = {
        "account_id": str(snapshot.get("account_id") or ""),
        "account_name": str(snapshot.get("account_name") or snapshot.get("name") or ""),
        "data_mode": "dry_run" if stock_provider_mode == fund_provider_mode == "dry_run" else "mixed_safe",
        "display_mode": _display_mode(display_policy),
        "has_real_market_data": False,
        "has_real_nav_data": False,
        "commit_safe": False,
        **merged,
        "safety_summary": {
            "all_results_audited": stock_section["all_results_audited"] and fund_section["all_results_audited"],
            "all_display_models_checked": stock_section["all_display_models_checked"] and fund_section["all_display_models_checked"],
            "default_redacted": _display_mode(display_policy) == "redacted",
            "real_data_written_to_repo": False,
            "secrets_detected": False,
        },
        "warnings": build_unified_data_warning(),
        "disclaimer": DISCLAIMER,
    }
    validate_account_real_data_unified_summary(summary)
    return summary


def summarize_unified_real_data_status(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {"data_mode": summary.get("data_mode"), "display_mode": summary.get("display_mode"), **dict(summary.get("combined_counts") or {}), **dict(summary.get("safety_summary") or {})}


def validate_account_real_data_unified_summary(summary: Mapping[str, Any]) -> bool:
    safety = summary.get("safety_summary") or {}
    if summary.get("display_mode") != "redacted" or summary.get("has_real_market_data") is not False or summary.get("has_real_nav_data") is not False:
        return False
    if summary.get("commit_safe") is not False or safety.get("real_data_written_to_repo") is not False or safety.get("secrets_detected") is not False:
        return False
    if "stock_etf" not in (summary.get("sections") or {}) or "fund_nav" not in (summary.get("sections") or {}):
        return False
    rendered = repr(summary)
    return not any(word in rendered for word in SECRET_WORDS)


def build_empty_unified_real_data_summary(group: Mapping[str, Any], reason: str) -> dict[str, Any]:
    summary = build_account_real_data_unified_summary({**dict(group), "assets": []})
    summary["empty_reason"] = reason
    return summary


def render_account_real_data_unified_summary_markdown(summary: Mapping[str, Any]) -> str:
    sections = summary.get("sections") or {}; stock = sections.get("stock_etf") or {}; fund = sections.get("fund_nav") or {}; safety = summary.get("safety_summary") or {}
    lines = [
        "# 账户股票 / ETF / 基金真实数据统一汇总 Demo", "", "## 1. 账户概览",
        f"- 账户：{summary.get('account_name') or summary.get('account_id') or '-'}", f"- data_mode：{summary.get('data_mode', 'dry_run')}", f"- display_mode：{summary.get('display_mode', 'redacted')}",
        f"- 是否含真实股票行情：{summary.get('has_real_market_data') is True}", f"- 是否含真实基金净值：{summary.get('has_real_nav_data') is True}", "- 是否可提交仓库：false", "", "## 2. 股票 / ETF 区域",
        f"- provider_mode：{stock.get('provider_mode', 'dry_run')}", f"- 支持数量：{stock.get('supported_count', 0)}", f"- 可展示数量：{stock.get('displayable_count', 0)}", f"- blocked 数量：{stock.get('blocked_count', 0)}", f"- unsupported 数量：{stock.get('unsupported_count', 0)}", "", "## 3. 场外基金区域",
        f"- provider_mode：{fund.get('provider_mode', 'dry_run')}", f"- 支持数量：{fund.get('supported_count', 0)}", f"- 可展示数量：{fund.get('displayable_count', 0)}", f"- blocked 数量：{fund.get('blocked_count', 0)}", f"- unsupported 数量：{fund.get('unsupported_count', 0)}", "", "## 4. 安全状态",
        f"- 是否全部审计：{safety.get('all_results_audited') is True}", f"- 是否全部展示适配：{safety.get('all_display_models_checked') is True}", f"- 是否默认脱敏：{safety.get('default_redacted') is True}", f"- 是否发现 secret：{safety.get('secrets_detected') is True}", "- 是否写入真实数据：false", "", "## 5. 数据说明",
        f"- {WARNING}", f"- {REDACTED_WARNING}", f"- {FUND_NO_REALTIME_WARNING}", f"- {ESTIMATE_WARNING}", "- 本页面只用于个人观察和记录，不构成交易建议。",
    ]
    return "\n".join(lines).replace("Token", "T***n").replace("API Key", "A*** K***").replace("Webhook", "W***hook") + "\n"
