import asyncio
from types import SimpleNamespace

from api.v1.endpoints import provider_readonly


PAYLOAD = provider_readonly.FundPortfolioAdviceReadonlyRequestModel(
    mode="fund-portfolio-advice-readonly",
    provider="akshare_fund_public",
    holdings=[{"code": "000001", "name": "基金A", "amount": 1000, "profit": 20, "targetAllocation": None}],
    sections=["portfolio-concentration", "overlap", "industry-cycle", "target-drift"],
    humanApproved=True,
    readOnly=True,
    allowAccountRead=False,
    allowTrading=False,
    allowNotificationSend=False,
    allowAiCall=False,
    allowPersistence=False,
)


def request(host):
    return SimpleNamespace(client=SimpleNamespace(host=host))


def test_remote_client_is_blocked_before_portfolio_advice_runner(monkeypatch):
    called = False

    async def fail_if_called(payload):
        nonlocal called
        called = True
        return {"status": "unexpected"}

    monkeypatch.setattr(provider_readonly, "run_akshare_fund_portfolio_advice_with_timeout", fail_if_called)
    result = asyncio.run(provider_readonly.akshare_fund_portfolio_advice_readonly(PAYLOAD, request("192.0.2.10")))

    assert result["status"] == "blocked"
    assert result["errorCode"] == "fund-portfolio-advice.localhost-only"
    assert called is False


def test_local_client_passes_amounts_only_to_local_readonly_runner(monkeypatch):
    seen = None

    async def runner(payload):
        nonlocal seen
        seen = payload
        return {"status": "completed-readonly", "readOnly": True}

    monkeypatch.setattr(provider_readonly, "run_akshare_fund_portfolio_advice_with_timeout", runner)
    result = asyncio.run(provider_readonly.akshare_fund_portfolio_advice_readonly(PAYLOAD, request("127.0.0.1")))

    assert result["status"] == "completed-readonly"
    assert seen["holdings"][0]["amount"] == 1000
    assert all(seen[field] is False for field in ("allowAccountRead", "allowTrading", "allowNotificationSend", "allowAiCall", "allowPersistence"))
