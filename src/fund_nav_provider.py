"""Offline fund NAV / estimated NAV provider framework.

This module defines fixture-only contracts for off-exchange funds. It does not
connect to external providers, read user configuration, persist real NAV values,
or return real estimated changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from src.asset_model import normalize_asset_type, normalize_market, scan_asset_for_sensitive_values
from src.quote_capability import get_quote_capability

DATA_STATUSES = frozenset({
    "available",
    "unavailable",
    "unsupported",
    "stale",
    "provider_error",
    "invalid_request",
    "estimate_only",
    "daily_nav_only",
})
FIXTURE_SOURCE_STATUS = "fixture_only"
ESTIMATE_WARNING = "场外基金盘中估算仅供观察，最终以基金公司公布净值为准。"
FIXTURE_DELAY_NOTE = "本阶段为 mock / fixture 数据，不代表真实基金净值。"
DISCLAIMER = "场外基金不支持真正实时价格，本结果仅用于验证净值 / 估算净值框架。"

UNSUPPORTED_REASONS = {
    "etf": "ETF 属于交易所交易品种，应使用股票 / ETF 实时行情框架。",
    "stock": "股票应使用实时行情框架。",
    "index": "指数应使用 index_quote 框架。",
    "company": "企业本身不是基金净值对象。",
    "industry": "行业 / 主题本阶段不直接获取基金净值。",
    "theme": "行业 / 主题本阶段不直接获取基金净值。",
}


@dataclass(frozen=True)
class FundNavRequest:
    request_id: str
    asset_id: str
    code: str
    name: str
    type: str = "fund"
    market: str = "CN"
    price_mode: str = "estimated_nav_or_daily_nav"
    requires_realtime: bool = False
    requires_daily_nav: bool = True
    requires_estimated_nav: bool = True
    provider_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class FundNavResult:
    request_id: str
    asset_id: str
    code: str
    name: str
    type: str
    market: str
    price_mode: str
    data_status: str
    nav: Mapping[str, Any] = field(default_factory=dict)
    estimate: Mapping[str, Any] = field(default_factory=dict)
    source: Mapping[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=lambda: [ESTIMATE_WARNING])
    disclaimer: str = DISCLAIMER
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "asset_id": self.asset_id,
            "code": self.code,
            "name": self.name,
            "type": self.type,
            "market": self.market,
            "price_mode": self.price_mode,
            "data_status": self.data_status,
            "nav": dict(self.nav),
            "estimate": dict(self.estimate),
            "source": dict(self.source),
            "warnings": list(self.warnings),
            "disclaimer": self.disclaimer,
            "reason": self.reason,
        }


class FundNavProvider(Protocol):
    name: str
    provider_type: str

    def supports_market(self, market: str) -> bool: ...
    def supports_item(self, item: FundNavRequest) -> bool: ...
    def fetch_one(self, request: FundNavRequest) -> FundNavResult: ...
    def fetch_many(self, requests: list[FundNavRequest]) -> list[FundNavResult]: ...


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _empty_nav() -> dict[str, Any]:
    return {"unit_nav": None, "accumulated_nav": None, "daily_change_pct": None, "nav_date": None}


def _empty_estimate() -> dict[str, Any]:
    return {"estimated_nav": None, "estimated_change_pct": None, "estimated_change_amount": None, "estimate_time": None}


def _source(provider: str, provider_type: str, checked_at: str | None = None, source_status: str = FIXTURE_SOURCE_STATUS) -> dict[str, Any]:
    return {"provider": provider, "provider_type": provider_type, "source_status": source_status, "checked_at": checked_at or _utc_now_iso(), "delay_note": FIXTURE_DELAY_NOTE}


def normalize_fund_code(asset: Mapping[str, Any]) -> str:
    return str(asset.get("code") or "").strip()


def is_fund_nav_supported(asset: Mapping[str, Any]) -> bool:
    if normalize_asset_type(asset.get("type")) != "fund":
        return False
    capability = get_quote_capability(dict(asset))
    return bool(capability.get("daily_nav_supported") or capability.get("intraday_estimate_supported"))


def build_fund_nav_request(asset: Mapping[str, Any]) -> FundNavRequest:
    asset_type = normalize_asset_type(asset.get("type"))
    if asset_type != "fund" or not is_fund_nav_supported(asset):
        raise ValueError("only supported fund assets can build FundNavRequest")
    capability = get_quote_capability(dict(asset))
    return FundNavRequest(
        request_id=str(asset.get("asset_id") or normalize_fund_code(asset)),
        asset_id=str(asset.get("asset_id") or ""),
        code=normalize_fund_code(asset),
        name=str(asset.get("name") or ""),
        type="fund",
        market=normalize_market(asset.get("market") or "CN"),
        price_mode=str(capability.get("price_mode") or "estimated_nav_or_daily_nav"),
        requires_realtime=False,
        requires_daily_nav=bool(capability.get("daily_nav_supported")),
        requires_estimated_nav=bool(capability.get("intraday_estimate_supported")),
        provider_hint=asset.get("provider_hint"),
    )


def build_fund_nav_requests(assets: list[Mapping[str, Any]]) -> list[FundNavRequest]:
    return [build_fund_nav_request(asset) for asset in assets if is_fund_nav_supported(asset)]


def _asset_result(asset: Mapping[str, Any], status: str, reason: str, provider: str = "fund_nav_framework", provider_type: str = "framework") -> FundNavResult:
    asset_type = normalize_asset_type(asset.get("type"))
    return FundNavResult(
        request_id=str(asset.get("asset_id") or asset.get("code") or ""),
        asset_id=str(asset.get("asset_id") or ""),
        code=str(asset.get("code") or ""),
        name=str(asset.get("name") or ""),
        type=asset_type,
        market=normalize_market(asset.get("market")),
        price_mode="unknown" if status == "invalid_request" else "unsupported",
        data_status=status,
        nav=_empty_nav(),
        estimate=_empty_estimate(),
        source=_source(provider, provider_type),
        reason=reason,
    )


def build_unsupported_fund_nav_result(asset: Mapping[str, Any], reason: str | None = None) -> FundNavResult:
    asset_type = normalize_asset_type(asset.get("type"))
    if asset_type == "unknown":
        return _asset_result(asset, "invalid_request", reason or "资产类型 unknown，无法生成基金净值请求。")
    return _asset_result(asset, "unsupported", reason or UNSUPPORTED_REASONS.get(asset_type, "该资产类型不进入基金净值框架。"))


def build_fund_nav_provider_error_result(asset: Mapping[str, Any] | FundNavRequest, error: Exception | str) -> FundNavResult:
    data = asset.to_dict() if isinstance(asset, FundNavRequest) else dict(asset)
    return FundNavResult(str(data.get("request_id") or data.get("asset_id") or ""), str(data.get("asset_id") or ""), str(data.get("code") or ""), str(data.get("name") or ""), normalize_asset_type(data.get("type", "fund")), normalize_market(data.get("market")), str(data.get("price_mode") or "estimated_nav_or_daily_nav"), "provider_error", _empty_nav(), _empty_estimate(), _source("fund_nav_framework", "framework", source_status="provider_error"), reason=f"provider error: {error}")


class FixtureFundNavProvider:
    name = "fixture_fund_nav"
    provider_type = "fixture"

    def __init__(self, fixture_status_by_code: Mapping[str, str] | None = None) -> None:
        self._statuses = {str(k): str(v) for k, v in (fixture_status_by_code or {}).items()}

    def supports_market(self, market: str) -> bool:
        return normalize_market(market) in {"CN", "HK", "US", "JP", "KR", "GLOBAL", "unknown"}

    def supports_item(self, item: FundNavRequest) -> bool:
        return isinstance(item, FundNavRequest) and item.type == "fund" and self.supports_market(item.market)

    def fetch_one(self, request: FundNavRequest) -> FundNavResult:
        checked_at = _utc_now_iso()
        if not self.supports_item(request):
            return build_fund_nav_provider_error_result(request, "invalid FundNavRequest")
        findings = scan_asset_for_sensitive_values(request.to_dict())
        if findings or not request.code:
            return FundNavResult(request.request_id, request.asset_id, request.code, request.name, request.type, request.market, request.price_mode, "invalid_request", _empty_nav(), _empty_estimate(), _source(self.name, self.provider_type, checked_at), reason="request is invalid or contains sensitive values")
        status = self._statuses.get(request.code, "available")
        if status == "provider_error":
            raise RuntimeError("fixture provider_error")
        nav = _empty_nav()
        estimate = _empty_estimate()
        if status in {"available", "daily_nav_only"}:
            nav = {"unit_nav": "fixture_unit_nav", "accumulated_nav": "fixture_accumulated_nav", "daily_change_pct": "fixture_daily_change_pct", "nav_date": "fixture_nav_date"}
        if status in {"available", "estimate_only"}:
            estimate = {"estimated_nav": "fixture_estimated_nav", "estimated_change_pct": "fixture_estimated_change_pct", "estimated_change_amount": "fixture_estimated_change_amount", "estimate_time": "fixture_estimate_time"}
        if status not in DATA_STATUSES:
            status = "unavailable"
        return FundNavResult(request.request_id, request.asset_id, request.code, request.name, request.type, request.market, request.price_mode, status, nav, estimate, _source(self.name, self.provider_type, checked_at), reason="fixture-only fund NAV placeholder")

    def fetch_many(self, requests: list[FundNavRequest]) -> list[FundNavResult]:
        results = []
        for request in requests:
            try:
                results.append(self.fetch_one(request))
            except Exception as exc:  # provider isolation for partial failures
                results.append(build_fund_nav_provider_error_result(request, exc))
        return results


class MockFundNavProvider(FixtureFundNavProvider):
    name = "mock_fund_nav"


def fetch_fund_nav(asset: Mapping[str, Any], provider: FundNavProvider | None = None) -> FundNavResult:
    asset_type = normalize_asset_type(asset.get("type"))
    if asset_type == "unknown":
        return build_unsupported_fund_nav_result(asset)
    if not is_fund_nav_supported(asset):
        return build_unsupported_fund_nav_result(asset)
    active_provider = provider or MockFundNavProvider()
    try:
        return active_provider.fetch_one(build_fund_nav_request(asset))
    except Exception as exc:
        return build_fund_nav_provider_error_result(build_fund_nav_request(asset), exc)


def fetch_fund_navs(assets: list[Mapping[str, Any]], provider: FundNavProvider | None = None) -> dict[str, Any]:
    active_provider = provider or MockFundNavProvider()
    results = [fetch_fund_nav(asset, active_provider) for asset in assets]
    return {"status": "empty" if not results else summarize_fund_nav_results(results)["status"], "results": [r.to_dict() for r in results], "summary": summarize_fund_nav_results(results)}


def validate_fund_nav_result(result: FundNavResult | Mapping[str, Any]) -> bool:
    data = result.to_dict() if isinstance(result, FundNavResult) else dict(result)
    if data.get("data_status") not in DATA_STATUSES:
        return False
    source = data.get("source") or {}
    return bool(source.get("provider") and source.get("checked_at") and source.get("source_status"))


def validate_fund_nav_results(results: list[FundNavResult | Mapping[str, Any]]) -> bool:
    return all(validate_fund_nav_result(result) for result in results)


def summarize_fund_nav_results(results: list[FundNavResult | Mapping[str, Any]]) -> dict[str, Any]:
    data = [r.to_dict() if isinstance(r, FundNavResult) else dict(r) for r in results]
    counts = {status: sum(1 for item in data if item.get("data_status") == status) for status in DATA_STATUSES}
    available_like = counts["available"] + counts["estimate_only"] + counts["daily_nav_only"]
    status = "empty" if not data else ("partial_available" if available_like and available_like < len(data) else ("available" if available_like == len(data) else "unavailable"))
    return {
        "status": status,
        "total": len(data),
        "available_count": counts["available"],
        "estimate_only_count": counts["estimate_only"],
        "daily_nav_only_count": counts["daily_nav_only"],
        "unsupported_count": counts["unsupported"],
        "unavailable_count": counts["unavailable"],
        "provider_error_count": counts["provider_error"],
        "invalid_request_count": counts["invalid_request"],
        "has_real_nav_data": False,
        "data_mode": FIXTURE_SOURCE_STATUS,
        "warnings": ["本阶段为 fixture 数据，不代表真实基金净值。"],
    }


def render_fund_nav_result_markdown(result: FundNavResult | Mapping[str, Any]) -> str:
    data = result.to_dict() if isinstance(result, FundNavResult) else dict(result)
    nav = data.get("nav") or {}
    estimate = data.get("estimate") or {}
    source = data.get("source") or {}
    def v(value: Any) -> str:
        return "-" if value in {None, ""} else str(value)
    return "\n".join([
        "# 场外基金净值 / 估算净值 Demo",
        "",
        "## 1. 基金信息",
        f"- 基金名称：{v(data.get('name'))}",
        f"- 基金代码：{v(data.get('code'))}",
        f"- 数据状态：{v(data.get('data_status'))}",
        "",
        "## 2. 每日净值",
        f"- 单位净值：{v(nav.get('unit_nav'))}",
        f"- 累计净值：{v(nav.get('accumulated_nav'))}",
        f"- 净值日期：{v(nav.get('nav_date'))}",
        f"- 日涨跌幅：{v(nav.get('daily_change_pct'))}",
        "",
        "## 3. 盘中估算",
        f"- 估算净值：{v(estimate.get('estimated_nav'))}",
        f"- 估算涨跌：{v(estimate.get('estimated_change_pct'))}",
        f"- 估算时间：{v(estimate.get('estimate_time'))}",
        "",
        "## 4. 数据说明",
        "- 场外基金不支持真正实时价格。",
        "- 盘中估算仅供观察，最终以基金公司公布净值为准。",
        "- 本阶段为 mock / fixture 数据，不代表真实基金净值。",
        f"- 来源：{v(source.get('provider'))} / {v(source.get('source_status'))}",
    ])
