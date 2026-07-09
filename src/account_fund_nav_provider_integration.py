"""Account-level off-exchange fund NAV provider dry-run integration.

This module orchestrates account fund assets through the existing fund NAV
provider, audit, and display-adapter layers. It is side-effect free: it does not
read real user_config, fetch networks by default, or persist NAV values.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from src.account_realtime_summary import split_assets_for_realtime_summary
from src.asset_model import normalize_asset_status, normalize_asset_type, normalize_market
from src.fund_nav_display_adapter import build_fund_nav_display_model, build_fund_nav_display_policy
from src.fund_nav_dry_run_provider import build_fund_nav_dry_run_request, fetch_fund_nav_dry_run
from src.fund_nav_local_only_provider import fetch_fund_nav_local_only
from src.fund_nav_real_provider import FundNavRealProvider
from src.fund_nav_result_audit import ESTIMATE_VALUE_FIELDS, NAV_VALUE_FIELDS, audit_fund_nav_result

SUPPORTED_PROVIDER_MODES = {"dry_run", "local_only", "real_gated"}
ACTIVE_PROVIDER_STATUSES = frozenset({"holding", "watching"})
CN_MARKETS = {"CN", "中国"}
WARNING = "本阶段为账户基金净值 provider dry-run 接入，不请求真实基金净值。"
AUDIT_DISPLAY_WARNING = "所有基金净值结果进入页面前必须经过审计和展示安全适配。"
REDACTED_WARNING = "默认展示脱敏结果，不保存真实基金净值到仓库。"
NO_REALTIME_WARNING = "场外基金不支持真正实时价格。"
ESTIMATE_WARNING = "盘中估算仅供观察，最终以基金公司公布净值为准。"
DISCLAIMER = "本汇总仅用于验证场外基金净值 provider 接入账户模型，不保存真实基金净值。"

UNSUPPORTED_REASON = {
    "stock": "股票应使用 A股 / ETF quote provider。",
    "etf": "ETF 属于交易所交易品种，应使用股票 / ETF provider。",
    "index": "指数应使用 index quote 或市场指数模块。",
    "official_index": "指数应使用 index quote 或市场指数模块。",
    "company": "企业本身不是基金净值对象。",
    "industry": "行业 / 主题不直接请求基金净值 provider。",
    "theme": "行业 / 主题不直接请求基金净值 provider。",
    "computed_indicator": "系统计算指标由市场广度模块生成，不直接请求基金净值 provider。",
}


def _assets(group: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(asset) for asset in group.get("assets", []) if isinstance(asset, Mapping)]


def _asset_type(asset: Mapping[str, Any]) -> str:
    item_type = str(asset.get("item_type") or asset.get("index_type") or asset.get("category") or "").strip().lower()
    if item_type == "computed_indicator":
        return "computed_indicator"
    raw_type = str(asset.get("type") or asset.get("asset_type") or "unknown").strip().lower()
    if raw_type in {"official_index", "official index"} or item_type in {"official_index", "official"}:
        return "official_index"
    return normalize_asset_type(raw_type)


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
    }


def split_account_assets_for_fund_nav_provider(group: Mapping[str, Any]) -> dict[str, Any]:
    """Split active account assets for off-exchange fund NAV provider routing."""

    try:
        base_split = split_assets_for_realtime_summary(deepcopy(dict(group)))
    except Exception:
        base_split = {"active": []}
    assets = [_safe_asset(asset) for asset in _assets(group)]
    active = [asset for asset in assets if asset["status"] in ACTIVE_PROVIDER_STATUSES]
    supported: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for asset in active:
        if asset["type"] == "unknown":
            invalid.append(asset)
        elif asset["type"] != "fund" or asset["market"] not in CN_MARKETS:
            unsupported.append(asset)
        else:
            supported.append(asset)
    return {
        "active": active,
        "inactive": [asset for asset in assets if asset["status"] not in ACTIVE_PROVIDER_STATUSES],
        "holding": [asset for asset in active if asset["status"] == "holding"],
        "watching": [asset for asset in active if asset["status"] == "watching"],
        "fund_nav_supported": supported,
        "unsupported": unsupported,
        "invalid_request": invalid,
        "asset_counts": {
            "total": len(assets),
            "active": len(active),
            "holding": sum(1 for asset in active if asset["status"] == "holding"),
            "watching": sum(1 for asset in active if asset["status"] == "watching"),
            "fund_nav_supported": len(supported),
            "unsupported": len(unsupported),
            "invalid_request": len(invalid),
            "realtime_summary_active": len(base_split.get("active") or []),
        },
    }


def build_account_fund_nav_provider_request(asset: Mapping[str, Any], provider_name: str = "eastmoney_fund") -> dict[str, Any]:
    return build_fund_nav_dry_run_request(_safe_asset(asset), provider_name)


def _account_result(asset: Mapping[str, Any], result: Mapping[str, Any], result_kind: str = "fund_nav_provider") -> dict[str, Any]:
    data = dict(result)
    checks = dict(data.get("provider_checks") or {})
    checks.pop("secret_scan_passed", None)
    checks.setdefault("allow_commit_to_repo", False)
    checks["cache_scope"] = "local_only"
    checks["network_enabled"] = False
    data["provider_checks"] = checks
    safe = _safe_asset(asset)
    data["asset"] = safe
    data["asset_status"] = safe["status"]
    data["result_kind"] = result_kind
    data["has_real_nav_data"] = bool(data.get("has_real_nav_data")) if data.get("data_mode") == "real_provider" else False
    data["will_fetch_real_data"] = False
    data.setdefault("warnings", [])
    data["warnings"] = list(dict.fromkeys([*data["warnings"], ESTIMATE_WARNING]))
    return data


def _unsupported_result(asset: Mapping[str, Any], kind: str, reason: str) -> dict[str, Any]:
    safe = _safe_asset(asset)
    return {
        "request_id": safe["asset_id"] or safe["code"], "asset_id": safe["asset_id"], "code": safe["code"], "name": safe["name"],
        "type": safe["type"], "market": safe["market"], "price_mode": "unknown" if kind == "invalid_request" else "unsupported",
        "provider_name": "account_fund_nav_provider_integration", "data_status": kind, "data_mode": "model_only",
        "has_real_nav_data": False, "will_fetch_real_data": False,
        "nav": {field: None for field in (*NAV_VALUE_FIELDS, "nav_date")},
        "estimate": {field: None for field in (*ESTIMATE_VALUE_FIELDS, "estimate_time")},
        "source": {"provider": "account_fund_nav_provider_integration", "provider_type": "model", "source_status": kind, "checked_at": "model_only"},
        "provider_checks": {"allow_commit_to_repo": False, "cache_scope": "local_only", "network_enabled": False},
        "warnings": [reason, ESTIMATE_WARNING], "reason": reason, "disclaimer": DISCLAIMER,
        "asset": safe, "asset_status": safe["status"], "result_kind": kind,
    }


def fetch_account_fund_nav_provider_results(group: Mapping[str, Any], provider_mode: str = "dry_run", provider: Any = None) -> list[dict[str, Any]]:
    if provider_mode not in SUPPORTED_PROVIDER_MODES:
        raise ValueError(f"unsupported provider_mode: {provider_mode}")
    split = split_account_assets_for_fund_nav_provider(group)
    results: list[dict[str, Any]] = []
    for asset in split["active"]:
        asset_type = asset["type"]
        if asset_type == "unknown":
            results.append(_unsupported_result(asset, "invalid_request", "unknown 资产类型无法生成基金净值 provider 请求。"))
        elif asset_type != "fund":
            results.append(_unsupported_result(asset, "unsupported", UNSUPPORTED_REASON.get(asset_type, "该资产不属于场外基金净值对象。")))
        elif asset["market"] not in CN_MARKETS:
            results.append(_unsupported_result(asset, "unsupported", "非 CN 市场基金暂不进入场外基金净值 provider。"))
        elif provider_mode == "dry_run":
            results.append(_account_result(asset, fetch_fund_nav_dry_run(asset)))
        elif provider_mode == "local_only":
            results.append(_account_result(asset, fetch_fund_nav_local_only(asset, provider)))
        else:
            provider_obj = provider if provider is not None else FundNavRealProvider(config={"network_enabled": False, "provider_enabled": False, "allow_real_request": False})
            fetch_one = provider_obj.fetch_one if hasattr(provider_obj, "fetch_one") else provider_obj
            results.append(_account_result(asset, fetch_one(asset)))
    return results


def audit_account_fund_nav_provider_results(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []
    for result in results:
        audit = audit_fund_nav_result(result)
        if result.get("has_real_nav_data") is not True and not audit.get("secret_fields_found"):
            audit = dict(audit)
            audit["cache_scope"] = "local_only"
            if audit.get("audit_status") in {"passed", "passed_with_warnings"}:
                audit["display_safe"] = True
        audits.append(audit)
    return audits


def build_account_fund_nav_display_models(results: Sequence[Mapping[str, Any]], audits: Sequence[Mapping[str, Any]] | None = None, display_policy: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    policy = {**build_fund_nav_display_policy(), **dict(display_policy or {})}
    active_audits = list(audits) if audits is not None else audit_account_fund_nav_provider_results(results)
    return [build_fund_nav_display_model(result, active_audits[index] if index < len(active_audits) else None, policy) for index, result in enumerate(results)]


def _status_summary(results: Sequence[Mapping[str, Any]], display_models: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "total": len(results),
        "supported_count": sum(1 for item in results if item.get("data_status") not in {"unsupported", "invalid_request"}),
        "displayable_count": sum(1 for model in display_models if model.get("display_status") == "displayable"),
        "blocked_count": sum(1 for model in display_models if model.get("display_status") == "blocked"),
        "unsupported_count": sum(1 for item in results if item.get("data_status") == "unsupported"),
        "invalid_request_count": sum(1 for item in results if item.get("data_status") == "invalid_request"),
    }


def summarize_account_fund_nav_provider_results(results: Sequence[Mapping[str, Any]], audits: Sequence[Mapping[str, Any]] | None = None, display_models: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    models = list(display_models) if display_models is not None else build_account_fund_nav_display_models(results, audits)
    return {
        "dry_run_count": sum(1 for item in results if item.get("data_mode") == "dry_run"),
        "local_only_count": sum(1 for item in results if item.get("data_mode") == "local_only_fixture"),
        "real_provider_count": sum(1 for item in results if item.get("data_mode") == "real_provider"),
        "displayable_count": sum(1 for model in models if model.get("display_status") == "displayable"),
        "blocked_count": sum(1 for model in models if model.get("display_status") == "blocked"),
        "unsupported_count": sum(1 for item in results if item.get("data_status") == "unsupported"),
        "provider_error_count": sum(1 for item in results if str(item.get("data_status")) in {"provider_error", "provider_timeout", "invalid_response"}),
        "invalid_request_count": sum(1 for item in results if item.get("data_status") == "invalid_request"),
        "estimate_unavailable_count": sum(1 for item in results if item.get("data_status") == "estimate_unavailable"),
        "daily_nav_unavailable_count": sum(1 for item in results if item.get("data_status") == "daily_nav_unavailable"),
    }


def build_account_fund_nav_provider_summary(group: Mapping[str, Any], provider_mode: str = "dry_run", provider: Any = None, display_policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    snapshot = deepcopy(dict(group))
    split = split_account_assets_for_fund_nav_provider(snapshot)
    results = fetch_account_fund_nav_provider_results(snapshot, provider_mode, provider)
    audits = audit_account_fund_nav_provider_results(results)
    display_models = build_account_fund_nav_display_models(results, audits, display_policy)
    display_mode = str(({**build_fund_nav_display_policy(), **dict(display_policy or {})}).get("default_display_mode") or "redacted")
    holding_results = [item for item in results if item.get("asset_status") == "holding"]
    watching_results = [item for item in results if item.get("asset_status") == "watching"]
    holding_models = [model for model, result in zip(display_models, results) if result.get("asset_status") == "holding"]
    watching_models = [model for model, result in zip(display_models, results) if result.get("asset_status") == "watching"]
    summary = {
        "account_id": str(snapshot.get("account_id") or ""), "account_name": str(snapshot.get("account_name") or snapshot.get("name") or ""),
        "provider_mode": provider_mode, "data_mode": provider_mode, "has_real_nav_data": False, "display_mode": display_mode,
        "asset_counts": {key: split["asset_counts"][key] for key in ("total", "active", "fund_nav_supported", "unsupported", "invalid_request")},
        "result_summary": summarize_account_fund_nav_provider_results(results, audits, display_models),
        "holding": {"display_models": holding_models, "summary": _status_summary(holding_results, holding_models)},
        "watching": {"display_models": watching_models, "summary": _status_summary(watching_results, watching_models)},
        "results": results, "audits": audits, "display_models": display_models,
        "warnings": [WARNING, AUDIT_DISPLAY_WARNING, REDACTED_WARNING, NO_REALTIME_WARNING, ESTIMATE_WARNING],
        "disclaimer": DISCLAIMER,
    }
    validate_account_fund_nav_provider_summary(summary)
    return summary


def build_account_fund_nav_provider_empty_result(group: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return build_account_fund_nav_provider_summary({**dict(group), "assets": []}) | {"empty_reason": reason}


def validate_account_fund_nav_provider_summary(summary: Mapping[str, Any]) -> bool:
    if summary.get("provider_mode") not in SUPPORTED_PROVIDER_MODES or summary.get("has_real_nav_data") is not False:
        return False
    if summary.get("display_mode") != "redacted":
        return False
    if "result_summary" not in summary or "holding" not in summary or "watching" not in summary:
        return False
    for result in summary.get("results") or []:
        if result.get("will_fetch_real_data") is True:
            return False
        nav = result.get("nav") or {}; estimate = result.get("estimate") or {}
        if result.get("data_status") in {"unsupported", "invalid_request", "provider_error", "provider_timeout", "invalid_response"}:
            if any(nav.get(field) is not None for field in NAV_VALUE_FIELDS) or any(estimate.get(field) is not None for field in ESTIMATE_VALUE_FIELDS):
                return False
    return True


def render_account_fund_nav_provider_summary_markdown(summary: Mapping[str, Any]) -> str:
    counts = summary.get("asset_counts") or {}; rs = summary.get("result_summary") or {}
    holding = (summary.get("holding") or {}).get("summary", {}); watching = (summary.get("watching") or {}).get("summary", {})
    lines = [
        "# 账户场外基金净值 Provider 汇总 Dry-run Demo", "", "## 1. 账户概览",
        f"- 账户：{summary.get('account_name') or summary.get('account_id') or '-'}",
        f"- provider_mode：{summary.get('provider_mode', 'dry_run')}", f"- data_mode：{summary.get('data_mode', 'dry_run')}",
        f"- 是否真实基金净值：{summary.get('has_real_nav_data') is True}", f"- display_mode：{summary.get('display_mode', 'redacted')}",
        "", "## 2. 持有基金", f"- 支持数量：{holding.get('supported_count', 0)}", f"- blocked 数量：{holding.get('blocked_count', 0)}", f"- unsupported 数量：{holding.get('unsupported_count', 0)}",
        "", "## 3. 收藏基金", f"- 支持数量：{watching.get('supported_count', 0)}", f"- blocked 数量：{watching.get('blocked_count', 0)}", f"- unsupported 数量：{watching.get('unsupported_count', 0)}",
        "", "## 4. 数据状态", f"- dry_run：{rs.get('dry_run_count', 0)}", f"- local_only：{rs.get('local_only_count', 0)}", f"- real_provider：{rs.get('real_provider_count', 0)}", f"- provider_error：{rs.get('provider_error_count', 0)}", f"- invalid_request：{rs.get('invalid_request_count', counts.get('invalid_request', 0))}", f"- estimate_unavailable：{rs.get('estimate_unavailable_count', 0)}", f"- daily_nav_unavailable：{rs.get('daily_nav_unavailable_count', 0)}",
        "", "## 5. 数据说明", f"- {WARNING}", f"- {AUDIT_DISPLAY_WARNING}", f"- {REDACTED_WARNING}", f"- {NO_REALTIME_WARNING}", f"- {ESTIMATE_WARNING}",
    ]
    return "\n".join(lines).replace("Token", "T***n").replace("API Key", "A*** K***").replace("Webhook", "W***hook") + "\n"
