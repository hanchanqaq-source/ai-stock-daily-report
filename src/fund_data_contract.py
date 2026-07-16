"""Canonical fund data contracts for the stock/fund dual-center workspace.

The contracts in this module are provider-neutral and contain no network,
account, persistence, or trading behavior.  Every factual section carries its
own provenance so stale and missing data cannot be presented as current data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping, Sequence


FUND_SECTIONS = frozenset({"profile", "nav", "holdings"})
SOURCE_KINDS = frozenset({"provider", "manual", "test_fixture", "unavailable"})
SOURCE_STATUSES = frozenset({"available", "partial", "missing", "stale", "provider_error", "test_fixture", "not_connected"})
BUNDLE_STATUSES = frozenset({"available", "partial", "missing", "stale", "provider_error"})
INDUSTRY_MAPPING_STATUSES = frozenset({"mapped", "unknown", "ambiguous", "unmapped"})
_REPORT_PERIOD = re.compile(r"^\d{4}-(?:Q[1-4]|\d{2}-\d{2})$")


def _mapping(value: Mapping[str, str]) -> dict[str, str]:
    return {str(key): str(item) for key, item in value.items()}


def _iso_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo is not None


def _iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def _valid_report_period(value: str) -> bool:
    return bool(_REPORT_PERIOD.fullmatch(value)) and ("Q" in value or _iso_date(value))


def _decimal(value: str | None) -> Decimal | None:
    if value in {None, ""}:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _missing_declared(source: "FundDataSource", field_name: str, value: Any) -> list[str]:
    missing = value is None or value == ""
    declared = field_name in source.missing_fields
    errors: list[str] = []
    if missing and not declared:
        errors.append(f"{field_name} is missing but not declared")
    if not missing and declared:
        errors.append(f"{field_name} is present but declared missing")
    return errors


@dataclass(frozen=True)
class FundDataSource:
    provider: str
    source_kind: str
    source_status: str
    fetched_at: str
    effective_at: str | None = None
    report_period: str | None = None
    stale: bool = False
    stale_reason: str = ""
    confidence: str | None = None
    missing_fields: tuple[str, ...] = ()
    missing_reasons: Mapping[str, str] = field(default_factory=dict)
    test_fixture: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source_kind": self.source_kind,
            "source_status": self.source_status,
            "fetched_at": self.fetched_at,
            "effective_at": self.effective_at,
            "report_period": self.report_period,
            "stale": self.stale,
            "stale_reason": self.stale_reason,
            "confidence": self.confidence,
            "missing_fields": list(self.missing_fields),
            "missing_reasons": _mapping(self.missing_reasons),
            "test_fixture": self.test_fixture,
        }


def validate_fund_data_source(source: FundDataSource) -> list[str]:
    errors: list[str] = []
    if not source.provider.strip():
        errors.append("provider is required")
    if source.source_kind not in SOURCE_KINDS:
        errors.append("unsupported source_kind")
    if source.source_status not in SOURCE_STATUSES:
        errors.append("unsupported source_status")
    if not _iso_datetime(source.fetched_at):
        errors.append("fetched_at must be a timezone-aware ISO datetime")
    if source.effective_at and not _iso_date(source.effective_at):
        errors.append("effective_at must be an ISO date")
    if source.report_period and not _valid_report_period(source.report_period):
        errors.append("report_period must be YYYY-QN or an ISO date")
    if source.stale and not source.stale_reason.strip():
        errors.append("stale data requires stale_reason")
    if not source.stale and source.stale_reason.strip():
        errors.append("fresh data cannot include stale_reason")
    if source.stale and source.source_kind != "test_fixture" and source.source_status != "stale":
        errors.append("stale source requires source_status=stale")
    if source.source_status == "stale" and not source.stale:
        errors.append("source_status=stale requires stale=true")
    confidence = _decimal(source.confidence)
    if source.confidence is not None and (confidence is None or confidence < 0 or confidence > 1):
        errors.append("confidence must be between 0 and 1")
    if len(source.missing_fields) != len(set(source.missing_fields)):
        errors.append("missing_fields must be unique")
    missing_reasons = _mapping(source.missing_reasons)
    for field_name in source.missing_fields:
        if not missing_reasons.get(field_name, "").strip():
            errors.append(f"missing reason required for {field_name}")
    if set(missing_reasons) - set(source.missing_fields):
        errors.append("missing_reasons contains undeclared fields")
    if source.source_kind == "test_fixture":
        if source.source_status != "test_fixture" or source.test_fixture is not True:
            errors.append("test fixture source requires explicit fixture markers")
    elif source.test_fixture:
        errors.append("test_fixture marker requires source_kind=test_fixture")
    if source.source_status == "available" and source.missing_fields:
        errors.append("available source cannot declare missing fields")
    if source.source_status in {"missing", "not_connected"} and not source.missing_fields:
        errors.append("missing source must declare missing fields")
    return errors


@dataclass(frozen=True)
class FundProfile:
    code: str
    name: str | None
    fund_type: str | None
    manager: str | None
    scale: str | None
    scale_currency: str | None
    inception_date: str | None
    source: FundDataSource

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "fund_type": self.fund_type,
            "manager": self.manager,
            "scale": self.scale,
            "scale_currency": self.scale_currency,
            "inception_date": self.inception_date,
            "source": self.source.to_dict(),
        }


def validate_fund_profile(profile: FundProfile) -> list[str]:
    errors = validate_fund_data_source(profile.source)
    if not profile.code.strip():
        errors.append("fund code is required")
    for field_name in ("name", "fund_type", "manager", "scale", "scale_currency", "inception_date"):
        errors.extend(_missing_declared(profile.source, field_name, getattr(profile, field_name)))
    if profile.scale is not None and (_decimal(profile.scale) is None or Decimal(profile.scale) < 0):
        errors.append("scale must be a non-negative decimal string")
    if profile.scale_currency and not re.fullmatch(r"[A-Z0-9_]{3,16}", profile.scale_currency):
        errors.append("scale_currency must be an explicit uppercase unit")
    if profile.inception_date and not _iso_date(profile.inception_date):
        errors.append("inception_date must be an ISO date")
    return errors


@dataclass(frozen=True)
class FundNavSnapshot:
    code: str
    unit_nav: str | None
    accumulated_nav: str | None
    daily_change_pct: str | None
    nav_date: str | None
    source: FundDataSource
    estimated_nav: str | None = None
    estimated_change_pct: str | None = None
    estimated_change_amount: str | None = None
    estimate_time: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "unit_nav": self.unit_nav,
            "accumulated_nav": self.accumulated_nav,
            "daily_change_pct": self.daily_change_pct,
            "nav_date": self.nav_date,
            "estimated_nav": self.estimated_nav,
            "estimated_change_pct": self.estimated_change_pct,
            "estimated_change_amount": self.estimated_change_amount,
            "estimate_time": self.estimate_time,
            "source": self.source.to_dict(),
        }


def validate_fund_nav_snapshot(snapshot: FundNavSnapshot) -> list[str]:
    errors = validate_fund_data_source(snapshot.source)
    if not snapshot.code.strip():
        errors.append("fund code is required")
    value_fields = (
        "unit_nav",
        "accumulated_nav",
        "daily_change_pct",
        "estimated_nav",
        "estimated_change_pct",
        "estimated_change_amount",
    )
    for field_name in value_fields:
        value = getattr(snapshot, field_name)
        errors.extend(_missing_declared(snapshot.source, field_name, value))
        if value is not None and _decimal(value) is None:
            errors.append(f"{field_name} must be a decimal string")
    for field_name in ("nav_date", "estimate_time"):
        errors.extend(_missing_declared(snapshot.source, field_name, getattr(snapshot, field_name)))
    if snapshot.nav_date and not _iso_date(snapshot.nav_date):
        errors.append("nav_date must be an ISO date")
    if snapshot.estimate_time and not _iso_datetime(snapshot.estimate_time):
        errors.append("estimate_time must be a timezone-aware ISO datetime")
    if snapshot.source.effective_at and snapshot.nav_date and snapshot.source.effective_at != snapshot.nav_date:
        errors.append("source effective_at must match nav_date")
    return errors


@dataclass(frozen=True)
class FundIndustryMapping:
    status: str
    industry_code: str | None
    industry_name: str | None
    source: FundDataSource

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "source": self.source.to_dict(),
        }


def validate_fund_industry_mapping(mapping: FundIndustryMapping) -> list[str]:
    errors = validate_fund_data_source(mapping.source)
    if mapping.status not in INDUSTRY_MAPPING_STATUSES:
        errors.append("unsupported industry mapping status")
    if mapping.status == "mapped" and not (mapping.industry_code and mapping.industry_name):
        errors.append("mapped industry requires code and name")
    if mapping.status in {"unknown", "unmapped", "ambiguous"} and (mapping.industry_code or mapping.industry_name):
        errors.append("unresolved industry must remain empty")
    errors.extend(_missing_declared(mapping.source, "industry_code", mapping.industry_code))
    errors.extend(_missing_declared(mapping.source, "industry_name", mapping.industry_name))
    return errors


@dataclass(frozen=True)
class FundHoldingPosition:
    security_code: str
    security_name: str
    weight_pct: str
    industry: FundIndustryMapping

    def to_dict(self) -> dict[str, Any]:
        return {
            "security_code": self.security_code,
            "security_name": self.security_name,
            "weight_pct": self.weight_pct,
            "industry": self.industry.to_dict(),
        }


def validate_fund_holding_position(position: FundHoldingPosition) -> list[str]:
    errors = validate_fund_industry_mapping(position.industry)
    if not position.security_code.strip() or not position.security_name.strip():
        errors.append("holding security code and name are required")
    weight = _decimal(position.weight_pct)
    if weight is None or weight < 0 or weight > 100:
        errors.append("holding weight_pct must be between 0 and 100")
    return errors


@dataclass(frozen=True)
class FundHoldingsSnapshot:
    code: str
    report_period: str
    positions: tuple[FundHoldingPosition, ...]
    disclosed_total_pct: str
    source: FundDataSource

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "report_period": self.report_period,
            "positions": [position.to_dict() for position in self.positions],
            "disclosed_total_pct": self.disclosed_total_pct,
            "source": self.source.to_dict(),
        }


def validate_fund_holdings_snapshot(snapshot: FundHoldingsSnapshot) -> list[str]:
    errors = validate_fund_data_source(snapshot.source)
    if not snapshot.code.strip():
        errors.append("fund code is required")
    if not _valid_report_period(snapshot.report_period):
        errors.append("holdings report_period must be YYYY-QN or an ISO date")
    if snapshot.source.report_period != snapshot.report_period:
        errors.append("source report_period must match holdings report_period")
    total = _decimal(snapshot.disclosed_total_pct)
    if total is None or total < 0 or total > 100:
        errors.append("disclosed_total_pct must be between 0 and 100")
    position_total = Decimal("0")
    seen: set[str] = set()
    for position in snapshot.positions:
        errors.extend(validate_fund_holding_position(position))
        if position.security_code in seen:
            errors.append(f"duplicate holding security_code: {position.security_code}")
        seen.add(position.security_code)
        position_total += _decimal(position.weight_pct) or Decimal("0")
    if total is not None and abs(position_total - total) > Decimal("0.20"):
        errors.append("disclosed_total_pct must match the disclosed position weights")
    return errors


@dataclass(frozen=True)
class FundDataBundle:
    code: str
    requested_sections: tuple[str, ...]
    data_status: str
    source: FundDataSource
    profile: FundProfile | None = None
    nav: FundNavSnapshot | None = None
    holdings: FundHoldingsSnapshot | None = None
    missing_sections: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "requested_sections": list(self.requested_sections),
            "data_status": self.data_status,
            "source": self.source.to_dict(),
            "profile": self.profile.to_dict() if self.profile else None,
            "nav": self.nav.to_dict() if self.nav else None,
            "holdings": self.holdings.to_dict() if self.holdings else None,
            "missing_sections": list(self.missing_sections),
            "reason": self.reason,
        }


def contains_test_fixture(bundle: FundDataBundle) -> bool:
    sources = [bundle.source]
    if bundle.profile:
        sources.append(bundle.profile.source)
    if bundle.nav:
        sources.append(bundle.nav.source)
    if bundle.holdings:
        sources.append(bundle.holdings.source)
        sources.extend(position.industry.source for position in bundle.holdings.positions)
    return any(source.source_kind == "test_fixture" or source.test_fixture for source in sources)


def validate_fund_data_bundle(bundle: FundDataBundle, *, allow_test_fixture: bool = False) -> list[str]:
    errors = validate_fund_data_source(bundle.source)
    if not bundle.code.strip():
        errors.append("fund code is required")
    if bundle.data_status not in BUNDLE_STATUSES:
        errors.append("unsupported bundle data_status")
    requested = set(bundle.requested_sections)
    missing = set(bundle.missing_sections)
    if not requested or requested - FUND_SECTIONS or len(requested) != len(bundle.requested_sections):
        errors.append("requested_sections must be unique supported fund sections")
    if missing - requested or len(missing) != len(bundle.missing_sections):
        errors.append("missing_sections must be unique requested sections")
    sections = {"profile": bundle.profile, "nav": bundle.nav, "holdings": bundle.holdings}
    for section_name in requested:
        section = sections[section_name]
        if section is None and section_name not in missing:
            errors.append(f"{section_name} is absent but not listed in missing_sections")
        if section is not None and section_name in missing:
            errors.append(f"{section_name} is present but listed in missing_sections")
    for section_name, section in sections.items():
        if section_name not in requested and section is not None:
            errors.append(f"unrequested section returned: {section_name}")
    if bundle.data_status == "available" and missing:
        errors.append("available bundle cannot contain missing_sections")
    if bundle.data_status == "stale" and not bundle.source.stale:
        errors.append("stale bundle requires stale source metadata")
    if bundle.data_status == "missing" and any(sections[name] is not None for name in requested):
        errors.append("missing bundle cannot contain requested data sections")
    if bundle.data_status in {"missing", "provider_error"} and not bundle.reason.strip():
        errors.append("missing or provider_error bundle requires reason")
    if bundle.profile:
        errors.extend(validate_fund_profile(bundle.profile))
    if bundle.nav:
        errors.extend(validate_fund_nav_snapshot(bundle.nav))
    if bundle.holdings:
        errors.extend(validate_fund_holdings_snapshot(bundle.holdings))
    for section in (bundle.profile, bundle.nav, bundle.holdings):
        if section is not None and section.code != bundle.code:
            errors.append("section fund code must match bundle code")
    if contains_test_fixture(bundle) and not allow_test_fixture:
        errors.append("test fixture data is blocked outside explicit tests")
    return errors


def build_missing_fund_data_source(
    *,
    provider: str,
    fetched_at: str,
    source_status: str,
    missing_sections: Sequence[str],
    reason: str,
) -> FundDataSource:
    return FundDataSource(
        provider=provider,
        source_kind="unavailable",
        source_status=source_status,
        fetched_at=fetched_at,
        missing_fields=tuple(missing_sections),
        missing_reasons={section: reason for section in missing_sections},
    )
