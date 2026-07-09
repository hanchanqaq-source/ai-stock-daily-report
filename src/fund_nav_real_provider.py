"""Gated real-request adapter for off-exchange fund NAV providers.

The adapter is intentionally closed by default. It never owns concrete network
code; callers must inject a fetcher and explicitly enable all real-request gates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from src.asset_model import normalize_asset_type, normalize_market, scan_asset_for_sensitive_values
from src.fund_nav_dry_run_provider import UNSUPPORTED_REASONS
from src.fund_nav_provider import FundNavRequest, _empty_estimate, _empty_nav
from src.fund_nav_provider_registry import get_fund_nav_provider_evaluation
from src.provider_safety import (
    FUND_ESTIMATE_WARNING,
    assert_real_data_not_written_to_repo,
    scan_provider_config_for_secrets,
    validate_provider_config,
    validate_provider_result,
)

NAV_FIELDS = ("unit_nav", "accumulated_nav", "daily_change_pct", "nav_date")
ESTIMATE_FIELDS = ("estimated_nav", "estimated_change_pct", "estimated_change_amount", "estimate_time")
REAL_STATUSES = frozenset({
    "real_provider_available", "disabled_by_default", "provider_policy_blocked", "unsupported",
    "invalid_request", "provider_error", "provider_timeout", "invalid_response", "stale_data",
    "conflict", "estimate_unavailable", "daily_nav_unavailable",
})
DISCLAIMER = "本结果来自显式启用的真实基金净值 provider，仅用于本地观察。"
DELAY_NOTE = "真实基金净值 provider 数据仅允许本地显式启用后使用，不写入 public 仓库。"
NO_REPO_WARNING = "真实基金净值结果不得写入 public 仓库。"
DEFAULT_OFF_WARNING = "真实基金净值 provider 默认关闭，必须显式开启 network_enabled、provider_enabled 和 allow_real_request。"
CI_WARNING = "CI 测试不会请求真实基金净值。"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _data(item: Mapping[str, Any] | FundNavRequest) -> dict[str, Any]:
    return item.to_dict() if isinstance(item, FundNavRequest) else dict(item)


def _is_cn_market(market: Any) -> bool:
    return str(market or "").strip() in {"CN", "cn", "中国"} or normalize_market(market) == "CN"


def _candidate(provider_name: str) -> dict[str, Any] | None:
    try:
        return get_fund_nav_provider_evaluation(provider_name)
    except KeyError:
        return None


def build_fund_nav_real_provider_config(provider_name: str = "eastmoney_fund") -> dict[str, Any]:
    candidate = _candidate(provider_name) or {}
    return {
        "provider_name": provider_name,
        "provider_type": candidate.get("provider_type", "public_web"),
        "mode": "real_provider",
        "data_mode": "real_provider",
        "market": "CN",
        "network_enabled": False,
        "provider_enabled": False,
        "allow_real_request": False,
        "default_enabled": False,
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
        "timeout_seconds": 10,
        "retry_limit": 0,
        "retry": 0,
        "rate_limit": "local_manual_only",
        "source_status": "real_provider_disabled",
        "notes": [DEFAULT_OFF_WARNING],
    }


def validate_fund_nav_real_provider_config(config: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if _candidate(str(config.get("provider_name") or "")) is None:
        errors.append("provider must be registered in fund_nav_provider_registry")
    if scan_provider_config_for_secrets(config):
        errors.append("real provider config contains secret fields")
    if config.get("default_enabled") is not False:
        errors.append("real provider requires default_enabled=false")
    if config.get("allow_commit_to_repo") is not False:
        errors.append("real provider requires allow_commit_to_repo=false")
    if config.get("cache_scope") != "local_only":
        errors.append("real provider cache_scope must be local_only")
    safety = dict(config)
    safety["enabled"] = bool(config.get("provider_enabled"))
    errors.extend(validate_provider_config(safety))
    try:
        assert_real_data_not_written_to_repo({"has_real_market_data": False, "allow_commit_to_repo": config.get("allow_commit_to_repo")})
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def build_fund_nav_real_request(asset_or_request: Mapping[str, Any] | FundNavRequest, provider_name: str = "eastmoney_fund", config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = _data(asset_or_request)
    code = str(data.get("code") or "").strip()
    asset_id = str(data.get("asset_id") or data.get("request_id") or code or "").strip()
    cfg = dict(config or build_fund_nav_real_provider_config(provider_name))
    return {
        "request_id": str(data.get("request_id") or asset_id or code), "asset_id": asset_id, "code": code,
        "name": str(data.get("name") or ""), "type": normalize_asset_type(data.get("type")),
        "market": normalize_market(data.get("market") or "CN"), "provider_name": provider_name,
        "data_mode": "real_provider", "network_enabled": bool(cfg.get("network_enabled")),
        "provider_enabled": bool(cfg.get("provider_enabled")), "allow_real_request": bool(cfg.get("allow_real_request")),
        "will_fetch_real_data": bool(cfg.get("network_enabled") and cfg.get("provider_enabled") and cfg.get("allow_real_request")),
        "allow_commit_to_repo": False,
    }


def validate_fund_nav_real_request(request: Mapping[str, Any]) -> bool:
    return not scan_asset_for_sensitive_values(request) and not scan_provider_config_for_secrets(request) and request.get("allow_commit_to_repo") is False


def _provider_checks(config: Mapping[str, Any], provider_name: str) -> dict[str, Any]:
    candidate = _candidate(provider_name) or {}
    mapping = candidate.get("field_mapping") or {}
    return {
        "network_enabled": bool(config.get("network_enabled")), "provider_enabled": bool(config.get("provider_enabled")),
        "allow_real_request": bool(config.get("allow_real_request")), "allow_commit_to_repo": False,
        "cache_scope": config.get("cache_scope", "local_only"),
        "daily_nav_mapping_ready": bool(mapping.get("daily_nav_fields", NAV_FIELDS)),
        "estimated_nav_mapping_ready": bool(mapping.get("estimated_nav_fields", ESTIMATE_FIELDS)),
        "provider_safety_ready": not validate_fund_nav_real_provider_config(config),
    }


def _base_result(item: Mapping[str, Any] | FundNavRequest, status: str, reason: str = "", provider_name: str = "eastmoney_fund", config: Mapping[str, Any] | None = None, nav: Mapping[str, Any] | None = None, estimate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    cfg = dict(config or build_fund_nav_real_provider_config(provider_name))
    req = build_fund_nav_real_request(item, provider_name, cfg)
    source_status = "real_provider" if status == "real_provider_available" else status
    result = {**{k: req[k] for k in ("request_id", "asset_id", "code", "name", "type", "market", "provider_name")},
        "data_status": status, "data_mode": "real_provider", "has_real_nav_data": status == "real_provider_available",
        "will_fetch_real_data": bool(req["will_fetch_real_data"]), "allow_commit_to_repo": False,
        "nav": {**_empty_nav(), **dict(nav or {})}, "estimate": {**_empty_estimate(), **dict(estimate or {})},
        "source": {"provider": provider_name, "provider_type": cfg.get("provider_type", "public_web"), "source_status": source_status, "checked_at": _utc_now_iso(), "delay_note": DELAY_NOTE},
        "provider_checks": _provider_checks(cfg, provider_name), "warnings": [NO_REPO_WARNING, FUND_ESTIMATE_WARNING],
        "disclaimer": DISCLAIMER, "reason": reason}
    if status != "real_provider_available":
        result["has_real_nav_data"] = False
    if reason:
        result["warnings"].append(reason)
    return result


def build_fund_nav_real_provider_disabled_result(item, reason): return _base_result(item, "disabled_by_default", reason)
def build_fund_nav_real_provider_unsupported_result(item, reason): return _base_result(item, "unsupported", reason)
def build_fund_nav_real_provider_invalid_request_result(item, reason): return _base_result(item, "invalid_request", reason)
def build_fund_nav_real_provider_error_result(item, error): return _base_result(item, "provider_error", str(error))
def build_fund_nav_real_provider_timeout_result(item, error): return _base_result(item, "provider_timeout", str(error))


def normalize_fund_nav_real_response(raw_response: Mapping[str, Any], request: Mapping[str, Any], provider_name: str) -> dict[str, Any]:
    if not isinstance(raw_response, Mapping):
        return _base_result(request, "invalid_response", "provider response is not a mapping", provider_name)
    status = str(raw_response.get("source_status") or raw_response.get("provider_status") or "ok")
    if status in {"stale", "stale_data"}:
        return _base_result(request, "stale_data", str(raw_response.get("reason") or "provider returned stale data"), provider_name)
    if status == "conflict":
        return _base_result(request, "conflict", str(raw_response.get("warning") or "provider returned conflicting data"), provider_name)
    has_nav = "nav" in raw_response
    has_estimate = "estimate" in raw_response
    if not has_nav and not has_estimate:
        return _base_result(request, "invalid_response", "provider response missing nav and estimate", provider_name)
    nav = {field: (raw_response.get("nav") or {}).get(field) for field in NAV_FIELDS}
    estimate = {field: (raw_response.get("estimate") or {}).get(field) for field in ESTIMATE_FIELDS}
    data_status = "real_provider_available"
    reason = "real provider response normalized in memory only"
    if not has_nav:
        data_status, reason = "daily_nav_unavailable", "daily_nav missing; estimate normalized only"
    elif not has_estimate:
        data_status, reason = "estimate_unavailable", "estimate missing; daily_nav normalized only"
    return _base_result(request, data_status, reason, provider_name, nav=nav, estimate=estimate)


class FundNavRealProvider:
    name = "fund_nav_real_provider"
    provider_type = "public_web"

    def __init__(self, provider_name: str = "eastmoney_fund", config: Mapping[str, Any] | None = None, fetcher: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None) -> None:
        self.provider_name = provider_name
        base = build_fund_nav_real_provider_config(provider_name)
        self.config = {**base, **dict(config or {})}
        self.fetcher = fetcher

    def supports_market(self, market: str) -> bool:
        return _is_cn_market(market)

    def supports_item(self, item: FundNavRequest) -> bool:
        return isinstance(item, FundNavRequest) and item.type == "fund" and self.supports_market(item.market)

    def fetch_one(self, item: Mapping[str, Any] | FundNavRequest) -> dict[str, Any]:
        data = _data(item); asset_type = normalize_asset_type(data.get("type"))
        if asset_type == "unknown":
            return _base_result(item, "invalid_request", "资产类型 unknown，无法生成基金净值 real-provider 请求。", self.provider_name, self.config)
        if asset_type != "fund":
            return _base_result(item, "unsupported", UNSUPPORTED_REASONS.get(asset_type, "该资产类型不进入基金净值 provider。"), self.provider_name, self.config)
        if not _is_cn_market(data.get("market") or "CN"):
            return _base_result(item, "unsupported", "非 CN 市场基金暂不进入场外基金净值 real-provider。", self.provider_name, self.config)
        if validate_fund_nav_real_provider_config(self.config):
            return _base_result(item, "provider_policy_blocked", "; ".join(validate_fund_nav_real_provider_config(self.config)), self.provider_name, self.config)
        if not (self.config.get("network_enabled") and self.config.get("provider_enabled") and self.config.get("allow_real_request")):
            return _base_result(item, "disabled_by_default", DEFAULT_OFF_WARNING, self.provider_name, self.config)
        req = build_fund_nav_real_request(item, self.provider_name, self.config)
        if self.fetcher is None:
            return _base_result(item, "provider_error", "未配置真实 fetcher", self.provider_name, self.config)
        try:
            raw = self.fetcher(req)
        except TimeoutError as exc:
            return _base_result(item, "provider_timeout", str(exc), self.provider_name, self.config)
        except Exception as exc:  # keep single-fund failure isolated
            return _base_result(item, "provider_error", str(exc), self.provider_name, self.config)
        result = normalize_fund_nav_real_response(raw, req, self.provider_name)
        result["provider_checks"] = _provider_checks(self.config, self.provider_name)
        result["will_fetch_real_data"] = True
        return result

    def fetch_many(self, items: list[Mapping[str, Any] | FundNavRequest]) -> list[dict[str, Any]]:
        return [self.fetch_one(item) for item in items]


def fetch_fund_nav_real(item, provider=None, config=None):
    provider_obj = provider if isinstance(provider, FundNavRealProvider) else FundNavRealProvider(config=config, fetcher=provider if callable(provider) else None)
    return provider_obj.fetch_one(item)


def fetch_fund_navs_real(items, provider=None, config=None):
    return [fetch_fund_nav_real(item, provider, config) for item in items]


def validate_fund_nav_real_result(result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("data_status") not in REAL_STATUSES: errors.append("unsupported real-provider data_status")
    if result.get("allow_commit_to_repo") is not False: errors.append("real result must not allow repo commits")
    if not (result.get("source") or {}).get("checked_at"): errors.append("real result requires checked_at")
    if not (result.get("source") or {}).get("source_status"): errors.append("real result requires source_status")
    if not result.get("provider_checks"): errors.append("real result requires provider_checks")
    if scan_provider_config_for_secrets(result) or scan_asset_for_sensitive_values(result): errors.append("real result contains sensitive values")
    errors.extend(validate_provider_result(result))
    return errors


def summarize_fund_nav_real_results(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("data_status") or "unknown"); counts[status] = counts.get(status, 0) + 1
    return {"summary_type": "fund_nav_real_summary", "data_mode": "real_provider", "total": len(results), "status_counts": counts, "results": list(results), "warnings": [DEFAULT_OFF_WARNING, NO_REPO_WARNING, CI_WARNING, FUND_ESTIMATE_WARNING]}


def render_fund_nav_real_markdown(result_or_summary: Mapping[str, Any]) -> str:
    result = (result_or_summary.get("results") or [{}])[0] if result_or_summary.get("summary_type") == "fund_nav_real_summary" else result_or_summary
    checks = result.get("provider_checks", {}); source = result.get("source", {})
    return "\n".join([
        "# 场外基金净值 Provider Real-request Minimal Demo", "", "## 1. Provider 信息",
        f"- provider：{result.get('provider_name', '')}", f"- provider 类型：{source.get('provider_type', '')}",
        f"- 数据模式：{result.get('data_mode', '')}", f"- 是否联网启用：{str(checks.get('network_enabled', False)).lower()}",
        f"- 是否真实请求启用：{str(checks.get('allow_real_request', False)).lower()}", "- 是否允许写入仓库：false", "",
        "## 2. 请求状态", f"- 基金：{result.get('name') or result.get('asset_id') or result.get('code')}",
        f"- 类型：{result.get('type', '')}", f"- 市场：{result.get('market', '')}", f"- data_status：{result.get('data_status', '')}",
        f"- source_status：{source.get('source_status', '')}", "", "## 3. 安全检查",
        f"- network_enabled：{str(checks.get('network_enabled', False)).lower()}", f"- provider_enabled：{str(checks.get('provider_enabled', False)).lower()}",
        f"- allow_real_request：{str(checks.get('allow_real_request', False)).lower()}", "- allow_commit_to_repo：false",
        f"- cache_scope：{checks.get('cache_scope', 'local_only')}", "", "## 4. 数据说明",
        DEFAULT_OFF_WARNING, NO_REPO_WARNING, CI_WARNING, FUND_ESTIMATE_WARNING,
    ]) + "\n"
