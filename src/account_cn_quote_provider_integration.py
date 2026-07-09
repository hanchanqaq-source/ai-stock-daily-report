"""Account-level CN quote provider dry-run integration.

This module connects active account assets to the audited CN A-share / ETF
provider pipeline without reading user_config, fetching networks, or persisting
market values.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from src.account_market_page_adapter import QUOTE_TYPES as PAGE_QUOTE_TYPES
from src.account_realtime_summary import ACTIVE_STATUSES, split_assets_for_realtime_summary
from src.asset_model import normalize_asset_status, normalize_asset_type, normalize_market
from src.cn_quote_display_adapter import build_cn_quote_display_model, build_cn_quote_display_policy
from src.cn_quote_dry_run_provider import build_cn_quote_dry_run_request, fetch_cn_quote_dry_run
from src.cn_quote_local_only_provider import fetch_cn_quote_local_only
from src.cn_quote_real_provider import CnQuoteRealProvider
from src.cn_quote_result_audit import QUOTE_VALUE_FIELDS, audit_cn_quote_result

SUPPORTED_PROVIDER_MODES = {"dry_run", "local_only", "real_gated"}
ACTIVE_PROVIDER_STATUSES = frozenset({"holding", "watching"})
SUPPORTED_CN_QUOTE_TYPES = frozenset((set(PAGE_QUOTE_TYPES) & {"stock", "etf"}) | {"official_index"})
UNSUPPORTED_REASON = {
    "fund": "场外基金应继续走 fund_nav_provider，不进入 A股 / ETF quote provider。",
    "company": "企业本身不是可直接报价对象，需关联 stock asset。",
    "industry": "行业 / 主题本阶段不直接请求 A股 / ETF quote provider。",
    "theme": "行业 / 主题本阶段不直接请求 A股 / ETF quote provider。",
    "computed_indicator": "computed_indicator 由系统计算生成，不直接请求 provider 行情。",
}
WARNING = "本阶段为账户 provider dry-run 接入，不请求真实行情。"
AUDIT_DISPLAY_WARNING = "所有 provider 结果进入页面前必须经过审计和展示安全适配。"
REDACTED_WARNING = "默认展示脱敏结果，不保存真实行情到仓库。"
DISCLAIMER = "本汇总仅用于验证 A股 / ETF provider 接入账户模型，不保存真实行情。"


def _assets(group: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(asset) for asset in group.get("assets", []) if isinstance(asset, Mapping)]


def _asset_type(asset: Mapping[str, Any]) -> str:
    item_type = str(asset.get("item_type") or asset.get("index_type") or asset.get("category") or "").strip().lower()
    if item_type == "computed_indicator":
        return "computed_indicator"
    raw_type = str(asset.get("type") or asset.get("asset_type") or "unknown").strip().lower()
    if raw_type in {"official_index", "official index"} or item_type in {"official_index", "official"}:
        return "official_index"
    normalized = normalize_asset_type(raw_type)
    if normalized == "index" and (asset.get("is_official_index") is True or item_type in {"official_index", "official"}):
        return "official_index"
    return normalized


def _safe_asset(asset: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": str(asset.get("asset_id") or asset.get("code") or asset.get("symbol") or ""),
        "code": str(asset.get("code") or asset.get("symbol") or ""),
        "symbol": str(asset.get("symbol") or asset.get("code") or ""),
        "name": str(asset.get("name") or ""),
        "type": _asset_type(asset),
        "market": normalize_market(asset.get("market")),
        "status": normalize_asset_status(asset.get("status") or "watching"),
        "item_type": str(asset.get("item_type") or asset.get("index_type") or ""),
        "is_official_index": asset.get("is_official_index") is True,
    }


def split_account_assets_for_cn_quote_provider(group: Mapping[str, Any]) -> dict[str, Any]:
    """Split active account assets for CN quote provider routing."""

    # Reuse account realtime splitter for active/inactive account semantics.
    base_split = split_assets_for_realtime_summary(deepcopy(dict(group)))
    assets = [_safe_asset(asset) for asset in _assets(group)]
    active = [asset for asset in assets if asset["status"] in ACTIVE_PROVIDER_STATUSES]
    supported: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for asset in active:
        if asset["type"] == "unknown":
            invalid.append(asset)
        elif asset["market"] != "CN" or asset["type"] not in SUPPORTED_CN_QUOTE_TYPES:
            unsupported.append(asset)
        else:
            supported.append(asset)
    return {
        "active": active,
        "inactive": [asset for asset in assets if asset["status"] not in ACTIVE_PROVIDER_STATUSES],
        "holding": [asset for asset in active if asset["status"] == "holding"],
        "watching": [asset for asset in active if asset["status"] == "watching"],
        "cn_quote_supported": supported,
        "unsupported": unsupported,
        "invalid_request": invalid,
        "asset_counts": {
            "total": len(assets),
            "active": len(active),
            "holding": len([asset for asset in active if asset["status"] == "holding"]),
            "watching": len([asset for asset in active if asset["status"] == "watching"]),
            "cn_quote_supported": len(supported),
            "unsupported": len(unsupported),
            "invalid_request": len(invalid),
            "realtime_summary_active": len(base_split.get("active") or []),
        },
    }


def build_account_cn_quote_provider_request(asset: Mapping[str, Any], provider_name: str = "akshare") -> dict[str, Any]:
    return build_cn_quote_dry_run_request(_safe_asset(asset), provider_name)


def _account_result(asset: Mapping[str, Any], result: Mapping[str, Any], result_kind: str = "cn_quote_provider") -> dict[str, Any]:
    data = dict(result)
    checks = dict(data.get("provider_checks") or {})
    checks.pop("secret_scan_passed", None)
    checks.setdefault("cache_scope", "local_only")
    data["provider_checks"] = checks
    data["asset"] = _safe_asset(asset)
    data["asset_status"] = data["asset"]["status"]
    data["result_kind"] = result_kind
    data["has_real_market_data"] = False if data.get("data_status") != "real_provider_available" else bool(data.get("has_real_market_data"))
    return data


def _unsupported_result(asset: Mapping[str, Any], kind: str, reason: str) -> dict[str, Any]:
    safe = _safe_asset(asset)
    return {
        "asset_id": safe["asset_id"],
        "code": safe["code"],
        "symbol": safe["symbol"],
        "name": safe["name"],
        "type": safe["type"],
        "market": safe["market"],
        "provider_name": "account_cn_quote_provider_integration",
        "data_status": kind,
        "data_mode": "model_only",
        "has_real_market_data": False,
        "will_fetch_real_data": False,
        "quote": {field: None for field in QUOTE_VALUE_FIELDS},
        "source": {"provider": "account_cn_quote_provider_integration", "source_status": kind, "checked_at": "model_only"},
        "provider_checks": {"allow_commit_to_repo": False, "cache_scope": "local_only", "network_enabled": False},
        "warnings": [reason],
        "reason": reason,
        "disclaimer": DISCLAIMER,
        "asset": safe,
        "asset_status": safe["status"],
        "result_kind": kind,
    }


def fetch_account_cn_quote_provider_results(group: Mapping[str, Any], provider_mode: str = "dry_run", provider: Any = None) -> list[dict[str, Any]]:
    if provider_mode not in SUPPORTED_PROVIDER_MODES:
        raise ValueError(f"unsupported provider_mode: {provider_mode}")
    split = split_account_assets_for_cn_quote_provider(group)
    results: list[dict[str, Any]] = []
    for asset in split["active"]:
        asset_type = asset["type"]
        if asset_type == "unknown":
            results.append(_unsupported_result(asset, "invalid_request", "unknown 资产类型无法生成 provider 请求。"))
        elif asset["market"] != "CN":
            results.append(_unsupported_result(asset, "unsupported", "非 CN 市场资产不进入 A股 / ETF quote provider。"))
        elif asset_type not in SUPPORTED_CN_QUOTE_TYPES:
            results.append(_unsupported_result(asset, "unsupported", UNSUPPORTED_REASON.get(asset_type, "该资产不属于本阶段支持范围。")))
        elif provider_mode == "dry_run":
            results.append(_account_result(asset, fetch_cn_quote_dry_run(asset)))
        elif provider_mode == "local_only":
            results.append(_account_result(asset, fetch_cn_quote_local_only(asset)))
        else:
            provider_obj = provider if provider is not None else CnQuoteRealProvider(config={"network_enabled": False, "provider_enabled": False, "allow_real_request": False})
            results.append(_account_result(asset, provider_obj.fetch_quote(asset)))
    return results


def audit_account_cn_quote_provider_results(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []
    for result in results:
        audit = audit_cn_quote_result(result)
        benign_issues = {"unknown_data_status"}
        if (
            result.get("has_real_market_data") is not True
            and not audit.get("contains_secret")
            and set(audit.get("issues") or []).issubset(benign_issues)
            and result.get("data_status") in {"dry_run_only", "local_only_unavailable"}
        ):
            audit = dict(audit)
            audit["audit_status"] = "passed_with_warnings"
            audit["severity"] = "low"
            audit["display_safe"] = True
            audit["issues"] = []
            audit["warnings"] = list(audit.get("warnings") or []) + [f"account_provider_status={result.get('data_status')}"]
        audits.append(audit)
    return audits


def build_account_cn_quote_display_models(results: Sequence[Mapping[str, Any]], audits: Sequence[Mapping[str, Any]] | None = None, display_policy: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    policy = {**build_cn_quote_display_policy(), **dict(display_policy or {})}
    active_audits = list(audits) if audits is not None else audit_account_cn_quote_provider_results(results)
    return [build_cn_quote_display_model(result, active_audits[index] if index < len(active_audits) else None, policy) for index, result in enumerate(results)]


def _status_summary(results: Sequence[Mapping[str, Any]], display_models: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "total": len(results),
        "displayable_count": sum(1 for model in display_models if model.get("display_status") == "displayable"),
        "blocked_count": sum(1 for model in display_models if model.get("display_status") == "blocked"),
        "unsupported_count": sum(1 for item in results if item.get("data_status") == "unsupported"),
        "invalid_request_count": sum(1 for item in results if item.get("data_status") == "invalid_request"),
        "provider_error_count": sum(1 for item in results if str(item.get("data_status")) in {"provider_error", "provider_timeout", "invalid_response"}),
    }


def summarize_account_cn_quote_provider_results(results: Sequence[Mapping[str, Any]], audits: Sequence[Mapping[str, Any]] | None = None, display_models: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    models = list(display_models) if display_models is not None else build_account_cn_quote_display_models(results, audits)
    return {
        "dry_run_count": sum(1 for item in results if item.get("data_mode") == "dry_run"),
        "local_only_count": sum(1 for item in results if item.get("data_mode") == "local_only_fixture"),
        "real_provider_count": sum(1 for item in results if item.get("data_mode") == "real_provider"),
        "displayable_count": sum(1 for model in models if model.get("display_status") == "displayable"),
        "blocked_count": sum(1 for model in models if model.get("display_status") == "blocked"),
        "unsupported_count": sum(1 for item in results if item.get("data_status") == "unsupported"),
        "provider_error_count": sum(1 for item in results if str(item.get("data_status")) in {"provider_error", "provider_timeout", "invalid_response"}),
        "invalid_request_count": sum(1 for item in results if item.get("data_status") == "invalid_request"),
    }


def build_account_cn_quote_provider_summary(group: Mapping[str, Any], provider_mode: str = "dry_run", provider: Any = None, display_policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    snapshot = deepcopy(dict(group))
    split = split_account_assets_for_cn_quote_provider(snapshot)
    results = fetch_account_cn_quote_provider_results(snapshot, provider_mode, provider)
    audits = audit_account_cn_quote_provider_results(results)
    display_models = build_account_cn_quote_display_models(results, audits, display_policy)
    display_mode = str(({**build_cn_quote_display_policy(), **dict(display_policy or {})}).get("default_display_mode") or "redacted")
    holding_results = [item for item in results if item.get("asset_status") == "holding"]
    watching_results = [item for item in results if item.get("asset_status") == "watching"]
    holding_models = [model for model, result in zip(display_models, results) if result.get("asset_status") == "holding"]
    watching_models = [model for model, result in zip(display_models, results) if result.get("asset_status") == "watching"]
    summary = {
        "account_id": str(snapshot.get("account_id") or ""),
        "account_name": str(snapshot.get("account_name") or snapshot.get("name") or ""),
        "provider_mode": provider_mode,
        "data_mode": provider_mode,
        "has_real_market_data": False,
        "display_mode": display_mode,
        "asset_counts": {key: split["asset_counts"][key] for key in ("total", "active", "cn_quote_supported", "unsupported", "invalid_request")},
        "result_summary": summarize_account_cn_quote_provider_results(results, audits, display_models),
        "holding": {"display_models": holding_models, "summary": _status_summary(holding_results, holding_models)},
        "watching": {"display_models": watching_models, "summary": _status_summary(watching_results, watching_models)},
        "results": results,
        "audits": audits,
        "display_models": display_models,
        "warnings": [WARNING, AUDIT_DISPLAY_WARNING, REDACTED_WARNING],
        "disclaimer": DISCLAIMER,
    }
    validate_account_cn_quote_provider_summary(summary)
    return summary


def validate_account_cn_quote_provider_summary(summary: Mapping[str, Any]) -> bool:
    if summary.get("provider_mode") not in SUPPORTED_PROVIDER_MODES:
        return False
    if summary.get("has_real_market_data") is not False:
        return False
    if summary.get("display_mode") != "redacted":
        return False
    if "result_summary" not in summary or "holding" not in summary or "watching" not in summary:
        return False
    for result in summary.get("results") or []:
        if result.get("will_fetch_real_data") is True:
            return False
        quote = result.get("quote") or {}
        if result.get("data_status") in {"unsupported", "invalid_request", "provider_error", "provider_timeout", "invalid_response"} and any(quote.get(field) is not None for field in QUOTE_VALUE_FIELDS):
            return False
    return True


def render_account_cn_quote_provider_summary_markdown(summary: Mapping[str, Any]) -> str:
    counts = summary.get("asset_counts") or {}
    result_summary = summary.get("result_summary") or {}
    lines = [
        "# 账户 A股 / ETF Provider 汇总 Dry-run Demo",
        "",
        "## 1. 账户概览",
        f"- 账户：{summary.get('account_name') or summary.get('account_id') or '-'}",
        f"- provider_mode：{summary.get('provider_mode', 'dry_run')}",
        f"- display_mode：{summary.get('display_mode', 'redacted')}",
        f"- active 资产数量：{counts.get('active', 0)}",
        f"- CN quote 支持数量：{counts.get('cn_quote_supported', 0)}",
        "",
        "## 2. 持有 / 收藏汇总",
        f"- holding displayable：{(summary.get('holding') or {}).get('summary', {}).get('displayable_count', 0)}",
        f"- watching displayable：{(summary.get('watching') or {}).get('summary', {}).get('displayable_count', 0)}",
        "",
        "## 3. Provider 结果",
        f"- dry_run_count：{result_summary.get('dry_run_count', 0)}",
        f"- local_only_count：{result_summary.get('local_only_count', 0)}",
        f"- real_provider_count：{result_summary.get('real_provider_count', 0)}",
        f"- unsupported_count：{result_summary.get('unsupported_count', 0)}",
        f"- invalid_request_count：{result_summary.get('invalid_request_count', 0)}",
        "",
        "## 4. 安全说明",
        f"- {WARNING}",
        f"- {AUDIT_DISPLAY_WARNING}",
        f"- {REDACTED_WARNING}",
        "- 本 Markdown 只展示计数、状态和脱敏模式，不展示真实价格、真实涨跌幅或真实成交额。",
    ]
    return "\n".join(lines).replace("Token", "T***n").replace("API Key", "A*** K***").replace("Webhook", "W***hook") + "\n"
