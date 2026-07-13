import ast
import asyncio
import math
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src import public_market_readonly as m

REQ = {"mode":"real-readonly-dry-run","provider":"akshare-public-market","market":"cn-a","instrumentType":"stock","symbol":"600519","humanApproved":True,"readOnly":True,"allowAccountRead":False,"allowTrading":False,"allowNotificationSend":False,"allowAiCall":False,"allowPersistence":False}


def frame():
    return pd.DataFrame([
        {"date":"2026-07-10","open":10,"high":12,"low":9,"close":11,"volume":100,"amount":1000},
        {"date":"2026-07-13","open":11,"high":13,"low":10,"close":12,"volume":200,"amount":2400},
    ])


class Manager:
    called = False
    provider_name = "AkshareFetcher"

    def get_daily_data(self, *a, **k):
        self.called = True
        return frame(), self.provider_name


def test_create_akshare_only_manager_only_contains_akshare(monkeypatch):
    def fail_default(self):
        raise AssertionError("default fetchers must not be initialized")

    monkeypatch.setattr(m.DataFetcherManager, "_init_default_fetchers", fail_default)
    manager = m.create_akshare_only_manager()
    names = [fetcher.__class__.__name__ for fetcher in manager._fetchers]
    assert names == ["AkshareFetcher"]


@pytest.mark.parametrize("envs", [
    {"TUSHARE_TOKEN":"fake"},
    {"TICKFLOW_API_KEY":"fake"},
    {"LONGBRIDGE_APP_KEY":"fake","LONGBRIDGE_APP_SECRET":"fake","LONGBRIDGE_ACCESS_TOKEN":"fake"},
])
def test_foreign_provider_credentials_do_not_change_akshare_only_manager(monkeypatch, envs):
    for key, value in envs.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(m.DataFetcherManager, "_init_default_fetchers", lambda self: (_ for _ in ()).throw(AssertionError("default fetchers called")))
    manager = m.create_akshare_only_manager()
    assert [fetcher.__class__.__name__ for fetcher in manager._fetchers] == ["AkshareFetcher"]


def test_default_disabled_does_not_create_or_call_provider(monkeypatch):
    monkeypatch.delenv("REAL_READONLY_PROVIDER_ENABLED", raising=False)
    monkeypatch.setattr(m, "create_akshare_only_manager", lambda: (_ for _ in ()).throw(AssertionError("manager created")))
    manager = Manager()
    result = m.run_public_market_readonly(REQ, manager)
    assert result["status"] == "blocked"
    assert manager.called is False


def test_unapproved_and_invalid_symbol_do_not_create_provider(monkeypatch):
    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED", "true")
    monkeypatch.setattr(m, "create_akshare_only_manager", lambda: (_ for _ in ()).throw(AssertionError("manager created")))
    assert m.run_public_market_readonly({**REQ, "humanApproved": False})["status"] == "invalid-response"
    assert m.run_public_market_readonly({**REQ, "symbol": "hk00700"})["status"] == "invalid-response"


def test_invalid_symbols_blocked():
    for symbol in ["hk00700", "600519,000001", "http://x", "../600519", "600 519"]:
        with pytest.raises(m.PublicMarketReadonlyError):
            m.validate_request({**REQ, "symbol": symbol})


def test_provider_success_sanitized(monkeypatch):
    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED", "true")
    result = m.run_public_market_readonly(REQ, Manager())
    assert result["status"] == "completed-real-readonly"
    snap = result["snapshot"]
    assert snap["providerLabel"] == "REDACTED_PROVIDER_LABEL"
    assert snap["sourceType"] == "real-readonly"
    assert "rawResponse" not in snap and "endpoint" not in snap and "token" not in snap
    assert snap["tradeDate"] == "2026-07-13"


@pytest.mark.parametrize("provider", ["EfinanceFetcher", "TushareFetcher", "TickFlowFetcher", "BaostockFetcher", "YfinanceFetcher", "", None, 123])
def test_provider_identity_mismatch_blocked_and_redacted(monkeypatch, provider):
    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED", "true")
    manager = Manager()
    manager.provider_name = provider
    result = m.run_public_market_readonly(REQ, manager)
    assert result == {"status":"blocked","errorCode":"real-readonly.provider-identity-mismatch","providerLabel":"REDACTED_PROVIDER_LABEL","readOnly":True,"redacted":True}
    assert str(provider) not in str(result)


def test_nan_and_price_range_blocked():
    good={"schemaVersion":"core-m3.public-market-readonly.v1","sourceType":"real-readonly","providerLabel":"REDACTED_PROVIDER_LABEL","market":"cn-a","instrumentType":"stock","symbol":"600519","instrumentName":"测试","tradeDate":"2026-07-13","open":1,"high":2,"low":1,"close":1.5,"previousClose":1,"changePercent":1,"volume":1,"amount":1,"delayed":True,"readOnly":True,"redacted":True}
    with pytest.raises(m.PublicMarketReadonlyError) as e:
        m.sanitize_public_market_readonly_snapshot({**good,"close":math.nan})
    assert e.value.code == m.ERROR_INVALID_NUMBER
    with pytest.raises(m.PublicMarketReadonlyError) as e:
        m.sanitize_public_market_readonly_snapshot({**good,"high":1,"low":2})
    assert e.value.code == m.ERROR_INVALID_PRICE_RANGE


def test_exception_low_sensitive(monkeypatch):
    class Bad:
        def get_daily_data(self,*a,**k): raise RuntimeError("secret token traceback /tmp/path")
    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED","true")
    result=m.run_public_market_readonly(REQ, Bad())
    assert result["status"] == "blocked"
    assert result["errorCode"] == "real-readonly.provider-failed"
    assert "secret" not in str(result).lower()
    assert "traceback" not in str(result).lower()
    assert "/tmp" not in str(result).lower()


def test_backend_request_timeout_low_sensitive(monkeypatch):
    class Slow:
        def get_daily_data(self,*a,**k):
            time.sleep(0.05)
            return frame(), "AkshareFetcher"
    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED","true")
    result = asyncio.run(m.run_public_market_readonly_with_timeout(REQ, Slow(), timeout_seconds=0.001))
    assert result == {"status":"timeout","errorCode":"real-readonly.provider-timeout","providerLabel":"REDACTED_PROVIDER_LABEL","readOnly":True,"redacted":True}
    assert "traceback" not in str(result).lower()


def test_endpoint_local_no_side_effects(monkeypatch):
    monkeypatch.delenv("REAL_READONLY_PROVIDER_ENABLED", raising=False)
    client=TestClient(create_app())
    res=client.post("/api/v1/provider-readonly/akshare/dry-run", json=REQ)
    assert res.status_code == 200
    assert res.json()["status"] == "blocked"


def test_no_notification_ai_database_or_trading_modules_imported():
    source = Path(m.__file__)
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.lower())

    forbidden_roots = {"notification", "trading", "database", "openai", "anthropic"}
    assert not {
        module
        for module in imported_modules
        if any(module == root or module.startswith(f"{root}.") for root in forbidden_roots)
    }
