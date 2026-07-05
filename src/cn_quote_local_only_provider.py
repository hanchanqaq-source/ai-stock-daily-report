"""A股 / ETF provider local-only adapter.

This module verifies future CN provider response mapping with local fixtures only.
It never imports provider SDKs, performs network requests, reads user
configuration, writes caches, or returns real market values.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.cn_quote_dry_run_provider import _asset_type_and_reason, _item_to_mapping, _normalize_cn_market, _unsupported_reason
from src.provider_safety import assert_real_data_not_written_to_repo, scan_provider_config_for_secrets, validate_provider_config, validate_provider_result
from src.realtime_quote_provider import QuoteRequest

QUOTE_FIELDS = ("last_price", "change_pct", "change_amount", "volume", "turnover", "open", "high", "low", "previous_close")
SUPPORTED_TYPES = frozenset({"stock", "etf", "official_index"})
LOCAL_ONLY_STATUSES = frozenset({"local_only_available", "local_only_unavailable", "unsupported", "invalid_request", "provider_error", "invalid_response", "stale_data", "conflict"})
DISCLAIMER = "本阶段仅验证 A股 / ETF provider local-only 映射流程，不抓取真实行情。"
DELAY_NOTE = "本阶段仅做 local-only fixture 测试，不请求真实行情。"
WARNING = "本结果来自 local-only fixture，不代表真实行情。"
NO_VALUES_NOTE = "本结果不包含真实价格、涨跌幅或成交额。"
REAL_PROVIDER_NOTE = "local-only 结果不得被当作 real_provider 数据。"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _empty_quote() -> dict[str, None]:
    return {field: None for field in QUOTE_FIELDS}


def build_cn_quote_local_only_config(provider_name: str = "local_fixture") -> dict[str, Any]:
    return {
        "provider_name": provider_name,
        "provider_type": "fixture",
        "mode": "local_only",
        "data_mode": "fixture_only",
        "market": "CN",
        "network_enabled": False,
        "default_enabled": True,
        "will_fetch_real_data": False,
        "has_real_market_data": False,
        "allow_commit_to_repo": True,
        "cache_scope": "test_fixture_only",
        "source_status": "local_fixture_only",
        "fixture_path": None,
        "notes": ["本配置仅用于 local-only 测试，不请求真实行情。"],
    }


def validate_cn_quote_local_only_config(config: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if scan_provider_config_for_secrets(config):
        errors.append("local-only config contains secret fields")
    if config.get("network_enabled") is not False:
        errors.append("local-only config requires network_enabled=false")
    if config.get("will_fetch_real_data") is not False:
        errors.append("local-only config requires will_fetch_real_data=false")
    if config.get("has_real_market_data") is not False:
        errors.append("local-only config requires has_real_market_data=false")
    if config.get("source_status") not in {"local_fixture_only", "fixture_only"}:
        errors.append("local-only source_status must be fixture-only")
    if config.get("provider_type") not in {"fixture", "local_fixture", "mock"}:
        errors.append("local-only provider_type must be fixture/local_fixture/mock")
    safety_config = dict(config)
    if safety_config.get("provider_type") == "local_fixture":
        safety_config["provider_type"] = "fixture"
    errors.extend(validate_provider_config(safety_config))
    try:
        assert_real_data_not_written_to_repo(dict(config))
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def build_cn_quote_local_only_fixture() -> dict[str, Any]:
    return {
        "data_mode": "local_only_fixture",
        "has_real_market_data": False,
        "source_status": "local_fixture_only",
        "rows": [
            {"asset_id": "demo_stock_001", "code": "000001", "symbol": "000001", "name": "示例股票A", "type": "stock", "market": "CN", "provider_symbol": "demo_stock_001", "provider_status": "ok", "quote": _empty_quote()},
            {"asset_id": "demo_etf_001", "code": "000000", "symbol": "000000", "name": "示例ETF", "type": "etf", "market": "CN", "provider_symbol": "demo_etf_001", "provider_status": "ok", "quote": _empty_quote()},
            {"asset_id": "demo_index_001", "code": "DEMOA", "symbol": "DEMOA", "name": "示例指数", "type": "official_index", "market": "CN", "provider_symbol": "demo_index_001", "provider_status": "ok", "quote": _empty_quote()},
        ],
    }


def load_cn_quote_local_only_fixture(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        return build_cn_quote_local_only_fixture()
    with Path(path).open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    return fixture


def validate_cn_quote_local_only_fixture(fixture: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if fixture.get("data_mode") != "local_only_fixture":
        errors.append("fixture data_mode must be local_only_fixture")
    if fixture.get("has_real_market_data") is not False:
        errors.append("fixture must not contain real market data")
    if fixture.get("source_status") == "real_provider":
        errors.append("fixture cannot be real_provider")
    if scan_provider_config_for_secrets(fixture):
        errors.append("fixture contains secret fields")
    for row in fixture.get("rows", []):
        quote = row.get("quote", {})
        if any(quote.get(field) is not None for field in QUOTE_FIELDS):
            errors.append("fixture quote fields must be null")
    return errors


def build_cn_quote_local_only_request(asset_or_request: Any, provider_name: str = "local_fixture") -> dict[str, Any]:
    asset = _item_to_mapping(asset_or_request)
    asset_type, _ = _asset_type_and_reason(asset)
    symbol = str(asset.get("symbol") or asset.get("code") or "").strip()
    asset_id = str(asset.get("asset_id") or asset.get("request_id") or symbol or "").strip()
    return {"request_id": str(asset.get("request_id") or asset_id or symbol), "asset_id": asset_id, "code": str(asset.get("code") or symbol), "symbol": symbol, "name": str(asset.get("name") or ""), "type": asset_type, "market": _normalize_cn_market(asset.get("market")), "provider_name": provider_name, "data_mode": "local_only_fixture", "network_enabled": False, "will_fetch_real_data": False, "has_real_market_data": False}


def _provider_checks(config: Mapping[str, Any]) -> dict[str, Any]:
    return {"network_enabled": False, "will_fetch_real_data": False, "has_real_market_data": False, "allow_commit_to_repo": True, "cache_scope": config.get("cache_scope", "test_fixture_only"), "field_mapping_ready": True, "provider_safety_ready": not validate_cn_quote_local_only_config(config)}


def _base_result(item: Any, data_status: str, reason: str = "", provider_name: str = "local_fixture", row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    request = build_cn_quote_local_only_request(item, provider_name)
    checked_at = _utc_now_iso()
    config = build_cn_quote_local_only_config(provider_name)
    quote = dict(row.get("quote", _empty_quote())) if row else _empty_quote()
    result = {**{k: request[k] for k in ("request_id", "asset_id", "code", "symbol", "name", "type", "market", "provider_name")}, "data_status": data_status, "data_mode": "local_only_fixture", "has_real_market_data": False, "will_fetch_real_data": False, "quote": quote, "source": {"provider": provider_name, "provider_type": "fixture", "source_status": "local_fixture_only", "checked_at": checked_at, "delay_note": DELAY_NOTE}, "provider_checks": _provider_checks(config), "warnings": [WARNING], "reason": reason, "disclaimer": DISCLAIMER}
    if row:
        for key in ("stale_reason", "warning"):
            if row.get(key):
                result["warnings"].append(str(row[key]))
    if reason:
        result["warnings"].append(reason)
    return result


def build_local_only_unsupported_result(item: Any, reason: str) -> dict[str, Any]:
    return _base_result(item, "unsupported", reason)


def build_local_only_invalid_request_result(item: Any, reason: str) -> dict[str, Any]:
    return _base_result(item, "invalid_request", reason)


def build_local_only_provider_error_result(item: Any, error: str) -> dict[str, Any]:
    return _base_result(item, "provider_error", error)


def normalize_cn_quote_local_only_row(row: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    required = {"asset_id", "code", "symbol", "name", "type", "market", "provider_symbol", "provider_status", "quote"}
    missing = sorted(required - set(row))
    if missing:
        return _base_result(request, "invalid_response", "fixture row missing fields: " + ", ".join(missing), row=row)
    quote = row.get("quote")
    if not isinstance(quote, Mapping) or any(field not in quote for field in QUOTE_FIELDS):
        return _base_result(request, "invalid_response", "fixture row quote missing unified fields", row=row)
    if any(quote.get(field) is not None for field in QUOTE_FIELDS):
        return _base_result(request, "invalid_response", "local-only quote fields must not contain real values", row=row)
    status = str(row.get("provider_status") or "ok")
    data_status = {"ok": "local_only_available", "error": "provider_error", "stale": "stale_data", "conflict": "conflict"}.get(status, "invalid_response")
    item = {**dict(request), **{k: row.get(k) for k in ("asset_id", "code", "symbol", "name", "type", "market")}}
    return _base_result(item, data_status, str(row.get("error") or row.get("stale_reason") or row.get("warning") or ""), row=row)


def _find_row(fixture: Mapping[str, Any], request: Mapping[str, Any]) -> Mapping[str, Any] | None:
    keys = {request.get("asset_id"), request.get("symbol"), request.get("code")}
    for row in fixture.get("rows", []):
        if {row.get("asset_id"), row.get("symbol"), row.get("code")} & keys:
            return row
    return None


def fetch_cn_quote_local_only(item: Any, provider: Any = None) -> dict[str, Any]:
    provider_obj = provider if isinstance(provider, CnQuoteLocalOnlyProvider) else CnQuoteLocalOnlyProvider(fixture=provider if isinstance(provider, Mapping) else None)
    return provider_obj.fetch_quote(item)


def fetch_cn_quotes_local_only(items: list[Any], provider: Any = None) -> list[dict[str, Any]]:
    return [fetch_cn_quote_local_only(item, provider) for item in items]


def validate_cn_quote_local_only_result(result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("data_status") not in LOCAL_ONLY_STATUSES:
        errors.append("unsupported local-only data_status")
    if result.get("data_status") == "available":
        errors.append("local-only result cannot be available")
    if result.get("has_real_market_data") is not False or result.get("will_fetch_real_data") is not False:
        errors.append("local-only result cannot contain or fetch real market data")
    if result.get("source", {}).get("source_status") == "real_provider":
        errors.append("local-only source cannot be real_provider")
    quote = result.get("quote", {})
    if set(QUOTE_FIELDS) - set(quote):
        errors.append("local-only quote missing unified fields")
    if any(quote.get(field) is not None for field in QUOTE_FIELDS):
        errors.append("local-only quote fields must be null")
    if scan_provider_config_for_secrets(result):
        errors.append("local-only result contains sensitive values")
    errors.extend(validate_provider_result({"provider_type": "fixture", "data_mode": "fixture_only", **dict(result)}))
    return errors


def summarize_cn_quote_local_only_results(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("data_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {"summary_type": "cn_quote_local_only_summary", "data_mode": "local_only_fixture", "has_real_market_data": False, "will_fetch_real_data": False, "total": len(results), "status_counts": counts, "results": list(results), "disclaimer": DISCLAIMER}


def render_cn_quote_local_only_markdown(result_or_summary: Mapping[str, Any]) -> str:
    result = result_or_summary
    if result_or_summary.get("summary_type") == "cn_quote_local_only_summary":
        result = (result_or_summary.get("results") or [{}])[0]
    checks = result.get("provider_checks", {})
    source = result.get("source", {})
    lines = ["# A股 / ETF Provider Local-only Demo", "", "## 1. Provider 信息", f"- provider：{result.get('provider_name', '')}", f"- provider 类型：{source.get('provider_type', '')}", f"- 数据模式：{result.get('data_mode', '')}", f"- 是否联网：{str(checks.get('network_enabled', False)).lower()}", "- 是否真实行情：false", "", "## 2. 映射结果", f"- 资产：{result.get('name') or result.get('asset_id') or result.get('symbol')}", f"- 类型：{result.get('type', '')}", f"- 市场：{result.get('market', '')}", f"- data_status：{result.get('data_status', '')}", f"- source_status：{source.get('source_status', '')}", "- 是否包含真实行情：false", "", "## 3. 字段映射", "- last_price：未填充", "- change_pct：未填充", "- volume：未填充", "- turnover：未填充", f"- checked_at：{source.get('checked_at', '')}", "", "## 4. 数据说明", f"- {DELAY_NOTE}", f"- {NO_VALUES_NOTE}", f"- {REAL_PROVIDER_NOTE}"]
    return "\n".join(lines) + "\n"


class CnQuoteLocalOnlyProvider:
    """QuoteProvider-compatible local-only provider backed by fixture rows."""

    def __init__(self, provider_name: str = "local_fixture", fixture: Mapping[str, Any] | None = None) -> None:
        self.provider_name = provider_name
        self.fixture = dict(fixture or build_cn_quote_local_only_fixture())

    def fetch_quote(self, request: Any) -> dict[str, Any]:
        req = build_cn_quote_local_only_request(request, self.provider_name)
        asset = _item_to_mapping(request)
        asset_type, index_reason = _asset_type_and_reason(asset)
        if asset_type == "unknown":
            return build_local_only_invalid_request_result(request, "unknown asset type is invalid for local-only request。")
        if req["market"] != "CN":
            return build_local_only_unsupported_result(request, "非 CN 市场资产不进入 A股 / ETF quote provider。")
        if asset_type in {"fund", "company", "industry", "theme", "computed_indicator"}:
            return build_local_only_unsupported_result(request, _unsupported_reason(asset_type))
        if index_reason:
            return build_local_only_unsupported_result(request, index_reason.replace("dry-run plan", "local-only provider"))
        if asset_type not in SUPPORTED_TYPES:
            return build_local_only_unsupported_result(request, _unsupported_reason(asset_type))
        fixture_errors = validate_cn_quote_local_only_fixture(self.fixture)
        if fixture_errors:
            return _base_result(request, "invalid_response", "; ".join(fixture_errors), self.provider_name)
        row = _find_row(self.fixture, req)
        if not row:
            return _base_result(request, "local_only_unavailable", "local-only fixture row not found", self.provider_name)
        result = normalize_cn_quote_local_only_row(row, req)
        errors = validate_cn_quote_local_only_result(result)
        if errors:
            return _base_result(request, "invalid_response", "; ".join(errors), self.provider_name, row=row)
        return result

    def fetch_quotes(self, requests: list[Any]) -> list[dict[str, Any]]:
        return [self.fetch_quote(request) for request in requests]

    def fetch_one(self, item: Any) -> dict[str, Any]:
        return self.fetch_quote(item)

    def fetch_many(self, items: list[Any]) -> list[dict[str, Any]]:
        return self.fetch_quotes(items)
