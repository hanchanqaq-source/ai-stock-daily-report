import asyncio
from datetime import datetime, timezone
import time

from src.fund_data_akshare_provider import (
    AkshareFundDataProvider,
    AkshareFundDataProviderConfig,
    run_akshare_fund_readonly,
    run_akshare_fund_readonly_with_timeout,
)
from src.fund_data_contract import validate_fund_data_bundle
from src.fund_data_provider import FundDataRequest, fetch_fund_data


READONLY_REQUEST = {
    "mode": "fund-public-readonly",
    "provider": "akshare_fund_public",
    "code": "000001",
    "sections": ["profile", "nav", "holdings"],
    "humanApproved": True,
    "readOnly": True,
    "allowAccountRead": False,
    "allowTrading": False,
    "allowNotificationSend": False,
    "allowAiCall": False,
    "allowPersistence": False,
}


class FakeAkshare:
    def __init__(self):
        self.calls = []

    def fund_overview_em(self, *, symbol):
        self.calls.append(("profile", symbol))
        return [{
            "基金全称": "公开测试基金",
            "基金类型": "混合型",
            "基金经理人": "公开经理",
            "资产规模": "12.34亿元（截止 2026-06-30）",
            "成立日期/规模": "2020年01月02日 / 1.00亿份",
        }]

    def fund_open_fund_info_em(self, *, symbol, indicator):
        self.calls.append((indicator, symbol))
        if indicator == "单位净值走势":
            return [
                {"净值日期": "2026-07-14", "单位净值": 1.2, "日增长率": -0.1},
                {"净值日期": "2026-07-15", "单位净值": 1.2345, "日增长率": 0.25},
            ]
        return [
            {"净值日期": "2026-07-14", "累计净值": 1.5},
            {"净值日期": "2026-07-15", "累计净值": 1.55},
        ]

    def fund_portfolio_hold_em(self, *, symbol, date):
        self.calls.append(("holdings", symbol, date))
        return [
            {"序号": 1, "股票代码": "600001", "股票名称": "公开证券甲", "占净值比例": 8.5, "季度": "2026 年2季度股票投资明细"},
            {"序号": 2, "股票代码": "000002", "股票名称": "公开证券乙", "占净值比例": 6.25, "季度": "2026 年2季度股票投资明细"},
            {"序号": 1, "股票代码": "600003", "股票名称": "旧季度证券", "占净值比例": 5, "季度": "2026 年1季度股票投资明细"},
        ]


def enabled_provider(fake=None):
    return AkshareFundDataProvider(
        config=AkshareFundDataProviderConfig(
            network_enabled=True,
            human_approved=True,
            holdings_years=(2026,),
        ),
        akshare_module=fake or FakeAkshare(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )


def test_default_gate_does_not_initialize_or_call_akshare():
    fake = FakeAkshare()
    provider = AkshareFundDataProvider(akshare_module=fake)

    result = fetch_fund_data(FundDataRequest("000001"), provider)

    assert result.data_status == "missing"
    assert result.profile is None
    assert fake.calls == []
    assert validate_fund_data_bundle(result) == []


def test_maps_public_profile_nav_and_latest_disclosed_holdings_to_canonical_contract():
    fake = FakeAkshare()
    result = fetch_fund_data(FundDataRequest("000001"), enabled_provider(fake))

    assert validate_fund_data_bundle(result) == []
    assert result.data_status == "partial"  # Intraday estimate and industry mapping are deliberately absent.
    assert result.profile is not None
    assert result.profile.name == "公开测试基金"
    assert result.profile.scale == "12.34"
    assert result.profile.scale_currency == "CNY_100M"
    assert result.profile.inception_date == "2020-01-02"
    assert result.nav is not None
    assert result.nav.unit_nav == "1.2345"
    assert result.nav.accumulated_nav == "1.55"
    assert result.nav.nav_date == "2026-07-15"
    assert result.holdings is not None
    assert result.holdings.report_period == "2026-Q2"
    assert [item.security_code for item in result.holdings.positions] == ["600001", "000002"]
    assert result.holdings.disclosed_total_pct == "14.75"
    assert all(item.industry.status == "unknown" for item in result.holdings.positions)
    assert all(item.industry.industry_name is None for item in result.holdings.positions)


def test_one_failed_section_degrades_without_leaking_provider_exception():
    class PartialAkshare(FakeAkshare):
        def fund_portfolio_hold_em(self, *, symbol, date):
            raise RuntimeError("private upstream detail")

    result = fetch_fund_data(FundDataRequest("000001"), enabled_provider(PartialAkshare()))

    assert validate_fund_data_bundle(result) == []
    assert result.data_status == "partial"
    assert result.holdings is None
    assert result.missing_sections == ("holdings",)
    assert "private upstream detail" not in str(result.to_dict())


def test_holdings_falls_back_to_previous_year_after_current_year_failure():
    class PreviousYearAkshare(FakeAkshare):
        def fund_portfolio_hold_em(self, *, symbol, date):
            if date == "2026":
                raise RuntimeError("current year temporarily unavailable")
            return super().fund_portfolio_hold_em(symbol=symbol, date=date)

    provider = AkshareFundDataProvider(
        config=AkshareFundDataProviderConfig(
            network_enabled=True,
            human_approved=True,
            holdings_years=(2026, 2025),
        ),
        akshare_module=PreviousYearAkshare(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )
    result = fetch_fund_data(FundDataRequest("000001", ("holdings",)), provider)

    assert validate_fund_data_bundle(result) == []
    assert result.holdings is not None
    assert result.holdings.report_period == "2026-Q2"


def test_readonly_request_requires_exact_manual_safety_flags():
    blocked = run_akshare_fund_readonly({**READONLY_REQUEST, "allowTrading": True}, akshare_module=FakeAkshare())
    invalid = run_akshare_fund_readonly({**READONLY_REQUEST, "code": "1"}, akshare_module=FakeAkshare())

    assert blocked["status"] == "blocked"
    assert blocked["errorCode"] == "fund-readonly.forbidden-capability"
    assert invalid["status"] == "blocked"
    assert invalid["errorCode"] == "fund-readonly.invalid-code"


def test_readonly_runner_returns_auditable_bundle_and_no_forbidden_capabilities():
    result = run_akshare_fund_readonly(READONLY_REQUEST, akshare_module=FakeAkshare())

    assert result["status"] == "completed-readonly"
    assert result["readOnly"] is True
    assert result["bundle"]["profile"]["source"]["provider"] == "akshare_fund_public"
    assert result["bundle"]["nav"]["source"]["effective_at"] == "2026-07-15"
    assert "account" not in result["bundle"]
    assert "trade" not in result["bundle"]


def test_timeout_is_fixed_and_does_not_expose_provider_details():
    class SlowAkshare(FakeAkshare):
        def fund_overview_em(self, *, symbol):
            time.sleep(0.05)
            return super().fund_overview_em(symbol=symbol)

    result = asyncio.run(
        run_akshare_fund_readonly_with_timeout(
            READONLY_REQUEST,
            akshare_module=SlowAkshare(),
            timeout_seconds=0.001,
        )
    )

    assert result == {
        "status": "timeout",
        "errorCode": "fund-readonly.provider-timeout",
        "providerLabel": "AKShare 公开基金数据",
        "readOnly": True,
    }
