import json

import pytest

from src.asset_model import AssetModelError
from src.quote_capability import (
    build_quote_capability,
    build_quote_capability_summary,
    get_price_mode,
    get_quote_capability,
    get_quote_capability_for_type,
    get_quote_display_label,
    supports_daily_nav,
    supports_exchange_quote,
    supports_intraday_estimate,
    supports_realtime_quote,
)


def asset(**overrides):
    base = {
        "asset_id": "demo_asset_001",
        "type": "fund",
        "code": "000000",
        "name": "示例资产",
        "market": "CN",
        "tags": ["示例"],
        "status": "holding",
        "weight_level": 3,
        "source_status": "manual_user_input",
    }
    base.update(overrides)
    return base


def payload_text(payload):
    return json.dumps(payload, ensure_ascii=False)


def test_stock_supports_realtime_quote_and_mode():
    stock = asset(type="stock", market="CN")
    capability = get_quote_capability(stock)
    assert capability["realtime_supported"] is True
    assert supports_realtime_quote(stock) is True
    assert capability["price_mode"] == "realtime_quote"
    assert get_price_mode(stock) == "realtime_quote"


def test_etf_supports_exchange_quote_and_mode():
    etf = asset(type="etf", market="CN")
    capability = get_quote_capability(etf)
    assert capability["exchange_quote_supported"] is True
    assert supports_exchange_quote(etf) is True
    assert capability["price_mode"] == "exchange_realtime_quote"


def test_index_uses_index_quote():
    assert get_quote_capability(asset(type="index", market="CN"))["price_mode"] == "index_quote"


def test_fund_uses_nav_capability_without_realtime_language():
    fund = asset(type="fund", market="CN")
    capability = get_quote_capability(fund)
    assert capability["realtime_supported"] is False
    assert supports_realtime_quote(fund) is False
    assert capability["daily_nav_supported"] is True
    assert supports_daily_nav(fund) is True
    assert capability["intraday_estimate_supported"] is True
    assert supports_intraday_estimate(fund) is True
    assert capability["price_mode"] == "estimated_nav_or_daily_nav"
    assert get_quote_display_label(fund) == "净值 / 估算净值"
    assert "实时涨跌" not in capability["display_label"]


@pytest.mark.parametrize("asset_type", ["company", "industry", "theme"])
def test_company_industry_theme_are_unsupported(asset_type):
    assert get_quote_capability(asset(type=asset_type))["price_mode"] == "unsupported"


def test_unknown_uses_unknown_mode():
    capability = get_quote_capability(asset(type="unknown", market="unknown"))
    assert capability["price_mode"] == "unknown"
    assert capability["realtime_supported"] is False


def test_get_quote_capability_for_type_normalizes_values():
    assert get_quote_capability_for_type(" STOCK ", "cn")["price_mode"] == "realtime_quote"


def test_build_quote_capability_shape_is_public_safe():
    payload = build_quote_capability(asset(asset_id="demo_stock_001", type="stock", code="000001", market="CN"))
    assert payload["asset_id"] == "demo_stock_001"
    assert payload["code"] == "000001"
    assert payload["type"] == "stock"
    assert payload["market"] == "CN"
    assert payload["quote_capability"]["needs_data_source"] is True


def test_build_quote_capability_summary_counts_correctly():
    summary = build_quote_capability_summary(
        [
            asset(asset_id="a1", type="stock", market="CN"),
            asset(asset_id="a2", type="etf", market="CN"),
            asset(asset_id="a3", type="fund", market="CN"),
            asset(asset_id="a4", type="company", market="CN"),
        ]
    )
    assert summary == {
        "total": 4,
        "realtime_supported_count": 2,
        "exchange_quote_supported_count": 2,
        "daily_nav_supported_count": 1,
        "intraday_estimate_supported_count": 1,
        "unsupported_count": 1,
        "by_price_mode": {
            "realtime_quote": 1,
            "exchange_realtime_quote": 1,
            "estimated_nav_or_daily_nav": 1,
            "unsupported": 1,
        },
        "warnings": [],
    }


def test_outputs_do_not_contain_private_or_quote_data_terms():
    output = build_quote_capability_summary([asset(type="stock"), asset(type="fund")])
    text = payload_text(output)
    forbidden_terms = ["真实金额", "成本价", "账户资产", "webhook", "token", "api_key", "API Key", "价格", "涨跌幅", "净值数据"]
    assert all(term not in text for term in forbidden_terms)


@pytest.mark.parametrize(
    "sensitive_payload",
    [
        {"amount": 1000},
        {"cost_price": 1.23},
        {"account_value": 9999},
        {"notes": "https://example.com/webhook/abc"},
        {"token": "token=abcdefghijklmnop123456"},
        {"api_key": "api_key=abcdefghijklmnop123456"},
    ],
)
def test_sensitive_asset_payloads_are_rejected(sensitive_payload):
    with pytest.raises(AssetModelError):
        build_quote_capability(asset(**sensitive_payload))
