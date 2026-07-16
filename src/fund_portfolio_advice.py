"""Deterministic, explainable fund-portfolio risk and allocation guidance.

Build D4 combines the active user's in-memory fund amounts with the public,
auditable D2/D3 evidence.  Amounts stay inside the localhost process: only the
selected fund codes are passed to AKShare.  Results are review prompts, never
orders, return forecasts, or account actions.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping

from src.fund_comparison import (
    MAX_FUNDS,
    AkshareFundComparisonConfig,
    AkshareFundComparisonService,
    FundComparisonResult,
)
from src.fund_data_akshare_provider import FUND_CODE_RE, PROVIDER_LABEL, PROVIDER_NAME, _decimal_text
from src.fund_industry_cycle import (
    AkshareFundIndustryCycleConfig,
    AkshareFundIndustryCycleService,
    FundIndustryCycleResult,
)


ADVICE_TIMEOUT_SECONDS = 100
MAX_PORTFOLIO_HOLDINGS = 20
ADVICE_SECTIONS = frozenset({"portfolio-concentration", "overlap", "industry-cycle", "target-drift"})
ADVICE_REQUEST_FIELDS = frozenset(
    {
        "mode", "provider", "holdings", "sections", "humanApproved", "readOnly",
        "allowAccountRead", "allowTrading", "allowNotificationSend", "allowAiCall", "allowPersistence",
    }
)


class FundPortfolioAdviceError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _number(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return parsed if parsed.is_finite() else None


def _render(value: Decimal, places: int = 2) -> str:
    quantum = Decimal("1").scaleb(-places)
    return _decimal_text(value.quantize(quantum, rounding=ROUND_HALF_UP)) or "0"


@dataclass(frozen=True)
class PortfolioHoldingInput:
    code: str
    name: str
    amount: Decimal
    profit: Decimal
    target_allocation: Decimal | None


@dataclass(frozen=True)
class PortfolioFundWeight:
    code: str
    name: str
    amount: str
    weight_pct: str
    profit: str
    target_allocation_pct: str | None
    target_drift_pct: str | None
    public_evidence_included: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "amount": self.amount,
            "weight_pct": self.weight_pct,
            "profit": self.profit,
            "target_allocation_pct": self.target_allocation_pct,
            "target_drift_pct": self.target_drift_pct,
            "public_evidence_included": self.public_evidence_included,
        }


@dataclass(frozen=True)
class AdviceFinding:
    category: str
    severity: str
    title: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AllocationSuggestion:
    priority: str
    title: str
    reason: str
    action_scope: str = "review-only-no-automatic-execution"

    def to_dict(self) -> dict[str, str]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class FundPortfolioAdviceResult:
    data_status: str
    risk_level: str
    total_amount: str
    total_profit: str
    holding_count: int
    unique_fund_count: int
    top_fund_weight_pct: str
    top3_weight_pct: str
    public_evidence_codes: tuple[str, ...]
    public_evidence_coverage_pct: str
    funds: tuple[PortfolioFundWeight, ...]
    findings: tuple[AdviceFinding, ...]
    suggestions: tuple[AllocationSuggestion, ...]
    missing_evidence: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "data_status": self.data_status,
            "risk_level": self.risk_level,
            "total_amount": self.total_amount,
            "total_profit": self.total_profit,
            "holding_count": self.holding_count,
            "unique_fund_count": self.unique_fund_count,
            "top_fund_weight_pct": self.top_fund_weight_pct,
            "top3_weight_pct": self.top3_weight_pct,
            "public_evidence_codes": list(self.public_evidence_codes),
            "public_evidence_coverage_pct": self.public_evidence_coverage_pct,
            "funds": [item.to_dict() for item in self.funds],
            "findings": [item.to_dict() for item in self.findings],
            "suggestions": [item.to_dict() for item in self.suggestions],
            "missing_evidence": list(self.missing_evidence),
            "warnings": list(self.warnings),
            "scope": "active-user-in-memory-fund-portfolio-review",
            "advice_boundary": "educational-review-not-investment-order",
        }


def _aggregate(holdings: tuple[PortfolioHoldingInput, ...]) -> tuple[PortfolioHoldingInput, ...]:
    merged: dict[str, PortfolioHoldingInput] = {}
    for item in holdings:
        previous = merged.get(item.code)
        if previous is None:
            merged[item.code] = item
            continue
        target = item.target_allocation if item.target_allocation is not None else previous.target_allocation
        merged[item.code] = PortfolioHoldingInput(
            code=item.code,
            name=previous.name or item.name,
            amount=previous.amount + item.amount,
            profit=previous.profit + item.profit,
            target_allocation=target,
        )
    return tuple(sorted(merged.values(), key=lambda item: (-item.amount, item.code)))


def analyze_fund_portfolio(
    holdings: tuple[PortfolioHoldingInput, ...],
    comparison: FundComparisonResult | None,
    cycle: FundIndustryCycleResult | None,
) -> FundPortfolioAdviceResult:
    aggregated = _aggregate(holdings)
    total = sum((item.amount for item in aggregated), Decimal("0"))
    total_profit = sum((item.profit for item in aggregated), Decimal("0"))
    evidence_codes = tuple(item.code for item in aggregated[:MAX_FUNDS])
    weights = {item.code: item.amount / total * Decimal("100") for item in aggregated}
    coverage = sum((weights[code] for code in evidence_codes), Decimal("0"))
    target_values = [item.target_allocation for item in aggregated if item.target_allocation is not None]
    targets_usable = len(target_values) >= 2 and Decimal("95") <= sum(target_values, Decimal("0")) <= Decimal("105")
    funds = tuple(
        PortfolioFundWeight(
            code=item.code,
            name=item.name,
            amount=_render(item.amount),
            weight_pct=_render(weights[item.code]),
            profit=_render(item.profit),
            target_allocation_pct=_render(item.target_allocation) if item.target_allocation is not None else None,
            target_drift_pct=_render(weights[item.code] - item.target_allocation)
            if targets_usable and item.target_allocation is not None else None,
            public_evidence_included=item.code in evidence_codes,
        )
        for item in aggregated
    )
    findings: list[AdviceFinding] = []
    suggestions: list[AllocationSuggestion] = []
    warnings = [
        "组合权重仅按当前页面录入的基金金额计算，不包含现金、股票、负债或外部账户。",
        "公开基金持仓和行业配置是披露数据，不代表实时完整仓位。",
    ]
    missing: list[str] = []

    top_weight = weights[aggregated[0].code]
    top3 = sum((weights[item.code] for item in aggregated[:3]), Decimal("0"))
    if top_weight >= Decimal("35"):
        findings.append(AdviceFinding("single-fund-concentration", "high", "单只基金占比较高", f"{aggregated[0].code} 占基金组合 {_render(top_weight)}%。"))
        suggestions.append(AllocationSuggestion("high", "复核单只基金上限", "单只基金超过固定审慎阈值 35%，先核对它是否符合您自行设定的集中度上限。"))
    elif top_weight >= Decimal("25"):
        findings.append(AdviceFinding("single-fund-concentration", "medium", "单只基金集中度需关注", f"{aggregated[0].code} 占基金组合 {_render(top_weight)}%。"))
    if top3 >= Decimal("75") and len(aggregated) > 3:
        findings.append(AdviceFinding("top3-concentration", "medium", "前三只基金集中", f"前三只合计占 {_render(top3)}%。"))
        suggestions.append(AllocationSuggestion("medium", "复核前三集中度", "检查前三只基金是否实际集中在相同基金类型、行业或重复持仓。"))

    if targets_usable:
        drifts = [(item, weights[item.code] - (item.target_allocation or Decimal("0"))) for item in aggregated]
        material = [(item, drift) for item, drift in drifts if abs(drift) >= Decimal("5")]
        if material:
            findings.append(AdviceFinding("target-drift", "medium", "当前权重偏离自定目标", "；".join(f"{item.code} {_render(drift)}个百分点" for item, drift in material[:5])))
            suggestions.append(AllocationSuggestion("medium", "按自定目标复核再平衡", "只对照您已录入且合计约为 100% 的目标比例；是否调整、何时调整由您确认。"))
    elif target_values:
        missing.append("usable-target-allocation-plan")
        warnings.append("目标比例不足两项或合计不在 95%—105%，未生成目标偏离建议。")
    else:
        missing.append("target-allocation-plan")

    if comparison is None or not comparison.funds:
        missing.append("fund-comparison-and-industry-exposure")
    else:
        type_weights: dict[str, Decimal] = {}
        for fund in comparison.funds:
            fund_type = fund.bundle.profile.fund_type if fund.bundle.profile else None
            if fund_type and fund.code in weights:
                type_weights[fund_type] = type_weights.get(fund_type, Decimal("0")) + weights[fund.code]
        if type_weights:
            fund_type, type_weight = max(type_weights.items(), key=lambda item: item[1])
            if type_weight >= Decimal("60"):
                findings.append(AdviceFinding("fund-type-concentration", "medium", "基金类型集中", f"已核验范围内 {fund_type} 约占组合 {_render(type_weight)}%。"))
        for pair in comparison.pair_overlaps:
            holding_overlap = _number(pair.disclosed_holdings_overlap_pct) or Decimal("0")
            industry_overlap = _number(pair.disclosed_industry_overlap_pct) or Decimal("0")
            if holding_overlap >= Decimal("20") or industry_overlap >= Decimal("30"):
                severity = "high" if holding_overlap >= Decimal("35") or industry_overlap >= Decimal("50") else "medium"
                findings.append(AdviceFinding(
                    "disclosed-overlap", severity, "基金之间存在披露重合",
                    f"{pair.left_code}/{pair.right_code}：持仓重合下限 {_render(holding_overlap)}%，行业重合下限 {_render(industry_overlap)}%。",
                ))
        if any(item.category == "disclosed-overlap" for item in findings):
            suggestions.append(AllocationSuggestion("medium", "复核重复暴露", "避免把基金数量多误认为真正分散；结合披露日期检查重复持仓和行业。"))
        if comparison.data_status != "available":
            missing.append("complete-fund-comparison-evidence")

    if cycle is None or not cycle.industries:
        missing.append("industry-cycle-and-productivity-evidence")
    else:
        fund_links = {fund.code: fund.industry_links for fund in cycle.funds}
        industry_map = {item.industry_name: item for item in cycle.industries}
        affected: dict[str, Decimal] = {}
        for code, links in fund_links.items():
            portfolio_weight = weights.get(code, Decimal("0"))
            for link in links:
                affected[link.industry_name] = affected.get(link.industry_name, Decimal("0")) + portfolio_weight * Decimal(link.fund_weight_pct) / Decimal("100")
        for industry_name, approx_weight in sorted(affected.items(), key=lambda item: -item[1]):
            evidence = industry_map.get(industry_name)
            if evidence is None or approx_weight < Decimal("8"):
                continue
            if evidence.phase in {"slowdown", "contraction", "overheated"} or evidence.productivity.status == "weakening":
                severity = "high" if approx_weight >= Decimal("20") and evidence.phase in {"contraction", "overheated"} else "medium"
                findings.append(AdviceFinding(
                    "industry-evidence-risk", severity, f"{industry_name} 证据需复核",
                    f"按披露权重估算影响约 {_render(approx_weight)}%；周期={evidence.phase}，经营代理={evidence.productivity.status}，置信度={evidence.confidence}。",
                ))
        if any(item.category == "industry-evidence-risk" for item in findings):
            suggestions.append(AllocationSuggestion("medium", "复核行业逆风暴露", "先核对披露日期、覆盖率和经营代理证据，不把短期周期直接当作交易信号。"))
        if cycle.data_status != "available" or cycle.missing_evidence:
            missing.append("complete-industry-cycle-evidence")

    if coverage < Decimal("70"):
        missing.append("public-evidence-coverage-below-70pct")
        findings.append(AdviceFinding("evidence-coverage", "medium", "公开证据覆盖不足", f"受每次公开读取上限约束，本次覆盖基金组合 {_render(coverage)}%。"))

    severities = {item.severity for item in findings}
    if "high" in severities:
        risk_level = "high"
    elif "medium" in severities:
        risk_level = "medium"
    elif missing:
        risk_level = "insufficient"
    else:
        risk_level = "low"
    data_status = "partial" if missing else "available"
    if not suggestions:
        suggestions.append(AllocationSuggestion("low", "维持观察并定期复核", "当前固定阈值未发现高/中风险，但仍需结合目标、期限和风险承受能力人工确认。"))
    return FundPortfolioAdviceResult(
        data_status=data_status,
        risk_level=risk_level,
        total_amount=_render(total),
        total_profit=_render(total_profit),
        holding_count=len(holdings),
        unique_fund_count=len(aggregated),
        top_fund_weight_pct=_render(top_weight),
        top3_weight_pct=_render(top3),
        public_evidence_codes=evidence_codes,
        public_evidence_coverage_pct=_render(coverage),
        funds=funds,
        findings=tuple(findings),
        suggestions=tuple(suggestions),
        missing_evidence=tuple(dict.fromkeys(missing)),
        warnings=tuple(warnings),
    )


def validate_advice_request(payload: Mapping[str, Any]) -> tuple[PortfolioHoldingInput, ...]:
    if not isinstance(payload, Mapping) or set(payload) != ADVICE_REQUEST_FIELDS:
        raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-request")
    raw_holdings = payload.get("holdings")
    if not isinstance(raw_holdings, list) or not 1 <= len(raw_holdings) <= MAX_PORTFOLIO_HOLDINGS:
        raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-holdings")
    holdings: list[PortfolioHoldingInput] = []
    expected = {"code", "name", "amount", "profit", "targetAllocation"}
    for item in raw_holdings:
        if not isinstance(item, Mapping) or set(item) != expected:
            raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-holdings")
        code, name = item.get("code"), item.get("name")
        amount, profit, target = _number(item.get("amount")), _number(item.get("profit")), _number(item.get("targetAllocation")) if item.get("targetAllocation") is not None else None
        if not isinstance(code, str) or not FUND_CODE_RE.fullmatch(code) or not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-holdings")
        if amount is None or amount <= 0 or amount > Decimal("1000000000") or profit is None or abs(profit) > Decimal("1000000000"):
            raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-holdings")
        if target is not None and (target < 0 or target > 100):
            raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-holdings")
        holdings.append(PortfolioHoldingInput(code, name.strip(), amount, profit, target))
    sections = payload.get("sections")
    if not isinstance(sections, list) or set(sections) != ADVICE_SECTIONS or len(sections) != len(ADVICE_SECTIONS):
        raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-sections")
    if not (payload.get("mode") == "fund-portfolio-advice-readonly" and payload.get("provider") == PROVIDER_NAME and payload.get("humanApproved") is True and payload.get("readOnly") is True):
        raise FundPortfolioAdviceError("fund-portfolio-advice.approval-required")
    if any(payload.get(field) is not False for field in ("allowAccountRead", "allowTrading", "allowNotificationSend", "allowAiCall", "allowPersistence")):
        raise FundPortfolioAdviceError("fund-portfolio-advice.forbidden-capability")
    return tuple(holdings)


def run_akshare_fund_portfolio_advice(payload: Mapping[str, Any], *, akshare_module: Any | None = None) -> dict[str, Any]:
    try:
        holdings = validate_advice_request(payload)
        codes = tuple(item.code for item in _aggregate(holdings)[:MAX_FUNDS])
        comparison = AkshareFundComparisonService(
            config=AkshareFundComparisonConfig(network_enabled=True, human_approved=True), akshare_module=akshare_module,
        ).fetch(codes)
        cycle = AkshareFundIndustryCycleService(
            config=AkshareFundIndustryCycleConfig(network_enabled=True, human_approved=True), akshare_module=akshare_module,
        ).fetch(codes)
        result = analyze_fund_portfolio(holdings, comparison, cycle)
        return {"status": "completed-readonly", "providerLabel": PROVIDER_LABEL, "readOnly": True, "advice": result.to_dict()}
    except FundPortfolioAdviceError as exc:
        return {"status": "blocked", "errorCode": exc.code, "providerLabel": PROVIDER_LABEL, "readOnly": True}
    except Exception:
        return {"status": "unavailable", "errorCode": "fund-portfolio-advice.provider-error", "providerLabel": PROVIDER_LABEL, "readOnly": True}


async def run_akshare_fund_portfolio_advice_with_timeout(payload: Mapping[str, Any], *, akshare_module: Any | None = None, timeout_seconds: float = ADVICE_TIMEOUT_SECONDS) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(asyncio.to_thread(run_akshare_fund_portfolio_advice, payload, akshare_module=akshare_module), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return {"status": "timeout", "errorCode": "fund-portfolio-advice.provider-timeout", "providerLabel": PROVIDER_LABEL, "readOnly": True}
