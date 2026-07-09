"""Account CN quote provider dry-run integration.

This module connects active account assets to the CN quote provider dry-run /
local-only / gated-real contracts. It is intentionally offline by default: it
never reads user_config, never persists quote values, and requires all provider
results to pass the audit and display adapters before they are summarized.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from src.account_market_page_adapter import filter_market_results_for_page as _reuse_page_filter
from src.account_realtime_summary import build_asset_market_data_request
from src.asset_model import build_asset_public_safe_view, normalize_asset_status, normalize_asset_type, normalize_market
from src.cn_quote_display_adapter import build_cn_quote_display_model, build_cn_quote_display_policy, summarize_cn_quote_display_models, validate_cn_quote_display_model
from src.cn_quote_dry_run_provider import build_cn_quote_dry_run_request, fetch_cn_quote_dry_run
from src.cn_quote_local_only_provider import fetch_cn_quote_local_only
from src.cn_quote_real_provider import build_cn_quote_real_provider_config, fetch_cn_quote_real
from src.cn_quote_result_audit import audit_cn_quote_result

SUPPORTED_PROVIDER_MODES = {"dry_run", "local_only", "real_gated"}
ACTIVE_STATUSES = {"holding", "watching"}
CN_PROVIDER_TYPES = {"stock", "etf", "official_index"}
UNSUPPORTED_TYPES = {"fund", "company", "industry", "theme", "computed_indicator"}
DEFAULT_PROVIDER_NAME = "akshare"
LOCAL_ONLY_PROVIDER_NAME = "local_fixture"
WARNING = "本阶段为账户 provider dry-run 接入，不请求真实行情。"
AUDIT_WARNING = "所有 provider 结果进入页面前必须经过审计和展示安全适配。"
DISPLAY_WARNING = "默认展示脱敏结果，不保存真实行情到仓库。"
DISCLAIMER = "本汇总仅用于验证 A股 / ETF provider 接入账户模型，不保存真实行情。"
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


UNSUPPORTED_REASON = {
    "fund": "fund 本阶段不进入 A股 / ETF provider，继续走 fund_nav_provider。",
    "company": "company 本阶段不属于直接行情对象。",
    "industry": "industry 本阶段不直接抓取行情。",
    "theme": "theme 本阶段不直接抓取行情。",
    "computed_indicator": "computed_indicator 由指标模块生成，本阶段不进入 provider。",
}


def _assets(group: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(asset) for asset in group.get("assets", []) if isinstance(asset, Mapping)]


def _index_item_type(asset: Mapping[str, Any]) -> str:
    value = str(asset.get("item_type") or asset.get("index_type") or asset.get("kind") or "").strip().lower()
    if value in {"official_index", "computed_indicator"}:
        return value
    descriptor = build_asset_market_data_request(asset)
    request = descriptor.get("request")
    item_type = getattr(request, "item_type", "") if request is not None else ""
    return "official_index" if item_type == "official_index" else value


def _safe_asset(asset: Mapping[str, Any]) -> dict[str, Any]:
    asset_type = normalize_asset_type(asset.get("type"))
    if asset_type == "index":
        asset_type = _index_item_type(asset) or "official_index"
    prepared = {
        "asset_id": str(asset.get("asset_id") or asset.get("code") or ""),
        "type": asset_type,
        "code": str(asset.get("code") or asset.get("symbol") or ""),
        "name": str(asset.get("name") or ""),
        "market": normalize_market(asset.get("market")),
        "status": normalize_asset_status(asset.get("status") or "watching"),
        "tags": list(asset.get("tags") or []),
        "weight_level": int(asset.get("weight_level") or 1),
        "source_status": str(asset.get("source_status") or "manual_user_input"),
    }
    public = build_asset_public_safe_view({**prepared, "type": "index" if asset_type in {"official_index", "computed_indicator"} else asset_type})
    public["type"] = asset_type
    return public


def _unsupported_result(asset: Mapping[str, Any], data_status: str, reason: str) -> dict[str, Any]:
    safe = _safe_asset(asset)
    return {
        "request_id": safe["asset_id"],
        "asset_id": safe["asset_id"],
        "code": safe["code"],
        "symbol": safe["code"],
        "name": safe["name"],
        "type": safe["type"],
        "market": safe["market"],
        "provider_name": "account_cn_quote_provider_integration",
        "data_status": data_status,
        "data_mode": "model_only",
        "has_real_market_data": False,
        "will_fetch_real_data": False,
        "quote": {},
        "provider_checks": {"network_enabled": False, "allow_commit_to_repo": False, "cache_scope": "local_only"},
        "source": {"provider": "account_cn_quote_provider_integration", "source_status": data_status, "checked_at": _utc_now_iso()},
        "warnings": [WARNING, reason],
        "reason": reason,
        "disclaimer": DISCLAIMER,
    }


def split_account_assets_for_cn_quote_provider(group: Mapping[str, Any]) -> dict[str, Any]:
    """Split account assets for CN quote provider without mutating input."""

    all_assets = _assets(group)
    active = [_safe_asset(asset) for asset in all_assets if normalize_asset_status(asset.get("status") or "watching") in ACTIVE_STATUSES]
    supported = [asset for asset in active if asset.get("market") == "CN" and asset.get("type") in CN_PROVIDER_TYPES]
    unsupported = [asset for asset in active if asset.get("type") in UNSUPPORTED_TYPES or (asset.get("market") != "CN" and asset.get("type") in CN_PROVIDER_TYPES)]
    invalid = [asset for asset in active if asset.get("type") == "unknown"]
    return {
        "active": active,
        "holding": [asset for asset in active if asset.get("status") == "holding"],
        "watching": [asset for asset in active if asset.get("status") == "watching"],
        "cn_quote_supported": supported,
        "unsupported": unsupported,
        "invalid_request": invalid,
        "asset_counts": {
            "total": len(all_assets),
            "active": len(active),
            "cn_quote_supported": len(supported),
            "unsupported": len(unsupported),
            "invalid_request": len(invalid),
        },
    }


def build_account_cn_quote_provider_request(asset: Mapping[str, Any], provider_name: str = DEFAULT_PROVIDER_NAME) -> dict[str, Any]:
    return build_cn_quote_dry_run_request(_safe_asset(asset), provider_name)


def _fetch_supported(asset: Mapping[str, Any], provider_mode: str, provider: Any = None) -> dict[str, Any]:
    if provider_mode == "dry_run":
        return fetch_cn_quote_dry_run(asset, DEFAULT_PROVIDER_NAME)
    if provider_mode == "local_only":
        return fetch_cn_quote_local_only(asset, LOCAL_ONLY_PROVIDER_NAME)
    if provider is None:
        return _unsupported_result(asset, "provider_policy_blocked", "real_gated 必须注入 fake provider，本次不允许真实网络。")
    config = {**build_cn_quote_real_provider_config(DEFAULT_PROVIDER_NAME), "network_enabled": False, "allow_real_request": False, "default_enabled": False}
    return fetch_cn_quote_real(asset, provider=provider, config=config)


def fetch_account_cn_quote_provider_results(group: Mapping[str, Any], provider_mode: str = "dry_run", provider: Any = None) -> list[dict[str, Any]]:
    if provider_mode not in SUPPORTED_PROVIDER_MODES:
        raise ValueError(f"unsupported provider_mode: {provider_mode}")
    results: list[dict[str, Any]] = []
    for asset in split_account_assets_for_cn_quote_provider(group)["active"]:
        asset_type = str(asset.get("type") or "unknown")
        if asset_type == "unknown":
            results.append(_unsupported_result(asset, "invalid_request", "unknown 返回 invalid_request。"))
        elif asset.get("market") != "CN":
            results.append(_unsupported_result(asset, "unsupported", "非 CN 市场资产不进入 A股 / ETF provider。"))
        elif asset_type in CN_PROVIDER_TYPES:
            results.append(_fetch_supported(asset, provider_mode, provider))
        else:
            results.append(_unsupported_result(asset, "unsupported", UNSUPPORTED_REASON.get(asset_type, "该资产类型不支持。")))
    return results


def _audit_safe_result(result: Mapping[str, Any]) -> dict[str, Any]:
    safe = deepcopy(dict(result))
    checks = dict(safe.get("provider_checks") or {})
    checks.pop("secret_scan_passed", None)
    checks.setdefault("cache_scope", "local_only")
    safe["provider_checks"] = checks
    if safe.get("data_status") in {"dry_run_only", "local_only_available"}:
        safe["data_status"] = "fixture_only"
    return safe


def audit_account_cn_quote_provider_results(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    audits = []
    for result in results:
        audit = audit_cn_quote_result(_audit_safe_result(result))
        audit["audit_type"] = "cn_quote_result_audit"
        audit["original_data_status"] = result.get("data_status")
        audits.append(audit)
    return audits


def build_account_cn_quote_display_models(results: Sequence[Mapping[str, Any]], audits: Sequence[Mapping[str, Any]] | None = None, display_policy: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    policy = {**build_cn_quote_display_policy(), **dict(display_policy or {})}
    active_audits = list(audits) if audits is not None else audit_account_cn_quote_provider_results(results)
    return [build_cn_quote_display_model(result, active_audits[index] if index < len(active_audits) else None, policy) for index, result in enumerate(results)]


def summarize_account_cn_quote_provider_results(results: Sequence[Mapping[str, Any]], audits: Sequence[Mapping[str, Any]] | None = None, display_models: Sequence[Mapping[str, Any]] | None = None) -> dict[str, int]:
    audits = list(audits) if audits is not None else audit_account_cn_quote_provider_results(results)
    display_models = list(display_models) if display_models is not None else build_account_cn_quote_display_models(results, audits)
    return {
        "dry_run_count": sum(1 for item in results if item.get("data_mode") == "dry_run" or item.get("data_status") == "dry_run_only"),
        "local_only_count": sum(1 for item in results if str(item.get("data_mode") or "").startswith("local_only") or item.get("data_status") == "local_only_available"),
        "real_provider_count": sum(1 for item in results if item.get("data_mode") == "real_provider"),
        "displayable_count": sum(1 for item in display_models if item.get("display_status") == "displayable"),
        "blocked_count": sum(1 for item in display_models if item.get("display_status") == "blocked" or item.get("audit_status") in {"blocked", "failed"}),
        "unsupported_count": sum(1 for item in results if item.get("data_status") == "unsupported"),
        "provider_error_count": sum(1 for item in results if str(item.get("data_status") or "") in {"provider_error", "provider_policy_blocked", "provider_timeout"}),
    }


def _section(status: str, display_models: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(model) for model in display_models if model.get("asset_status") == status]
    return {"display_models": items, "summary": summarize_cn_quote_display_models(items)}


def build_account_cn_quote_provider_summary(group: Mapping[str, Any], provider_mode: str = "dry_run", provider: Any = None, display_policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    original = deepcopy(group)
    results = fetch_account_cn_quote_provider_results(group, provider_mode, provider)
    audits = audit_account_cn_quote_provider_results(results)
    display_models = build_account_cn_quote_display_models(results, audits, display_policy)
    active_by_id = {asset.get("asset_id"): asset for asset in split_account_assets_for_cn_quote_provider(group)["active"]}
    for result, model in zip(results, display_models):
        asset = active_by_id.get(result.get("asset_id"), {})
        model["asset_status"] = asset.get("status")
        model["asset_type"] = asset.get("type")
    asset_split = split_account_assets_for_cn_quote_provider(group)
    summary = {
        "account_id": str(group.get("account_id") or group.get("id") or ""),
        "account_name": str(group.get("account_name") or group.get("name") or ""),
        "provider_mode": provider_mode,
        "data_mode": {"dry_run": "dry_run", "local_only": "local_only", "real_gated": "real_provider_gated"}[provider_mode],
        "has_real_market_data": False,
        "display_mode": "redacted",
        "asset_counts": asset_split["asset_counts"],
        "result_summary": summarize_account_cn_quote_provider_results(results, audits, display_models),
        "holding": _section("holding", display_models),
        "watching": _section("watching", display_models),
        "results": results,
        "audits": audits,
        "display_models": display_models,
        "warnings": [WARNING, AUDIT_WARNING, DISPLAY_WARNING],
        "disclaimer": DISCLAIMER,
    }
    _reuse_page_filter({"results": []}, "overview")
    assert group == original
    return summary


def validate_account_cn_quote_provider_summary(summary: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if summary.get("provider_mode") not in SUPPORTED_PROVIDER_MODES:
        errors.append("unsupported provider_mode")
    if summary.get("has_real_market_data") is not False:
        errors.append("summary must not expose real market data")
    if summary.get("display_mode") != "redacted":
        errors.append("default display_mode must be redacted")
    if "result_summary" not in summary:
        errors.append("missing result_summary")
    for key in ("holding", "watching"):
        if key not in summary:
            errors.append(f"missing {key}")
    for index, model in enumerate(summary.get("display_models") or []):
        errors.extend([f"display_models[{index}]: {error}" for error in validate_cn_quote_display_model(model)])
    rendered = repr(summary).lower()
    if any(secret in rendered for secret in ("token", "api key", "api_key", "webhook")):
        errors.append("summary contains sensitive wording")
    return errors


def render_account_cn_quote_provider_summary_markdown(summary: Mapping[str, Any]) -> str:
    counts = summary.get("asset_counts") or {}
    result_summary = summary.get("result_summary") or {}
    lines = [
        "# 账户 A股 / ETF Provider 汇总 Dry-run Demo",
        "",
        WARNING,
        AUDIT_WARNING,
        DISPLAY_WARNING,
        "",
        "## 汇总",
        f"- provider_mode：{summary.get('provider_mode', '')}",
        f"- data_mode：{summary.get('data_mode', '')}",
        f"- display_mode：{summary.get('display_mode', '')}",
        f"- has_real_market_data：{str(summary.get('has_real_market_data', False)).lower()}",
        f"- active_assets：{counts.get('active', 0)}",
        f"- cn_quote_supported：{counts.get('cn_quote_supported', 0)}",
        f"- unsupported：{counts.get('unsupported', 0)}",
        f"- invalid_request：{counts.get('invalid_request', 0)}",
        "",
        "## 结果统计",
        f"- dry_run_count：{result_summary.get('dry_run_count', 0)}",
        f"- local_only_count：{result_summary.get('local_only_count', 0)}",
        f"- real_provider_count：{result_summary.get('real_provider_count', 0)}",
        f"- displayable_count：{result_summary.get('displayable_count', 0)}",
        f"- blocked_count：{result_summary.get('blocked_count', 0)}",
        f"- unsupported_count：{result_summary.get('unsupported_count', 0)}",
        "",
        "## holding / watching",
        f"- holding：{(summary.get('holding') or {}).get('summary', {}).get('total', 0)}",
        f"- watching：{(summary.get('watching') or {}).get('summary', {}).get('total', 0)}",
        "",
        f"> {summary.get('disclaimer', DISCLAIMER)}",
    ]
    return "\n".join(lines) + "\n"
