import asyncio
import math
import time

import pandas as pd
import pytest

from src import public_market_readonly as m

REQ = {
    "mode": "real-readonly-dry-run",
    "provider": "akshare-public-market",
    "market": "cn-a",
    "instrumentType": "stock",
    "symbol": "600519",
    "humanApproved": True,
    "readOnly": True,
    "allowAccountRead": False,
    "allowTrading": False,
    "allowNotificationSend": False,
    "allowAiCall": False,
    "allowPersistence": False,
}


def frame():
    return pd.DataFrame([
        {"date": "2026-07-10", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 100, "amount": 1000},
        {"date": "2026-07-13", "open": 11, "high": 13, "low": 10, "close": 12, "volume": 200, "amount": 2400},
    ])


class Manager:
    def __init__(self, provider_name="AkshareFetcher"):
        self.called = False
        self.provider_name = provider_name

    def get_daily_data(self, *args, **kwargs):
        self.called = True
        return frame(), self.provider_name


def test_create_akshare_only_manager_only_contains_akshare(monkeypatch):
    def fail_default(self):
        raise AssertionError("default fetchers must not be initialized")

    monkeypatch.setattr(m.DataFetcherManager, "_init_default_fetchers", fail_default)
    manager = m.create_akshare_only_manager()
    assert [fetcher.__class__.__name__ for fetcher in manager._fetchers] == ["AkshareFetcher"]


def test_default_disabled_does_not_call_provider(monkeypatch):
    monkeypatch.delenv("REAL_READONLY_PROVIDER_ENABLED", raising=False)
    manager = Manager()
    result = m.run_public_market_readonly(REQ, manager)
    assert result["status"] == "blocked"
    assert manager.called is False


@pytest.mark.parametrize(
    "provider_name",
    ["EfinanceFetcher", "TushareFetcher", "TickFlowFetcher", "BaostockFetcher", "YfinanceFetcher", None, 123],
)
def test_provider_identity_mismatch_is_blocked_and_redacted(monkeypatch, provider_name):
    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED", "true")
    result = m.run_public_market_readonly(REQ, Manager(provider_name))
    assert result["status"] == "blocked"
    assert result["errorCode"] == "real-readonly.provider-identity-mismatch"
    assert str(provider_name) not in str(result)


def test_provider_success_is_sanitized(monkeypatch):
    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED", "true")
    result = m.run_public_market_readonly(REQ, Manager())
    assert result["status"] == "completed-real-readonly"
    snapshot = result["snapshot"]
    assert snapshot["providerLabel"] == "REDACTED_PROVIDER_LABEL"
    assert snapshot["sourceType"] == "real-readonly"
    assert snapshot["tradeDate"] == "2026-07-13"


def test_invalid_numbers_and_ranges_are_blocked():
    good = {
        "schemaVersion": "core-m3.public-market-readonly.v1",
        "sourceType": "real-readonly",
        "providerLabel": "REDACTED_PROVIDER_LABEL",
        "market": "cn-a",
        "instrumentType": "stock",
        "symbol": "600519",
        "instrumentName": "测试",
        "tradeDate": "2026-07-13",
        "open": 1,
        "high": 2,
        "low": 1,
        "close": 1.5,
        "previousClose": 1,
        "changePercent": 1,
        "volume": 1,
        "amount": 1,
        "delayed": True,
        "readOnly": True,
        "redacted": True,
    }
    with pytest.raises(m.PublicMarketReadonlyError) as exc:
        m.sanitize_public_market_readonly_snapshot({**good, "close": math.nan})
    assert exc.value.code == m.ERROR_INVALID_NUMBER

    with pytest.raises(m.PublicMarketReadonlyError) as exc:
        m.sanitize_public_market_readonly_snapshot({**good, "high": 1, "low": 2})
    assert exc.value.code == m.ERROR_INVALID_PRICE_RANGE


def test_backend_timeout_returns_fixed_safe_result(monkeypatch):
    class SlowManager(Manager):
        def get_daily_data(self, *args, **kwargs):
            time.sleep(0.05)
            return frame(), "AkshareFetcher"

    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED", "true")
    result = asyncio.run(
        m.run_public_market_readonly_with_timeout(REQ, SlowManager(), timeout_seconds=0.001)
    )
    assert result == {
        "status": "timeout",
        "errorCode": "real-readonly.provider-timeout",
        "providerLabel": "REDACTED_PROVIDER_LABEL",
        "readOnly": True,
        "redacted": True,
    }
