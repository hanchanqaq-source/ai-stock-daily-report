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


def _install_fake_config(monkeypatch, *, enabled=False, fail=False):
    import sys
    import types

    module = types.ModuleType("src.config")

    def get_config():
        if fail:
            raise AssertionError("get_config must not be called")
        return types.SimpleNamespace(enable_eastmoney_patch=enabled)

    module.get_config = get_config
    monkeypatch.setitem(sys.modules, "src.config", module)
    return module


def _install_fake_eastmoney_patch(monkeypatch):
    import sys
    import types

    calls = []
    module = types.ModuleType("src.patches.eastmoney_patch")

    def eastmoney_patch():
        calls.append("called")

    module.eastmoney_patch = eastmoney_patch
    monkeypatch.setitem(sys.modules, "src.patches.eastmoney_patch", module)
    return calls


def test_create_akshare_only_manager_passes_explicit_patch_false(monkeypatch):
    from data_provider import akshare_fetcher

    seen = []

    class FakeAkshareFetcher:
        name = "AkshareFetcher"

        def __init__(self, *args, **kwargs):
            seen.append((args, kwargs))

    monkeypatch.setattr(akshare_fetcher, "AkshareFetcher", FakeAkshareFetcher)
    manager = m.create_akshare_only_manager()

    assert [fetcher.__class__.__name__ for fetcher in manager._fetchers] == ["FakeAkshareFetcher"]
    assert seen == [((), {"enable_eastmoney_patch": False})]


def test_core_m3_manager_does_not_call_config_or_patch_even_with_provider_env(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "fake-token")
    monkeypatch.setenv("TICKFLOW_API_KEY", "fake-key")
    monkeypatch.setenv("LONGBRIDGE_APP_KEY", "fake-app-key")
    monkeypatch.setenv("LONGBRIDGE_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("LONGBRIDGE_ACCESS_TOKEN", "fake-access-token")
    monkeypatch.setenv("ENABLE_EASTMONEY_PATCH", "true")
    _install_fake_config(monkeypatch, fail=True)
    calls = _install_fake_eastmoney_patch(monkeypatch)

    manager = m.create_akshare_only_manager()

    assert [fetcher.__class__.__name__ for fetcher in manager._fetchers] == ["AkshareFetcher"]
    assert calls == []


def test_akshare_fetcher_patch_false_does_not_call_config_or_patch(monkeypatch):
    from data_provider.akshare_fetcher import AkshareFetcher

    _install_fake_config(monkeypatch, fail=True)
    calls = _install_fake_eastmoney_patch(monkeypatch)

    fetcher = AkshareFetcher(enable_eastmoney_patch=False)

    assert fetcher.sleep_min == 2.0
    assert fetcher.sleep_max == 5.0
    assert calls == []


def test_akshare_fetcher_patch_true_calls_patch_without_config(monkeypatch):
    from data_provider.akshare_fetcher import AkshareFetcher

    _install_fake_config(monkeypatch, fail=True)
    calls = _install_fake_eastmoney_patch(monkeypatch)

    AkshareFetcher(enable_eastmoney_patch=True)

    assert calls == ["called"]


@pytest.mark.parametrize(
    ("config_enabled", "expected_calls"),
    [(False, []), (True, ["called"])],
)
def test_akshare_fetcher_patch_none_keeps_config_behavior(monkeypatch, config_enabled, expected_calls):
    from data_provider.akshare_fetcher import AkshareFetcher

    _install_fake_config(monkeypatch, enabled=config_enabled)
    calls = _install_fake_eastmoney_patch(monkeypatch)

    AkshareFetcher(enable_eastmoney_patch=None)

    assert calls == expected_calls


def test_akshare_fetcher_sleep_args_are_unchanged(monkeypatch):
    from data_provider.akshare_fetcher import AkshareFetcher

    _install_fake_config(monkeypatch, enabled=False)

    positional = AkshareFetcher(0.1, 0.2)
    keyword = AkshareFetcher(sleep_min=0.3, sleep_max=0.4)

    assert (positional.sleep_min, positional.sleep_max) == (0.1, 0.2)
    assert (keyword.sleep_min, keyword.sleep_max) == (0.3, 0.4)


def test_public_market_readonly_static_config_boundary():
    import ast
    from pathlib import Path

    source = Path(m.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_names = {
        "get_config",
        "ENABLE_EASTMONEY_PATCH",
        "TUSHARE_TOKEN",
        "TICKFLOW_API_KEY",
        "LONGBRIDGE",
        "FINNHUB",
        "ALPHAVANTAGE",
        "Cookie",
        "Authorization",
    }

    imported_modules = []
    literal_values = []
    call_keywords = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported_modules.append(node.module or "")
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            literal_values.append(node.value)
        elif isinstance(node, ast.Call):
            call_keywords.extend(keyword.arg for keyword in node.keywords if keyword.arg)

    checked_text = "\n".join(imported_modules + literal_values)
    for forbidden in forbidden_names:
        assert forbidden not in checked_text
    assert "src.config" not in imported_modules
    assert "enable_eastmoney_patch" in call_keywords
    assert "AkshareFetcher(enable_eastmoney_patch=False)" in source
