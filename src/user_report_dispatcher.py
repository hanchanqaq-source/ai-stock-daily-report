# -*- coding: utf-8 -*-
"""Public-safe dry-run delivery planning for multi-user reports.

This module only reads committed example configuration by default, builds a
structured delivery plan, and never sends Discord messages or reads webhook
values. It is intentionally not wired into daily or weekly report runtimes.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from src.personal_radar import build_personal_radar_for_user
from src.user_config import EXAMPLE_CONFIG_DIR, OUTPUT_MODES, load_user_config, scan_config_for_sensitive_values

DELIVERY_PLAN_VERSION = 1

def build_delivery_plan(config_dir: str | Path | None = None, dry_run: bool = True) -> dict[str, Any]:
    """Build a structured dry-run delivery plan from example configuration."""
    config = _load_example_only(config_dir)
    users_out: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocked_targets: list[dict[str, Any]] = []
    groups_by_id = {g.get("task_group_id"): g for g in config.get("task_groups", {}).get("task_groups", []) if isinstance(g, Mapping)}

    for user in config.get("users", {}).get("users", []):
        if not isinstance(user, Mapping):
            continue
        user_plan = _base_user_plan(user)
        if not user.get("enabled", False):
            user_plan["status"] = "skipped"
            user_plan["skip_reason"] = "用户未启用。"
            warnings.append(f"用户未启用：{user.get('user_id')}")
            users_out.append(user_plan)
            continue
        for group_id in user.get("task_group_ids", []):
            group = groups_by_id.get(group_id)
            if not group:
                blocked_targets.append({"user_id": user.get("user_id"), "task_group_id": group_id, "reason": "未找到任务组配置。"})
                continue
            group_plan = _build_group_plan(user, group, dry_run=dry_run)
            user_plan["task_groups"].append(group_plan)
            blocked_targets.extend(group_plan.pop("_blocked_targets", []))
        users_out.append(user_plan)

    plan = {
        "delivery_plan_version": DELIVERY_PLAN_VERSION,
        "status": "available" if users_out else "insufficient_data",
        "dry_run": bool(dry_run),
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat(),
        "source": "example_config",
        "users": users_out,
        "warnings": warnings,
        "blocked_targets": blocked_targets,
    }
    validation = validate_delivery_plan(plan)
    plan["validation"] = validation
    if not validation["valid"]:
        plan["status"] = "insufficient_data"
    return plan


def build_delivery_plan_for_user(user_id: str, config_dir: str | Path | None = None, dry_run: bool = True) -> dict[str, Any]:
    """Build a delivery plan containing only one example user."""
    plan = build_delivery_plan(config_dir=config_dir, dry_run=dry_run)
    plan["users"] = [u for u in plan.get("users", []) if u.get("user_id") == user_id]
    if not plan["users"]:
        plan["status"] = "insufficient_data"
        plan["warnings"].append(f"未找到示例用户：{user_id}")
    return plan


def build_delivery_target(user: Mapping[str, Any], task_group: Mapping[str, Any], dry_run: bool = True) -> dict[str, Any]:
    """Build a dry-run delivery target for one user and task group."""
    output_mode = task_group.get("output_mode")
    base = {"enabled": True, "dry_run": bool(dry_run), "secret_required": False, "secret_name": None, "will_send": False}
    if output_mode == "public_summary_only":
        return {**base, "target_type": "public_summary", "reason": "public_summary_only 当前仅生成公开摘要 dry-run 计划。"}
    if output_mode == "local_private_report":
        return {**base, "target_type": "local_report", "reason": "local_private_report 当前 public 阶段不写真实私人报告，仅生成 dry-run 计划。"}
    if output_mode == "private_discord_channel":
        secret_name = user.get("discord_webhook_secret_name") or task_group.get("discord_webhook_secret_name")
        return {**base, "target_type": "private_discord", "secret_required": True, "secret_name": secret_name, "enabled": bool(secret_name), "reason": "private_discord_channel 当前只记录 Secret 名称，不读取 webhook，不发送。"}
    return {**base, "target_type": "unsupported", "enabled": False, "reason": f"不支持的 output_mode：{output_mode}"}


def validate_delivery_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Validate safety invariants for a delivery plan."""
    findings = scan_config_for_sensitive_values(plan)
    errors = []
    if findings:
        errors.extend(findings)
    for user in plan.get("users", []):
        for group in user.get("task_groups", []):
            for target in group.get("delivery_targets", []):
                if target.get("will_send") is not False:
                    errors.append(f"will_send must be false for {user.get('user_id')}/{group.get('task_group_id')}")
                secret_name = target.get("secret_name")
                if isinstance(secret_name, str) and secret_name.startswith(("http://", "https://")):
                    errors.append(f"webhook URL is not allowed in secret_name for {user.get('user_id')}")
    return {"valid": not errors, "warnings": errors}


