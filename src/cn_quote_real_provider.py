"""A股 / ETF real-provider minimal gated adapter.

The adapter is intentionally disabled by default. It only calls an injected
fetcher when network_enabled, provider_enabled and allow_real_request are all
explicitly true, and it never persists provider responses.
"""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from src.cn_quote_dry_run_provider import _asset_type_and_reason, _item_to_mapping, _normalize_cn_market, _unsupported_reason
from src.provider_registry import get_provider_evaluation
from src.provider_safety import assert_real_data_not_written_to_repo, scan_provider_config_for_secrets, validate_provider_config, validate_provider_result
from src.realtime_quote_provider import QuoteRequest

QUOTE_FIELDS = ("last_price", "change_pct", "change_amount", "volume", "turnover", "open", "high", "low", "previous_close")
SUPPORTED_TYPES = frozenset({"stock", "etf", "official_index"})
REAL_PROVIDER_STATUSES = frozenset({"real_provider_available", "disabled_by_default", "provider_policy_blocked", "unsupported", "invalid_request", "provider_error", "provider_timeout", "invalid_response", "stale_data", "conflict"})
DISCLAIMER = "本结果来自显式启用的真实 provider，仅用于本地观察。"
DELAY_NOTE = "真实 provider 数据仅允许本地显式启用后使用，不写入 public 仓库。"
WARNING = "真实 provider 结果不得写入 public 仓库。"
DEFAULT_DISABLED_WARNING = "真实 provider 默认关闭，必须显式开启 network_enabled、provider_enabled 和 allow_real_request。"

Fetcher = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _empty_quote() -> dict[str, None]:
    return {field: None for field in QUOTE_FIELDS}


def build_cn_quote_real_provider_config(provider_name: str = "akshare") -> dict[str, Any]:
    return {
        "provider_name": provider_name,
        "provider_type": "public_web_or_library",
        "mode": "real_provider",
        "data_mode": "real_provider",
        "market": "CN",
        "network_enabled": False,
        "provider_enabled": False,
        "enabled": False,
        "allow_real_request": False,
        "default_enabled": False,
        "allow_commit_to_repo": False,
        "cache_scope": "local_only",
        "timeout_seconds": 10,
        "retry_limit": 0,
        "retry": 0,
        "rate_limit": "manual_local_only",
        "source_status": "real_provider_disabled",
        "notes": [DEFAULT_DISABLED_WARNING],
    }


