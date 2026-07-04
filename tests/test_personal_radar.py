import json
from pathlib import Path

import pytest

from src.personal_radar import (
    analyze_watchlist_item_impact,
    build_personal_radar_for_user,
    load_demo_personal_radar,
    match_item_tags_to_market_signals,
    render_personal_radar_markdown,
)
from src.user_config import scan_config_for_sensitive_values


@pytest.fixture
def market_context():
    return {
        "status": "available",
        "data_date": "2026-07-03",
        "signals": {
            "persistent_leaders": ["半导体"],
            "short_term_breakouts": ["PCB"],
            "rotation_candidates": ["AI硬件"],
            "pullback_risks": ["AI硬件"],
            "persistent_laggers": ["企业观察"],
            "risk_radar": ["PCB"],
            "watchlist_diffusion": ["半导体"],
            "warming": ["半导体"],
        },
        "data_warnings": [],
    }


def test_demo_user_builds_personal_radar_from_example_config():
    radar = load_demo_personal_radar()

    assert radar["radar_version"] == 1
    assert radar["user_id"] == "demo_public_user"
    assert radar["task_group_id"] == "demo_ai_hardware"
    assert radar["watchlist_id"] == "demo_ai_hardware_watchlist"
    assert isinstance(radar["items"], list)
    assert "示例" in render_personal_radar_markdown(radar)


def test_tag_match_generates_positive_risk_and_neutral_signals(market_context):
    item = {"type": "fund", "name": "示例基金A", "code": "000000", "tags": ["半导体", "PCB", "AI硬件"]}

    signals = match_item_tags_to_market_signals(item, market_context)

    assert any(s["signal_type"] == "positive_signal" and s["tag"] == "半导体" for s in signals)
    assert any(s["signal_type"] == "risk_signal" and s["tag"] in {"PCB", "AI硬件"} for s in signals)
    assert any(s["signal_type"] == "neutral_signal" and s["tag"] in {"PCB", "AI硬件"} for s in signals)
    assert all(s.get("source") for s in signals)
    assert all(s.get("reason") for s in signals)


def test_item_without_history_returns_insufficient_data():
    item = {"type": "stock", "name": "示例股票A", "code": "000000", "tags": ["半导体"]}

    result = analyze_watchlist_item_impact(item, {"status": "insufficient_data", "signals": {}})

    assert result["impact_level"] == "数据不足"
    assert result["signals"][0]["signal_type"] == "insufficient_data"


def test_missing_real_config_dir_is_safe_and_empty(tmp_path):
    missing = tmp_path / "data" / "user_config"

    radar = build_personal_radar_for_user("demo_public_user", config_dir=missing)

    assert radar["status"] == "insufficient_data"
    assert radar["items"] == []


def test_does_not_read_real_user_config_dir(tmp_path):
    real_dir = tmp_path / "data" / "user_config"
    real_dir.mkdir(parents=True)
    (real_dir / "users.json").write_text(
        json.dumps({"config_version": 1, "users": [{"user_id": "real_user", "display_name": "Real", "risk_profile": "balanced", "enabled": True, "task_group_ids": []}]}),
        encoding="utf-8",
    )

    radar = build_personal_radar_for_user("real_user", config_dir=real_dir)

    assert radar["status"] == "insufficient_data"
    assert radar["user_id"] == "real_user"
    assert radar["items"] == []


def test_output_contains_no_sensitive_or_trading_advice_terms(market_context):
    result = analyze_watchlist_item_impact(
        {"type": "fund", "name": "示例基金A", "code": "000000", "tags": ["半导体", "PCB"]}, market_context
    )
    markdown = render_personal_radar_markdown({
        "user_id": "demo_public_user",
        "task_group_id": "demo_ai_hardware",
        "watchlist_id": "demo_ai_hardware_watchlist",
        "items": [result],
        "overall_watch_points": result["watch_points"],
        "data_warnings": [],
    })
    serialized = json.dumps(result, ensure_ascii=False) + markdown

    assert scan_config_for_sensitive_values(result) == []
    banned_terms = [
        "https://discord.com/api/webhooks/",
        "ghp_",
        "sk-",
        "api_key",
        "token=",
        "金额",
        "成本价",
        "账户资产",
        "买入",
        "卖出",
        "加仓",
        "减仓",
    ]
    assert not any(term in serialized for term in banned_terms)


def test_script_exists_without_persisting_reports():
    script = Path("scripts/run_personal_radar_demo.py")

    assert script.exists()
    assert "write_text" not in script.read_text(encoding="utf-8")
