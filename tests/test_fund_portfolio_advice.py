import asyncio
from datetime import date, datetime, timedelta, timezone
import time

from src.fund_portfolio_advice import (
    AkshareFundPortfolioAdviceConfig,
    AkshareFundPortfolioAdviceService,
    PortfolioPosition,
    run_akshare_fund_portfolio_advice,
    run_akshare_fund_portfolio_advice_with_timeout,
    validate_portfolio_advice_result,
)


REQUEST = {
    "mode": "fund-portfolio-advice-readonly",
    "provider": "akshare_fund_public",
    "positions": [
        {"code": "000001", "weightPct": 60, "targetWeightPct": 50},
        {"code": "110022", "weightPct": 40, "targetWeightPct": 50},
    ],
    "riskProfile": "balanced",
    "sections": [
        "portfolio-allocation",
        "nav-risk",
        "disclosed-overlap",
        "industry-cycle",
        "allocation-guidance",
    ],
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
        start = date(2026, 3, 1)
        if indicator == "单位净值走势":
            base = 1 if symbol == "000001" else 1.5
            return [
                {
                    "净值日期": start + timedelta(days=index),
                    "单位净值": base + index * 0.002 + (0.01 if symbol == "110022" and index % 2 else 0),
                    "日增长率": 0.2,
                }
                for index in range(90)
            ]
        return [{"净值日期": "2026-05-29", "累计净值": 1.8}]

    def fund_portfolio_hold_em(self, *, symbol, date):
        self.calls.append(("holdings", symbol, date))
        if symbol == "000001":
            return [
                {"股票代码": "600001", "股票名称": "软件甲", "占净值比例": 20, "季度": "2026年2季度"},
                {"股票代码": "600002", "股票名称": "软件乙", "占净值比例": 10, "季度": "2026年2季度"},
            ]
        return [
            {"股票代码": "600001", "股票名称": "软件甲", "占净值比例": 15, "季度": "2026年2季度"},
            {"股票代码": "600003", "股票名称": "能源甲", "占净值比例": 10, "季度": "2026年2季度"},
        ]

    def fund_portfolio_industry_allocation_em(self, *, symbol, date):
        self.calls.append(("industry", symbol, date))
        rows = (
            [("软件开发", 45), ("医药商业", 15)]
            if symbol == "000001"
            else [("软件开发", 35), ("能源设备", 25)]
        )
        return [
            {"行业类别": name, "占净值比例": weight, "市值": weight * 100, "截止时间": "2026-06-30"}
            for name, weight in rows
        ]

    def stock_board_industry_name_em(self):
        return [
            {"板块名称": "软件开发", "板块代码": "BK0737"},
            {"板块名称": "医药商业", "板块代码": "BK1045"},
            {"板块名称": "能源设备", "板块代码": "BK0999"},
        ]

    def stock_yjbb_em(self, *, date):
        self.calls.append(("financial", date))
        return [
            {
                "股票代码": f"6000{index:02d}",
                "所处行业": "软件开发" if index <= 4 else "医药商业" if index <= 8 else "能源设备",
                "营业总收入-同比增长": 12,
                "净利润-同比增长": 15,
                "净资产收益率": 10,
                "销售毛利率": 35,
                "每股经营现金流量": 0.5,
            }
            for index in range(1, 13)
        ]

    def index_zh_a_hist(self, *, symbol, period, start_date, end_date):
        start = date(2026, 3, 1)
        return [{"日期": start + timedelta(days=index), "收盘": 100 + index * 0.1, "成交额": 100} for index in range(80)]

    def stock_board_industry_hist_em(self, *, symbol, start_date, end_date, period, adjust):
        start = date(2026, 3, 1)
        direction = -0.4 if symbol == "能源设备" else 0.8
        return [
            {"日期": start + timedelta(days=index), "收盘": 100 + index * direction, "成交额": 100 + index}
            for index in range(80)
        ]

    def stock_board_industry_cons_em(self, *, symbol):
        first = {"软件开发": 1, "医药商业": 5, "能源设备": 9}[symbol]
        change = -2 if symbol == "能源设备" else 2
        return [
            {"代码": f"6000{index:02d}", "涨跌幅": change, "市盈率-动态": 25, "市净率": 3}
            for index in range(first, first + 4)
        ]


def positions():
    return (
        PortfolioPosition("000001", weight_pct=60, target_weight_pct=50),
        PortfolioPosition("110022", weight_pct=40, target_weight_pct=50),
    )


def service(fake=None, *, enabled=True):
    return AkshareFundPortfolioAdviceService(
        config=AkshareFundPortfolioAdviceConfig(
            network_enabled=enabled,
            human_approved=enabled,
            years=(2026,),
        ),
        akshare_module=fake or FakeAkshare(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )


def test_builds_current_weight_risk_dimensions_and_target_gap_guidance():
    result = service().fetch(positions(), "balanced")

    assert validate_portfolio_advice_result(result) == []
    assert result["concentration"]["status"] == "high"
    assert result["concentration"]["largest_fund_weight_pct"] == "60"
    assert result["disclosed_overlap"]["status"] == "high"
    assert result["disclosed_overlap"]["max_disclosed_industry_overlap_pct"] == "35"
    assert result["industry_exposure"]["top_industries"][0] == {
        "industry_name": "软件开发",
        "portfolio_exposure_pct": "41",
    }
    guidance_ids = {item["id"] for item in result["allocation_guidance"]}
    assert {"target-gap-000001", "target-gap-110022", "fund-concentration"} <= guidance_ids


def test_never_receives_or_returns_user_identity_amount_cost_or_account_read():
    response = run_akshare_fund_portfolio_advice(REQUEST, akshare_module=FakeAkshare())

    assert response["status"] == "completed-readonly"
    result = response["advice"]
    assert result["input_privacy"] == {
        "amount_shared": False,
        "cost_basis_shared": False,
        "user_identity_shared": False,
        "account_read": False,
    }
    assert all(set(item) == {"code", "weight_pct", "target_weight_pct"} for item in result["positions"])
    assert "userId" not in str(result)
    assert "holdingAmount" not in str(result)


def test_default_gate_returns_missing_without_provider_calls():
    fake = FakeAkshare()
    result = service(fake, enabled=False).fetch(positions(), "balanced")

    assert result["data_status"] == "missing"
    assert result["missing_evidence"] == ["manual-local-approval"]
    assert fake.calls == []


def test_request_contract_rejects_extra_amount_invalid_total_and_forbidden_capability():
    with_amount = {
        **REQUEST,
        "positions": [{**REQUEST["positions"][0], "amount": 123}, REQUEST["positions"][1]],
    }
    invalid_total = {
        **REQUEST,
        "positions": [
            {"code": "000001", "weightPct": 50, "targetWeightPct": None},
            {"code": "110022", "weightPct": 40, "targetWeightPct": None},
        ],
    }
    forbidden = {**REQUEST, "allowAccountRead": True}

    assert run_akshare_fund_portfolio_advice(with_amount, akshare_module=FakeAkshare())["errorCode"] == "fund-portfolio-advice.invalid-positions"
    assert run_akshare_fund_portfolio_advice(invalid_total, akshare_module=FakeAkshare())["errorCode"] == "fund-portfolio-advice.invalid-weight-total"
    assert run_akshare_fund_portfolio_advice(forbidden, akshare_module=FakeAkshare())["errorCode"] == "fund-portfolio-advice.forbidden-capability"


def test_missing_nav_history_degrades_without_leaking_provider_error():
    class NavFailure(FakeAkshare):
        def fund_open_fund_info_em(self, *, symbol, indicator):
            if indicator == "单位净值走势":
                raise RuntimeError("private upstream detail")
            return super().fund_open_fund_info_em(symbol=symbol, indicator=indicator)

    result = service(NavFailure()).fetch(positions(), "balanced")

    assert validate_portfolio_advice_result(result) == []
    assert result["nav_risk"]["status"] == "insufficient"
    assert "private upstream detail" not in str(result)


def test_timeout_is_fixed_and_low_detail():
    class SlowAkshare(FakeAkshare):
        def fund_overview_em(self, *, symbol):
            time.sleep(0.05)
            return super().fund_overview_em(symbol=symbol)

    result = asyncio.run(
        run_akshare_fund_portfolio_advice_with_timeout(
            REQUEST,
            akshare_module=SlowAkshare(),
            timeout_seconds=0.001,
        )
    )

    assert result == {
        "status": "timeout",
        "errorCode": "fund-portfolio-advice.provider-timeout",
        "providerLabel": "AKShare 公开基金数据",
        "readOnly": True,
    }
