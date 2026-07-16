"""Current-user fund portfolio risk evidence and allocation guidance.

Build D4 accepts only manually approved, normalized fund weights from the
browser's in-memory current-user workspace.  It never receives user identity,
holding amounts, cost basis, account credentials, or trading authority.  The
result combines D2 disclosed comparison, D3 cycle evidence, and public NAV
history using deterministic rules.  Guidance is a review checklist, not an
order, model forecast, or automatic rebalance plan.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import sqrt
from statistics import pstdev
from typing import Any, Mapping

from src.fund_comparison import (
    MAX_FUNDS,
    AkshareFundComparisonConfig,
    AkshareFundComparisonService,
    FundComparisonResult,
)
from src.fund_data_akshare_provider import (
    FUND_CODE_RE,
    PROVIDER_LABEL,
    PROVIDER_NAME,
    _date_text,
    _field,
    _records,
)
from src.fund_industry_cycle import (
    AkshareFundIndustryCycleConfig,
    AkshareFundIndustryCycleService,
    FundIndustryCycleResult,
)


PORTFOLIO_ADVICE_TIMEOUT_SECONDS = 75
PORTFOLIO_ADVICE_SECTIONS = frozenset(
    {
        "portfolio-allocation",
        "nav-risk",
        "disclosed-overlap",
        "industry-cycle",
        "allocation-guidance",
    }
)
PORTFOLIO_ADVICE_REQUEST_FIELDS = frozenset(
    {
        "mode",
        "provider",
        "positions",
        "riskProfile",
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
POSITION_FIELDS = frozenset({"code", "weightPct", "targetWeightPct"})
RISK_PROFILES = frozenset({"conservative", "balanced", "aggressive"})
DIMENSION_STATES = frozenset({"normal", "watch", "high", "insufficient", "not-applicable"})
FORCED_ACTION_PHRASES = (
    "立即买入",
    "立即卖出",
    "必须买入",
    "必须卖出",
    "清仓",
    "满仓",
    "保证收益",
    "自动下单",
)


class FundPortfolioAdviceError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PortfolioPosition:
    code: str
    weight_pct: Decimal
    target_weight_pct: Decimal | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "weight_pct": _render(self.weight_pct, 4),
            "target_weight_pct": _render(self.target_weight_pct, 4),
        }


@dataclass(frozen=True)
class FundNavRisk:
    code: str
    data_status: str
    as_of_date: str | None
    observations: int
    return_20d_pct: str | None
    return_60d_pct: str | None
    annualized_volatility_60d_pct: str | None
    max_drawdown_120d_pct: str | None
    missing_evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "data_status": self.data_status,
            "as_of_date": self.as_of_date,
            "observations": self.observations,
            "return_20d_pct": self.return_20d_pct,
            "return_60d_pct": self.return_60d_pct,
            "annualized_volatility_60d_pct": self.annualized_volatility_60d_pct,
            "max_drawdown_120d_pct": self.max_drawdown_120d_pct,
            "missing_evidence": list(self.missing_evidence),
        }


@dataclass(frozen=True)
class AkshareFundPortfolioAdviceConfig:
    network_enabled: bool = False
    human_approved: bool = False
    years: tuple[int, ...] = ()


PROFILE_THRESHOLDS: dict[str, dict[str, Decimal]] = {
    "conservative": {
        "single_fund": Decimal("30"),
        "top_two": Decimal("60"),
        "single_industry": Decimal("20"),
        "volatility": Decimal("18"),
        "drawdown": Decimal("10"),
    },
    "balanced": {
        "single_fund": Decimal("40"),
        "top_two": Decimal("70"),
        "single_industry": Decimal("25"),
        "volatility": Decimal("25"),
        "drawdown": Decimal("15"),
    },
    "aggressive": {
        "single_fund": Decimal("50"),
        "top_two": Decimal("80"),
        "single_industry": Decimal("35"),
        "volatility": Decimal("35"),
        "drawdown": Decimal("25"),
    },
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _render(value: Decimal | int | float | None, places: int = 2) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    quantum = Decimal("1").scaleb(-places)
    rendered = value.quantize(quantum, rounding=ROUND_HALF_UP)
    text = format(rendered, "f").rstrip("0").rstrip(".")
    return text or "0"


def _status(value: Decimal | None, watch: Decimal, high: Decimal) -> str:
    if value is None:
        return "insufficient"
    if value > high:
        return "high"
    if value > watch:
        return "watch"
    return "normal"


def _nav_history(akshare_module: Any, code: str) -> FundNavRisk:
    try:
        rows = _records(akshare_module.fund_open_fund_info_em(symbol=code, indicator="单位净值走势"))
    except Exception:
        rows = []
    dated: dict[str, Decimal] = {}
    for row in rows:
        day = _date_text(_field(row, "净值日期", "日期"))
        nav = _decimal(_field(row, "单位净值", "净值"))
        if day and nav is not None and nav > 0:
            dated[day] = nav
    series = sorted(dated.items())
    values = [value for _, value in series]
    missing: list[str] = []
    return_20 = None
    return_60 = None
    volatility = None
    drawdown = None
    if len(values) >= 21:
        return_20 = (values[-1] / values[-21] - Decimal("1")) * Decimal("100")
    else:
        missing.append("nav-return-20d")
    if len(values) >= 61:
        return_60 = (values[-1] / values[-61] - Decimal("1")) * Decimal("100")
        recent = values[-61:]
        daily_returns = [float(recent[index] / recent[index - 1] - Decimal("1")) for index in range(1, len(recent))]
        volatility = Decimal(str(pstdev(daily_returns) * sqrt(252) * 100))
    else:
        missing.extend(("nav-return-60d", "nav-volatility-60d"))
    if len(values) >= 2:
        window = values[-120:]
        peak = window[0]
        worst = Decimal("0")
        for value in window:
            peak = max(peak, value)
            worst = min(worst, (value / peak - Decimal("1")) * Decimal("100"))
        drawdown = worst
    else:
        missing.append("nav-drawdown")
    status = "missing" if not values else "partial" if missing else "available"
    return FundNavRisk(
        code=code,
        data_status=status,
        as_of_date=series[-1][0] if series else None,
        observations=len(values),
        return_20d_pct=_render(return_20),
        return_60d_pct=_render(return_60),
        annualized_volatility_60d_pct=_render(volatility),
        max_drawdown_120d_pct=_render(drawdown),
        missing_evidence=tuple(dict.fromkeys(missing)),
    )


def _concentration(positions: tuple[PortfolioPosition, ...], profile: str) -> dict[str, Any]:
    weights = sorted((item.weight_pct for item in positions), reverse=True)
    maximum = weights[0]
    top_two = sum(weights[:2], Decimal("0"))
    hhi = sum(((weight / Decimal("100")) ** 2 for weight in weights), Decimal("0"))
    effective = Decimal("1") / hhi if hhi else Decimal("0")
    thresholds = PROFILE_THRESHOLDS[profile]
    level = "high" if (
        maximum > thresholds["single_fund"] + Decimal("10")
        or top_two > thresholds["top_two"] + Decimal("10")
    ) else "watch" if (
        maximum > thresholds["single_fund"] or top_two > thresholds["top_two"]
    ) else "normal"
    return {
        "status": level,
        "largest_fund_weight_pct": _render(maximum),
        "top_two_weight_pct": _render(top_two),
        "herfindahl_index": _render(hhi, 4),
        "effective_fund_count": _render(effective),
        "attention_thresholds": {
            "single_fund_pct": _render(thresholds["single_fund"]),
            "top_two_pct": _render(thresholds["top_two"]),
            "scope": "monitoring-thresholds-not-prescribed-allocation",
        },
    }


def _overlap(comparison: FundComparisonResult) -> dict[str, Any]:
    if len(comparison.requested_codes) < 2:
        return {
            "status": "not-applicable",
            "max_disclosed_holdings_overlap_pct": None,
            "max_disclosed_industry_overlap_pct": None,
            "highest_pair": None,
            "pair_count": 0,
            "scope": "latest-disclosed-data-lower-bound",
        }
    holding_max = Decimal("0")
    industry_max = Decimal("0")
    highest_pair: str | None = None
    highest_score = Decimal("-1")
    funds = {item.code: item for item in comparison.funds}
    evaluable_pairs = 0
    for pair in comparison.pair_overlaps:
        left = funds.get(pair.left_code)
        right = funds.get(pair.right_code)
        holdings_available = bool(left and right and left.bundle.holdings and right.bundle.holdings)
        industries_available = bool(left and right and left.industry_exposure and right.industry_exposure)
        if not holdings_available and not industries_available:
            continue
        evaluable_pairs += 1
        holding = (_decimal(pair.disclosed_holdings_overlap_pct) or Decimal("0")) if holdings_available else Decimal("0")
        industry = (_decimal(pair.disclosed_industry_overlap_pct) or Decimal("0")) if industries_available else Decimal("0")
        holding_max = max(holding_max, holding)
        industry_max = max(industry_max, industry)
        score = max(holding, industry)
        if score > highest_score:
            highest_score = score
            highest_pair = f"{pair.left_code}-{pair.right_code}"
    maximum = max(holding_max, industry_max) if evaluable_pairs else None
    return {
        "status": _status(maximum, Decimal("15"), Decimal("30")),
        "max_disclosed_holdings_overlap_pct": _render(holding_max) if evaluable_pairs else None,
        "max_disclosed_industry_overlap_pct": _render(industry_max) if evaluable_pairs else None,
        "highest_pair": highest_pair,
        "pair_count": evaluable_pairs,
        "scope": "latest-disclosed-data-lower-bound",
    }


def _industry_exposure(
    comparison: FundComparisonResult,
    weights: Mapping[str, Decimal],
    profile: str,
) -> dict[str, Any]:
    totals: dict[str, Decimal] = {}
    coverage = Decimal("0")
    report_dates: list[str] = []
    for fund in comparison.funds:
        exposure = fund.industry_exposure
        portfolio_weight = weights.get(fund.code, Decimal("0"))
        if exposure is None:
            continue
        report_dates.append(exposure.report_date)
        coverage += portfolio_weight * (Decimal(exposure.disclosed_total_pct) / Decimal("100"))
        for item in exposure.industries:
            totals[item.industry_name] = totals.get(item.industry_name, Decimal("0")) + (
                portfolio_weight * Decimal(item.weight_pct) / Decimal("100")
            )
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    top = ranked[0][1] if ranked else None
    threshold = PROFILE_THRESHOLDS[profile]["single_industry"]
    return {
        "status": _status(top, threshold, threshold + Decimal("10")),
        "disclosed_portfolio_coverage_pct": _render(coverage),
        "unclassified_or_undisclosed_pct": _render(max(Decimal("0"), Decimal("100") - coverage)),
        "top_industries": [
            {"industry_name": name, "portfolio_exposure_pct": _render(value)}
            for name, value in ranked[:5]
        ],
        "top_three_exposure_pct": _render(sum((value for _, value in ranked[:3]), Decimal("0"))),
        "report_dates": list(dict.fromkeys(report_dates)),
        "attention_threshold_pct": _render(threshold),
        "scope": "provider-disclosed-look-through-not-complete-current-portfolio",
    }


def _nav_summary(
    nav_items: tuple[FundNavRisk, ...],
    weights: Mapping[str, Decimal],
    profile: str,
) -> dict[str, Any]:
    weighted_volatility = Decimal("0")
    covered_weight = Decimal("0")
    worst_drawdown: Decimal | None = None
    for item in nav_items:
        volatility = _decimal(item.annualized_volatility_60d_pct)
        drawdown = _decimal(item.max_drawdown_120d_pct)
        weight = weights.get(item.code, Decimal("0"))
        if volatility is not None:
            weighted_volatility += volatility * weight / Decimal("100")
            covered_weight += weight
        if drawdown is not None:
            worst_drawdown = drawdown if worst_drawdown is None else min(worst_drawdown, drawdown)
    adjusted_volatility = (
        weighted_volatility * Decimal("100") / covered_weight if covered_weight > 0 else None
    )
    drawdown_magnitude = abs(worst_drawdown) if worst_drawdown is not None else None
    thresholds = PROFILE_THRESHOLDS[profile]
    vol_state = _status(
        adjusted_volatility,
        thresholds["volatility"],
        thresholds["volatility"] + Decimal("10"),
    )
    drawdown_state = _status(
        drawdown_magnitude,
        thresholds["drawdown"],
        thresholds["drawdown"] + Decimal("10"),
    )
    state = "insufficient" if vol_state == "insufficient" and drawdown_state == "insufficient" else (
        "high" if "high" in {vol_state, drawdown_state} else
        "watch" if "watch" in {vol_state, drawdown_state} else "normal"
    )
    return {
        "status": state,
        "weighted_average_fund_volatility_60d_pct": _render(adjusted_volatility),
        "volatility_coverage_pct": _render(covered_weight),
        "worst_fund_drawdown_120d_pct": _render(worst_drawdown),
        "funds": [item.to_dict() for item in nav_items],
        "attention_thresholds": {
            "annualized_volatility_pct": _render(thresholds["volatility"]),
            "drawdown_magnitude_pct": _render(thresholds["drawdown"]),
        },
        "scope": "weighted-average-of-fund-volatility-not-covariance-portfolio-volatility",
    }


def _cycle_exposure(cycle: FundIndustryCycleResult, weights: Mapping[str, Decimal]) -> dict[str, Any]:
    phases = {item.industry_name: item.phase for item in cycle.industries}
    productivity = {item.industry_name: item.productivity.status for item in cycle.industries}
    totals: dict[str, Decimal] = {}
    weakening = Decimal("0")
    covered = Decimal("0")
    for fund in cycle.funds:
        fund_weight = weights.get(fund.code, Decimal("0"))
        for link in fund.industry_links:
            exposure = fund_weight * Decimal(link.fund_weight_pct) / Decimal("100")
            phase = phases.get(link.industry_name, "insufficient")
            totals[phase] = totals.get(phase, Decimal("0")) + exposure
            covered += exposure
            if productivity.get(link.industry_name) == "weakening":
                weakening += exposure
    pressure = sum((totals.get(name, Decimal("0")) for name in ("overheated", "slowdown", "contraction")), Decimal("0"))
    state = "insufficient" if covered == 0 else _status(pressure, Decimal("10"), Decimal("20"))
    return {
        "status": state,
        "analyzed_portfolio_exposure_pct": _render(covered),
        "phase_exposure_pct": {name: _render(value) for name, value in sorted(totals.items())},
        "pressure_exposure_pct": _render(pressure),
        "weakening_productivity_proxy_exposure_pct": _render(weakening),
        "financial_report_period": cycle.financial_report_period,
        "scope": "selected-disclosed-industry-evidence-not-market-timing-signal",
    }


def _guidance(
    positions: tuple[PortfolioPosition, ...],
    concentration: Mapping[str, Any],
    overlap: Mapping[str, Any],
    industry: Mapping[str, Any],
    nav: Mapping[str, Any],
    cycle: Mapping[str, Any],
    missing: list[str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    target_complete = all(item.target_weight_pct is not None for item in positions)
    target_total = sum((item.target_weight_pct or Decimal("0") for item in positions), Decimal("0"))
    if target_complete and abs(target_total - Decimal("100")) <= Decimal("0.1"):
        for position in positions:
            target = position.target_weight_pct or Decimal("0")
            gap = position.weight_pct - target
            if abs(gap) >= Decimal("5"):
                direction = "高于" if gap > 0 else "低于"
                items.append({
                    "id": f"target-gap-{position.code}",
                    "priority": "watch",
                    "title": f"{position.code} 当前占比{direction}已记录目标",
                    "reason": "当前占比与用户自行记录的目标仓位偏差达到 5 个百分点。",
                    "evidence": [
                        f"当前 {_render(position.weight_pct)}%",
                        f"目标 {_render(target)}%",
                        f"偏差 {_render(gap)} 个百分点",
                    ],
                    "action": "核对该偏离是否仍符合你的目标；如不符合，由用户决定是否分步再平衡。",
                })
    else:
        items.append({
            "id": "target-allocation-incomplete",
            "priority": "info",
            "title": "目标仓位尚未完整",
            "reason": "只有完整且合计约为 100% 的目标仓位，才能可靠比较配置偏差。",
            "evidence": [f"已填写 {sum(item.target_weight_pct is not None for item in positions)}/{len(positions)} 只基金"],
            "action": "先在当前用户基金持仓中补全并复核目标仓位，再比较配置偏差。",
        })
    dimensions = (
        ("fund-concentration", concentration, "基金集中度需要复核", "核对单只基金和前两只基金的占比是否仍符合你的风险承受能力与目标仓位。"),
        ("disclosed-overlap", overlap, "披露重合度需要复核", "不要只按基金数量判断分散程度；结合共同持仓、共同产业和披露日期复核。"),
        ("industry-concentration", industry, "披露行业暴露需要复核", "检查同类行业风险是否重复；是否调整由用户结合期限和目标自行决定。"),
        ("nav-risk", nav, "净值波动与回撤需要复核", "核对资金使用期限和可承受回撤，不把短期净值波动当作收益预测。"),
        ("cycle-pressure", cycle, "行业周期压力证据需要复核", "把偏热、放缓或收缩行业作为压力情景观察，不把周期阶段当作择时指令。"),
    )
    for item_id, dimension, title, action in dimensions:
        if dimension.get("status") in {"watch", "high"}:
            items.append({
                "id": item_id,
                "priority": dimension["status"],
                "title": title,
                "reason": "该维度超过当前风险偏好的固定关注阈值。",
                "evidence": [f"状态 {dimension['status']}"],
                "action": action,
            })
    if missing:
        items.append({
            "id": "data-quality",
            "priority": "watch",
            "title": "部分证据缺失",
            "reason": "公开净值或披露数据不完整时，组合风险只能作为保守的局部观察。",
            "evidence": missing[:8],
            "action": "先核对缺失项和数据日期，不用缺失结果替代完整组合判断。",
        })
    if not items:
        items.append({
            "id": "no-threshold-triggered",
            "priority": "info",
            "title": "当前固定阈值未触发额外关注",
            "reason": "本次可用证据未超过当前风险偏好的关注阈值。",
            "evidence": ["仍需核对披露日期、未知敞口和目标仓位"],
            "action": "保持定期复核；本结果不替代用户自己的配置决定。",
        })
    return items


class AkshareFundPortfolioAdviceService:
    def __init__(
        self,
        *,
        config: AkshareFundPortfolioAdviceConfig | None = None,
        akshare_module: Any | None = None,
        now: datetime | None = None,
    ) -> None:
        self.config = config or AkshareFundPortfolioAdviceConfig()
        self.akshare_module = akshare_module
        self.now = now or datetime.now(timezone.utc)

    def _akshare(self) -> Any:
        if self.akshare_module is None:
            import akshare as ak

            self.akshare_module = ak
        return self.akshare_module

    def fetch(self, positions: tuple[PortfolioPosition, ...], risk_profile: str) -> dict[str, Any]:
        codes = tuple(item.code for item in positions)
        fetched_at = _utc_now_iso()
        if not (self.config.network_enabled and self.config.human_approved):
            return {
                "requested_codes": list(codes),
                "data_status": "missing",
                "fetched_at": fetched_at,
                "risk_profile": risk_profile,
                "positions": [item.to_dict() for item in positions],
                "missing_evidence": ["manual-local-approval"],
                "warnings": ["必须由用户在本机逐次确认后读取公开证据。"],
            }
        akshare_module = self._akshare()
        years = self.config.years or (self.now.year, self.now.year - 1)
        comparison = AkshareFundComparisonService(
            config=AkshareFundComparisonConfig(network_enabled=True, human_approved=True, years=years),
            akshare_module=akshare_module,
            now=self.now,
        ).fetch(codes)
        cycle = AkshareFundIndustryCycleService(
            config=AkshareFundIndustryCycleConfig(network_enabled=True, human_approved=True, years=years),
            akshare_module=akshare_module,
            now=self.now,
        ).fetch(codes, comparison_result=comparison)
        nav_items = tuple(_nav_history(akshare_module, code) for code in codes)
        weights = {item.code: item.weight_pct for item in positions}
        concentration = _concentration(positions, risk_profile)
        overlap = _overlap(comparison)
        industry = _industry_exposure(comparison, weights, risk_profile)
        nav = _nav_summary(nav_items, weights, risk_profile)
        cycle_summary = _cycle_exposure(cycle, weights)
        missing: list[str] = []
        missing.extend(f"fund:{code}" for code in comparison.missing_funds)
        for item in nav_items:
            missing.extend(f"{item.code}:{reason}" for reason in item.missing_evidence)
        missing.extend(cycle.missing_evidence)
        if _decimal(industry["disclosed_portfolio_coverage_pct"]) is None or Decimal(industry["disclosed_portfolio_coverage_pct"] or "0") < Decimal("50"):
            missing.append("disclosed-industry-coverage-below-50pct")
        missing = list(dict.fromkeys(missing))
        guidance = _guidance(positions, concentration, overlap, industry, nav, cycle_summary, missing)
        status = "missing" if comparison.data_status == "missing" else "partial" if (
            missing or comparison.data_status == "partial" or cycle.data_status != "available"
        ) else "available"
        return {
            "requested_codes": list(codes),
            "data_status": status,
            "fetched_at": fetched_at,
            "risk_profile": risk_profile,
            "positions": [item.to_dict() for item in positions],
            "input_privacy": {
                "amount_shared": False,
                "cost_basis_shared": False,
                "user_identity_shared": False,
                "account_read": False,
            },
            "concentration": concentration,
            "disclosed_overlap": overlap,
            "industry_exposure": industry,
            "nav_risk": nav,
            "cycle_exposure": cycle_summary,
            "allocation_guidance": guidance,
            "missing_evidence": missing,
            "warnings": [
                "配置建议由固定规则生成，仅用于当前用户人工复核，不构成买卖指令或收益承诺。",
                "公开持仓和行业配置有披露滞后，未知部分保持未知。",
                "结果只保存在当前页面内存，切换用户或刷新后清空。",
            ],
            "method": "deterministic-current-user-fund-risk-and-allocation-review",
        }


def validate_portfolio_advice_result(result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("data_status") not in {"available", "partial", "missing"}:
        errors.append("unsupported result status")
    if result.get("risk_profile") not in RISK_PROFILES:
        errors.append("unsupported risk profile")
    positions = result.get("positions")
    if not isinstance(positions, list) or not 1 <= len(positions) <= MAX_FUNDS:
        errors.append("positions must be within the fund limit")
    else:
        codes = [item.get("code") for item in positions if isinstance(item, Mapping)]
        if len(codes) != len(positions) or len(codes) != len(set(codes)):
            errors.append("result positions must be unique")
        total = sum((_decimal(item.get("weight_pct")) or Decimal("0") for item in positions), Decimal("0"))
        if abs(total - Decimal("100")) > Decimal("0.05"):
            errors.append("result weights must total 100")
    for key in ("concentration", "disclosed_overlap", "industry_exposure", "nav_risk", "cycle_exposure"):
        dimension = result.get(key)
        if not isinstance(dimension, Mapping) or dimension.get("status") not in DIMENSION_STATES:
            errors.append(f"invalid {key} dimension")
    guidance = result.get("allocation_guidance")
    if not isinstance(guidance, list) or not guidance:
        errors.append("allocation guidance is required")
    else:
        for item in guidance:
            action = item.get("action", "") if isinstance(item, Mapping) else ""
            if any(phrase in action for phrase in FORCED_ACTION_PHRASES):
                errors.append("guidance contains a forced trading instruction")
    privacy = result.get("input_privacy")
    if privacy != {
        "amount_shared": False,
        "cost_basis_shared": False,
        "user_identity_shared": False,
        "account_read": False,
    }:
        errors.append("input privacy declaration is invalid")
    return errors


def validate_portfolio_advice_request(
    payload: Mapping[str, Any],
) -> tuple[tuple[PortfolioPosition, ...], str]:
    if not isinstance(payload, Mapping) or set(payload) != PORTFOLIO_ADVICE_REQUEST_FIELDS:
        raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-request")
    raw_positions = payload.get("positions")
    if not isinstance(raw_positions, list) or not 1 <= len(raw_positions) <= MAX_FUNDS:
        raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-positions")
    positions: list[PortfolioPosition] = []
    for raw in raw_positions:
        if not isinstance(raw, Mapping) or set(raw) != POSITION_FIELDS:
            raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-positions")
        code = raw.get("code")
        weight = _decimal(raw.get("weightPct"))
        target = _decimal(raw.get("targetWeightPct")) if raw.get("targetWeightPct") is not None else None
        if (
            not isinstance(code, str)
            or not FUND_CODE_RE.fullmatch(code)
            or weight is None
            or weight <= 0
            or weight > 100
            or (target is not None and (target < 0 or target > 100))
        ):
            raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-positions")
        positions.append(PortfolioPosition(code, weight, target))
    if len({item.code for item in positions}) != len(positions):
        raise FundPortfolioAdviceError("fund-portfolio-advice.duplicate-codes")
    if abs(sum((item.weight_pct for item in positions), Decimal("0")) - Decimal("100")) > Decimal("0.05"):
        raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-weight-total")
    sections = payload.get("sections")
    if not isinstance(sections, list) or set(sections) != PORTFOLIO_ADVICE_SECTIONS or len(sections) != len(PORTFOLIO_ADVICE_SECTIONS):
        raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-sections")
    risk_profile = payload.get("riskProfile")
    if risk_profile not in RISK_PROFILES:
        raise FundPortfolioAdviceError("fund-portfolio-advice.invalid-risk-profile")
    if not (
        payload.get("mode") == "fund-portfolio-advice-readonly"
        and payload.get("provider") == PROVIDER_NAME
        and payload.get("humanApproved") is True
        and payload.get("readOnly") is True
    ):
        raise FundPortfolioAdviceError("fund-portfolio-advice.approval-required")
    if any(
        payload.get(field) is not False
        for field in ("allowAccountRead", "allowTrading", "allowNotificationSend", "allowAiCall", "allowPersistence")
    ):
        raise FundPortfolioAdviceError("fund-portfolio-advice.forbidden-capability")
    return tuple(positions), str(risk_profile)


def run_akshare_fund_portfolio_advice(
    payload: Mapping[str, Any],
    *,
    akshare_module: Any | None = None,
) -> dict[str, Any]:
    try:
        positions, risk_profile = validate_portfolio_advice_request(payload)
        result = AkshareFundPortfolioAdviceService(
            config=AkshareFundPortfolioAdviceConfig(network_enabled=True, human_approved=True),
            akshare_module=akshare_module,
        ).fetch(positions, risk_profile)
        if validate_portfolio_advice_result(result):
            return {
                "status": "unavailable",
                "errorCode": "fund-portfolio-advice.invalid-provider-result",
                "providerLabel": PROVIDER_LABEL,
                "readOnly": True,
            }
        return {
            "status": "completed-readonly" if result["data_status"] in {"available", "partial"} else "unavailable",
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
            "advice": result,
        }
    except FundPortfolioAdviceError as exc:
        return {
            "status": "blocked",
            "errorCode": exc.code,
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
        }


async def run_akshare_fund_portfolio_advice_with_timeout(
    payload: Mapping[str, Any],
    *,
    akshare_module: Any | None = None,
    timeout_seconds: float = PORTFOLIO_ADVICE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(run_akshare_fund_portfolio_advice, payload, akshare_module=akshare_module),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "errorCode": "fund-portfolio-advice.provider-timeout",
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
        }
