"""Manual localhost-only AKShare adapter for canonical fund data contracts.

The adapter is closed unless both runtime gates are explicitly enabled by the
caller.  It reads public fund facts only, keeps all results in memory, and does
not touch accounts, credentials, AI, notifications, trading, or persistence.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any, Mapping, Sequence

from src.fund_data_contract import (
    FundDataBundle,
    FundDataSource,
    FundHoldingPosition,
    FundHoldingsSnapshot,
    FundIndustryMapping,
    FundNavSnapshot,
    FundProfile,
)
from src.fund_data_provider import (
    FundDataRequest,
    build_unavailable_fund_data_bundle,
    fetch_fund_data,
)


PROVIDER_NAME = "akshare_fund_public"
PROVIDER_LABEL = "AKShare 公开基金数据"
READONLY_TIMEOUT_SECONDS = 20
FUND_CODE_RE = re.compile(r"^\d{6}$")
READONLY_REQUEST_FIELDS = frozenset(
    {
        "mode",
        "provider",
        "code",
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


class AkshareFundDataError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return not str(value).strip() or str(value).strip().lower() in {"nan", "none", "null", "--"}


def _text(value: Any, *, limit: int = 160) -> str | None:
    if _is_missing(value):
        return None
    cleaned = " ".join(str(value).strip().split())
    lowered = cleaned.lower()
    if len(cleaned) > limit or any(marker in lowered for marker in ("authorization", "bearer ", "cookie=", "token=")):
        return None
    return cleaned


def _decimal_text(value: Any) -> str | None:
    if _is_missing(value):
        return None
    raw = str(value).strip().replace(",", "").replace("%", "")
    try:
        parsed = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite():
        return None
    rendered = format(parsed, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _date_text(value: Any) -> str | None:
    if _is_missing(value):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            pass
    raw = str(value).strip()
    match = re.search(r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})", raw)
    if not match:
        return None
    try:
        return date(*(int(part) for part in match.groups())).isoformat()
    except ValueError:
        return None


def _records(table: Any) -> list[dict[str, Any]]:
    if table is None:
        return []
    if isinstance(table, Mapping):
        return [dict(table)]
    if isinstance(table, Sequence) and not isinstance(table, (str, bytes, bytearray)):
        return [dict(row) for row in table if isinstance(row, Mapping)]
    to_dict = getattr(table, "to_dict", None)
    if callable(to_dict):
        try:
            value = to_dict(orient="records")
        except TypeError:
            value = to_dict("records")
        if isinstance(value, list):
            return [dict(row) for row in value if isinstance(row, Mapping)]
    return []


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


def _field(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and not _is_missing(row[name]):
            return row[name]
    return None


def _scale(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*亿", text.replace(",", ""))
    if not match:
        return None
    parsed = _decimal_text(match.group(1))
    return parsed if parsed is not None and Decimal(parsed) >= 0 else None


def _quarter(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"(\d{4})\s*年?\s*([1-4])\s*季", text)
    return f"{match.group(1)}-Q{match.group(2)}" if match else None


def _position_code(value: Any) -> str | None:
    text = _text(value, limit=32)
    if not text:
        return None
    if text.isdigit() and len(text) <= 6:
        return text.zfill(6)
    return text if re.fullmatch(r"[A-Za-z0-9._-]{1,24}", text) else None


@dataclass(frozen=True)
class AkshareFundDataProviderConfig:
    network_enabled: bool = False
    human_approved: bool = False
    holdings_years: tuple[int, ...] = ()


class AkshareFundDataProvider:
    """Provider implementation using three documented AKShare fund endpoints."""

    name = PROVIDER_NAME
    provider_type = "provider"

    def __init__(
        self,
        *,
        config: AkshareFundDataProviderConfig | None = None,
        akshare_module: Any | None = None,
        now: datetime | None = None,
    ) -> None:
        self.config = config or AkshareFundDataProviderConfig()
        self.akshare_module = akshare_module
        self.now = now or datetime.now(timezone.utc)

    def _akshare(self) -> Any:
        if self.akshare_module is None:
            import akshare as ak  # Lazy import: disabled paths never initialize network libraries.

            self.akshare_module = ak
        return self.akshare_module

    def _profile(self, code: str, fetched_at: str) -> FundProfile | None:
        rows = _records(self._akshare().fund_overview_em(symbol=code))
        if not rows:
            return None
        row = rows[0]
        values = {
            "name": _text(_field(row, "基金全称", "基金简称")),
            "fund_type": _text(_field(row, "基金类型")),
            "manager": _text(_field(row, "基金经理人", "基金经理")),
            "scale": _scale(_field(row, "资产规模", "成立日期/规模")),
            "inception_date": _date_text(_field(row, "成立日期/规模", "成立日期")),
        }
        values["scale_currency"] = "CNY_100M" if values["scale"] is not None else None
        missing = {
            name: "AKShare 基金概况未提供该字段。"
            for name, value in values.items()
            if value is None
        }
        return FundProfile(
            code=code,
            name=values["name"],
            fund_type=values["fund_type"],
            manager=values["manager"],
            scale=values["scale"],
            scale_currency=values["scale_currency"],
            inception_date=values["inception_date"],
            source=_source(
                fetched_at=fetched_at,
                status="partial" if missing else "available",
                missing=missing,
            ),
        )

    def _nav(self, code: str, fetched_at: str) -> FundNavSnapshot | None:
        unit_rows = _records(
            self._akshare().fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        )
        try:
            cumulative_rows = _records(
                self._akshare().fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
            )
        except Exception:
            cumulative_rows = []
        dated_units = [(_date_text(_field(row, "净值日期", "日期")), row) for row in unit_rows]
        dated_units = [(day, row) for day, row in dated_units if day]
        if not dated_units:
            return None
        nav_date, unit_row = max(dated_units, key=lambda item: item[0])
        cumulative_by_date = {
            day: row
            for row in cumulative_rows
            if (day := _date_text(_field(row, "净值日期", "日期")))
        }
        cumulative_row = cumulative_by_date.get(nav_date, {})
        values = {
            "unit_nav": _decimal_text(_field(unit_row, "单位净值")),
            "accumulated_nav": _decimal_text(_field(cumulative_row, "累计净值")),
            "daily_change_pct": _decimal_text(_field(unit_row, "日增长率")),
            "nav_date": nav_date,
            "estimated_nav": None,
            "estimated_change_pct": None,
            "estimated_change_amount": None,
            "estimate_time": None,
        }
        missing = {
            name: (
                "Build D1 只读取正式净值，不提供盘中估算。"
                if name.startswith("estimated") or name == "estimate_time"
                else "AKShare 最新净值记录未提供该字段。"
            )
            for name, value in values.items()
            if value is None
        }
        return FundNavSnapshot(
            code=code,
            unit_nav=values["unit_nav"],
            accumulated_nav=values["accumulated_nav"],
            daily_change_pct=values["daily_change_pct"],
            nav_date=values["nav_date"],
            estimated_nav=None,
            estimated_change_pct=None,
            estimated_change_amount=None,
            estimate_time=None,
            source=_source(
                fetched_at=fetched_at,
                status="partial" if missing else "available",
                effective_at=nav_date,
                missing=missing,
            ),
        )

    def _holdings_rows(self, code: str) -> list[dict[str, Any]]:
        years = self.config.holdings_years or (self.now.year, self.now.year - 1)
        for year in years:
            try:
                rows = _records(self._akshare().fund_portfolio_hold_em(symbol=code, date=str(year)))
            except Exception:
                rows = []
            if rows:
                return rows
        return []

    def _holdings(self, code: str, fetched_at: str) -> FundHoldingsSnapshot | None:
        rows = self._holdings_rows(code)
        quarter_rows = [(_quarter(_field(row, "季度", "报告期")), row) for row in rows]
        quarter_rows = [(quarter, row) for quarter, row in quarter_rows if quarter]
        if not quarter_rows:
            return None
        report_period = max(quarter for quarter, _ in quarter_rows)
        latest = [row for quarter, row in quarter_rows if quarter == report_period]
        latest.sort(key=lambda row: int(_decimal_text(_field(row, "序号")) or "9999"))
        positions: list[FundHoldingPosition] = []
        seen: set[str] = set()
        for row in latest:
            security_code = _position_code(_field(row, "股票代码", "证券代码"))
            security_name = _text(_field(row, "股票名称", "证券名称"), limit=80)
            weight = _decimal_text(_field(row, "占净值比例", "占净值比例(%)"))
            if not security_code or not security_name or weight is None or security_code in seen:
                continue
            parsed_weight = Decimal(weight)
            if parsed_weight < 0 or parsed_weight > 100:
                continue
            seen.add(security_code)
            industry_reason = "Build D2 尚未执行证券到行业的可核验映射。"
            industry = FundIndustryMapping(
                status="unknown",
                industry_code=None,
                industry_name=None,
                source=_source(
                    fetched_at=fetched_at,
                    status="partial",
                    report_period=report_period,
                    missing={
                        "industry_code": industry_reason,
                        "industry_name": industry_reason,
                    },
                    confidence="0.00",
                ),
            )
            positions.append(FundHoldingPosition(security_code, security_name, weight, industry))
            if len(positions) == 10:
                break
        if not positions:
            return None
        total = sum((Decimal(position.weight_pct) for position in positions), Decimal("0"))
        return FundHoldingsSnapshot(
            code=code,
            report_period=report_period,
            positions=tuple(positions),
            disclosed_total_pct=_decimal_text(total) or "0",
            source=_source(
                fetched_at=fetched_at,
                status="available",
                report_period=report_period,
                confidence="0.85",
            ),
        )

    def fetch(self, request: FundDataRequest) -> FundDataBundle:
        if not (self.config.network_enabled and self.config.human_approved):
            return build_unavailable_fund_data_bundle(
                request,
                provider=PROVIDER_NAME,
                reason="AKShare 基金公开数据必须由用户在本机逐次确认后读取。",
            )
        if not FUND_CODE_RE.fullmatch(request.code):
            return build_unavailable_fund_data_bundle(
                request,
                provider=PROVIDER_NAME,
                status="provider_error",
                source_status="provider_error",
                reason="基金代码必须是六位数字。",
            )

        fetched_at = _utc_now_iso()
        section_values: dict[str, Any] = {}
        missing_reasons: dict[str, str] = {}
        loaders = {
            "profile": self._profile,
            "nav": self._nav,
            "holdings": self._holdings,
        }
        for section in request.requested_sections:
            try:
                section_values[section] = loaders[section](request.code, fetched_at)
            except Exception:
                section_values[section] = None
            if section_values[section] is None:
                missing_reasons[section] = "AKShare 未返回可验证的基金数据。"

        missing_sections = tuple(section for section in request.requested_sections if section_values.get(section) is None)
        if len(missing_sections) == len(request.requested_sections):
            return build_unavailable_fund_data_bundle(
                request,
                provider=PROVIDER_NAME,
                reason="AKShare 暂未返回该基金的可验证公开数据。",
            )

        sections = [section_values.get(name) for name in request.requested_sections if section_values.get(name)]
        has_partial_fields = any(getattr(section, "source").source_status != "available" for section in sections)
        data_status = "partial" if missing_sections or has_partial_fields else "available"
        return FundDataBundle(
            code=request.code,
            requested_sections=request.requested_sections,
            data_status=data_status,
            source=_source(
                fetched_at=fetched_at,
                status="partial" if data_status == "partial" else "available",
                missing=missing_reasons,
                confidence="0.85",
            ),
            profile=section_values.get("profile"),
            nav=section_values.get("nav"),
            holdings=section_values.get("holdings"),
            missing_sections=missing_sections,
            reason="部分字段或区块缺失，请按来源日期使用。" if data_status == "partial" else "",
        )


def validate_readonly_request(payload: Mapping[str, Any]) -> FundDataRequest:
    if not isinstance(payload, Mapping) or set(payload) != READONLY_REQUEST_FIELDS:
        raise AkshareFundDataError("fund-readonly.invalid-request")
    code = payload.get("code")
    sections = payload.get("sections")
    if not isinstance(code, str) or not FUND_CODE_RE.fullmatch(code):
        raise AkshareFundDataError("fund-readonly.invalid-code")
    if not isinstance(sections, list) or not sections or any(not isinstance(item, str) for item in sections):
        raise AkshareFundDataError("fund-readonly.invalid-sections")
    request = FundDataRequest(code=code, requested_sections=tuple(sections))
    if set(request.requested_sections) - {"profile", "nav", "holdings"} or len(set(request.requested_sections)) != len(request.requested_sections):
        raise AkshareFundDataError("fund-readonly.invalid-sections")
    if not (
        payload.get("mode") == "fund-public-readonly"
        and payload.get("provider") == PROVIDER_NAME
        and payload.get("humanApproved") is True
        and payload.get("readOnly") is True
    ):
        raise AkshareFundDataError("fund-readonly.approval-required")
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
        raise AkshareFundDataError("fund-readonly.forbidden-capability")
    return request


def run_akshare_fund_readonly(payload: Mapping[str, Any], *, akshare_module: Any | None = None) -> dict[str, Any]:
    try:
        request = validate_readonly_request(payload)
        provider = AkshareFundDataProvider(
            config=AkshareFundDataProviderConfig(network_enabled=True, human_approved=True),
            akshare_module=akshare_module,
        )
        bundle = fetch_fund_data(request, provider)
        status = "completed-readonly" if bundle.data_status in {"available", "partial"} else "unavailable"
        return {
            "status": status,
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
            "bundle": bundle.to_dict(),
        }
    except AkshareFundDataError as exc:
        return {
            "status": "blocked",
            "errorCode": exc.code,
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
        }


async def run_akshare_fund_readonly_with_timeout(
    payload: Mapping[str, Any],
    *,
    akshare_module: Any | None = None,
    timeout_seconds: float = READONLY_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(run_akshare_fund_readonly, payload, akshare_module=akshare_module),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "errorCode": "fund-readonly.provider-timeout",
            "providerLabel": PROVIDER_LABEL,
            "readOnly": True,
        }
