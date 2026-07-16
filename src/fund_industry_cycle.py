"""Explainable fund industry-cycle and productivity-proxy evidence.

Build D3 reuses the public fund facts introduced in D1/D2, then derives a
small, deterministic evidence set from AKShare industry-board and financial
report data.  The module deliberately keeps short-cycle evidence separate from
longer-horizon operating-productivity proxies.  It does not load Qlib, call AI,
read accounts, persist results, or produce allocation/trading advice.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from statistics import median
from typing import Any, Mapping

from src.fund_comparison import (
    AkshareFundComparisonConfig,
    AkshareFundComparisonService,
    FundComparisonItem,
    FundComparisonResult,
    MAX_FUNDS,
)
from src.fund_data_akshare_provider import (
    FUND_CODE_RE,
    PROVIDER_LABEL,
    PROVIDER_NAME,
    _date_text,
    _decimal_text,
    _field,
    _records,
    _text,
)


CYCLE_TIMEOUT_SECONDS = 60
MAX_ANALYZED_INDUSTRIES = 6
MAX_INDUSTRIES_PER_FUND = 3
BENCHMARK_CODE = "000300"
CYCLE_SECTIONS = frozenset(
    {"funds", "disclosed-holdings", "industry-cycle-evidence", "productivity-proxy-evidence"}
)
CYCLE_REQUEST_FIELDS = frozenset(
    {
        "mode",
        "provider",
        "codes",
        "sections",
        "humanApproved",
        "readOnly",
        "allowAccountRead",
        "allowTrading",
        "allowNotificationSend",
        "allowAiCall",
        "allowPersistence",
    }
)
PHASES = frozenset({"recovery", "expansion", "overheated", "slowdown", "contraction", "insufficient"})
PRODUCTIVITY_STATES = frozenset({"improving", "stable", "weakening", "insufficient"})


class FundIndustryCycleError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _number(value: Any) -> Decimal | None:
    rendered = _decimal_text(value)
    if rendered is None:
        return None
    try:
        parsed = Decimal(rendered)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _render(value: Decimal | float | int | None, places: int = 2) -> str | None:
    if value is None:
        return None
    parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    quantum = Decimal("1").scaleb(-places)
    return _decimal_text(parsed.quantize(quantum, rounding=ROUND_HALF_UP))


def _percent_change(latest: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return (latest / previous - Decimal("1")) * Decimal("100")


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return Decimal(str(median(values)))


def _average(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _security_code(value: Any) -> str | None:
    text = _text(value, limit=16)
    if not text:
        return None
    cleaned = text.split(".", 1)[0]
    return cleaned.zfill(6) if cleaned.isdigit() and len(cleaned) <= 6 else None


def _quarter_candidates(today: date, limit: int = 4) -> tuple[str, ...]:
    quarter_ends = ((3, 31), (6, 30), (9, 30), (12, 31))
    candidates: list[str] = []
    year = today.year
    while len(candidates) < limit:
        for month, day in reversed(quarter_ends):
            current = date(year, month, day)
            if current <= today:
                candidates.append(current.strftime("%Y%m%d"))
                if len(candidates) == limit:
                    break
        year -= 1
    return tuple(candidates)


def _quarter_label(raw: str) -> str:
    month = int(raw[4:6])
    return f"{raw[:4]}-Q{month // 3}"


def _quarter_date(raw: str) -> str:
    return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8])).isoformat()


@dataclass(frozen=True)
class IndustryLink:
    industry_name: str
    fund_weight_pct: str
    scope: str

    def to_dict(self) -> dict[str, str]:
        return {
            "industry_name": self.industry_name,
            "fund_weight_pct": self.fund_weight_pct,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class CycleMetrics:
    as_of_date: str | None
    return_20d_pct: str | None
    return_60d_pct: str | None
    turnover_change_20d_pct: str | None
    breadth_rise_ratio_pct: str | None
    relative_strength_20d_pct: str | None
    median_dynamic_pe: str | None
    median_pb: str | None
    constituent_count: int
    breadth_sample_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of_date": self.as_of_date,
            "return_20d_pct": self.return_20d_pct,
            "return_60d_pct": self.return_60d_pct,
            "turnover_change_20d_pct": self.turnover_change_20d_pct,
            "breadth_rise_ratio_pct": self.breadth_rise_ratio_pct,
            "relative_strength_20d_pct": self.relative_strength_20d_pct,
            "median_dynamic_pe": self.median_dynamic_pe,
            "median_pb": self.median_pb,
            "constituent_count": self.constituent_count,
            "breadth_sample_count": self.breadth_sample_count,
        }


@dataclass(frozen=True)
class ProductivityProxy:
    status: str
    report_period: str | None
    effective_at: str | None
    revenue_yoy_median_pct: str | None
    profit_yoy_median_pct: str | None
    roe_median_pct: str | None
    gross_margin_median_pct: str | None
    operating_cashflow_positive_ratio_pct: str | None
    covered_constituents: int
    total_constituents: int
    confidence: str
    missing_dimensions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "report_period": self.report_period,
            "effective_at": self.effective_at,
            "revenue_yoy_median_pct": self.revenue_yoy_median_pct,
            "profit_yoy_median_pct": self.profit_yoy_median_pct,
            "roe_median_pct": self.roe_median_pct,
            "gross_margin_median_pct": self.gross_margin_median_pct,
            "operating_cashflow_positive_ratio_pct": self.operating_cashflow_positive_ratio_pct,
            "covered_constituents": self.covered_constituents,
            "total_constituents": self.total_constituents,
            "confidence": self.confidence,
            "missing_dimensions": list(self.missing_dimensions),
            "scope": "operating-productivity-proxy-not-total-factor-productivity",
        }


@dataclass(frozen=True)
class IndustryCycleEvidence:
    industry_name: str
    board_code: str
    data_status: str
    phase: str
    confidence: str
    metrics: CycleMetrics
    productivity: ProductivityProxy
    source_interfaces: tuple[str, ...]
    evidence_dates: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "industry_name": self.industry_name,
            "board_code": self.board_code,
            "data_status": self.data_status,
            "phase": self.phase,
            "confidence": self.confidence,
            "metrics": self.metrics.to_dict(),
            "productivity": self.productivity.to_dict(),
            "source_interfaces": list(self.source_interfaces),
            "evidence_dates": list(self.evidence_dates),
            "missing_evidence": list(self.missing_evidence),
            "warnings": list(self.warnings),
            "cycle_scope": "market-cycle-evidence-not-trading-advice",
        }


@dataclass(frozen=True)
class FundCycleImpact:
    code: str
    name: str | None
    holdings_report_period: str | None
    industry_links: tuple[IndustryLink, ...]
    analyzed_weight_pct: str
    unclassified_holdings: tuple[str, ...]
    omitted_industries: int
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "holdings_report_period": self.holdings_report_period,
            "industry_links": [item.to_dict() for item in self.industry_links],
            "analyzed_weight_pct": self.analyzed_weight_pct,
            "unclassified_holdings": list(self.unclassified_holdings),
            "omitted_industries": self.omitted_industries,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class FundIndustryCycleResult:
    requested_codes: tuple[str, ...]
    data_status: str
    fetched_at: str
    benchmark_code: str
    financial_report_period: str | None
    funds: tuple[FundCycleImpact, ...]
    industries: tuple[IndustryCycleEvidence, ...]
    missing_evidence: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_codes": list(self.requested_codes),
            "data_status": self.data_status,
            "fetched_at": self.fetched_at,
            "provider": PROVIDER_NAME,
            "benchmark_code": self.benchmark_code,
            "financial_report_period": self.financial_report_period,
            "funds": [item.to_dict() for item in self.funds],
            "industries": [item.to_dict() for item in self.industries],
            "missing_evidence": list(self.missing_evidence),
            "warnings": list(self.warnings),
            "method": "deterministic-explainable-features-inspired-by-market-state-analysis",
        }


def _board_map(akshare_module: Any) -> dict[str, str]:
    rows = _records(akshare_module.stock_board_industry_name_em())
    result: dict[str, str] = {}
    for row in rows:
        name = _text(_field(row, "板块名称", "行业名称"), limit=80)
        code = _text(_field(row, "板块代码", "行业代码"), limit=24)
        if name and code and name not in result:
            result[name] = code
    return result


def _financial_rows(akshare_module: Any, today: date) -> tuple[str | None, list[dict[str, Any]]]:
    for quarter in _quarter_candidates(today):
        try:
            rows = _records(akshare_module.stock_yjbb_em(date=quarter))
        except Exception:
            rows = []
        if rows:
            return quarter, rows
    return None, []


def _financial_by_code(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = _security_code(_field(row, "股票代码", "代码"))
        if code and code not in result:
            result[code] = row
    return result


def _fund_links(
    item: FundComparisonItem,
    *,
    board_names: set[str],
    financial_by_code: Mapping[str, Mapping[str, Any]],
) -> tuple[list[IndustryLink], list[str]]:
    disclosed: list[IndustryLink] = []
    if item.industry_exposure:
        for exposure in item.industry_exposure.industries:
            if exposure.industry_name in board_names:
                disclosed.append(
                    IndustryLink(
                        industry_name=exposure.industry_name,
                        fund_weight_pct=exposure.weight_pct,
                        scope="provider-disclosed-industry-allocation",
                    )
                )
    if disclosed:
        return disclosed[:MAX_INDUSTRIES_PER_FUND], []

    weights: dict[str, Decimal] = {}
    unclassified: list[str] = []
    holdings = item.bundle.holdings
    for position in holdings.positions if holdings else ():
        row = financial_by_code.get(position.security_code)
        industry = _text(_field(row or {}, "所处行业", "行业"), limit=80)
        weight = _number(position.weight_pct)
        if not industry or industry not in board_names or weight is None:
            unclassified.append(position.security_code)
            continue
        weights[industry] = weights.get(industry, Decimal("0")) + weight
    links = [
        IndustryLink(name, _render(weight) or "0", "latest-disclosed-top-holdings-provider-industry")
        for name, weight in sorted(weights.items(), key=lambda pair: (-pair[1], pair[0]))
    ]
    return links[:MAX_INDUSTRIES_PER_FUND], unclassified


def _history_metrics(rows: list[dict[str, Any]]) -> tuple[str | None, Decimal | None, Decimal | None, Decimal | None]:
    parsed: list[tuple[str, Decimal, Decimal | None]] = []
    for row in rows:
        day = _date_text(_field(row, "日期", "date"))
        close = _number(_field(row, "收盘", "收盘价", "close"))
        turnover = _number(_field(row, "成交额", "amount"))
        if day and close is not None and close > 0:
            parsed.append((day, close, turnover if turnover is not None and turnover >= 0 else None))
    parsed.sort(key=lambda item: item[0])
    if not parsed:
        return None, None, None, None
    return_20 = _percent_change(parsed[-1][1], parsed[-21][1]) if len(parsed) >= 21 else None
    return_60 = _percent_change(parsed[-1][1], parsed[-61][1]) if len(parsed) >= 61 else None
    turnover_change = None
    if len(parsed) >= 40:
        latest = [value for _, _, value in parsed[-20:] if value is not None]
        previous = [value for _, _, value in parsed[-40:-20] if value is not None]
        latest_average, previous_average = _average(latest), _average(previous)
        if latest_average is not None and previous_average is not None:
            turnover_change = _percent_change(latest_average, previous_average)
    return parsed[-1][0], return_20, return_60, turnover_change


def _constituent_metrics(
    rows: list[dict[str, Any]],
) -> tuple[Decimal | None, Decimal | None, int, int, Decimal | None]:
    changes: list[Decimal] = []
    positive_pe: list[Decimal] = []
    positive_pb: list[Decimal] = []
    for row in rows:
        change = _number(_field(row, "涨跌幅", "change_pct"))
        pe = _number(_field(row, "市盈率-动态", "市盈率", "pe"))
        pb = _number(_field(row, "市净率", "pb"))
        if change is not None:
            changes.append(change)
        if pe is not None and pe > 0:
            positive_pe.append(pe)
        if pb is not None and pb > 0:
            positive_pb.append(pb)
    breadth = None
    if changes:
        breadth = Decimal(sum(1 for item in changes if item > 0)) / Decimal(len(changes)) * Decimal("100")
    return breadth, _median(positive_pe), len(rows), len(changes), _median(positive_pb)


def _phase(
    *,
    return_20: Decimal | None,
    return_60: Decimal | None,
    turnover_change: Decimal | None,
    breadth: Decimal | None,
    relative_strength: Decimal | None,
) -> tuple[str, str, tuple[str, ...]]:
    metrics = {
        "return_20d": return_20,
        "return_60d": return_60,
        "turnover_change_20d": turnover_change,
        "breadth_rise_ratio": breadth,
        "relative_strength_20d": relative_strength,
    }
    missing = tuple(name for name, value in metrics.items() if value is None)
    if sum(value is not None for value in metrics.values()) < 4 or return_20 is None or return_60 is None:
        return "insufficient", "0.30", missing
    score = 0
    score += 1 if return_20 > 3 else -1 if return_20 < -3 else 0
    score += 1 if return_60 > 6 else -1 if return_60 < -6 else 0
    if turnover_change is not None:
        score += 1 if turnover_change > 15 else -1 if turnover_change < -15 else 0
    if breadth is not None:
        score += 1 if breadth >= 60 else -1 if breadth <= 40 else 0
    if relative_strength is not None:
        score += 1 if relative_strength > 2 else -1 if relative_strength < -2 else 0
    if return_20 > 8 and return_60 > 12 and (breadth or Decimal("0")) >= 70 and (turnover_change or Decimal("0")) > 25:
        phase = "overheated"
    elif score >= 3 and return_20 > 0 and return_60 > 0:
        phase = "expansion"
    elif score <= -3 and return_20 < 0 and return_60 < 0:
        phase = "contraction"
    elif return_20 < 0 and (return_60 > 0 or score <= -1):
        phase = "slowdown"
    elif return_20 >= 0 and score >= 1:
        phase = "recovery"
    else:
        phase = "insufficient"
    if phase == "insufficient" and not missing:
        missing = ("conflicting-or-neutral-cycle-evidence",)
    observed = 5 - len(missing)
    confidence = "0.85" if observed == 5 and phase != "insufficient" else "0.70" if phase != "insufficient" else "0.40"
    return phase, confidence, missing


def _productivity(
    *,
    constituent_rows: list[dict[str, Any]],
    financial_by_code: Mapping[str, Mapping[str, Any]],
    report_quarter: str | None,
) -> ProductivityProxy:
    matched = [
        financial_by_code[code]
        for row in constituent_rows
        if (code := _security_code(_field(row, "代码", "股票代码"))) in financial_by_code
    ]
    revenue = [_number(_field(row, "营业总收入-同比增长", "营业收入同比增长")) for row in matched]
    profit = [_number(_field(row, "净利润-同比增长", "净利润同比增长")) for row in matched]
    roe = [_number(_field(row, "净资产收益率", "ROE")) for row in matched]
    gross_margin = [_number(_field(row, "销售毛利率", "毛利率")) for row in matched]
    cashflow = [_number(_field(row, "每股经营现金流量", "每股经营现金流")) for row in matched]
    revenue_values = [value for value in revenue if value is not None]
    profit_values = [value for value in profit if value is not None]
    roe_values = [value for value in roe if value is not None]
    gross_margin_values = [value for value in gross_margin if value is not None]
    cashflow_values = [value for value in cashflow if value is not None]
    revenue_median, profit_median, roe_median = _median(revenue_values), _median(profit_values), _median(roe_values)
    positive_cashflow = None
    if cashflow_values:
        positive_cashflow = Decimal(sum(1 for value in cashflow_values if value > 0)) / Decimal(len(cashflow_values)) * 100
    core = (revenue_median, profit_median, roe_median, positive_cashflow)
    coverage = len(matched)
    minimum_coverage = max(3, min(8, len(constituent_rows) // 5)) if constituent_rows else 3
    if sum(value is not None for value in core) < 3 or coverage < minimum_coverage:
        status, confidence = "insufficient", "0.30"
    else:
        score = 0
        score += 1 if revenue_median is not None and revenue_median > 5 else -1 if revenue_median is not None and revenue_median < 0 else 0
        score += 1 if profit_median is not None and profit_median > 5 else -1 if profit_median is not None and profit_median < 0 else 0
        score += 1 if roe_median is not None and roe_median >= 8 else -1 if roe_median is not None and roe_median < 3 else 0
        score += 1 if positive_cashflow is not None and positive_cashflow >= 60 else -1 if positive_cashflow is not None and positive_cashflow <= 40 else 0
        status = "improving" if score >= 2 else "weakening" if score <= -2 else "stable"
        ratio = Decimal(coverage) / Decimal(max(len(constituent_rows), 1))
        confidence = "0.80" if ratio >= Decimal("0.60") else "0.65"
    missing_dimensions = ["capital_expenditure", "inventory_cycle", "penetration_rate", "orders", "policy"]
    for name, value in (
        ("revenue_yoy", revenue_median),
        ("profit_yoy", profit_median),
        ("roe", roe_median),
        ("operating_cashflow", positive_cashflow),
    ):
        if value is None:
            missing_dimensions.append(name)
    return ProductivityProxy(
        status=status,
        report_period=_quarter_label(report_quarter) if report_quarter else None,
        effective_at=_quarter_date(report_quarter) if report_quarter else None,
        revenue_yoy_median_pct=_render(revenue_median),
        profit_yoy_median_pct=_render(profit_median),
        roe_median_pct=_render(roe_median),
        gross_margin_median_pct=_render(_median(gross_margin_values)),
        operating_cashflow_positive_ratio_pct=_render(positive_cashflow),
        covered_constituents=coverage,
        total_constituents=len(constituent_rows),
        confidence=confidence,
        missing_dimensions=tuple(missing_dimensions),
    )


@dataclass(frozen=True)
class AkshareFundIndustryCycleConfig:
    network_enabled: bool = False
    human_approved: bool = False
    years: tuple[int, ...] = ()


class AkshareFundIndustryCycleService:
    def __init__(
        self,
        *,
        config: AkshareFundIndustryCycleConfig | None = None,
        akshare_module: Any | None = None,
        now: datetime | None = None,
    ) -> None:
        self.config = config or AkshareFundIndustryCycleConfig()
        self.akshare_module = akshare_module
        self.now = now or datetime.now(timezone.utc)

    def _akshare(self) -> Any:
        if self.akshare_module is None:
            import akshare as ak

            self.akshare_module = ak
        return self.akshare_module

    def fetch(
        self,
        codes: tuple[str, ...],
        *,
        comparison_result: FundComparisonResult | None = None,
    ) -> FundIndustryCycleResult:
        fetched_at = _utc_now_iso()
        if not (self.config.network_enabled and self.config.human_approved):
            return FundIndustryCycleResult(
                requested_codes=codes,
                data_status="missing",
                fetched_at=fetched_at,
                benchmark_code=BENCHMARK_CODE,
                financial_report_period=None,
                funds=(),
                industries=(),
                missing_evidence=("manual-local-approval",),
                warnings=("必须由用户在本机逐次确认后读取公开证据。",),
            )
        akshare_module = self._akshare()
        comparison = comparison_result
        if comparison is None or comparison.requested_codes != codes:
            comparison = AkshareFundComparisonService(
                config=AkshareFundComparisonConfig(
                    network_enabled=True,
                    human_approved=True,
                    years=self.config.years or (self.now.year, self.now.year - 1),
                ),
                akshare_module=akshare_module,
                now=self.now,
            ).fetch(codes)
        try:
            boards = _board_map(akshare_module)
        except Exception:
            boards = {}
        try:
            report_quarter, financial_rows = _financial_rows(akshare_module, self.now.date())
        except Exception:
            report_quarter, financial_rows = None, []
        financial_by_code = _financial_by_code(financial_rows)
        fund_links: dict[str, list[IndustryLink]] = {}
        unclassified: dict[str, list[str]] = {}
        totals: dict[str, Decimal] = {}
        for item in comparison.funds:
            links, missing_codes = _fund_links(
                item,
                board_names=set(boards),
                financial_by_code=financial_by_code,
            )
            fund_links[item.code] = links
            unclassified[item.code] = missing_codes
            for link in links:
                totals[link.industry_name] = totals.get(link.industry_name, Decimal("0")) + Decimal(link.fund_weight_pct)
        selected = [
            name for name, _ in sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))[:MAX_ANALYZED_INDUSTRIES]
        ]
        start_date = (self.now.date() - timedelta(days=180)).strftime("%Y%m%d")
        end_date = self.now.date().strftime("%Y%m%d")
        try:
            benchmark_rows = _records(
                akshare_module.index_zh_a_hist(
                    symbol=BENCHMARK_CODE,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                )
            )
            _, benchmark_20, _, _ = _history_metrics(benchmark_rows)
        except Exception:
            benchmark_20 = None
        industries: list[IndustryCycleEvidence] = []
        for name in selected:
            try:
                history_rows = _records(
                    akshare_module.stock_board_industry_hist_em(
                        symbol=name,
                        start_date=start_date,
                        end_date=end_date,
                        period="日k",
                        adjust="",
                    )
                )
            except Exception:
                history_rows = []
            try:
                constituent_rows = _records(akshare_module.stock_board_industry_cons_em(symbol=name))
            except Exception:
                constituent_rows = []
            as_of, return_20, return_60, turnover_change = _history_metrics(history_rows)
            breadth, median_pe, constituent_count, breadth_count, median_pb = _constituent_metrics(constituent_rows)
            relative = return_20 - benchmark_20 if return_20 is not None and benchmark_20 is not None else None
            phase, confidence, missing = _phase(
                return_20=return_20,
                return_60=return_60,
                turnover_change=turnover_change,
                breadth=breadth,
                relative_strength=relative,
            )
            productivity = _productivity(
                constituent_rows=constituent_rows,
                financial_by_code=financial_by_code,
                report_quarter=report_quarter,
            )
            dates = tuple(
                dict.fromkeys(
                    item for item in (as_of, productivity.effective_at) if item
                )
            )
            missing_all = list(missing)
            if not constituent_rows:
                missing_all.append("industry_constituents")
            if productivity.status == "insufficient":
                missing_all.append("productivity_proxy_coverage")
            data_status = "missing" if not history_rows and not constituent_rows else "partial" if missing_all else "available"
            industries.append(
                IndustryCycleEvidence(
                    industry_name=name,
                    board_code=boards[name],
                    data_status=data_status,
                    phase=phase,
                    confidence=confidence,
                    metrics=CycleMetrics(
                        as_of_date=as_of,
                        return_20d_pct=_render(return_20),
                        return_60d_pct=_render(return_60),
                        turnover_change_20d_pct=_render(turnover_change),
                        breadth_rise_ratio_pct=_render(breadth),
                        relative_strength_20d_pct=_render(relative),
                        median_dynamic_pe=_render(median_pe),
                        median_pb=_render(median_pb),
                        constituent_count=constituent_count,
                        breadth_sample_count=breadth_count,
                    ),
                    productivity=productivity,
                    source_interfaces=(
                        "stock_board_industry_hist_em",
                        "stock_board_industry_cons_em",
                        "index_zh_a_hist",
                        "stock_yjbb_em",
                    ),
                    evidence_dates=dates,
                    missing_evidence=tuple(dict.fromkeys(missing_all)),
                    warnings=(
                        "周期阶段由固定阈值生成，仅表示公开证据状态，不是买卖信号。",
                        "生产力为经营指标代理，不等同于全要素生产率或长期收益预测。",
                    ),
                )
            )
        selected_set = set(selected)
        funds: list[FundCycleImpact] = []
        for item in comparison.funds:
            all_links = fund_links.get(item.code, [])
            links = tuple(link for link in all_links if link.industry_name in selected_set)
            analyzed_weight = sum((Decimal(link.fund_weight_pct) for link in links), Decimal("0"))
            funds.append(
                FundCycleImpact(
                    code=item.code,
                    name=item.bundle.profile.name if item.bundle.profile else None,
                    holdings_report_period=item.bundle.holdings.report_period if item.bundle.holdings else None,
                    industry_links=links,
                    analyzed_weight_pct=_render(analyzed_weight) or "0",
                    unclassified_holdings=tuple(unclassified.get(item.code, [])),
                    omitted_industries=sum(1 for link in all_links if link.industry_name not in selected_set),
                    warnings=(
                        "基金影响仅关联公开披露行业或最新披露前十大持仓样本，不代表实时完整组合。",
                    ),
                )
            )
        missing_evidence: list[str] = []
        if not boards:
            missing_evidence.append("industry-board-directory")
        if not financial_rows:
            missing_evidence.append("financial-performance-report")
        if benchmark_20 is None:
            missing_evidence.append("benchmark-20d-return")
        if not selected:
            missing_evidence.append("verifiable-fund-industry-links")
        if not industries:
            status = "missing"
        elif any(
            item.data_status != "available"
            or item.productivity.status == "insufficient"
            or item.productivity.missing_dimensions
            for item in industries
        ):
            status = "partial"
        else:
            status = "available"
        return FundIndustryCycleResult(
            requested_codes=codes,
            data_status=status,
            fetched_at=fetched_at,
            benchmark_code=BENCHMARK_CODE,
            financial_report_period=_quarter_label(report_quarter) if report_quarter else None,
            funds=tuple(funds),
            industries=tuple(industries),
            missing_evidence=tuple(missing_evidence),
            warnings=(
                "短期行业周期与长期经营生产力代理分开展示。",
                "不包含仓位、调仓、买卖或自动执行建议。",
            ),
        )


def validate_cycle_result(result: FundIndustryCycleResult) -> list[str]:
    errors: list[str] = []
    if not 1 <= len(result.requested_codes) <= MAX_FUNDS or len(result.requested_codes) != len(set(result.requested_codes)):
        errors.append("requested fund codes must be unique and within the limit")
    if any(not FUND_CODE_RE.fullmatch(code) for code in result.requested_codes):
        errors.append("requested fund codes must be six digits")
    if result.data_status not in {"available", "partial", "missing"}:
        errors.append("unsupported result status")
    if result.benchmark_code != BENCHMARK_CODE:
        errors.append("unexpected benchmark")
    if len(result.industries) > MAX_ANALYZED_INDUSTRIES:
        errors.append("too many analyzed industries")
    names = [item.industry_name for item in result.industries]
    if len(names) != len(set(names)):
        errors.append("industry evidence must be unique")
    for item in result.industries:
        if not item.industry_name or not item.board_code or item.phase not in PHASES:
            errors.append("invalid industry evidence identity or phase")
        if not item.source_interfaces or len(item.source_interfaces) != len(set(item.source_interfaces)):
            errors.append("industry evidence requires unique source interfaces")
        if item.productivity.status not in PRODUCTIVITY_STATES:
            errors.append("invalid productivity status")
        for confidence in (item.confidence, item.productivity.confidence):
            parsed = _number(confidence)
            if parsed is None or parsed < 0 or parsed > 1:
                errors.append("confidence must be between zero and one")
        if item.phase == "insufficient" and not item.missing_evidence:
            errors.append("insufficient phase must declare missing evidence")
        if item.productivity.status == "insufficient" and not item.productivity.missing_dimensions:
            errors.append("insufficient productivity must declare missing dimensions")
    fund_codes = [item.code for item in result.funds]
    if len(fund_codes) != len(set(fund_codes)) or set(fund_codes) - set(result.requested_codes):
        errors.append("fund impact codes must be unique requested funds")
    return errors


def validate_cycle_request(payload: Mapping[str, Any]) -> tuple[str, ...]:
    if not isinstance(payload, Mapping) or set(payload) != CYCLE_REQUEST_FIELDS:
        raise FundIndustryCycleError("fund-industry-cycle.invalid-request")
    codes = payload.get("codes")
    sections = payload.get("sections")
    if not isinstance(codes, list) or not 1 <= len(codes) <= MAX_FUNDS:
        raise FundIndustryCycleError("fund-industry-cycle.invalid-codes")
    if any(not isinstance(code, str) or not FUND_CODE_RE.fullmatch(code) for code in codes):
        raise FundIndustryCycleError("fund-industry-cycle.invalid-codes")
    if len(codes) != len(set(codes)):
        raise FundIndustryCycleError("fund-industry-cycle.duplicate-codes")
    if not isinstance(sections, list) or set(sections) != CYCLE_SECTIONS or len(sections) != len(CYCLE_SECTIONS):
        raise FundIndustryCycleError("fund-industry-cycle.invalid-sections")
    if not (
        payload.get("mode") == "fund-industry-cycle-readonly"
        and payload.get("provider") == PROVIDER_NAME
        and payload.get("humanApproved") is True
        and payload.get("readOnly") is True
    ):
        raise FundIndustryCycleError("fund-industry-cycle.approval-required")
    if any(
        payload.get(field) is not False
        for field in ("allowAccountRead", "allowTrading", "allowNotificationSend", "allowAiCall", "allowPersistence")
    ):
        raise FundIndustryCycleError("fund-industry-cycle.forbidden-capability")
    return tuple(codes)


def run_akshare_fund_industry_cycle(
    payload: Mapping[str, Any],
    *,
    akshare_module: Any | None = None,
) -> dict[str, Any]:
    try:
        codes = validate_cycle_request(payload)
        result = AkshareFundIndustryCycleService(
            config=AkshareFundIndustryCycleConfig(network_enabled=True, human_approved=True),
            akshare_module=akshare_module,
        ).fetch(codes)
        if validate_cycle_result(result):
            return {
                "status": "unavailable",
                "errorCode": "fund-industry-cycle.invalid-provider-result",
                "providerLabel": PROVIDER_LABEL,
                "readOnly": True,
            }
        return {
            "status": "completed-readonly" if result.data_status in {"available", "partial"} else "unavailable",
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
            "cycle": result.to_dict(),
        }
    except FundIndustryCycleError as exc:
        return {
            "status": "blocked",
            "errorCode": exc.code,
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
        }


async def run_akshare_fund_industry_cycle_with_timeout(
    payload: Mapping[str, Any],
    *,
    akshare_module: Any | None = None,
    timeout_seconds: float = CYCLE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(run_akshare_fund_industry_cycle, payload, akshare_module=akshare_module),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "errorCode": "fund-industry-cycle.provider-timeout",
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
        }
