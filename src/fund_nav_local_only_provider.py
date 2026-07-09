"""Off-exchange fund NAV provider local-only adapter.

This module verifies future fund NAV provider response mapping with local
fixtures only. It never performs network requests, reads user configuration,
writes caches, or returns real NAV / estimated NAV values.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from src.asset_model import normalize_asset_type, normalize_market, scan_asset_for_sensitive_values
from src.fund_nav_provider import FundNavRequest, _empty_estimate, _empty_nav
from src.fund_nav_dry_run_provider import UNSUPPORTED_REASONS as DRY_RUN_UNSUPPORTED_REASONS
from src.provider_safety import (
    FUND_ESTIMATE_WARNING,
    assert_real_data_not_written_to_repo,
    scan_provider_config_for_secrets,
    validate_provider_config,
    validate_provider_result,
)

NAV_FIELDS = ("unit_nav", "accumulated_nav", "daily_change_pct", "nav_date")
ESTIMATE_FIELDS = ("estimated_nav", "estimated_change_pct", "estimated_change_amount", "estimate_time")
LOCAL_ONLY_STATUSES = frozenset({
    "local_only_available",
    "local_only_unavailable",
    "unsupported",
    "invalid_request",
    "provider_error",
    "invalid_response",
    "stale_data",
    "conflict",
    "estimate_unavailable",
    "daily_nav_unavailable",
})
DISCLAIMER = "本阶段仅验证场外基金净值 provider local-only 映射流程，不抓取真实基金净值。"
DELAY_NOTE = "本阶段仅做 local-only fixture 测试，不请求真实基金净值。"
WARNING = "本结果来自 local-only fixture，不代表真实基金净值。"
NO_VALUES_NOTE = "本结果不包含真实单位净值、估算净值或涨跌幅。"
REAL_PROVIDER_NOTE = "local-only 结果不得被当作 real_provider 数据。"
ALLOWED_FIXTURE_NAMES = {"示例场外基金A", "示例场外基金B"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _data(item: Mapping[str, Any] | FundNavRequest) -> dict[str, Any]:
    return item.to_dict() if isinstance(item, FundNavRequest) else dict(item)


def _is_cn_market(market: Any) -> bool:
    return str(market or "").strip() in {"CN", "cn", "中国", "A股"} or normalize_market(market) == "CN"


def build_fund_nav_local_only_config(provider_name: str = "local_fund_nav_fixture") -> dict[str, Any]:
    return {
        "provider_name": provider_name,
        "provider_type": "fixture",
        "mode": "local_only",
        "data_mode": "fixture_only",
        "market": "CN",
        "network_enabled": False,
        "default_enabled": True,
        "will_fetch_real_data": False,
        "has_real_nav_data": False,
        "allow_commit_to_repo": False,
        "allow_fixture_definition_in_repo": True,
        "cache_scope": "test_fixture_only",
        "source_status": "local_fixture_only",
        "fixture_path": None,
        "notes": ["本配置仅用于 local-only 测试，不请求真实基金净值。"],
    }


def validate_fund_nav_local_only_config(config: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if scan_provider_config_for_secrets(config):
        errors.append("local-only config contains secret fields")
    if config.get("network_enabled") is not False:
        errors.append("local-only config requires network_enabled=false")
    if config.get("will_fetch_real_data") is not False:
        errors.append("local-only config requires will_fetch_real_data=false")
    if config.get("has_real_nav_data") is not False:
        errors.append("local-only config requires has_real_nav_data=false")
    if config.get("source_status") not in {"local_fixture_only", "fixture_only"}:
        errors.append("local-only source_status must be fixture-only")
    if config.get("provider_type") not in {"fixture", "local_fixture", "mock"}:
        errors.append("local-only provider_type must be fixture/local_fixture/mock")
    safety_config = dict(config)
    if safety_config.get("provider_type") == "local_fixture":
        safety_config["provider_type"] = "fixture"
    errors.extend(validate_provider_config(safety_config))
    try:
        assert_real_data_not_written_to_repo({"has_real_market_data": config.get("has_real_nav_data"), "allow_commit_to_repo": config.get("allow_commit_to_repo")})
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def build_fund_nav_local_only_fixture() -> dict[str, Any]:
    return {
        "data_mode": "local_only_fixture",
        "has_real_nav_data": False,
        "source_status": "local_fixture_only",
        "rows": [
            {"asset_id": "demo_fund_001", "code": "000000", "name": "示例场外基金A", "type": "fund", "market": "CN", "provider_symbol": "demo_cn_fund_001", "provider_status": "ok", "nav": _empty_nav(), "estimate": _empty_estimate()},
            {"asset_id": "demo_fund_002", "code": "000001", "name": "示例场外基金B", "type": "fund", "market": "CN", "provider_symbol": "demo_cn_fund_002", "provider_status": "ok", "nav": _empty_nav(), "estimate": _empty_estimate()},
        ],
    }


def load_fund_nav_local_only_fixture(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        return build_fund_nav_local_only_fixture()
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_fund_nav_local_only_fixture(fixture: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if fixture.get("data_mode") != "local_only_fixture":
        errors.append("fixture data_mode must be local_only_fixture")
    if fixture.get("has_real_nav_data") is not False:
        errors.append("fixture must not contain real NAV data")
    if fixture.get("source_status") == "real_provider":
        errors.append("fixture cannot be real_provider")
    if scan_provider_config_for_secrets(fixture):
        errors.append("fixture contains secret fields")
    for row in fixture.get("rows", []):
        if row.get("name") not in ALLOWED_FIXTURE_NAMES:
            errors.append("fixture may only use 示例场外基金A / 示例场外基金B")
        nav = row.get("nav", {})
        estimate = row.get("estimate", {})
        if any(nav.get(field) is not None for field in NAV_FIELDS) or any(estimate.get(field) is not None for field in ESTIMATE_FIELDS):
            errors.append("fixture NAV / estimate fields must be null")
    return errors


def build_fund_nav_local_only_request(asset_or_request: Mapping[str, Any] | FundNavRequest, provider_name: str = "local_fund_nav_fixture") -> dict[str, Any]:
    data = _data(asset_or_request)
    asset_type = normalize_asset_type(data.get("type"))
    code = str(data.get("code") or "").strip()
    asset_id = str(data.get("asset_id") or data.get("request_id") or code or "").strip()
    return {"request_id": str(data.get("request_id") or asset_id or code), "asset_id": asset_id, "code": code, "name": str(data.get("name") or ""), "type": asset_type, "market": normalize_market(data.get("market") or "CN"), "provider_name": provider_name, "data_mode": "local_only_fixture", "network_enabled": False, "will_fetch_real_data": False, "has_real_nav_data": False}


def _provider_checks(config: Mapping[str, Any]) -> dict[str, Any]:
    return {"network_enabled": False, "will_fetch_real_data": False, "has_real_nav_data": False, "allow_commit_to_repo": False, "allow_fixture_definition_in_repo": True, "cache_scope": config.get("cache_scope", "test_fixture_only"), "daily_nav_mapping_ready": True, "estimated_nav_mapping_ready": True, "provider_safety_ready": not validate_fund_nav_local_only_config(config)}


def _base_result(item: Mapping[str, Any] | FundNavRequest, data_status: str, reason: str = "", provider_name: str = "local_fund_nav_fixture", row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    request = build_fund_nav_local_only_request(item, provider_name)
    checked_at = _utc_now_iso()
    nav = dict(row.get("nav", _empty_nav())) if row else _empty_nav()
    estimate = dict(row.get("estimate", _empty_estimate())) if row else _empty_estimate()
    result = {**{k: request[k] for k in ("request_id", "asset_id", "code", "name", "type", "market", "provider_name")}, "data_status": data_status, "data_mode": "local_only_fixture", "has_real_nav_data": False, "will_fetch_real_data": False, "nav": nav, "estimate": estimate, "source": {"provider": provider_name, "provider_type": "fixture", "source_status": "local_fixture_only", "checked_at": checked_at, "delay_note": DELAY_NOTE}, "provider_checks": _provider_checks(build_fund_nav_local_only_config(provider_name)), "warnings": [WARNING, FUND_ESTIMATE_WARNING], "reason": reason, "disclaimer": DISCLAIMER}
    if row:
        for key in ("stale_reason", "warning"):
            if row.get(key):
                result["warnings"].append(str(row[key]))
    if reason:
        result["warnings"].append(reason)
    return result


def build_fund_nav_local_only_unsupported_result(item: Mapping[str, Any] | FundNavRequest, reason: str) -> dict[str, Any]:
    return _base_result(item, "unsupported", reason)


def build_fund_nav_local_only_invalid_request_result(item: Mapping[str, Any] | FundNavRequest, reason: str) -> dict[str, Any]:
    return _base_result(item, "invalid_request", reason)


def build_fund_nav_local_only_provider_error_result(item: Mapping[str, Any] | FundNavRequest, error: str) -> dict[str, Any]:
    return _base_result(item, "provider_error", error)


def normalize_fund_nav_local_only_row(row: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    required = {"asset_id", "code", "name", "type", "market", "provider_symbol", "provider_status", "nav", "estimate"}
    missing = sorted(required - set(row))
    if missing:
        return _base_result(request, "invalid_response", "fixture row missing fields: " + ", ".join(missing), row=row)
    nav = row.get("nav")
    estimate = row.get("estimate")
    if not isinstance(nav, Mapping) or any(field not in nav for field in NAV_FIELDS):
        return _base_result(request, "invalid_response", "fixture row nav missing unified fields", row=row)
    if not isinstance(estimate, Mapping) or any(field not in estimate for field in ESTIMATE_FIELDS):
        return _base_result(request, "invalid_response", "fixture row estimate missing unified fields", row=row)
    if any(nav.get(field) is not None for field in NAV_FIELDS) or any(estimate.get(field) is not None for field in ESTIMATE_FIELDS):
        return _base_result(request, "invalid_response", "local-only NAV / estimate fields must not contain real values", row=row)
    status = str(row.get("provider_status") or "ok")
    data_status = {
        "ok": "local_only_available",
        "error": "provider_error",
        "stale": "stale_data",
        "conflict": "conflict",
        "estimate_missing": "estimate_unavailable",
        "daily_nav_missing": "daily_nav_unavailable",
    }.get(status, "invalid_response")
    item = {**dict(request), **{k: row.get(k) for k in ("asset_id", "code", "name", "type", "market")}}
    return _base_result(item, data_status, str(row.get("error") or row.get("stale_reason") or row.get("warning") or ""), row=row)


def _find_row(fixture: Mapping[str, Any], request: Mapping[str, Any]) -> Mapping[str, Any] | None:
    keys = {request.get("asset_id"), request.get("code")}
    for row in fixture.get("rows", []):
        if {row.get("asset_id"), row.get("code")} & keys:
            return row
    return None


def _unsupported_reason(asset_type: str) -> str:
    return DRY_RUN_UNSUPPORTED_REASONS.get(asset_type, "该资产类型不进入基金净值 provider。")


def fetch_fund_nav_local_only(item: Mapping[str, Any] | FundNavRequest, provider: Any = None) -> dict[str, Any]:
    provider_obj = provider if isinstance(provider, FundNavLocalOnlyProvider) else FundNavLocalOnlyProvider(fixture=provider if isinstance(provider, Mapping) else None)
    return provider_obj.fetch_one(item)


def fetch_fund_navs_local_only(items: list[Mapping[str, Any] | FundNavRequest], provider: Any = None) -> list[dict[str, Any]]:
    return [fetch_fund_nav_local_only(item, provider) for item in items]


def validate_fund_nav_local_only_result(result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("data_status") not in LOCAL_ONLY_STATUSES:
        errors.append("unsupported local-only data_status")
    if result.get("data_status") == "available":
        errors.append("local-only result cannot be available")
    if result.get("has_real_nav_data") is not False or result.get("will_fetch_real_data") is not False:
        errors.append("local-only result cannot contain or fetch real NAV data")
    if result.get("source", {}).get("source_status") == "real_provider":
        errors.append("local-only source cannot be real_provider")
    nav = result.get("nav", {})
    estimate = result.get("estimate", {})
    if set(NAV_FIELDS) - set(nav):
        errors.append("local-only nav missing unified fields")
    if set(ESTIMATE_FIELDS) - set(estimate):
        errors.append("local-only estimate missing unified fields")
    if any(nav.get(field) is not None for field in NAV_FIELDS) or any(estimate.get(field) is not None for field in ESTIMATE_FIELDS):
        errors.append("local-only NAV / estimate fields must be null")
    if scan_provider_config_for_secrets(result) or scan_asset_for_sensitive_values(result):
        errors.append("local-only result contains sensitive values")
    errors.extend(validate_provider_result({"provider_type": "fixture", "data_mode": "fixture_only", **dict(result)}))
    return errors


def summarize_fund_nav_local_only_results(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("data_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {"summary_type": "fund_nav_local_only_summary", "data_mode": "local_only_fixture", "has_real_nav_data": False, "will_fetch_real_data": False, "total": len(results), "status_counts": counts, "results": list(results), "warnings": [WARNING, FUND_ESTIMATE_WARNING], "disclaimer": DISCLAIMER}


def render_fund_nav_local_only_markdown(result_or_summary: Mapping[str, Any]) -> str:
    result = result_or_summary
    if result_or_summary.get("summary_type") == "fund_nav_local_only_summary":
        result = (result_or_summary.get("results") or [{}])[0]
    checks = result.get("provider_checks", {})
    source = result.get("source", {})
    lines = [
        "# 场外基金净值 Provider Local-only Demo",
        "",
        "## 1. Provider 信息",
        f"- provider：{result.get('provider_name', '')}",
        f"- provider 类型：{source.get('provider_type', '')}",
        f"- 数据模式：{result.get('data_mode', '')}",
        f"- 是否联网：{str(checks.get('network_enabled', False)).lower()}",
        "- 是否真实基金净值：false",
        "",
        "## 2. 映射结果",
        f"- 基金：{result.get('name') or result.get('asset_id') or result.get('code')}",
        f"- 类型：{result.get('type', '')}",
        f"- 市场：{result.get('market', '')}",
        f"- data_status：{result.get('data_status', '')}",
        f"- source_status：{source.get('source_status', '')}",
        "- 是否包含真实基金净值：false",
        "",
        "## 3. 字段映射",
        "- unit_nav：未填充",
        "- accumulated_nav：未填充",
        "- daily_change_pct：未填充",
        "- nav_date：未填充",
        "- estimated_nav：未填充",
        "- estimated_change_pct：未填充",
        "- estimate_time：未填充",
        f"- checked_at：{source.get('checked_at', '')}",
        "",
        "## 4. 数据说明",
        f"- {DELAY_NOTE}",
        f"- {NO_VALUES_NOTE}",
        "- 场外基金不支持真正实时价格。",
        f"- {FUND_ESTIMATE_WARNING}",
        f"- {REAL_PROVIDER_NOTE}",
    ]
    return "\n".join(lines) + "\n"


class FundNavLocalOnlyProvider:
    """FundNavProvider-compatible local-only provider backed by fixture rows."""

    name = "fund_nav_local_only"
    provider_type = "fixture"

    def __init__(self, provider_name: str = "local_fund_nav_fixture", fixture: Mapping[str, Any] | None = None) -> None:
        self.provider_name = provider_name
        self.fixture = dict(fixture or build_fund_nav_local_only_fixture())

    def supports_market(self, market: str) -> bool:
        return _is_cn_market(market)

    def supports_item(self, item: FundNavRequest) -> bool:
        return isinstance(item, FundNavRequest) and item.type == "fund" and self.supports_market(item.market)

    def fetch_one(self, item: Mapping[str, Any] | FundNavRequest) -> dict[str, Any]:
        req = build_fund_nav_local_only_request(item, self.provider_name)
        data = _data(item)
        asset_type = normalize_asset_type(data.get("type"))
        if asset_type == "unknown":
            return build_fund_nav_local_only_invalid_request_result(item, "资产类型 unknown，无法生成基金净值 local-only 请求。")
        if asset_type != "fund":
            return build_fund_nav_local_only_unsupported_result(item, _unsupported_reason(asset_type))
        if not _is_cn_market(data.get("market") or req.get("market")):
            return build_fund_nav_local_only_unsupported_result(item, "非 CN 市场基金暂不进入场外基金净值 provider local-only。")
        fixture_errors = validate_fund_nav_local_only_fixture(self.fixture)
        if fixture_errors:
            return _base_result(item, "invalid_response", "; ".join(fixture_errors), self.provider_name)
        row = _find_row(self.fixture, req)
        if not row:
            return _base_result(item, "local_only_unavailable", "local-only fixture row not found", self.provider_name)
        result = normalize_fund_nav_local_only_row(row, req)
        errors = validate_fund_nav_local_only_result(result)
        if errors:
            return _base_result(item, "invalid_response", "; ".join(errors), self.provider_name, row=row)
        return result

    def fetch_many(self, items: list[Mapping[str, Any] | FundNavRequest]) -> list[dict[str, Any]]:
        return [self.fetch_one(item) for item in items]
