import pytest

from src.account_groups import (
    AccountGroupConfigError,
    build_account_group_summary,
    get_account_group_by_id,
    get_assets_by_status,
    get_assets_by_type,
    get_visible_sections_for_account,
    load_example_account_groups,
    scan_account_group_for_sensitive_values,
    split_assets_by_type,
    validate_account_group,
    validate_account_group_config,
    validate_asset,
)


def test_loads_example_account_groups():
    config = load_example_account_groups()
    validate_account_group_config(config)
    assert config["config_version"] == 1
    assert {group["account_id"] for group in config["account_groups"]} >= {
        "demo_fund_group",
        "demo_stock_group",
        "demo_mixed_group",
    }


def test_example_config_contains_no_sensitive_personal_or_money_values():
    config = load_example_account_groups()
    assert scan_account_group_for_sensitive_values(config) == []
    serialized = str(config).lower()
    forbidden_fragments = [
        "email",
        "phone",
        "id_card",
        "身份证",
        "手机号",
        "amount",
        "cost_price",
        "account_value",
        "balance",
        "profit",
        "holding_amount",
        "position_amount",
        "webhook",
        "token",
        "api_key",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in serialized


def test_validates_required_account_group_fields():
    config = load_example_account_groups()
    group = get_account_group_by_id(config, "demo_fund_group")
    validate_account_group(group)
    assert group["account_id"]
    assert group["account_name"]
    assert group["enabled"] is True


@pytest.mark.parametrize("field", ["account_id", "account_name"])
def test_rejects_missing_account_required_string_fields(field):
    config = load_example_account_groups()
    group = dict(get_account_group_by_id(config, "demo_fund_group"))
    group[field] = ""
    with pytest.raises(AccountGroupConfigError):
        validate_account_group(group)


def test_rejects_non_boolean_enabled():
    config = load_example_account_groups()
    group = dict(get_account_group_by_id(config, "demo_fund_group"), enabled="true")
    with pytest.raises(AccountGroupConfigError):
        validate_account_group(group)


def test_validates_required_asset_fields():
    config = load_example_account_groups()
    asset = get_account_group_by_id(config, "demo_fund_group")["assets"][0]
    validate_asset(asset)
    for field in ["asset_id", "type", "code", "name", "market", "status"]:
        assert asset[field]


def test_type_must_be_allowed_value():
    config = load_example_account_groups()
    asset = dict(get_account_group_by_id(config, "demo_fund_group")["assets"][0], type="crypto")
    with pytest.raises(AccountGroupConfigError):
        validate_asset(asset)


@pytest.mark.parametrize("status", ["holding", "watching", "cleared", "archived"])
def test_status_allows_defined_values(status):
    config = load_example_account_groups()
    asset = dict(get_account_group_by_id(config, "demo_fund_group")["assets"][0], status=status)
    validate_asset(asset)


def test_status_rejects_unknown_value():
    config = load_example_account_groups()
    asset = dict(get_account_group_by_id(config, "demo_fund_group")["assets"][0], status="sold")
    with pytest.raises(AccountGroupConfigError):
        validate_asset(asset)


@pytest.mark.parametrize("weight_level", [1, 2, 3, 4, 5])
def test_weight_level_allows_one_to_five(weight_level):
    config = load_example_account_groups()
    asset = dict(get_account_group_by_id(config, "demo_fund_group")["assets"][0], weight_level=weight_level)
    validate_asset(asset)


@pytest.mark.parametrize("weight_level", [0, 6, "3"])
def test_weight_level_rejects_out_of_range_or_non_int(weight_level):
    config = load_example_account_groups()
    asset = dict(get_account_group_by_id(config, "demo_fund_group")["assets"][0], weight_level=weight_level)
    with pytest.raises(AccountGroupConfigError):
        validate_asset(asset)


def test_fund_group_visible_sections_contains_funds():
    config = load_example_account_groups()
    group = get_account_group_by_id(config, "demo_fund_group")
    assert get_visible_sections_for_account(group) == ["overview", "funds"]


def test_stock_group_visible_sections_contains_stocks():
    config = load_example_account_groups()
    group = get_account_group_by_id(config, "demo_stock_group")
    assert get_visible_sections_for_account(group) == ["overview", "stocks"]


def test_mixed_group_visible_sections_contains_funds_and_stocks():
    config = load_example_account_groups()
    group = get_account_group_by_id(config, "demo_mixed_group")
    assert get_visible_sections_for_account(group) == ["overview", "funds", "stocks"]


def test_empty_group_visible_sections_returns_empty_state():
    config = load_example_account_groups()
    group = get_account_group_by_id(config, "demo_empty_group")
    assert get_visible_sections_for_account(group) == ["empty_state"]


def test_cleared_and_archived_do_not_count_as_main_page_active_assets():
    group = {
        "account_id": "demo_inactive_group",
        "account_name": "示例非活跃分组",
        "enabled": True,
        "risk_profile": "balanced",
        "assets": [
            {
                "asset_id": "demo_cleared_fund",
                "type": "fund",
                "code": "000000",
                "name": "示例已清仓基金",
                "market": "CN",
                "tags": [],
                "status": "cleared",
                "weight_level": 1,
                "source_status": "manual_user_input",
            },
            {
                "asset_id": "demo_archived_stock",
                "type": "stock",
                "code": "000000",
                "name": "示例已归档股票",
                "market": "CN",
                "tags": [],
                "status": "archived",
                "weight_level": 1,
                "source_status": "manual_user_input",
            },
        ],
    }
    assert get_visible_sections_for_account(group) == ["empty_state"]
    summary = build_account_group_summary(group)
    assert summary["has_active_assets"] is False
    assert summary["has_funds"] is False
    assert summary["has_stocks"] is False


def test_filters_assets_by_type_and_status():
    config = load_example_account_groups()
    mixed = get_account_group_by_id(config, "demo_mixed_group")
    assert [asset["asset_id"] for asset in get_assets_by_type(mixed, "fund")] == ["demo_mixed_fund_001"]
    assert [asset["asset_id"] for asset in get_assets_by_type(mixed, "stock")] == ["demo_mixed_stock_001"]
    assert [asset["asset_id"] for asset in get_assets_by_status(mixed, "holding")] == ["demo_mixed_fund_001"]
    assert [asset["asset_id"] for asset in get_assets_by_status(mixed, "watching")] == ["demo_mixed_stock_001"]

    company = get_account_group_by_id(config, "demo_company_group")
    assert [asset["asset_id"] for asset in get_assets_by_status(company, "cleared")] == ["demo_industry_001"]
    assert [asset["asset_id"] for asset in get_assets_by_status(company, "archived")] == ["demo_theme_001"]


def test_split_assets_by_type_returns_stable_buckets():
    config = load_example_account_groups()
    group = get_account_group_by_id(config, "demo_company_group")
    buckets = split_assets_by_type(group)
    assert set(buckets) == {"fund", "stock", "company", "industry", "theme", "index"}
    assert [asset["asset_id"] for asset in buckets["company"]] == ["demo_company_001"]


def test_build_account_group_summary_outputs_counts_and_sections():
    config = load_example_account_groups()
    summary = build_account_group_summary(get_account_group_by_id(config, "demo_mixed_group"))
    assert summary == {
        "account_id": "demo_mixed_group",
        "account_name": "示例基金股票混合组",
        "enabled": True,
        "asset_counts": {
            "total": 2,
            "fund": 1,
            "stock": 1,
            "company": 0,
            "industry": 0,
            "theme": 0,
            "index": 0,
            "holding": 1,
            "watching": 1,
            "cleared": 0,
            "archived": 0,
        },
        "visible_sections": ["overview", "funds", "stocks"],
        "has_funds": True,
        "has_stocks": True,
        "has_active_assets": True,
        "warnings": [],
    }


def test_weight_level_is_not_misclassified_as_sensitive_money():
    config = load_example_account_groups()
    assert scan_account_group_for_sensitive_values({"weight_level": 5, "source_status": "manual_user_input"}) == []
    assert scan_account_group_for_sensitive_values(config) == []


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "demo@example.com"},
        {"phone": "13800138000"},
        {"id_card": "110105199001011234"},
        {"amount": 1000},
        {"cost_price": 1.23},
        {"account_value": 1000},
        {"balance": 1000},
        {"profit": 100},
        {"holding_amount": 1000},
        {"position_amount": 1000},
        {"notify": "https://example.com/webhook/abc"},
        {"token": "token=abcdefghijklmnop123456"},
        {"api_key": "api_key=abcdefghijklmnop123456"},
    ],
)
def test_sensitive_scanner_flags_forbidden_fields_and_values(payload):
    assert scan_account_group_for_sensitive_values(payload)
