import pytest

from src.fund_nav_real_provider import (
    FundNavRealProvider,
    build_fund_nav_real_provider_config,
    fetch_fund_nav_real,
    normalize_fund_nav_real_response,
    render_fund_nav_real_markdown,
    validate_fund_nav_real_provider_config,
    validate_fund_nav_real_result,
)

DEMO = {"asset_id": "demo_fund_001", "code": "000000", "name": "示例场外基金A", "type": "fund", "market": "CN"}
OPEN = {"network_enabled": True, "provider_enabled": True, "allow_real_request": True}


def _raw(**extra):
    data = {"nav": {"unit_nav": None, "accumulated_nav": None, "daily_change_pct": None, "nav_date": None}, "estimate": {"estimated_nav": None, "estimated_change_pct": None, "estimated_change_amount": None, "estimate_time": None}}
    data.update(extra)
    return data


def test_default_config_is_closed_and_does_not_call_fetcher():
    cfg = build_fund_nav_real_provider_config()
    assert cfg["network_enabled"] is False
    assert cfg["provider_enabled"] is False
    assert cfg["allow_real_request"] is False
    assert cfg["allow_commit_to_repo"] is False
    called = False
    def fake(_):
        nonlocal called; called = True; return _raw()
    result = FundNavRealProvider(fetcher=fake).fetch_one(DEMO)
    assert result["data_status"] in {"disabled_by_default", "provider_policy_blocked"}
    assert called is False
    assert result["will_fetch_real_data"] is False


def test_partial_gates_do_not_call_fetcher():
    called = False
    def fake(_):
        nonlocal called; called = True; return _raw()
    result = FundNavRealProvider(config={"network_enabled": True}, fetcher=fake).fetch_one(DEMO)
    assert result["data_status"] == "disabled_by_default"
    assert called is False


def test_all_gates_open_calls_fake_fetcher_and_normalizes_available():
    calls = []
    def fake(req):
        calls.append(req); return _raw()
    result = FundNavRealProvider(config=OPEN, fetcher=fake).fetch_one(DEMO)
    assert calls
    assert result["data_status"] == "real_provider_available"
    assert result["has_real_nav_data"] is True
    assert result["allow_commit_to_repo"] is False
    assert result["provider_checks"]["network_enabled"] is True
    assert result["source"]["checked_at"]
    assert result["source"]["source_status"] == "real_provider"
    assert validate_fund_nav_real_result(result) == []


@pytest.mark.parametrize("asset_type,status", [("stock", "unsupported"), ("etf", "unsupported"), ("index", "unsupported"), ("company", "unsupported"), ("industry", "unsupported"), ("theme", "unsupported"), ("computed_indicator", "unsupported"), ("unknown", "invalid_request")])
def test_unsupported_asset_types(asset_type, status):
    item = {**DEMO, "type": asset_type}
    result = FundNavRealProvider(config=OPEN, fetcher=lambda _: _raw()).fetch_one(item)
    assert result["data_status"] == status


def test_non_cn_fund_is_unsupported():
    result = FundNavRealProvider(config=OPEN, fetcher=lambda _: _raw()).fetch_one({**DEMO, "market": "US"})
    assert result["data_status"] == "unsupported"


def test_fetcher_errors_are_structured():
    def boom(_):
        raise RuntimeError("demo failure")
    def timeout(_):
        raise TimeoutError("demo timeout")
    assert FundNavRealProvider(config=OPEN, fetcher=boom).fetch_one(DEMO)["data_status"] == "provider_error"
    assert FundNavRealProvider(config=OPEN, fetcher=timeout).fetch_one(DEMO)["data_status"] == "provider_timeout"
    assert FundNavRealProvider(config=OPEN).fetch_one(DEMO)["data_status"] == "provider_error"


def test_invalid_stale_conflict_and_partial_responses():
    req = {**DEMO, "request_id": "demo_fund_001", "provider_name": "eastmoney_fund"}
    assert normalize_fund_nav_real_response({}, req, "eastmoney_fund")["data_status"] == "invalid_response"
    assert normalize_fund_nav_real_response({"source_status": "stale"}, req, "eastmoney_fund")["data_status"] == "stale_data"
    assert normalize_fund_nav_real_response({"source_status": "conflict"}, req, "eastmoney_fund")["data_status"] == "conflict"
    assert normalize_fund_nav_real_response({"nav": _raw()["nav"]}, req, "eastmoney_fund")["data_status"] == "estimate_unavailable"
    assert normalize_fund_nav_real_response({"estimate": _raw()["estimate"]}, req, "eastmoney_fund")["data_status"] == "daily_nav_unavailable"


def test_provider_safety_blocks_plaintext_secret_fields():
    cfg = build_fund_nav_real_provider_config()
    for key in ("token", "api_key", "webhook"):
        bad = {**cfg, key: "demo-secret"}
        assert "real provider config contains secret fields" in validate_fund_nav_real_provider_config(bad)


def test_markdown_is_safe_and_contains_required_disclaimers():
    result = fetch_fund_nav_real(DEMO)
    markdown = render_fund_nav_real_markdown(result)
    assert "真实基金净值 provider 默认关闭" in markdown
    assert "最终以基金公司公布净值为准" in markdown
    assert "CI 测试不会请求真实基金净值" in markdown
    assert "已接入真实基金净值" not in markdown
    for forbidden in ("真实单位净值", "真实估算净值", "真实涨跌幅", "token", "api_key", "webhook", "Token", "API Key", "Webhook"):
        assert forbidden not in markdown