def validate_cn_quote_real_provider_config(config: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if scan_provider_config_for_secrets(config):
        errors.append("real provider config contains secret fields")
    provider_name = str(config.get("provider_name") or "")
    try:
        candidate = get_provider_evaluation(provider_name)
    except KeyError:
        errors.append("provider must be registered in provider_registry")
        candidate = None
    if candidate and candidate.get("status") == "verified":
        errors.append("provider must not be marked verified")
    if config.get("default_enabled") is not False:
        errors.append("real provider default_enabled must be false")
    if config.get("allow_commit_to_repo") is not False:
        errors.append("real provider results cannot be committed to public repo")
    if config.get("cache_scope") != "local_only":
        errors.append("real provider cache_scope must be local_only")
    safety_config = dict(config)
    safety_config["enabled"] = bool(config.get("provider_enabled"))
    errors.extend(validate_provider_config(safety_config))
    try:
        assert_real_data_not_written_to_repo({"has_real_market_data": False, "allow_commit_to_repo": config.get("allow_commit_to_repo")})
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def _gates_open(config: Mapping[str, Any]) -> bool:
    return config.get("network_enabled") is True and config.get("provider_enabled") is True and config.get("allow_real_request") is True


def build_cn_quote_real_request(asset_or_request: Any, provider_name: str = "akshare", config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    asset = _item_to_mapping(asset_or_request)
    asset_type, _ = _asset_type_and_reason(asset)
    symbol = str(asset.get("symbol") or asset.get("code") or "").strip()
    asset_id = str(asset.get("asset_id") or asset.get("request_id") or symbol or "").strip()
    active_config = dict(config or build_cn_quote_real_provider_config(provider_name))
    return {
        "request_id": str(asset.get("request_id") or asset_id or symbol),
        "asset_id": asset_id,
        "code": str(asset.get("code") or symbol),
        "symbol": symbol,
        "name": str(asset.get("name") or ""),
        "type": asset_type,
        "market": _normalize_cn_market(asset.get("market")),
        "provider_name": provider_name,
        "data_mode": "real_provider",
        "network_enabled": active_config.get("network_enabled") is True,
        "provider_enabled": active_config.get("provider_enabled") is True,
        "allow_real_request": active_config.get("allow_real_request") is True,
        "will_fetch_real_data": _gates_open(active_config),
        "allow_commit_to_repo": False,
    }


def validate_cn_quote_real_request(request: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(request, Mapping):
        return ["request must be a mapping"]
    if request.get("allow_commit_to_repo") is not False:
        errors.append("real provider request cannot allow repo writes")
    if scan_provider_config_for_secrets(request):
        errors.append("real provider request contains secret fields")
    if request.get("will_fetch_real_data") is True and not (request.get("network_enabled") is True and request.get("provider_enabled") is True and request.get("allow_real_request") is True):
        errors.append("real provider request requires all explicit gates")
    return errors


def _provider_checks(config: Mapping[str, Any], safety_errors: list[str] | None = None) -> dict[str, Any]:
    return {
        "network_enabled": config.get("network_enabled") is True,
        "provider_enabled": config.get("provider_enabled") is True,
        "allow_real_request": config.get("allow_real_request") is True,
        "allow_commit_to_repo": False,
        "cache_scope": config.get("cache_scope", "local_only"),
        "field_mapping_ready": True,
        "provider_safety_ready": not bool(safety_errors if safety_errors is not None else validate_cn_quote_real_provider_config(config)),
    }


def _base_result(item: Any, data_status: str, reason: str = "", provider_name: str = "akshare", config: Mapping[str, Any] | None = None, quote: Mapping[str, Any] | None = None) -> dict[str, Any]:
    active_config = dict(config or build_cn_quote_real_provider_config(provider_name))
    request = build_cn_quote_real_request(item, provider_name, active_config)
    safety_errors = validate_cn_quote_real_provider_config(active_config)
    source_status = "real_provider" if data_status == "real_provider_available" else data_status
    warnings = [WARNING]
    if not _gates_open(active_config):
        warnings.insert(0, DEFAULT_DISABLED_WARNING)
    if reason:
        warnings.append(reason)
    return {
        **{key: request[key] for key in ("request_id", "asset_id", "code", "symbol", "name", "type", "market", "provider_name")},
        "data_status": data_status,
        "data_mode": "real_provider",
        "has_real_market_data": data_status == "real_provider_available",
        "will_fetch_real_data": _gates_open(active_config),
        "allow_commit_to_repo": False,
        "quote": {field: (quote or _empty_quote()).get(field) for field in QUOTE_FIELDS},
        "source": {"provider": provider_name, "provider_type": active_config.get("provider_type", "public_web_or_library"), "source_status": source_status, "checked_at": _utc_now_iso(), "delay_note": DELAY_NOTE},
        "provider_checks": _provider_checks(active_config, safety_errors),
        "warnings": warnings,
        "reason": reason,
        "disclaimer": DISCLAIMER,
    }


def build_real_provider_disabled_result(item: Any, reason: str) -> dict[str, Any]:
    return _base_result(item, "disabled_by_default", reason)


def build_real_provider_unsupported_result(item: Any, reason: str) -> dict[str, Any]:
    return _base_result(item, "unsupported", reason)


def build_real_provider_invalid_request_result(item: Any, reason: str) -> dict[str, Any]:
    return _base_result(item, "invalid_request", reason)


def build_real_provider_error_result(item: Any, error: str) -> dict[str, Any]:
    return _base_result(item, "provider_error", str(error))


def build_real_provider_timeout_result(item: Any, error: str) -> dict[str, Any]:
    return _base_result(item, "provider_timeout", str(error))


def normalize_cn_quote_real_response(raw_response: Mapping[str, Any], request: Mapping[str, Any], provider_name: str) -> dict[str, Any]:
    config = dict(request.get("config") or build_cn_quote_real_provider_config(provider_name))
    config.update({"network_enabled": request.get("network_enabled"), "provider_enabled": request.get("provider_enabled"), "allow_real_request": request.get("allow_real_request")})
    if not isinstance(raw_response, Mapping):
        return _base_result(request, "invalid_response", "provider response must be a mapping", provider_name, config)
    status = str(raw_response.get("source_status") or raw_response.get("provider_status") or "ok")
    if status in {"stale", "stale_data"}:
        return _base_result(request, "stale_data", str(raw_response.get("reason") or "provider returned stale data"), provider_name, config)
    if status == "conflict":
        return _base_result(request, "conflict", str(raw_response.get("reason") or "provider returned conflicting data"), provider_name, config)
    quote = raw_response.get("quote", raw_response)
    if not isinstance(quote, Mapping) or any(field not in quote for field in QUOTE_FIELDS):
        return _base_result(request, "invalid_response", "provider response quote missing unified fields", provider_name, config)
    return _base_result({**dict(request), **{k: raw_response.get(k, request.get(k)) for k in ("asset_id", "code", "symbol", "name", "type", "market")}}, "real_provider_available", "", provider_name, config, quote)


class CnQuoteRealProvider:
    """QuoteProvider-compatible real provider shell with explicit local gates."""

    def __init__(self, provider_name: str = "akshare", config: Mapping[str, Any] | None = None, fetcher: Fetcher | None = None) -> None:
        self.provider_name = provider_name
        self.config = {**build_cn_quote_real_provider_config(provider_name), **dict(config or {})}
        self.fetcher = fetcher

    def fetch_quote(self, request: Any) -> dict[str, Any]:
        req = build_cn_quote_real_request(request, self.provider_name, self.config)
        asset = _item_to_mapping(request)
        asset_type, index_reason = _asset_type_and_reason(asset)
        if asset_type == "unknown":
            return _base_result(request, "invalid_request", "unknown asset type is invalid for real provider request。", self.provider_name, self.config)
        if req["market"] != "CN":
            return _base_result(request, "unsupported", "非 CN 市场资产不进入 A股 / ETF quote provider。", self.provider_name, self.config)
        if asset_type in {"fund", "company", "industry", "theme", "computed_indicator"}:
            return _base_result(request, "unsupported", _unsupported_reason(asset_type), self.provider_name, self.config)
        if index_reason:
            return _base_result(request, "unsupported", index_reason.replace("dry-run plan", "real provider"), self.provider_name, self.config)
        if asset_type not in SUPPORTED_TYPES:
            return _base_result(request, "unsupported", _unsupported_reason(asset_type), self.provider_name, self.config)
        config_errors = validate_cn_quote_real_provider_config(self.config)
        if config_errors:
            return _base_result(request, "provider_policy_blocked", "; ".join(config_errors), self.provider_name, self.config)
        if not _gates_open(self.config):
            return _base_result(request, "disabled_by_default", "network_enabled、provider_enabled 和 allow_real_request 必须同时为 true。", self.provider_name, self.config)
        request_errors = validate_cn_quote_real_request(req)
        if request_errors:
            return _base_result(request, "invalid_request", "; ".join(request_errors), self.provider_name, self.config)
        if self.fetcher is None:
            return _base_result(request, "provider_error", "未配置真实 fetcher。", self.provider_name, self.config)
        try:
            raw_response = self.fetcher({**req, "config": dict(self.config)})
        except (TimeoutError, socket.timeout) as exc:
            return _base_result(request, "provider_timeout", str(exc) or "provider timeout", self.provider_name, self.config)
        except Exception as exc:  # provider failures must not crash the batch
            return _base_result(request, "provider_error", str(exc) or exc.__class__.__name__, self.provider_name, self.config)
        result = normalize_cn_quote_real_response(raw_response, {**req, "config": dict(self.config)}, self.provider_name)
        errors = validate_cn_quote_real_result(result)
        if errors:
            return _base_result(request, "invalid_response", "; ".join(errors), self.provider_name, self.config)
        return result

    def fetch_quotes(self, requests: list[Any]) -> list[dict[str, Any]]:
        return [self.fetch_quote(request) for request in requests]

    def fetch_one(self, item: Any) -> dict[str, Any]:
        return self.fetch_quote(item)

    def fetch_many(self, items: list[Any]) -> list[dict[str, Any]]:
        return self.fetch_quotes(items)


def fetch_cn_quote_real(item: Any, provider: Any = None, config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    provider_obj = provider if isinstance(provider, CnQuoteRealProvider) else CnQuoteRealProvider(config=config, fetcher=provider if callable(provider) else None)
    return provider_obj.fetch_quote(item)


def fetch_cn_quotes_real(items: list[Any], provider: Any = None, config: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    provider_obj = provider if isinstance(provider, CnQuoteRealProvider) else CnQuoteRealProvider(config=config, fetcher=provider if callable(provider) else None)
    return provider_obj.fetch_quotes(items)


def validate_cn_quote_real_result(result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("data_status") not in REAL_PROVIDER_STATUSES:
        errors.append("unsupported real provider data_status")
    if result.get("allow_commit_to_repo") is not False:
        errors.append("real provider result cannot allow repo writes")
    if result.get("provider_checks", {}).get("cache_scope") != "local_only":
        errors.append("real provider result cache_scope must be local_only")
    quote = result.get("quote", {})
    if set(QUOTE_FIELDS) - set(quote):
        errors.append("real provider quote missing unified fields")
    if scan_provider_config_for_secrets(result):
        errors.append("real provider result contains sensitive values")
    if result.get("data_status") == "real_provider_available":
        if result.get("has_real_market_data") is not True:
            errors.append("available real provider result must mark has_real_market_data=true")
        for field in ("provider", "checked_at", "source_status"):
            if not (result.get(field) or result.get("source", {}).get(field)):
                errors.append(f"real provider result requires {field}")
    errors.extend(validate_provider_result({"provider_type": result.get("source", {}).get("provider_type", "public_web_or_library"), **dict(result)}))
    return errors


def summarize_cn_quote_real_results(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("data_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {"summary_type": "cn_quote_real_summary", "data_mode": "real_provider", "has_real_market_data": any(item.get("has_real_market_data") is True for item in results), "allow_commit_to_repo": False, "total": len(results), "status_counts": counts, "results": list(results), "disclaimer": DISCLAIMER}


def render_cn_quote_real_markdown(result_or_summary: Mapping[str, Any]) -> str:
    result = result_or_summary
    if result_or_summary.get("summary_type") == "cn_quote_real_summary":
        result = (result_or_summary.get("results") or [{}])[0]
    checks = result.get("provider_checks", {})
    source = result.get("source", {})
    lines = [
        "# A股 / ETF Provider Real-request Minimal Demo",
        "",
        "## 1. Provider 信息",
        f"- provider：{result.get('provider_name', '')}",
        f"- provider 类型：{source.get('provider_type', '')}",
        f"- 数据模式：{result.get('data_mode', '')}",
        f"- 是否联网启用：{str(checks.get('network_enabled', False)).lower()}",
        f"- 是否真实请求启用：{str(checks.get('allow_real_request', False)).lower()}",
        "- 是否允许写入仓库：false",
        "",
        "## 2. 请求状态",
        f"- 资产：{result.get('name') or result.get('asset_id') or result.get('symbol')}",
        f"- 类型：{result.get('type', '')}",
        f"- 市场：{result.get('market', '')}",
        f"- data_status：{result.get('data_status', '')}",
        f"- source_status：{source.get('source_status', '')}",
        "",
        "## 3. 安全检查",
        f"- network_enabled：{str(checks.get('network_enabled', False)).lower()}",
        f"- provider_enabled：{str(checks.get('provider_enabled', False)).lower()}",
        f"- allow_real_request：{str(checks.get('allow_real_request', False)).lower()}",
        "- allow_commit_to_repo：false",
        f"- cache_scope：{checks.get('cache_scope', 'local_only')}",
        "",
        "## 4. 数据说明",
        f"- {DEFAULT_DISABLED_WARNING}",
        f"- {WARNING}",
        "- CI 测试不会请求真实行情。",
    ]
    return "\n".join(lines) + "\n"
