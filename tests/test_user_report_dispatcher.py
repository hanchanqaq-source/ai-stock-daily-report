import json
from pathlib import Path

from src.user_config import scan_config_for_sensitive_values
from src.user_report_dispatcher import (
    build_delivery_plan,
    build_delivery_plan_for_user,
    build_delivery_target,
    load_demo_delivery_plan,
    render_delivery_plan_markdown,
    validate_delivery_plan,
)


def _write_config(base: Path, users, groups, watchlists=None):
    base.mkdir(parents=True, exist_ok=True)
    (base / "users.json").write_text(json.dumps({"config_version": 1, "users": users}, ensure_ascii=False), encoding="utf-8")
    (base / "task_groups.json").write_text(json.dumps({"config_version": 1, "task_groups": groups}, ensure_ascii=False), encoding="utf-8")
    (base / "watchlists.json").write_text(json.dumps({"config_version": 1, "watchlists": watchlists or []}, ensure_ascii=False), encoding="utf-8")


def _user(**overrides):
    data = {"user_id": "demo_public_user", "display_name": "示例用户", "risk_profile": "balanced", "enabled": True, "task_group_ids": ["g1"], "discord_webhook_secret_name": "DISCORD_WEBHOOK_DEMO_USER"}
    data.update(overrides)
    return data


def _group(**overrides):
    data = {"task_group_id": "g1", "name": "示例任务组", "type": "industry_tracking", "enabled": True, "watchlist_id": "w1", "report_types": ["daily", "weekly"], "output_mode": "public_summary_only"}
    data.update(overrides)
    return data


def test_demo_config_builds_structured_delivery_plan():
    plan = load_demo_delivery_plan()
    assert plan["delivery_plan_version"] == 1
    assert plan["dry_run"] is True
    assert plan["source"] == "example_config"
    assert plan["users"][0]["user_id"] == "demo_public_user"
    target = plan["users"][0]["task_groups"][0]["delivery_targets"][0]
    assert target["target_type"] == "public_summary"
    assert target["will_send"] is False
    assert plan["validation"]["valid"] is True


def test_disabled_user_is_skipped(tmp_path):
    base = tmp_path / "examples"
    _write_config(base, [_user(enabled=False)], [_group()])
    plan = build_delivery_plan(base)
    assert plan["users"][0]["status"] == "skipped"
    assert plan["users"][0]["task_groups"] == []


def test_disabled_task_group_is_skipped(tmp_path):
    base = tmp_path / "examples"
    _write_config(base, [_user()], [_group(enabled=False)])
    group = build_delivery_plan(base)["users"][0]["task_groups"][0]
    assert group["status"] == "skipped"
    assert group["delivery_targets"] == []


def test_output_modes_create_expected_dry_run_targets(tmp_path):
    base = tmp_path / "examples"
    users = [_user(task_group_ids=["public", "local", "discord"])]
    groups = [
        _group(task_group_id="public", output_mode="public_summary_only"),
        _group(task_group_id="local", output_mode="local_private_report"),
        _group(task_group_id="discord", output_mode="private_discord_channel"),
    ]
    _write_config(base, users, groups)
    targets = [g["delivery_targets"][0] for g in build_delivery_plan(base)["users"][0]["task_groups"]]
    assert [t["target_type"] for t in targets] == ["public_summary", "local_report", "private_discord"]
    assert all(t["will_send"] is False for t in targets)
    assert targets[2]["secret_name"] == "DISCORD_WEBHOOK_DEMO_USER"
    assert "http" not in json.dumps(targets, ensure_ascii=False).lower()


def test_private_discord_missing_secret_is_blocked(tmp_path):
    base = tmp_path / "examples"
    _write_config(base, [_user(discord_webhook_secret_name=None)], [_group(output_mode="private_discord_channel")])
    plan = build_delivery_plan(base)
    assert plan["blocked_targets"][0]["reason"] == "缺少 secret name，不能推送。"
    assert plan["users"][0]["task_groups"][0]["delivery_targets"][0]["will_send"] is False


def test_validate_delivery_plan_rejects_webhook_url_and_will_send():
    plan = {"users": [{"user_id": "u", "task_groups": [{"task_group_id": "g", "delivery_targets": [{"will_send": True, "secret_name": "https://discord.com/api/webhooks/bad"}]}]}]}
    result = validate_delivery_plan(plan)
    assert result["valid"] is False
    assert any("webhook" in item.lower() for item in result["warnings"])
    assert any("will_send" in item for item in result["warnings"])


def test_markdown_demo_renders_safety_language():
    markdown = render_delivery_plan_markdown(load_demo_delivery_plan())
    assert "# 多用户报告分发计划 Demo" in markdown
    assert "不会真实发送 Discord" in markdown
    assert "不会保存金额、成本价、账户资产" in markdown
    assert not scan_config_for_sensitive_values(markdown)


def test_does_not_read_real_user_config_dir(tmp_path):
    real_dir = tmp_path / "data" / "user_config"
    _write_config(real_dir, [_user(user_id="real_user")], [_group()])
    plan = build_delivery_plan(real_dir)
    assert plan["users"] == []
    assert build_delivery_plan_for_user("real_user", config_dir=real_dir)["status"] == "insufficient_data"


def test_build_delivery_target_never_reads_secret_value():
    target = build_delivery_target(_user(discord_webhook_secret_name="DISCORD_WEBHOOK_DEMO_USER"), _group(output_mode="private_discord_channel"), dry_run=False)
    assert target["dry_run"] is False
    assert target["will_send"] is False
    assert target["secret_name"] == "DISCORD_WEBHOOK_DEMO_USER"
