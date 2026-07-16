import asyncio

from api.v1.endpoints import provider_readonly


PAYLOAD = provider_readonly.FundPortfolioAdviceReadonlyRequestModel(
    mode="fund-portfolio-advice-readonly",
    provider="akshare_fund_public",
    positions=[
        provider_readonly.FundPortfolioPositionModel(code="000001", weightPct=60, targetWeightPct=50),
        provider_readonly.FundPortfolioPositionModel(code="110022", weightPct=40, targetWeightPct=50),
    ],
    riskProfile="balanced",
    sections=[
        "portfolio-allocation",
        "nav-risk",
        "disclosed-overlap",
        "industry-cycle",
        "allocation-guidance",
    ],
    humanApproved=True,
    readOnly=True,
    allowAccountRead=False,
    allowTrading=False,
    allowNotificationSend=False,
    allowAiCall=False,
    allowPersistence=False,
)


class Request:
    def __init__(self, host):
        self.client = type("Client", (), {"host": host})()


def test_remote_client_is_blocked_before_portfolio_provider_call(monkeypatch):
    called = False

    async def fail_if_called(payload):
        nonlocal called
        called = True
        return {"status": "unexpected"}

    monkeypatch.setattr(provider_readonly, "run_akshare_fund_portfolio_advice_with_timeout", fail_if_called)
    result = asyncio.run(provider_readonly.akshare_fund_portfolio_advice_readonly(PAYLOAD, Request("192.0.2.10")))

    assert result["status"] == "blocked"
    assert result["errorCode"] == "fund-portfolio-advice.localhost-only"
    assert called is False


def test_local_client_passes_normalized_weights_and_exact_safety_flags(monkeypatch):
    seen = None

    async def fake_runner(payload):
        nonlocal seen
        seen = payload
        return {"status": "completed-readonly", "providerLabel": "AKShare 公开基金数据", "readOnly": True}

    monkeypatch.setattr(provider_readonly, "run_akshare_fund_portfolio_advice_with_timeout", fake_runner)
    result = asyncio.run(provider_readonly.akshare_fund_portfolio_advice_readonly(PAYLOAD, Request("127.0.0.1")))

    assert result["status"] == "completed-readonly"
    assert seen["positions"] == [
        {"code": "000001", "weightPct": 60.0, "targetWeightPct": 50.0},
        {"code": "110022", "weightPct": 40.0, "targetWeightPct": 50.0},
    ]
    assert "userId" not in seen
    assert "amount" not in seen["positions"][0]
    assert seen["humanApproved"] is True
    assert seen["allowAccountRead"] is False
    assert seen["allowTrading"] is False
    assert seen["allowNotificationSend"] is False
    assert seen["allowAiCall"] is False
    assert seen["allowPersistence"] is False
