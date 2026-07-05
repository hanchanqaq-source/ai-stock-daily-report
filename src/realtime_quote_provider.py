"""Offline realtime quote provider framework.

This module defines contracts and fixture-only providers for future stock / ETF /
official-index realtime quote fetching. It intentionally does not connect to any
external data source, read user configuration, persist quote values, or return
real prices, percentage changes, or turnover values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from src.asset_model import normalize_asset_type, normalize_market, scan_asset_for_sensitive_values

SUPPORTED_QUOTE_TYPES = frozenset({"stock", "etf", "index", "official_index"})
UNSUPPORTED_SOURCE_STATUS = frozenset({"unsupported", "invalid_request", "provider_error"})
DISCLAIMER = "本框架仅返回离线 fixture / mock 状态，不抓取、不保存真实价格、真实涨跌幅或真实成交额。"
FUND_UNSUPPORTED_MESSAGE = "fund 不进入实时行情框架；后续应走 NAV / 净值模块。"
COMPUTED_UNSUPPORTED_MESSAGE = "computed_indicator 为系统计算指标，不能直接抓取 quote。"


@dataclass(frozen=True)
class QuoteRequest:
    """Public-safe quote request for one stock / ETF / official index."""

    symbol: str
    asset_type: str
    market: str = "unknown"
    name: str = ""
    request_id: str = ""
    item_type: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def normalized_asset_type(self) -> str:
        item_type = str(self.item_type or "").strip().lower()
        if item_type in {"official_index", "computed_indicator"}:
            return item_type
        return normalize_asset_type(self.asset_type)

    def normalized_market(self) -> str:
        return normalize_market(self.market)


@dataclass(frozen=True)
class QuoteResult:
    """Offline quote result without real market values."""

    request_id: str
    symbol: str
    asset_type: str
    market: str
    success: bool
    source_status: str
    provider: str
    checked_at: str
    disclaimer: str
    message: str = ""
    fixture_only: bool = True
    price: None = None
    change_pct: None = None
    turnover: None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "symbol": self.symbol,
            "asset_type": self.asset_type,
            "market": self.market,
            "success": self.success,
            "source_status": self.source_status,
            "provider": self.provider,
            "checked_at": self.checked_at,
            "disclaimer": self.disclaimer,
            "message": self.message,
            "fixture_only": self.fixture_only,
            "price": self.price,
            "change_pct": self.change_pct,
            "turnover": self.turnover,
        }


class QuoteProvider(Protocol):
    """Interface for offline-safe realtime quote providers."""

    provider_name: str

    def fetch_quote(self, request: QuoteRequest) -> QuoteResult:
        """Fetch one quote result without persisting data."""

    def fetch_quotes(self, requests: list[QuoteRequest]) -> list[QuoteResult]:
        """Fetch a batch of quote results, preserving partial failures."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _request_id(request: QuoteRequest) -> str:
    return request.request_id or request.symbol


def _validate_request(request: QuoteRequest, provider: str, checked_at: str) -> QuoteResult | None:
    if not isinstance(request, QuoteRequest):
        return QuoteResult("", "", "unknown", "unknown", False, "invalid_request", provider, checked_at, DISCLAIMER, "request must be QuoteRequest")
    findings = scan_asset_for_sensitive_values({
        "symbol": request.symbol,
        "name": request.name,
        "request_id": request.request_id,
        "metadata": dict(request.metadata),
    })
    if findings:
        return QuoteResult(_request_id(request), request.symbol, request.normalized_asset_type(), request.normalized_market(), False, "invalid_request", provider, checked_at, DISCLAIMER, "request contains sensitive values")
    if not str(request.symbol or "").strip():
        return QuoteResult(_request_id(request), request.symbol, request.normalized_asset_type(), request.normalized_market(), False, "invalid_request", provider, checked_at, DISCLAIMER, "symbol is required")
    return None


class FixtureQuoteProvider:
    """Deterministic fixture provider for tests and UI wiring."""

    provider_name = "fixture_quote_provider"

    def __init__(self, fixture_status_by_symbol: Mapping[str, str] | None = None) -> None:
        self._fixture_status_by_symbol = {str(k).upper(): str(v) for k, v in (fixture_status_by_symbol or {}).items()}

    def fetch_quote(self, request: QuoteRequest) -> QuoteResult:
        checked_at = _utc_now_iso()
        invalid = _validate_request(request, self.provider_name, checked_at)
        if invalid:
            return invalid

        asset_type = request.normalized_asset_type()
        market = request.normalized_market()
        if asset_type == "fund":
            return QuoteResult(_request_id(request), request.symbol, asset_type, market, False, "unsupported", self.provider_name, checked_at, DISCLAIMER, FUND_UNSUPPORTED_MESSAGE)
        if asset_type == "computed_indicator":
            return QuoteResult(_request_id(request), request.symbol, asset_type, market, False, "unsupported", self.provider_name, checked_at, DISCLAIMER, COMPUTED_UNSUPPORTED_MESSAGE)
        if asset_type not in SUPPORTED_QUOTE_TYPES:
            return QuoteResult(_request_id(request), request.symbol, asset_type, market, False, "unsupported", self.provider_name, checked_at, DISCLAIMER, "asset type is not supported by realtime quote framework")

        fixture_status = self._fixture_status_by_symbol.get(request.symbol.upper(), "fixture_only")
        if fixture_status == "provider_error":
            return QuoteResult(_request_id(request), request.symbol, asset_type, market, False, "provider_error", self.provider_name, checked_at, DISCLAIMER, "fixture provider_error")
        if fixture_status in {"invalid_request", "unsupported"}:
            return QuoteResult(_request_id(request), request.symbol, asset_type, market, False, fixture_status, self.provider_name, checked_at, DISCLAIMER, f"fixture {fixture_status}")
        return QuoteResult(_request_id(request), request.symbol, asset_type, market, True, "fixture_only", self.provider_name, checked_at, DISCLAIMER, "fixture-only quote placeholder")

    def fetch_quotes(self, requests: list[QuoteRequest]) -> list[QuoteResult]:
        return [self.fetch_quote(request) for request in requests]


class MockQuoteProvider(FixtureQuoteProvider):
    """Named mock provider backed by fixture-only behavior."""

    provider_name = "mock_quote_provider"


def fetch_realtime_quotes(requests: list[QuoteRequest], provider: QuoteProvider | None = None) -> list[QuoteResult]:
    """Batch-fetch offline quote placeholders, preserving per-request status."""

    active_provider = provider or MockQuoteProvider()
    return active_provider.fetch_quotes(requests)
