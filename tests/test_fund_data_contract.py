from dataclasses import replace

from src.fund_data_contract import (
    FundDataBundle,
    FundDataSource,
    FundHoldingPosition,
    FundHoldingsSnapshot,
    FundIndustryMapping,
    FundNavSnapshot,
    FundProfile,
    contains_test_fixture,
    validate_fund_data_bundle,
    validate_fund_data_source,
    validate_fund_holdings_snapshot,
    validate_fund_industry_mapping,
    validate_fund_profile,
)
from src.fund_data_provider import FundDataRequest, fetch_fund_data


FETCHED_AT = "2026-07-16T08:00:00+00:00"


def fixture_source(
    *,
    effective_at=None,
    report_period=None,
    missing_fields=(),
    missing_reasons=None,
):
    return FundDataSource(
        provider="fund_contract_test_fixture",
        source_kind="test_fixture",
        source_status="test_fixture",
        fetched_at=FETCHED_AT,
        effective_at=effective_at,
        report_period=report_period,
        missing_fields=tuple(missing_fields),
        missing_reasons=missing_reasons or {},
        test_fixture=True,
    )


def fixture_bundle(code="000000"):
    profile = FundProfile(
        code=code,
        name="测试基金A",
        fund_type="测试类型",
        manager="测试经理",
        scale="10.00",
        scale_currency="CNY_100M",
        inception_date="2020-01-02",
        source=fixture_source(effective_at="2026-07-15"),
    )
    nav = FundNavSnapshot(
        code=code,
        unit_nav="1.0000",
        accumulated_nav="1.2000",
        daily_change_pct="0.10",
        nav_date="2026-07-15",
        source=fixture_source(effective_at="2026-07-15"),
        estimated_nav="1.0010",
        estimated_change_pct="0.20",
        estimated_change_amount="0.0010",
        estimate_time="2026-07-16T07:30:00+00:00",
    )
    mapped = FundIndustryMapping(
        status="mapped",
        industry_code="TEST-INDUSTRY",
        industry_name="测试行业",
        source=fixture_source(effective_at="2026-07-15"),
    )
    holdings = FundHoldingsSnapshot(
        code=code,
        report_period="2026-Q2",
        positions=(FundHoldingPosition("TEST001", "测试证券", "8.50", mapped),),
        disclosed_total_pct="8.50",
        source=fixture_source(report_period="2026-Q2"),
    )
    return FundDataBundle(
        code=code,
        requested_sections=("profile", "nav", "holdings"),
        data_status="available",
        source=fixture_source(effective_at="2026-07-15"),
        profile=profile,
        nav=nav,
        holdings=holdings,
    )


def test_complete_fixture_bundle_is_valid_only_with_explicit_test_gate():
    bundle = fixture_bundle()

    assert validate_fund_data_bundle(bundle, allow_test_fixture=True) == []
    assert "test fixture data is blocked" in " ".join(validate_fund_data_bundle(bundle))
    assert contains_test_fixture(bundle) is True
    payload = bundle.to_dict()
    assert payload["nav"]["source"]["effective_at"] == "2026-07-15"
    assert payload["holdings"]["source"]["report_period"] == "2026-Q2"


def test_missing_profile_fields_require_field_level_reasons():
    source = fixture_source(
        effective_at="2026-07-15",
        missing_fields=("manager", "scale", "scale_currency"),
        missing_reasons={
            "manager": "provider omitted manager",
            "scale": "provider omitted scale",
            "scale_currency": "provider omitted scale unit",
        },
    )
    profile = FundProfile(
        code="000000",
        name="测试基金A",
        fund_type="测试类型",
        manager=None,
        scale=None,
        scale_currency=None,
        inception_date="2020-01-02",
        source=source,
    )

    assert validate_fund_profile(profile) == []
    missing_reason = replace(
        source,
        missing_reasons={"manager": "provider omitted manager", "scale_currency": "provider omitted scale unit"},
    )
    errors = validate_fund_profile(replace(profile, source=missing_reason))
    assert "missing reason required for scale" in errors


