import asyncio
from datetime import datetime, timezone
import time

from src.fund_comparison import (
    AkshareFundComparisonConfig,
    AkshareFundComparisonService,
    run_akshare_fund_comparison,
    run_akshare_fund_comparison_with_timeout,
    validate_comparison_result,
)


REQUEST = {
    "mode": "fund-comparison-readonly",
    "provider": "akshare_fund_public",
    "codes": ["000001", "110022"],
    "sections": ["profile", "nav", "holdings", "industry-exposure"],
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
            "基金全称": f"公开基金{symbol}",
            "基金类型": "混合型",
            "基金经理人": "公开经理",
            "资产规模": "12.34亿元（截止 2026-06-30）",
            "成立日期/规模": "2020年01月02日 / 1.00亿份",
        }]

    def fund_open_fund_info_em(self, *, symbol, indicator):
        self.calls.append((indicator, symbol))
        if indicator == "单位净值走势":
            return [{"净值日期": "2026-07-15", "单位净值": 1.23, "日增长率": 0.2}]
        return [{"净值日期": "2026-07-15", "累计净值": 1.5}]

    def fund_portfolio_hold_em(self, *, symbol, date):
        self.calls.append(("holdings", symbol, date))
        if symbol == "000001":
            return [
                {"序号": 1, "股票代码": "600001", "股票名称": "共同证券", "占净值比例": 8.5, "季度": "2026年2季度"},
                {"序号": 2, "股票代码": "000002", "股票名称": "证券甲", "占净值比例": 6.25, "季度": "2026年2季度"},
            ]
        return [
            {"序号": 1, "股票代码": "600001", "股票名称": "共同证券", "占净值比例": 7, "季度": "2026年2季度"},
            {"序号": 2, "股票代码": "000003", "股票名称": "证券乙", "占净值比例": 6, "季度": "2026年2季度"},
        ]

    def fund_portfolio_industry_allocation_em(self, *, symbol, date):
        self.calls.append(("industry", symbol, date))
        if symbol == "000001":
            return [
                {"序号": 1, "行业类别": "医药", "占净值比例": 30, "市值": 3000, "截止时间": "2026-06-30"},
                {"序号": 2, "行业类别": "科技", "占净值比例": 20, "市值": 2000, "截止时间": "2026-06-30"},
                {"序号": 3, "行业类别": "消费", "占净值比例": 10, "市值": 1000, "截止时间": "2026-06-30"},
                {"序号": 1, "行业类别": "旧行业", "占净值比例": 40, "市值": 4000, "截止时间": "2026-03-31"},
            ]
        return [
            {"序号": 1, "行业类别": "医药", "占净值比例": 25, "市值": 2500, "截止时间": "2026-06-30"},
            {"序号": 2, "行业类别": "金融", "占净值比例": 15, "市值": 1500, "截止时间": "2026-06-30"},
            {"序号": 3, "行业类别": "科技", "占净值比例": 10, "市值": 1000, "截止时间": "2026-06-30"},
        ]


def service(fake=None, *, enabled=True):
    return AkshareFundComparisonService(
        config=AkshareFundComparisonConfig(
            network_enabled=enabled,
            human_approved=enabled,
            years=(2026,),
        ),
        akshare_module=fake or FakeAkshare(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )


def test_default_gate_does_not_call_akshare():
    fake = FakeAkshare()
    result = service(fake, enabled=False).fetch(("000001", "110022"))

    assert result.data_status == "missing"
    assert result.missing_funds == ("000001", "110022")
    assert fake.calls == []
    assert validate_comparison_result(result) == []


def test_maps_latest_disclosed_industries_and_concentration():
    result = service().fetch(("000001",))

    assert validate_comparison_result(result) == []
    item = result.funds[0]
    assert item.industry_exposure is not None
    assert item.industry_exposure.report_date == "2026-06-30"
    assert [row.industry_name for row in item.industry_exposure.industries] == ["医药", "科技", "消费"]
    assert item.industry_exposure.disclosed_total_pct == "60"
    assert item.industry_exposure.top3_concentration_pct == "60"
    assert item.top10_holdings_concentration_pct == "14.75"


def test_pair_overlap_uses_minimum_disclosed_weights_only():
    result = service().fetch(("000001", "110022"))

    assert validate_comparison_result(result) == []
    pair = result.pair_overlaps[0]
    assert pair.disclosed_holdings_overlap_pct == "7"
    assert [row["security_code"] for row in pair.common_holdings] == ["600001"]
    assert pair.disclosed_industry_overlap_pct == "35"
    assert [row["industry_name"] for row in pair.common_industries] == ["医药", "科技"]
    assert "下限" in pair.warnings[0]


def test_industry_failure_degrades_without_leaking_raw_error():
    class IndustryFailure(FakeAkshare):
        def fund_portfolio_industry_allocation_em(self, *, symbol, date):
            raise RuntimeError("private upstream detail")

    result = service(IndustryFailure()).fetch(("000001",))

    assert validate_comparison_result(result) == []
    assert result.data_status == "partial"
    assert result.funds[0].industry_exposure is None
    assert "industry-exposure" in result.funds[0].missing_sections
    assert "private upstream detail" not in str(result.to_dict())


def test_invalid_industry_total_is_rejected_instead_of_normalized():
    class InvalidTotal(FakeAkshare):
        def fund_portfolio_industry_allocation_em(self, *, symbol, date):
            return [
                {"行业类别": "行业甲", "占净值比例": 70, "截止时间": "2026-06-30"},
                {"行业类别": "行业乙", "占净值比例": 60, "截止时间": "2026-06-30"},
            ]

    result = service(InvalidTotal()).fetch(("000001",))

    assert result.funds[0].industry_exposure is None
    assert result.data_status == "partial"


def test_request_contract_blocks_duplicates_invalid_counts_and_capabilities():
    duplicate = run_akshare_fund_comparison({**REQUEST, "codes": ["000001", "000001"]}, akshare_module=FakeAkshare())
    too_many = run_akshare_fund_comparison({**REQUEST, "codes": ["000001", "000002", "000003", "000004", "000005"]}, akshare_module=FakeAkshare())
    forbidden = run_akshare_fund_comparison({**REQUEST, "allowAiCall": True}, akshare_module=FakeAkshare())

    assert duplicate["errorCode"] == "fund-comparison.duplicate-codes"
    assert too_many["errorCode"] == "fund-comparison.invalid-codes"
    assert forbidden["errorCode"] == "fund-comparison.forbidden-capability"


def test_runner_returns_auditable_result_without_advice_or_forbidden_capabilities():
    result = run_akshare_fund_comparison(REQUEST, akshare_module=FakeAkshare())

    assert result["status"] == "completed-readonly"
    assert result["readOnly"] is True
    assert result["comparison"]["pair_overlaps"][0]["holdings_scope"] == "latest-disclosed-top-holdings"
    assert "advice" not in result["comparison"]
    assert "trade" not in result["comparison"]
    assert "account" not in result["comparison"]


def test_timeout_is_fixed_and_low_detail():
    class SlowAkshare(FakeAkshare):
        def fund_overview_em(self, *, symbol):
            time.sleep(0.05)
            return super().fund_overview_em(symbol=symbol)

    result = asyncio.run(
        run_akshare_fund_comparison_with_timeout(
            REQUEST,
            akshare_module=SlowAkshare(),
            timeout_seconds=0.001,
        )
    )

    assert result == {
        "status": "timeout",
        "errorCode": "fund-comparison.provider-timeout",
        "providerLabel": "AKShare 公开基金数据",
        "readOnly": True,
    }
