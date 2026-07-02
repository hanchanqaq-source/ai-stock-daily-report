# -*- coding: utf-8 -*-
"""Standalone Discord channel command listener.

This module is intentionally not imported by ``main.py`` or any scheduled
workflow. Run it manually with ``python -m src.discord_command_bot`` after
configuring the required Discord and GitHub dispatch environment variables.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Set

from src.command_executor import CommandExecutionResult, execute_command_text
from src.github_dispatcher import mask_token
from src.notification import DISCORD_OPERATION_PANEL

logger = logging.getLogger(__name__)

BOT_DISPLAY_NAME = "AI日报助手"
MAX_LOG_COMMAND_TEXT = 120

Executor = Callable[..., CommandExecutionResult]


@dataclass(frozen=True)
class DiscordCommandResponse:
    """Result of evaluating one Discord message."""

    should_reply: bool
    reply_text: Optional[str] = None
    reason: str = "ignored"
    command_text: str = ""


def parse_allowed_channel_ids(raw_value: Optional[str] = None) -> Set[str]:
    """Parse comma-separated Discord channel IDs from env/config text."""
    value = os.getenv("DISCORD_COMMAND_CHANNEL_IDS") if raw_value is None else raw_value
    return {part.strip() for part in str(value or "").split(",") if part.strip()}


def truncate_log_text(text: str, limit: int = MAX_LOG_COMMAND_TEXT) -> str:
    """Return a log-safe command preview capped to ``limit`` characters."""
    value = str(text or "")
    return value if len(value) <= limit else f"{value[:limit]}..."


def handle_discord_message(
    content: str,
    *,
    author_is_bot: bool,
    channel_id: str,
    mentioned_bot: bool,
    allowed_channel_ids: Iterable[str],
    executor: Executor = execute_command_text,
) -> DiscordCommandResponse:
    """Validate and execute a Discord channel command without Discord I/O."""
    channel = str(channel_id or "").strip()
    allowed = {str(item).strip() for item in allowed_channel_ids if str(item).strip()}
    raw_text = str(content or "")

    if author_is_bot:
        return DiscordCommandResponse(False, reason="author_is_bot")
    if not allowed or channel not in allowed:
        return DiscordCommandResponse(False, reason="channel_not_allowed")
    if not mentioned_bot and f"@{BOT_DISPLAY_NAME}" not in raw_text:
        return DiscordCommandResponse(False, reason="bot_not_mentioned")

    if not _command_body(raw_text):
        return DiscordCommandResponse(True, reply_text=DISCORD_OPERATION_PANEL, reason="help", command_text=raw_text)

    logger.info("Handling Discord command channel_id=%s command_text=%s", channel, truncate_log_text(raw_text))
    try:
        result = executor(raw_text, dry_run=False)
    except Exception as exc:  # pragma: no cover - defensive boundary for real bot runtime
        logger.exception("Discord command execution failed channel_id=%s error=%s", channel, exc)
        return DiscordCommandResponse(
            True,
            reply_text="❌ 指令处理失败，请稍后重试。",
            reason="executor_error",
            command_text=raw_text,
        )
    return DiscordCommandResponse(True, reply_text=result.reply_text, reason=result.status, command_text=raw_text)


def run_bot() -> None:
    """Start the standalone Discord listener."""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    token = (os.getenv("DISCORD_BOT_TOKEN") or "").strip()
    allowed_channel_ids = parse_allowed_channel_ids()

    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required to start the Discord command bot")
    if not allowed_channel_ids:
        raise RuntimeError("DISCORD_COMMAND_CHANNEL_IDS is required to start the Discord command bot")

    try:
        import discord
    except ImportError as exc:  # pragma: no cover - depends on optional runtime dependency
        raise RuntimeError("discord.py is required. Install dependencies with: pip install -r requirements.txt") from exc

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:  # pragma: no cover - Discord integration callback
        user = getattr(client, "user", None)
        logger.info(
            "Discord command bot ready user=%s allowed_channels=%s discord_token=%s github_token=%s",
            user,
            sorted(allowed_channel_ids),
            mask_token(token),
            mask_token(os.getenv("GITHUB_DISPATCH_TOKEN")),
        )

    @client.event
    async def on_message(message) -> None:  # pragma: no cover - Discord integration callback
        author = getattr(message, "author", None)
        author_is_bot = bool(getattr(author, "bot", False))
        channel = getattr(message, "channel", None)
        channel_id = str(getattr(channel, "id", ""))
        content = str(getattr(message, "content", "") or "")
        mentions = list(getattr(message, "mentions", []) or [])
        mentioned_bot = client.user in mentions if getattr(client, "user", None) is not None else False

        response = handle_discord_message(
            content,
            author_is_bot=author_is_bot,
            channel_id=channel_id,
            mentioned_bot=mentioned_bot,
            allowed_channel_ids=allowed_channel_ids,
        )
        if not response.should_reply or not response.reply_text:
            return
        try:
            await message.channel.send(response.reply_text)
        except Exception as exc:
            logger.exception("Failed to send Discord command reply channel_id=%s error=%s", channel_id, exc)

    client.run(token)


def _command_body(content: str) -> str:
    text = str(content or "").strip()
    text = re.sub(r"<@!?\d+>", " ", text)
    text = text.replace(f"@{BOT_DISPLAY_NAME}", " ")
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    run_bot()