def render_delivery_plan_markdown(plan: Mapping[str, Any]) -> str:
    """Render a public-safe demo Markdown summary without writing files."""
    lines = [
        "# 多用户报告分发计划 Demo", "", "## 1. 分发状态", "",
        f"- 当前模式：{'dry-run' if plan.get('dry_run', True) else 'non-send preview'}",
        "- 配置来源：example", "- 是否真实发送：否", "- 是否读取真实 webhook：否", "",
        "## 2. 用户分发计划", "",
    ]
    for user in plan.get("users", []):
        lines.extend([f"- 用户 ID：{user.get('user_id')}", f"  - 显示名称：{user.get('display_name') or '-'}", f"  - 启用状态：{user.get('enabled')}"])
        if user.get("status") == "skipped":
            lines.append(f"  - 跳过原因：{user.get('skip_reason')}")
        for group in user.get("task_groups", []):
            lines.extend([f"  - 任务组：{group.get('task_group_name') or group.get('task_group_id')}", f"    - 输出模式：{group.get('output_mode')}"])
            for target in group.get("delivery_targets", []):
                lines.extend([f"    - 分发目标：{target.get('target_type')}", "    - 是否会发送：否", f"    - 原因：{target.get('reason')}"])
    lines.extend(["", "## 3. 阻止项 / 警告", ""])
    warnings = list(plan.get("warnings", [])) + list((plan.get("validation") or {}).get("warnings", []))
    blocked = plan.get("blocked_targets", [])
    if not warnings and not blocked:
        lines.append("- 暂无阻止项或警告。")
    lines.extend(f"- {item}" for item in warnings)
    lines.extend(f"- {item.get('reason')}（user={item.get('user_id')}, task_group={item.get('task_group_id')}）" for item in blocked)
    lines.extend(["", "## 4. 安全说明", "", "当前为示例 dry-run。不会真实发送 Discord。不会保存真实用户数据。不会保存金额、成本价、账户资产。真实配置应放本地或 private 仓库。"])
    return "\n".join(lines).rstrip() + "\n"


def load_demo_delivery_plan() -> dict[str, Any]:
    """Load a demo delivery plan for the committed public example config."""
    return build_delivery_plan(config_dir=EXAMPLE_CONFIG_DIR, dry_run=True)


def _base_user_plan(user: Mapping[str, Any]) -> dict[str, Any]:
    return {"user_id": user.get("user_id"), "display_name": user.get("display_name"), "enabled": bool(user.get("enabled", False)), "status": "available", "task_groups": []}


def _build_group_plan(user: Mapping[str, Any], group: Mapping[str, Any], dry_run: bool) -> dict[str, Any]:
    group_plan = {"task_group_id": group.get("task_group_id"), "task_group_name": group.get("name"), "enabled": bool(group.get("enabled", False)), "status": "available", "output_mode": group.get("output_mode"), "report_types": list(group.get("report_types", [])), "delivery_targets": [], "personal_radar_status": "insufficient_data", "notes": [], "_blocked_targets": []}
    if not group.get("enabled", False):
        group_plan.update({"status": "skipped", "notes": ["任务组未启用。"]})
        return group_plan
    target = build_delivery_target(user, group, dry_run=dry_run)
    group_plan["delivery_targets"].append(target)
    if group.get("output_mode") not in OUTPUT_MODES:
        group_plan["_blocked_targets"].append({"user_id": user.get("user_id"), "task_group_id": group.get("task_group_id"), "reason": "output_mode 不支持。"})
    if target.get("target_type") == "private_discord" and not target.get("secret_name"):
        group_plan["_blocked_targets"].append({"user_id": user.get("user_id"), "task_group_id": group.get("task_group_id"), "target_type": "private_discord", "reason": "缺少 secret name，不能推送。"})
    radar = build_personal_radar_for_user(str(user.get("user_id") or ""), config_dir=EXAMPLE_CONFIG_DIR)
    group_plan["personal_radar_status"] = radar.get("status", "insufficient_data")
    return group_plan


def _load_example_only(config_dir: str | Path | None) -> dict[str, Any]:
    base = Path(config_dir) if config_dir is not None else EXAMPLE_CONFIG_DIR
    if base != EXAMPLE_CONFIG_DIR and base.name != "examples":
        return {"users": {"config_version": 1, "users": []}, "task_groups": {"config_version": 1, "task_groups": []}, "watchlists": {"config_version": 1, "watchlists": []}}
    return load_user_config(base)
