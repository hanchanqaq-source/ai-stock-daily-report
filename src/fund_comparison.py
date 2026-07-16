"""Auditable AKShare fund comparison and disclosed industry exposure.

Build D2 consumes only public fund facts after explicit localhost approval.  It
does not infer industries from security names and does not produce cycle,
productivity, allocation, or trading advice.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from itertools import combinations
from typing import Any, Mapping

from src.fund_data_akshare_provider import (
    FUND_CODE_RE,
    PROVIDER_LABEL,
    PROVIDER_NAME,
    AkshareFundDataProvider,
    AkshareFundDataProviderConfig,
    _date_text,
    _decimal_text,
    _field,
    _records,
    _text,
)
from src.fund_data_contract import (
    FundDataBundle,
    FundDataSource,
    validate_fund_data_bundle,
    validate_fund_data_source,
)
from src.fund_data_provider import FundDataRequest, fetch_fund_data


COMPARISON_TIMEOUT_SECONDS = 45
MAX_FUNDS = 4
COMPARISON_SECTIONS = frozenset({"profile", "nav", "holdings", "industry-exposure"})
COMPARISON_REQUEST_FIELDS = frozenset(
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


class FundComparisonError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _decimal(value: str) -> Decimal | None:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _decimal_sum(values: list[str]) -> str:
    total = sum((Decimal(value) for value in values), Decimal("0"))
    return _decimal_text(total) or "0"


def _source(
    *,
    fetched_at: str,
    status: str,
    effective_at: str | None = None,
    report_period: str | None = None,
    missing: Mapping[str, str] | None = None,
    confidence: str = "0.90",
) -> FundDataSource:
    reasons = dict(missing or {})
    return FundDataSource(
        provider=PROVIDER_NAME,
        source_kind="provider",
        source_status=status,
        fetched_at=fetched_at,
        effective_at=effective_at,
        report_period=report_period,
        confidence=confidence,
        missing_fields=tuple(reasons),
        missing_reasons=reasons,
    )


@dataclass(frozen=True)
class FundIndustryExposureItem:
    industry_name: str
    weight_pct: str
    market_value_cny_10k: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "industry_name": self.industry_name,
            "weight_pct": self.weight_pct,
            "market_value_cny_10k": self.market_value_cny_10k,
        }


@dataclass(frozen=True)
class FundIndustryExposure:
    code: str
    report_date: str
    industries: tuple[FundIndustryExposureItem, ...]
    disclosed_total_pct: str
    top3_concentration_pct: str
    source: FundDataSource

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "report_date": self.report_date,
            "industries": [item.to_dict() for item in self.industries],
            "disclosed_total_pct": self.disclosed_total_pct,
            "top3_concentration_pct": self.top3_concentration_pct,
            "source": self.source.to_dict(),
        }


@dataclass(frozen=True)
class FundComparisonItem:
    code: str
    data_status: str
    bundle: FundDataBundle
    industry_exposure: FundIndustryExposure | None
    top10_holdings_concentration_pct: str | None
    missing_sections: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "data_status": self.data_status,
            "bundle": self.bundle.to_dict(),
            "industry_exposure": self.industry_exposure.to_dict() if self.industry_exposure else None,
            "top10_holdings_concentration_pct": self.top10_holdings_concentration_pct,
            "missing_sections": list(self.missing_sections),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class FundPairOverlap:
    left_code: str
    right_code: str
    common_holdings: tuple[Mapping[str, str], ...]
    disclosed_holdings_overlap_pct: str
    common_industries: tuple[Mapping[str, str], ...]
    disclosed_industry_overlap_pct: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_code": self.left_code,
            "right_code": self.right_code,
            "common_holdings": [dict(item) for item in self.common_holdings],
            "disclosed_holdings_overlap_pct": self.disclosed_holdings_overlap_pct,
            "common_industries": [dict(item) for item in self.common_industries],
            "disclosed_industry_overlap_pct": self.disclosed_industry_overlap_pct,
            "holdings_scope": "latest-disclosed-top-holdings",
            "industry_scope": "provider-disclosed-industry-allocation",
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class FundComparisonResult:
    requested_codes: tuple[str, ...]
    data_status: str
    source: FundDataSource
    funds: tuple[FundComparisonItem, ...]
    pair_overlaps: tuple[FundPairOverlap, ...]
    missing_funds: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_codes": list(self.requested_codes),
            "data_status": self.data_status,
            "source": self.source.to_dict(),
            "funds": [item.to_dict() for item in self.funds],
            "pair_overlaps": [item.to_dict() for item in self.pair_overlaps],
            "missing_funds": list(self.missing_funds),
            "reason": self.reason,
        }


def validate_industry_exposure(exposure: FundIndustryExposure) -> list[str]:
    errors = validate_fund_data_source(exposure.source)
    if not FUND_CODE_RE.fullmatch(exposure.code):
        errors.append("industry exposure code must be six digits")
    if not _date_text(exposure.report_date) or exposure.source.report_period != exposure.report_date:
        errors.append("industry exposure report date must match source report_period")
    names = [item.industry_name for item in exposure.industries]
    if not names or len(names) != len(set(names)):
        errors.append("industry exposure names must be non-empty and unique")
    weights: list[Decimal] = []
    for item in exposure.industries:
        weight = _decimal(item.weight_pct)
        if not item.industry_name.strip() or weight is None or weight < 0 or weight > 100:
            errors.append("industry exposure item is invalid")
            continue
        weights.append(weight)
        if item.market_value_cny_10k is not None:
            market_value = _decimal(item.market_value_cny_10k)
            if market_value is None or market_value < 0:
                errors.append("industry market value must be non-negative")
    total = _decimal(exposure.disclosed_total_pct)
    top3 = _decimal(exposure.top3_concentration_pct)
    if total is None or total != sum(weights, Decimal("0")) or total > Decimal("100.5"):
        errors.append("industry disclosed total must match valid weights and not exceed 100.5")
    if top3 is None or top3 != sum(sorted(weights, reverse=True)[:3], Decimal("0")):
        errors.append("industry top3 concentration must match the three largest weights")
    return errors


def _industry_exposure(
    akshare_module: Any,
    *,
    code: str,
    years: tuple[int, ...],
    fetched_at: str,
) -> FundIndustryExposure | None:
    rows: list[dict[str, Any]] = []
    for year in years:
        try:
            rows = _records(
                akshare_module.fund_portfolio_industry_allocation_em(symbol=code, date=str(year))
            )
        except Exception:
            rows = []
        if rows:
            break
    dated = [(_date_text(_field(row, "截止时间", "报告期", "日期")), row) for row in rows]
    dated = [(report_date, row) for report_date, row in dated if report_date]
    if not dated:
        return None
    report_date = max(report_date for report_date, _ in dated)
    latest = [row for day, row in dated if day == report_date]
    items: list[FundIndustryExposureItem] = []
    seen: set[str] = set()
    for row in latest:
        name = _text(_field(row, "行业类别", "行业名称"), limit=80)
        weight = _decimal_text(_field(row, "占净值比例", "占净值比例(%)"))
        market_value = _decimal_text(_field(row, "市值", "市值(万元)"))
        parsed_weight = _decimal(weight or "")
        if not name or name in seen or parsed_weight is None or parsed_weight < 0 or parsed_weight > 100:
            continue
        if market_value is not None and (_decimal(market_value) is None or Decimal(market_value) < 0):
            market_value = None
        seen.add(name)
        items.append(FundIndustryExposureItem(name, weight or "0", market_value))
    items.sort(key=lambda item: Decimal(item.weight_pct), reverse=True)
    if not items:
        return None
    total = _decimal_sum([item.weight_pct for item in items])
    top3 = _decimal_sum([item.weight_pct for item in items[:3]])
    exposure = FundIndustryExposure(
        code=code,
        report_date=report_date,
        industries=tuple(items),
        disclosed_total_pct=total,
        top3_concentration_pct=top3,
        source=_source(
            fetched_at=fetched_at,
            status="available",
            effective_at=report_date,
            report_period=report_date,
            confidence="0.95",
        ),
    )
    return exposure if not validate_industry_exposure(exposure) else None


def _comparison_item(
    *,
    code: str,
    bundle: FundDataBundle,
    exposure: FundIndustryExposure | None,
) -> FundComparisonItem:
    missing = list(bundle.missing_sections)
    if exposure is None:
        missing.append("industry-exposure")
    warnings: list[str] = []
    if bundle.holdings is not None:
        warnings.append("持仓重合仅按最新披露前十大持仓计算，不代表完整组合。")
    if exposure is None:
        warnings.append("AKShare 未返回可验证的行业配置，未知行业保持未知。")
    top10 = bundle.holdings.disclosed_total_pct if bundle.holdings else None
    has_data = any((bundle.profile, bundle.nav, bundle.holdings, exposure))
    status = "missing" if not has_data else "partial" if missing or bundle.data_status != "available" else "available"
    return FundComparisonItem(
        code=code,
        data_status=status,
        bundle=bundle,
        industry_exposure=exposure,
        top10_holdings_concentration_pct=top10,
        missing_sections=tuple(dict.fromkeys(missing)),
        warnings=tuple(warnings),
    )


def _pair_overlap(left: FundComparisonItem, right: FundComparisonItem) -> FundPairOverlap:
    left_positions = {
        item.security_code: item for item in (left.bundle.holdings.positions if left.bundle.holdings else ())
    }
    right_positions = {
        item.security_code: item for item in (right.bundle.holdings.positions if right.bundle.holdings else ())
    }
    common_holdings: list[Mapping[str, str]] = []
    for code in sorted(set(left_positions) & set(right_positions)):
        left_item, right_item = left_positions[code], right_positions[code]
        common_holdings.append(
            {
                "security_code": code,
                "security_name": left_item.security_name,
                "left_weight_pct": left_item.weight_pct,
                "right_weight_pct": right_item.weight_pct,
                "overlap_weight_pct": _decimal_text(
                    min(Decimal(left_item.weight_pct), Decimal(right_item.weight_pct))
                ) or "0",
            }
        )
    left_industries = {
        item.industry_name: item for item in (left.industry_exposure.industries if left.industry_exposure else ())
    }
    right_industries = {
        item.industry_name: item for item in (right.industry_exposure.industries if right.industry_exposure else ())
    }
    common_industries: list[Mapping[str, str]] = []
    for name in sorted(set(left_industries) & set(right_industries)):
        left_item, right_item = left_industries[name], right_industries[name]
        common_industries.append(
            {
                "industry_name": name,
                "left_weight_pct": left_item.weight_pct,
                "right_weight_pct": right_item.weight_pct,
                "overlap_weight_pct": _decimal_text(
                    min(Decimal(left_item.weight_pct), Decimal(right_item.weight_pct))
                ) or "0",
            }
        )
    warnings = ["重合比例是披露数据下限，不等于完整持仓重合度。"]
    if left.bundle.holdings and right.bundle.holdings and left.bundle.holdings.report_period != right.bundle.holdings.report_period:
        warnings.append("两只基金的持仓报告期不同，请勿直接当作同日组合比较。")
    if left.industry_exposure and right.industry_exposure and left.industry_exposure.report_date != right.industry_exposure.report_date:
        warnings.append("两只基金的行业配置截止日期不同。")
    if left.bundle.nav and right.bundle.nav and left.bundle.nav.nav_date != right.bundle.nav.nav_date:
        warnings.append("两只基金的净值日期不同。")
    return FundPairOverlap(
        left_code=left.code,
        right_code=right.code,
        common_holdings=tuple(common_holdings),
        disclosed_holdings_overlap_pct=_decimal_sum(
            [item["overlap_weight_pct"] for item in common_holdings]
        ),
        common_industries=tuple(common_industries),
        disclosed_industry_overlap_pct=_decimal_sum(
            [item["overlap_weight_pct"] for item in common_industries]
        ),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class AkshareFundComparisonConfig:
    network_enabled: bool = False
    human_approved: bool = False
    years: tuple[int, ...] = ()


class AkshareFundComparisonService:
    def __init__(
        self,
        *,
        config: AkshareFundComparisonConfig | None = None,
        akshare_module: Any | None = None,
        now: datetime | None = None,
    ) -> None:
        self.config = config or AkshareFundComparisonConfig()
        self.akshare_module = akshare_module
        self.now = now or datetime.now(timezone.utc)

    def _akshare(self) -> Any:
        if self.akshare_module is None:
            import akshare as ak

            self.akshare_module = ak
        return self.akshare_module

    def fetch(self, codes: tuple[str, ...]) -> FundComparisonResult:
        fetched_at = _utc_now_iso()
        if not (self.config.network_enabled and self.config.human_approved):
            return FundComparisonResult(
                requested_codes=codes,
                data_status="missing",
                source=_source(
                    fetched_at=fetched_at,
                    status="missing",
                    missing={code: "必须由用户在本机逐次确认后读取。" for code in codes},
                    confidence="0.00",
                ),
                funds=(),
                pair_overlaps=(),
                missing_funds=codes,
                reason="AKShare 基金对比必须由用户在本机逐次确认后读取。",
            )
        akshare_module = self._akshare()
        years = self.config.years or (self.now.year, self.now.year - 1)
        items: list[FundComparisonItem] = []
        for code in codes:
            provider = AkshareFundDataProvider(
                config=AkshareFundDataProviderConfig(
                    network_enabled=True,
                    human_approved=True,
                    holdings_years=years,
                ),
                akshare_module=akshare_module,
                now=self.now,
            )
            bundle = fetch_fund_data(FundDataRequest(code), provider)
            try:
                exposure = _industry_exposure(
                    akshare_module,
                    code=code,
                    years=years,
                    fetched_at=fetched_at,
                )
            except Exception:
                exposure = None
            items.append(_comparison_item(code=code, bundle=bundle, exposure=exposure))
        missing_funds = tuple(item.code for item in items if item.data_status == "missing")
        overlaps = tuple(_pair_overlap(left, right) for left, right in combinations(items, 2))
        missing = {code: "AKShare 未返回可验证的基金资料或披露数据。" for code in missing_funds}
        if len(missing_funds) == len(codes):
            status = "missing"
            reason = "AKShare 暂未返回这些基金的可验证公开数据。"
        elif missing_funds or any(item.data_status != "available" for item in items):
            status = "partial"
            reason = "部分基金、字段或披露区块缺失，请按各自日期和报告期使用。"
        else:
            status = "available"
            reason = ""
        return FundComparisonResult(
            requested_codes=codes,
            data_status=status,
            source=_source(
                fetched_at=fetched_at,
                status="missing" if status == "missing" else "partial" if status == "partial" else "available",
                missing=missing,
                confidence="0.85",
            ),
            funds=tuple(items),
            pair_overlaps=overlaps,
            missing_funds=missing_funds,
            reason=reason,
        )


def validate_comparison_result(result: FundComparisonResult) -> list[str]:
    errors = validate_fund_data_source(result.source)
    requested = set(result.requested_codes)
    fund_codes = [item.code for item in result.funds]
    if not 1 <= len(result.requested_codes) <= MAX_FUNDS or len(requested) != len(result.requested_codes):
        errors.append("requested fund codes must be unique and within the limit")
    if any(not FUND_CODE_RE.fullmatch(code) for code in result.requested_codes):
        errors.append("requested fund codes must be six digits")
    if set(fund_codes) - requested or len(fund_codes) != len(set(fund_codes)):
        errors.append("comparison funds must be unique requested funds")
    if set(result.missing_funds) - requested or len(result.missing_funds) != len(set(result.missing_funds)):
        errors.append("missing funds must be unique requested funds")
    if result.data_status not in {"available", "partial", "missing"}:
        errors.append("unsupported comparison status")
    if result.data_status == "missing" and not result.reason.strip():
        errors.append("missing comparison requires a reason")
    for item in result.funds:
        if item.bundle.code != item.code:
            errors.append("comparison item bundle code must match")
        errors.extend(validate_fund_data_bundle(item.bundle))
        if item.industry_exposure:
            if item.industry_exposure.code != item.code:
                errors.append("industry exposure code must match comparison item")
            errors.extend(validate_industry_exposure(item.industry_exposure))
    valid_pairs = {tuple(sorted(pair)) for pair in combinations(fund_codes, 2)}
    overlap_pairs = {(item.left_code, item.right_code) for item in result.pair_overlaps}
    if len(overlap_pairs) != len(result.pair_overlaps) or {
        tuple(sorted(pair)) for pair in overlap_pairs
    } - valid_pairs:
        errors.append("pair overlaps must be unique comparison fund pairs")
    return errors


def validate_comparison_request(payload: Mapping[str, Any]) -> tuple[str, ...]:
    if not isinstance(payload, Mapping) or set(payload) != COMPARISON_REQUEST_FIELDS:
        raise FundComparisonError("fund-comparison.invalid-request")
    codes = payload.get("codes")
    sections = payload.get("sections")
    if not isinstance(codes, list) or not 1 <= len(codes) <= MAX_FUNDS:
        raise FundComparisonError("fund-comparison.invalid-codes")
    if any(not isinstance(code, str) or not FUND_CODE_RE.fullmatch(code) for code in codes):
        raise FundComparisonError("fund-comparison.invalid-codes")
    if len(codes) != len(set(codes)):
        raise FundComparisonError("fund-comparison.duplicate-codes")
    if not isinstance(sections, list) or set(sections) != COMPARISON_SECTIONS or len(sections) != len(COMPARISON_SECTIONS):
        raise FundComparisonError("fund-comparison.invalid-sections")
    if not (
        payload.get("mode") == "fund-comparison-readonly"
        and payload.get("provider") == PROVIDER_NAME
        and payload.get("humanApproved") is True
        and payload.get("readOnly") is True
    ):
        raise FundComparisonError("fund-comparison.approval-required")
    if any(
        payload.get(field) is not False
        for field in (
            "allowAccountRead",
            "allowTrading",
            "allowNotificationSend",
            "allowAiCall",
            "allowPersistence",
        )
    ):
        raise FundComparisonError("fund-comparison.forbidden-capability")
    return tuple(codes)


def run_akshare_fund_comparison(
    payload: Mapping[str, Any],
    *,
    akshare_module: Any | None = None,
) -> dict[str, Any]:
    try:
        codes = validate_comparison_request(payload)
        result = AkshareFundComparisonService(
            config=AkshareFundComparisonConfig(network_enabled=True, human_approved=True),
            akshare_module=akshare_module,
        ).fetch(codes)
        if validate_comparison_result(result):
            return {
                "status": "unavailable",
                "errorCode": "fund-comparison.invalid-provider-result",
                "providerLabel": PROVIDER_LABEL,
                "readOnly": True,
            }
        return {
            "status": "completed-readonly" if result.data_status in {"available", "partial"} else "unavailable",
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
            "comparison": result.to_dict(),
        }
    except FundComparisonError as exc:
        return {
            "status": "blocked",
            "errorCode": exc.code,
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
        }


async def run_akshare_fund_comparison_with_timeout(
    payload: Mapping[str, Any],
    *,
    akshare_module: Any | None = None,
    timeout_seconds: float = COMPARISON_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(run_akshare_fund_comparison, payload, akshare_module=akshare_module),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "errorCode": "fund-comparison.provider-timeout",
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
        }
