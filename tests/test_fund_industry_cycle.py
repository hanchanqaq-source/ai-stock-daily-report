import asyncio
from datetime import date, datetime, timedelta, timezone
import time

from src.fund_industry_cycle import (
    AkshareFundIndustryCycleConfig,
    AkshareFundIndustryCycleService,
    run_akshare_fund_industry_cycle,
    run_akshare_fund_industry_cycle_with_timeout,
    validate_cycle_result,
)


REQUEST = {
    "mode": "fund-industry-cycle-readonly",
    "provider": "akshare_fund_public",
    "codes": ["000001"],
    "sections": ["funds", "disclosed-holdings", "industry-cycle-evidence", "productivity-proxy-evidence"],
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
        return [
            {"股票代码": "600001", "股票名称": "软件甲", "占净值比例": 8, "季度": "2026年2季度"},
            {"股票代码": "600002", "股票名称": "软件乙", "占净值比例": 7, "季度": "2026年2季度"},
        ]

    def fund_portfolio_industry_allocation_em(self, *, symbol, date):
        self.calls.append(("industry", symbol, date))
        return [
            {"行业类别": "软件开发", "占净值比例": 35, "市值": 3500, "截止时间": "2026-06-30"},
            {"行业类别": "医药商业", "占净值比例": 20, "市值": 2000, "截止时间": "2026-06-30"},
        ]

    def stock_board_industry_name_em(self):
        self.calls.append(("board_names",))
        return [
            {"板块名称": "软件开发", "板块代码": "BK0737"},
            {"板块名称": "医药商业", "板块代码": "BK1045"},
        ]

    def stock_yjbb_em(self, *, date):
        self.calls.append(("financial", date))
        return [
            {
                "股票代码": f"6000{index:02d}",
                "所处行业": "软件开发" if index <= 8 else "医药商业",
                "营业总收入-同比增长": 18 if index <= 8 else -5,
                "净利润-同比增长": 22 if index <= 8 else -8,
                "净资产收益率": 12 if index <= 8 else 2,
                "销售毛利率": 45 if index <= 8 else 20,
                "每股经营现金流量": 0.5 if index <= 8 else -0.1,
            }
            for index in range(1, 17)
        ]

    def index_zh_a_hist(self, *, symbol, period, start_date, end_date):
        self.calls.append(("benchmark", symbol, period, start_date, end_date))
        start = date(2026, 3, 1)
        return [
            {"日期": start + timedelta(days=index), "收盘": 100 + index * 0.1, "成交额": 100}
            for index in range(80)
        ]

    def stock_board_industry_hist_em(self, *, symbol, start_date, end_date, period, adjust):
        self.calls.append(("history", symbol, start_date, end_date, period, adjust))
        start = date(2026, 3, 1)
        if symbol == "软件开发":
            return [
                {"日期": start + timedelta(days=index), "收盘": 100 + index, "成交额": 100 if index < 60 else 200}
                for index in range(80)
            ]
        return [
            {"日期": start + timedelta(days=index), "收盘": 200 - index, "成交额": 180 if index < 60 else 100}
            for index in range(80)
        ]

    def stock_board_industry_cons_em(self, *, symbol):
        self.calls.append(("constituents", symbol))
        first = 1 if symbol == "软件开发" else 9
        change = 2 if symbol == "软件开发" else -2
        return [
            {"代码": f"6000{index:02d}", "涨跌幅": change, "市盈率-动态": 25, "市净率": 3}
            for index in range(first, first + 8)
        ]


def service(fake=None, *, enabled=True):
    return AkshareFundIndustryCycleService(
        config=AkshareFundIndustryCycleConfig(
            network_enabled=enabled,
            human_approved=enabled,
            years=(2026,),
        ),
        akshare_module=fake or FakeAkshare(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )


def test_default_gate_returns_missing_without_provider_calls():
    fake = FakeAkshare()
    result = service(fake, enabled=False).fetch(("000001",))

    assert result.data_status == "missing"
    assert result.industries == ()
    assert fake.calls == []
    assert validate_cycle_result(result) == []


def test_builds_separate_cycle_and_productivity_proxy_evidence():
    result = service().fetch(("000001",))

    assert validate_cycle_result(result) == []
    assert result.data_status == "partial"
    evidence = {item.industry_name: item for item in result.industries}
    assert evidence["软件开发"].phase == "overheated"
    assert evidence["软件开发"].productivity.status == "improving"
    assert evidence["医药商业"].phase == "contraction"
    assert evidence["医药商业"].productivity.status == "weakening"
    assert evidence["软件开发"].metrics.relative_strength_20d_pct is not None
    assert "capital_expenditure" in evidence["软件开发"].productivity.missing_dimensions


def test_preserves_fund_report_period_dates_and_disclosed_scope():
    result = service().fetch(("000001",))

    fund = result.funds[0]
    assert fund.holdings_report_period == "2026-Q2"
    assert fund.analyzed_weight_pct == "55"
    assert [item.scope for item in fund.industry_links] == [
        "provider-disclosed-industry-allocation",
        "provider-disclosed-industry-allocation",
    ]
    assert result.financial_report_period == "2026-Q2"
    assert result.industries[0].evidence_dates


def test_uses_provider_industry_for_holdings_when_disclosed_name_has_no_exact_board_match():
    class BroadDisclosure(FakeAkshare):
        def fund_portfolio_industry_allocation_em(self, *, symbol, date):
            return [{"行业类别": "信息技术大类", "占净值比例": 55, "截止时间": "2026-06-30"}]

    result = service(BroadDisclosure()).fetch(("000001",))

    assert [item.industry_name for item in result.funds[0].industry_links] == ["软件开发"]
    assert result.funds[0].industry_links[0].scope == "latest-disclosed-top-holdings-provider-industry"
    assert result.funds[0].analyzed_weight_pct == "15"


def test_conflicting_market_evidence_fails_closed_with_explicit_reason():
    class NeutralCycle(FakeAkshare):
        def stock_board_industry_hist_em(self, *, symbol, start_date, end_date, period, adjust):
            start = date(2026, 3, 1)
            return [
                {"日期": start + timedelta(days=index), "收盘": 100, "成交额": 100}
                for index in range(80)
            ]

        def stock_board_industry_cons_em(self, *, symbol):
            rows = super().stock_board_industry_cons_em(symbol=symbol)
            return [{**row, "涨跌幅": 1 if index % 2 else -1} for index, row in enumerate(rows)]

        def index_zh_a_hist(self, *, symbol, period, start_date, end_date):
            start = date(2026, 3, 1)
            return [
                {"日期": start + timedelta(days=index), "收盘": 100, "成交额": 100}
                for index in range(80)
            ]

    result = service(NeutralCycle()).fetch(("000001",))

    assert all(item.phase == "insufficient" for item in result.industries)
    assert all("conflicting-or-neutral-cycle-evidence" in item.missing_evidence for item in result.industries)


def test_missing_history_degrades_without_leaking_provider_error():
    class HistoryFailure(FakeAkshare):
        def stock_board_industry_hist_em(self, **kwargs):
            raise RuntimeError("private upstream detail")

    result = service(HistoryFailure()).fetch(("000001",))

    assert validate_cycle_result(result) == []
    assert all(item.phase == "insufficient" for item in result.industries)
    assert "private upstream detail" not in str(result.to_dict())


def test_request_contract_blocks_invalid_codes_duplicates_and_capabilities():
    invalid = run_akshare_fund_industry_cycle({**REQUEST, "codes": ["1"]}, akshare_module=FakeAkshare())
    duplicate = run_akshare_fund_industry_cycle({**REQUEST, "codes": ["000001", "000001"]}, akshare_module=FakeAkshare())
    forbidden = run_akshare_fund_industry_cycle({**REQUEST, "allowTrading": True}, akshare_module=FakeAkshare())

    assert invalid["errorCode"] == "fund-industry-cycle.invalid-codes"
    assert duplicate["errorCode"] == "fund-industry-cycle.duplicate-codes"
    assert forbidden["errorCode"] == "fund-industry-cycle.forbidden-capability"


def test_runner_is_auditable_and_contains_no_advice_or_forbidden_capabilities():
    result = run_akshare_fund_industry_cycle(REQUEST, akshare_module=FakeAkshare())

    assert result["status"] == "completed-readonly"
    assert result["readOnly"] is True
    assert result["cycle"]["method"] == "deterministic-explainable-features-inspired-by-market-state-analysis"
    assert "advice" not in result["cycle"]
    assert "trade" not in result["cycle"]
    assert "account" not in result["cycle"]


def test_timeout_is_fixed_and_low_detail():
    class SlowAkshare(FakeAkshare):
        def fund_overview_em(self, *, symbol):
            time.sleep(0.05)
            return super().fund_overview_em(symbol=symbol)

    result = asyncio.run(
        run_akshare_fund_industry_cycle_with_timeout(
            REQUEST,
            akshare_module=SlowAkshare(),
            timeout_seconds=0.001,
        )
    )

    assert result == {
        "status": "timeout",
        "errorCode": "fund-industry-cycle.provider-timeout",
        "providerLabel": "AKShare 公开基金数据",
        "readOnly": True,
    }
