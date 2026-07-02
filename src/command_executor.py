# -*- coding: utf-8 -*-
"""Execution layer for reserved Discord report commands."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from src.github_dispatcher import build_repository_dispatch_payload, send_repository_dispatch
from src.notification import DISCORD_OPERATION_PANEL, parse_discord_command_text

logger = logging.getLogger(__name__)

_ALLOWED_ACTIONS = {"resend_latest", "rerun_report", "help", "unknown"}
_ALLOWED_RUN_MODES = {"full", "market-only", "stocks-only"}
_ALLOWED_MODEL_PROFILES = {"free", "daily", "pro", "auto", "final"}


@dataclass(frozen=True)
class CommandExecutionResult:
    action: str
    status: str
    message: str
    reply_text: str
    command_text: str
    request_id: Optional[str] = None
    run_mode: Optional[str] = None
    model_profile: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    parsed_command: Dict[str, Any] = field(default_factory=dict)


def execute_command_text(
    command_text: str,
    *,
    dry_run: bool = False,
    request_id: Optional[str] = None,
) -> CommandExecutionResult:
    """Parse and execute a reserved channel command without running user input."""
    raw_text = str(command_text or "")
    safe_log_text = _truncate_log_text(raw_text)
    parsed = parse_discord_command_text(raw_text)
    action = _safe_choice(parsed.get("action"), _ALLOWED_ACTIONS, "unknown")
    run_mode = _safe_choice(parsed.get("run_mode"), _ALLOWED_RUN_MODES, "full")
    model_profile = _safe_choice(parsed.get("model_profile"), _ALLOWED_MODEL_PROFILES, "daily")

    logger.info("Executing channel command action=%s dry_run=%s command_text=%s", action, dry_run, safe_log_text)

    if action == "unknown":
        return CommandExecutionResult(
            action=action,
            status="unknown_command",
            message="无法识别指令，请发送“@AI日报助手 帮助”",
            reply_text="❓ 未识别指令\n可发送：@AI日报助手 帮助",
            command_text=raw_text,
            parsed_command=parsed,
        )

    if action == "help":
        return CommandExecutionResult(
            action=action,
            status="ok",
            message="显示帮助信息",
            reply_text=DISCORD_OPERATION_PANEL,
            command_text=raw_text,
            run_mode=run_mode,
            model_profile=model_profile,
            parsed_command=parsed,
        )

    if action == "resend_latest":
        return CommandExecutionResult(
            action=action,
            status="planned",
            message="重推功能需要最近一次成功日报缓存/文件，后续 Bot 接入时启用",
            reply_text="✅ 已收到命令：重推\n📌 当前版本已识别重推指令，实际重发将在 Discord Bot 接入后启用。",
            command_text=raw_text,
            run_mode=run_mode,
            model_profile=model_profile,
            parsed_command=parsed,
        )

    resolved_request_id = _resolve_request_id(request_id)
    payload = build_repository_dispatch_payload(
        run_mode=run_mode,
        model_profile=model_profile,
        request_id=resolved_request_id,
        command_text=raw_text,
    )
    logger.info("Prepared rerun dispatch request_id=%s run_mode=%s model_profile=%s", resolved_request_id, run_mode, model_profile)

    if dry_run:
        return CommandExecutionResult(
            action=action,
            status="dry_run",
            message="Dry run：已生成 GitHub Actions 重跑请求，但未发送",
            reply_text=f"🧪 Dry run：已生成 GitHub Actions 重跑请求，但未发送\n🆔 request_id: {resolved_request_id}",
            command_text=raw_text,
            request_id=resolved_request_id,
            run_mode=run_mode,
            model_profile=model_profile,
            payload=payload,
            parsed_command=parsed,
        )

    dispatch_result = send_repository_dispatch(payload)
    if dispatch_result.status == "submitted":
        reply_text = (
            f"✅ 已收到命令：{_display_command(raw_text)}\n"
            "📦 已提交到 GitHub Actions\n"
            f"🆔 request_id: {resolved_request_id}\n"
            f"模式：{run_mode}\n"
            f"档位：{model_profile}"
        )
    elif dispatch_result.status == "missing_token":
        reply_text = "❌ 重跑提交失败：缺少 GITHUB_DISPATCH_TOKEN\n请在运行环境配置 GitHub dispatch token。"
    else:
        reply_text = f"❌ 重跑提交失败：{dispatch_result.message}\n🆔 request_id: {resolved_request_id}"

    return CommandExecutionResult(
        action=action,
        status=dispatch_result.status,
        message=dispatch_result.message,
        reply_text=reply_text,
        command_text=raw_text,
        request_id=resolved_request_id,
        run_mode=run_mode,
        model_profile=model_profile,
        payload=payload,
        parsed_command=parsed,
    )


def _resolve_request_id(request_id: Optional[str]) -> str:
    value = str(request_id or "").strip()
    if value:
        return value
    return datetime.now().strftime("discord-%Y%m%d-%H%M%S")


def _safe_choice(value: Any, allowed: set[str], default: str) -> str:
    text = str(value or "").strip()
    return text if text in allowed else default


def _truncate_log_text(text: str, limit: int = 120) -> str:
    value = str(text or "")
    return value if len(value) <= limit else f"{value[:limit]}..."


def _display_command(command_text: str) -> str:
    text = str(command_text or "").strip()
    return text.replace("@AI日报助手", "").strip() or text[:120]
