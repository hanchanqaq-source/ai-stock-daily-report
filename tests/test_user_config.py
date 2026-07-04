import json
from pathlib import Path

import pytest

from src.user_config import (
    UserConfigError,
    get_enabled_users,
    get_task_group_by_id,
    get_watchlist_by_id,
    load_example_user_config,
    load_user_config,
    scan_config_for_sensitive_values,
    validate_task_groups,
    validate_user_config,
    validate_watchlists,
)


def test_loads_example_config_sections():
    config = load_example_user_config()

    assert config["users"]["users"][0]["user_id"] == "demo_public_user"
    assert config["task_groups"]["task_groups"][0]["task_group_id"] == "demo_ai_hardware"
    assert config["watchlists"]["watchlists"][0]["watchlist_id"] == "demo_ai_hardware_watchlist"


def test_enabled_users_and_lookup_helpers():
    config = load_example_user_config()

    users = get_enabled_users(config)
    assert [user["user_id"] for user in users] == ["demo_public_user"]
    assert get_task_group_by_id(config, "demo_ai_hardware")["name"] == "示例 AI 硬件观察组"
    assert get_watchlist_by_id(config, "demo_ai_hardware_watchlist")["name"] == "示例 AI 硬件关注列表"
    assert get_task_group_by_id(config, "missing") is None
    assert get_watchlist_by_id(config, "missing") is None


def test_missing_private_config_dir_returns_empty_config(tmp_path):
    config = load_user_config(tmp_path / "missing")

    assert config["users"]["users"] == []
    assert config["task_groups"]["task_groups"] == []
    assert config["watchlists"]["watchlists"] == []


def test_example_config_contains_no_sensitive_values():
    config = load_example_user_config()

    findings = scan_config_for_sensitive_values(config)
    assert findings == []
    serialized = json.dumps(config, ensure_ascii=False)
    assert "webhook" not in serialized.lower() or "https://" not in serialized.lower()
    assert "ghp_" not in serialized
    assert "sk-" not in serialized


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"url": "https://discord.com/api/webhooks/123/abc"}, "webhook URL"),
        ({"token": "ghp_abcdefghijklmnopqrstuvwxyz123456"}, "GitHub token"),
        ({"api_key": "sk-proj-abcdefghijklmnopqrstuvwxyz123456"}, "OpenAI API key"),
        ({"email": "demo@example.com"}, "email"),
        ({"phone": "13800138000"}, "phone number"),
        ({"id": "110105199001011234"}, "Chinese ID number"),
        ({"cost_price": 12.34}, "sensitive money/account field"),
        ({"account_balance": 10000}, "sensitive money/account field"),
    ],
)
def test_sensitive_scan_detects_private_values(payload, expected):
    findings = scan_config_for_sensitive_values(payload)

    assert any(expected in finding for finding in findings)


def test_gitignore_ignores_real_user_config_but_keeps_examples():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "data/user_config/*.json" in gitignore
    assert "data/user_config/**/*.json" in gitignore
    assert "!config/examples/*.example.json" in gitignore
    assert "!data/user_config/*.example.json" in gitignore


def test_validation_errors_are_clear():
    with pytest.raises(UserConfigError, match="Invalid risk_profile"):
        validate_user_config({"config_version": 1, "users": [{"user_id": "demo", "risk_profile": "hot", "enabled": True}]})

    with pytest.raises(UserConfigError, match="Invalid output_mode"):
        validate_task_groups(
            {
                "config_version": 1,
                "task_groups": [
                    {
                        "task_group_id": "demo",
                        "type": "industry_tracking",
                        "enabled": True,
                        "report_types": ["daily"],
                        "output_mode": "private_url",
                    }
                ],
            }
        )

    with pytest.raises(UserConfigError, match="Invalid item type"):
        validate_watchlists(
            {
                "config_version": 1,
                "watchlists": [
                    {
                        "watchlist_id": "demo",
                        "items": [{"type": "holding", "name": "demo", "code": None, "tags": []}],
                    }
                ],
            }
        )
