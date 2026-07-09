import json
from pathlib import Path

import pytest

from scripts.run_fund_nav_provider_smoke import (
    CI_REAL_BLOCK_MESSAGE,
    assert_not_ci_for_real_request,
    is_ci_environment,
    run_smoke,
)

BASE = ["--provider", "eastmoney_fund", "--code", "000000", "--type", "fund", "--market", "CN"]
REAL_ENV = {
    "FUND_NAV_ENABLE_REAL_PROVIDER": "1",
    "FUND_NAV_NETWORK_ENABLED": "1",
    "FUND_NAV_ALLOW_REAL_REQUEST": "1",
}


def _dump(payload):
    return json.dumps(payload, ensure_ascii=False)


def test_default_mode_is_dry_run_and_does_not_request_real_provider(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_smoke(BASE, env={})
    assert result["data_status"] == "dry_run_only"
    assert result["data_mode"] == "dry_run"
    assert result["will_fetch_real_data"] is False
    assert result["has_real_nav_data"] is False
    assert result["allow_commit_to_repo"] is False
    assert result["provider"] == "eastmoney_fund"
    assert not list(tmp_path.iterdir())


def test_explicit_dry_run_does_not_request_real_provider():
    result = run_smoke(BASE + ["--dry-run"], env=REAL_ENV)
    assert result["data_status"] == "dry_run_only"
    assert result["will_fetch_real_data"] is False


def test_local_only_uses_fixture_without_network(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_smoke(["--provider", "local_fund_nav_fixture", "--code", "000000", "--type", "fund", "--market", "CN", "--local-only"], env=REAL_ENV)
    assert result["data_status"] == "local_only_available"
    assert result["data_mode"] == "local_only_fixture"
    assert result["will_fetch_real_data"] is False
    assert result["has_real_nav_data"] is False
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("env", [{}, {"FUND_NAV_ENABLE_REAL_PROVIDER": "1"}, {"FUND_NAV_ENABLE_REAL_PROVIDER": "1", "FUND_NAV_NETWORK_ENABLED": "1"}])
def test_real_without_all_environment_gates_is_blocked(env):
    called = False

    def fake_fetcher(_request):
        nonlocal called
        called = True
        return {}

    result = run_smoke(BASE + ["--real"], env=env, real_fetcher=fake_fetcher)
    assert result["data_status"] == "provider_policy_blocked"
    assert result["will_fetch_real_data"] is False
    assert called is False


@pytest.mark.parametrize("env", [{"CI": "true", **REAL_ENV}, {"GITHUB_ACTIONS": "true", **REAL_ENV}])
def test_real_is_blocked_in_ci(env):
    result = run_smoke(BASE + ["--real"], env=env, real_fetcher=lambda _request: {})
    assert result["data_status"] == "provider_policy_blocked"
    assert result["message"] == CI_REAL_BLOCK_MESSAGE
    assert result["has_real_nav_data"] is False


def test_ci_helpers():
    assert is_ci_environment({"CI": "true"}) is True
    assert is_ci_environment({"GITHUB_ACTIONS": "true"}) is True
    assert is_ci_environment({}) is False
    with pytest.raises(RuntimeError, match="CI 环境禁止真实基金净值"):
        assert_not_ci_for_real_request({"CI": "true"})


def test_real_with_all_gates_uses_fake_fetcher_only():
    calls = []

    def fake_fetcher(request):
        calls.append(dict(request))
        return {"source_status": "ok", "nav": {}, "estimate": {}}

    result = run_smoke(BASE + ["--real", "--no-save"], env=REAL_ENV, real_fetcher=fake_fetcher)
    assert len(calls) == 1
    assert result["data_status"] == "real_provider_available"
    assert result["will_fetch_real_data"] is True
    assert result["has_real_nav_data"] is True
    assert result["allow_commit_to_repo"] is False
    assert result["no_save"] is True
    assert result["will_write_files"] is False


def test_output_contains_required_fields_and_redacts_sensitive_values():
    result = run_smoke(BASE + ["--real"], env={"FUND_NAV_ENABLE_REAL_PROVIDER": "1", "SECRET_TOKEN": "x"})
    dumped = _dump(result).lower()
    assert "provider" in result
    assert "data_status" in result
    assert "has_real_nav_data" in result
    assert result["allow_commit_to_repo"] is False
    assert "token" not in dumped
    assert "api key" not in dumped
    assert "webhook" not in dumped


@pytest.mark.parametrize("asset_type", ["stock", "etf", "index"])
def test_non_fund_types_are_unsupported(asset_type):
    result = run_smoke(["--code", "000000", "--type", asset_type], env={})
    assert result["data_status"] == "unsupported"


def test_unknown_type_is_invalid_request():
    result = run_smoke(["--code", "000000", "--type", "unknown"], env={})
    assert result["data_status"] == "invalid_request"


def test_manual_smoke_doc_contains_required_disclaimer():
    doc = Path("docs/fund_nav_provider_manual_smoke.md").read_text(encoding="utf-8")
    assert "最终以基金公司公布净值为准" in doc