def test_stale_source_requires_reason_and_dates_are_auditable():
    stale = replace(
        fixture_source(effective_at="2026-06-30"),
        stale=True,
        stale_reason="older than freshness policy",
    )
    assert validate_fund_data_source(stale) == []
    assert "stale data requires stale_reason" in validate_fund_data_source(replace(stale, stale_reason=""))
    assert "fetched_at must be a timezone-aware ISO datetime" in validate_fund_data_source(
        replace(stale, fetched_at="2026-07-16T08:00:00")
    )


def test_unknown_industry_is_preserved_and_cannot_be_forced_into_other():
    unknown_source = fixture_source(
        effective_at="2026-07-15",
        missing_fields=("industry_code", "industry_name"),
        missing_reasons={
            "industry_code": "no verified mapping",
            "industry_name": "no verified mapping",
        },
    )
    unknown = FundIndustryMapping("unknown", None, None, unknown_source)

    assert validate_fund_industry_mapping(unknown) == []
    forced = replace(unknown, industry_code="OTHER", industry_name="其他")
    assert "unresolved industry must remain empty" in validate_fund_industry_mapping(forced)


def test_holdings_total_and_report_period_must_match_disclosure():
    holdings = fixture_bundle().holdings
    assert holdings is not None
    assert validate_fund_holdings_snapshot(holdings) == []

    total_errors = validate_fund_holdings_snapshot(replace(holdings, disclosed_total_pct="20.00"))
    assert "disclosed_total_pct must match" in " ".join(total_errors)
    period_errors = validate_fund_holdings_snapshot(replace(holdings, report_period="2026-Q1"))
    assert "source report_period must match" in " ".join(period_errors)


class FixtureProviderForTests:
    name = "fund_contract_test_fixture"
    provider_type = "test_fixture"

    def fetch(self, request):
        return fixture_bundle(request.code)


def test_provider_fixture_is_blocked_by_default_and_allowed_only_in_tests():
    request = FundDataRequest("000000")

    blocked = fetch_fund_data(request, FixtureProviderForTests())
    assert blocked.data_status == "provider_error"
    assert blocked.missing_sections == request.requested_sections
    assert "fixture" in blocked.reason

    allowed = fetch_fund_data(request, FixtureProviderForTests(), allow_test_fixture=True)
    assert allowed.data_status == "available"
    assert allowed.profile is not None


def test_production_default_returns_explicit_missing_state_without_fake_values():
    request = FundDataRequest("000000")

    result = fetch_fund_data(request)

    assert result.data_status == "missing"
    assert result.profile is None
    assert result.nav is None
    assert result.holdings is None
    assert result.source.source_status == "not_connected"
    assert set(result.missing_sections) == {"profile", "nav", "holdings"}
    assert validate_fund_data_bundle(result) == []


def test_invalid_request_returns_a_contract_valid_low_detail_error():
    result = fetch_fund_data(FundDataRequest(" ", ("profile", "unknown", "profile")))

    assert result.data_status == "provider_error"
    assert result.code == "invalid-fund-code"
    assert result.requested_sections == ("profile",)
    assert validate_fund_data_bundle(result) == []


class InvalidProvider:
    name = "invalid_provider"
    provider_type = "provider"

    def fetch(self, request):
        return replace(fixture_bundle("WRONG"), source=replace(fixture_source(), source_kind="provider", source_status="available", test_fixture=False))


def test_invalid_provider_contract_fails_closed_without_exposing_payload():
    result = fetch_fund_data(FundDataRequest("000000"), InvalidProvider(), allow_test_fixture=True)

    assert result.data_status == "provider_error"
    assert result.profile is None
    assert "provider contract invalid" in result.reason


class BrokenProvider:
    name = "broken_provider"
    provider_type = "provider"

    def fetch(self, request):
        raise RuntimeError("private-provider-detail")


class WrongShapeProvider:
    name = "wrong_shape_provider"
    provider_type = "provider"

    def fetch(self, request):
        return {"raw": "payload-must-not-pass"}


def test_provider_errors_and_raw_payloads_fail_closed():
    failed = fetch_fund_data(FundDataRequest("000000"), BrokenProvider())
    wrong_shape = fetch_fund_data(FundDataRequest("000000"), WrongShapeProvider())

    assert failed.data_status == "provider_error"
    assert "private-provider-detail" not in failed.reason
    assert wrong_shape.data_status == "provider_error"
    assert "payload-must-not-pass" not in wrong_shape.reason
