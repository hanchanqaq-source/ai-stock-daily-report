"""Provider boundary for canonical fund data contracts.

No real provider is implemented or enabled here.  The production default is an
explicit unavailable provider; tests must opt in before fixture data is accepted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Protocol

from src.fund_data_contract import (
    FUND_SECTIONS,
    FundDataBundle,
    build_missing_fund_data_source,
    contains_test_fixture,
    validate_fund_data_bundle,
)


@dataclass(frozen=True)
class FundDataRequest:
    code: str
    requested_sections: tuple[str, ...] = ("profile", "nav", "holdings")


class FundDataProvider(Protocol):
    name: str
    provider_type: str

    def fetch(self, request: FundDataRequest) -> FundDataBundle: ...


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_provider_name(value: object) -> str:
    name = str(value or "fund_data_provider")
    return name if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", name) else "fund_data_provider"


def validate_fund_data_request(request: FundDataRequest) -> list[str]:
    errors: list[str] = []
    requested = set(request.requested_sections)
    if not request.code.strip():
        errors.append("fund code is required")
    elif len(request.code) > 32 or any(character.isspace() for character in request.code):
        errors.append("fund code must be a compact identifier up to 32 characters")
    if not requested or requested - FUND_SECTIONS or len(requested) != len(request.requested_sections):
        errors.append("requested_sections must be unique supported fund sections")
    return errors


def _safe_error_request(request: FundDataRequest) -> FundDataRequest:
    code = request.code.strip()
    if not code or len(code) > 32 or any(character.isspace() for character in code):
        code = "invalid-fund-code"
    sections = tuple(dict.fromkeys(section for section in request.requested_sections if section in FUND_SECTIONS))
    return FundDataRequest(code=code, requested_sections=sections or ("profile", "nav", "holdings"))


def build_unavailable_fund_data_bundle(
    request: FundDataRequest,
    *,
    provider: str = "fund_data_not_connected",
    status: str = "missing",
    source_status: str = "not_connected",
    reason: str = "真实基金数据尚未接入。",
) -> FundDataBundle:
    return FundDataBundle(
        code=request.code,
        requested_sections=request.requested_sections,
        data_status=status,
        source=build_missing_fund_data_source(
            provider=provider,
            fetched_at=_utc_now_iso(),
            source_status=source_status,
            missing_sections=request.requested_sections,
            reason=reason,
        ),
        missing_sections=request.requested_sections,
        reason=reason,
    )


class UnavailableFundDataProvider:
    """Safe production default that never fabricates or requests fund facts."""

    name = "fund_data_not_connected"
    provider_type = "unavailable"

    def fetch(self, request: FundDataRequest) -> FundDataBundle:
        return build_unavailable_fund_data_bundle(request, provider=self.name)


def fetch_fund_data(
    request: FundDataRequest,
    provider: FundDataProvider | None = None,
    *,
    allow_test_fixture: bool = False,
) -> FundDataBundle:
    request_errors = validate_fund_data_request(request)
    if request_errors:
        return build_unavailable_fund_data_bundle(
            _safe_error_request(request),
            status="provider_error",
            source_status="provider_error",
            reason="; ".join(request_errors),
        )
    active_provider = provider or UnavailableFundDataProvider()
    provider_name = _safe_provider_name(getattr(active_provider, "name", "fund_data_provider"))
    provider_type = str(getattr(active_provider, "provider_type", ""))
    if not provider_type or not callable(getattr(active_provider, "fetch", None)):
        return build_unavailable_fund_data_bundle(
            request,
            provider=provider_name,
            status="provider_error",
            source_status="provider_error",
            reason="基金 Provider 未实现规定接口。",
        )
    if provider_type == "test_fixture" and not allow_test_fixture:
        return build_unavailable_fund_data_bundle(
            request,
            provider=provider_name,
            status="provider_error",
            source_status="provider_error",
            reason="测试 fixture 被正式运行门禁阻止。",
        )
    try:
        result = active_provider.fetch(request)
    except Exception:
        return build_unavailable_fund_data_bundle(
            request,
            provider=provider_name,
            status="provider_error",
            source_status="provider_error",
            reason="基金 Provider 执行失败；错误载荷未透传。",
        )
    if not isinstance(result, FundDataBundle):
        return build_unavailable_fund_data_bundle(
            request,
            provider=provider_name,
            status="provider_error",
            source_status="provider_error",
            reason="基金 Provider 返回了不受支持的契约类型。",
        )
    contract_errors = validate_fund_data_bundle(result, allow_test_fixture=allow_test_fixture)
    fixture_payload = contains_test_fixture(result)
    if provider_type == "test_fixture" and not fixture_payload:
        contract_errors.append("test fixture provider returned unmarked data")
    if provider_type != "test_fixture" and fixture_payload:
        contract_errors.append("fixture data requires provider_type=test_fixture")
    if result.code != request.code:
        contract_errors.append("provider returned a different fund code")
    if result.requested_sections != request.requested_sections:
        contract_errors.append("provider changed requested_sections")
    if contract_errors:
        return build_unavailable_fund_data_bundle(
            request,
            provider=provider_name,
            status="provider_error",
            source_status="provider_error",
            reason="provider contract invalid: " + "; ".join(contract_errors),
        )
    return result
