import json
from pathlib import Path

import pytest

from scripts.run_cn_quote_provider_smoke import main, redact_output, run_smoke


def _env(**overrides):
    base = {
        "CN_QUOTE_ENABLE_REAL_PROVIDER": "",
        "CN_QUOTE_NETWORK_ENABLED": "",
        "CN_QUOTE_ALLOW_REAL_REQUEST": "",
        "CI": "",
        "GITHUB_ACTIONS": "",
    }
    base.update(overrides)
    return base


def _fake_real_fetcher(calls):
    def fetcher(request):
        calls.append(dict(request))
        return {
            "provider_status": "ok",
            "quote": {
                "last_price": 1,
                "change_pct": 0,
                "change_amount": 0,
                "volume": 1,
                "turnover": 1,
                "open": 1,
                "high": 1,
                "low": 1,
                "previous_close": 1,
            },
        }

    return fetcher


def test_default_mode_is_dry_run_and_does_not_request_real_provider():
    calls = []
    result = run_smoke(["--provider", "akshare", "--code", "000001", "--type", "stock"], env=_env(), real_fetcher=_fake_real_fetcher(calls))
    assert result["data_status"] == "dry_run_only"
    assert result["data_mode"] == "dry_run"
    assert result["provider"] == "akshare"
    assert result["has_real_market_data"] is False
    assert result["will_fetch_real_data"] is False
    assert result["allow_commit_to_repo"] is False
    assert calls == []


def test_explicit_dry_run_does_not_request_real_provider():
    calls = []
    result = run_smoke(["--dry-run", "--code", "000001", "--type", "stock"], env=_env(), real_fetcher=_fake_real_fetcher(calls))
    assert result["data_status"] == "dry_run_only"
    assert result["has_real_market_data"] is False
    assert calls == []


def test_local_only_uses_fixture_without_network_or_real_provider():
    calls = []
    result = run_smoke(["--local-only", "--code", "000001", "--type", "stock"], env=_env(), real_fetcher=_fake_real_fetcher(calls))
    assert result["data_mode"] == "local_only_fixture"
    assert result["source_status"] == "local_fixture_only"
    assert result["has_real_market_data"] is False
    assert result["will_fetch_real_data"] is False
    assert calls == []


def test_real_without_all_environment_gates_is_policy_blocked():
    calls = []
    result = run_smoke(["--real", "--code", "000001", "--type", "stock"], env=_env(CN_QUOTE_ENABLE_REAL_PROVIDER="1"), real_fetcher=_fake_real_fetcher(calls))
    assert result["data_status"] == "provider_policy_blocked"
    assert "CN_QUOTE_NETWORK_ENABLED" in result["reason"]
    assert result["has_real_market_data"] is False
    assert calls == []


@pytest.mark.parametrize("ci_var", ["CI", "GITHUB_ACTIONS"])
def test_real_is_blocked_in_ci(ci_var):
    calls = []
    env = _env(CN_QUOTE_ENABLE_REAL_PROVIDER="1", CN_QUOTE_NETWORK_ENABLED="1", CN_QUOTE_ALLOW_REAL_REQUEST="1", **{ci_var: "true"})
    result = run_smoke(["--real", "--code", "000001", "--type", "stock"], env=env, real_fetcher=_fake_real_fetcher(calls))
    assert result["data_status"] == "provider_policy_blocked"
    assert result["source_status"] == "provider_policy_blocked"
    assert "CI 环境禁止真实 provider 请求" in result["reason"]
    assert result["has_real_market_data"] is False
    assert calls == []


def test_real_with_all_gates_allows_injected_fake_provider_without_network():
    calls = []
    env = _env(CN_QUOTE_ENABLE_REAL_PROVIDER="1", CN_QUOTE_NETWORK_ENABLED="1", CN_QUOTE_ALLOW_REAL_REQUEST="1")
    result = run_smoke(["--real", "--code", "000001", "--type", "stock", "--no-save"], env=env, real_fetcher=_fake_real_fetcher(calls))
    assert result["data_status"] == "real_provider_available"
    assert result["has_real_market_data"] is True
    assert result["allow_commit_to_repo"] is False
    assert len(calls) == 1
    assert calls[0]["code"] == "000001"


def test_printed_output_contains_required_fields_and_redacts_sensitive_words(capsys):
    assert main(["--code", "000001", "--type", "stock", "--print-json"]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["provider"] == "akshare"
    assert "data_status" in payload
    assert "has_real_market_data" in payload
    assert payload["allow_commit_to_repo"] is False
    assert "Token" not in output
    assert "API Key" not in output
    assert "Webhook" not in output
    assert "secret" not in output.lower()
    redacted = json.dumps(redact_output({"Token": "abc", "API Key": "def", "Webhook": "ghi"}))
    assert "Token" not in redacted
    assert "API Key" not in redacted
    assert "Webhook" not in redacted
    assert "<redacted>" in redacted


def test_script_does_not_write_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = sorted(Path(tmp_path).iterdir())
    result = run_smoke(["--code", "000001", "--type", "stock"], env=_env())
    after = sorted(Path(tmp_path).iterdir())
    assert result["no_save"] is True
    assert before == after == []


@pytest.mark.parametrize("asset_type,expected", [("stock", "dry_run_only"), ("etf", "dry_run_only"), ("index", "dry_run_only")])
def test_supported_asset_types(asset_type, expected):
    result = run_smoke(["--code", "000001", "--type", asset_type], env=_env())
    assert result["data_status"] == expected
    assert result["has_real_market_data"] is False


@pytest.mark.parametrize("asset_type,expected", [("fund", "unsupported"), ("unknown", "invalid_request")])
def test_unsupported_and_unknown_asset_types(asset_type, expected):
    result = run_smoke(["--code", "000001", "--type", asset_type], env=_env())
    assert result["data_status"] == expected
    assert result["has_real_market_data"] is False
