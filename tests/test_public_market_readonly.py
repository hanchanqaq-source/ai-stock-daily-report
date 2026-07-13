import math
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src import public_market_readonly as m

REQ={"mode":"real-readonly-dry-run","provider":"akshare-public-market","market":"cn-a","instrumentType":"stock","symbol":"600519","humanApproved":True,"readOnly":True,"allowAccountRead":False,"allowTrading":False,"allowNotificationSend":False,"allowAiCall":False,"allowPersistence":False}
class Manager:
    called=False
    def get_daily_data(self,*a,**k):
        self.called=True
        return pd.DataFrame([
            {"date":"2026-07-10","open":10,"high":12,"low":9,"close":11,"volume":100,"amount":1000},
            {"date":"2026-07-13","open":11,"high":13,"low":10,"close":12,"volume":200,"amount":2400},
        ]), "AkshareFetcher"

def test_default_disabled_does_not_call_provider(monkeypatch):
    monkeypatch.delenv("REAL_READONLY_PROVIDER_ENABLED", raising=False)
    manager=Manager()
    result=m.run_public_market_readonly(REQ, manager)
    assert result["status"] == "blocked"
    assert manager.called is False

def test_invalid_symbols_blocked():
    for symbol in ["hk00700","600519,000001","http://x","../600519","600 519"]:
        with pytest.raises(m.PublicMarketReadonlyError):
            m.validate_request({**REQ,"symbol":symbol})

def test_provider_success_sanitized(monkeypatch):
    monkeypatch.setenv("REAL_READONLY_PROVIDER_ENABLED","true")
    result=m.run_public_market_readonly(REQ, Manager())
    assert result["status"] == "completed-real-readonly"
    snap=result["snapshot"]
    assert snap["providerLabel"] == "REDACTED_PROVIDER_LABEL"
    assert "rawResponse" not in snap and "endpoint" not in snap and "token" not in snap
    assert snap["tradeDate"] == "2026-07-13"

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

def test_endpoint_local_no_side_effects(monkeypatch):
    monkeypatch.delenv("REAL_READONLY_PROVIDER_ENABLED", raising=False)
    client=TestClient(create_app())
    res=client.post("/api/v1/provider-readonly/akshare/dry-run", json=REQ)
    assert res.status_code == 200
    assert res.json()["status"] == "blocked"
