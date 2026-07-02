# -*- coding: utf-8 -*-
"""
Discord 发送提醒服务

职责：
1. 通过 webhook 或 Discord bot API 发送 Discord 消息
"""
import logging
import re
import time
from typing import Optional

import requests

from src.config import Config
from src.formatters import MIN_MAX_WORDS, chunk_content_by_max_words


logger = logging.getLogger(__name__)


DISCORD_MAX_CONTENT_LENGTH = 2000
DISCORD_MAX_RETRIES = 3
DISCORD_CHUNK_SLEEP_SECONDS = 1
DISCORD_ARTIFACT_HINT = "完整报告请查看 artifact 附件。"


class DiscordSender:
    
    def __init__(self, config: Config):
        """
        初始化 Discord 配置

        Args:
            config: 配置对象
        """
        self._discord_config = {
            'bot_token': getattr(config, 'discord_bot_token', None),
            'channel_id': getattr(config, 'discord_main_channel_id', None),
            'webhook_url': getattr(config, 'discord_webhook_url', None),
        }
        self._discord_max_words = self._normalize_max_words(
            getattr(config, 'discord_max_words', DISCORD_MAX_CONTENT_LENGTH)
        )
        self._webhook_verify_ssl = getattr(config, 'webhook_verify_ssl', True)

    @staticmethod
    def _normalize_max_words(value) -> int:
        try:
            configured = int(value)
        except (TypeError, ValueError):
            configured = DISCORD_MAX_CONTENT_LENGTH
        return max(MIN_MAX_WORDS, min(configured, DISCORD_MAX_CONTENT_LENGTH))
    
    def _is_discord_configured(self) -> bool:
        """检查 Discord 配置是否完整（支持 Bot 或 Webhook）"""
        # 只要配置了 Webhook 或完整的 Bot Token+Channel，即视为可用
        bot_ok = bool(self._discord_config['bot_token'] and self._discord_config['channel_id'])
        webhook_ok = bool(self._discord_config['webhook_url'])
        return bot_ok or webhook_ok
    
    def send_to_discord(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool:
        """
        推送消息到 Discord（支持 Webhook 和 Bot API）
        
        Args:
            content: Markdown 格式的消息内容
            
        Returns:
            是否发送成功
        """
        # Discord 手机端不适合阅读 Markdown 表格；发送前转换为更紧凑的摘要正文。
        content = self._format_discord_mobile_content(content)

        # 分割内容，避免单条消息超过 Discord 限制
        chunks = self._split_discord_content(content)

        # 优先使用 Webhook（配置简单，权限低）
        if self._discord_config['webhook_url']:
            return self._send_discord_chunks(
                chunks,
                self._send_discord_webhook,
                "Webhook",
                timeout_seconds=timeout_seconds,
            )

        # 其次使用 Bot API（权限高，需要 channel_id）
        if self._discord_config['bot_token'] and self._discord_config['channel_id']:
            return self._send_discord_chunks(
                chunks,
                self._send_discord_bot,
                "Bot",
                timeout_seconds=timeout_seconds,
            )

        logger.warning("Discord 配置不完整，跳过推送")
        return False


    def _format_discord_mobile_content(self, content: str) -> str:
        """Render a Discord-friendly summary without Markdown tables."""
        text = str(content or "").strip()
        if not text:
            return ""

        converted = self._convert_markdown_tables_to_numbered_lists(text)
        compact = self._compact_discord_summary(converted)
        return compact or converted

    def _convert_markdown_tables_to_numbered_lists(self, content: str) -> str:
        lines = content.splitlines()
        output: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if self._is_markdown_table_header(line) and i + 1 < len(lines) and self._is_markdown_table_separator(lines[i + 1]):
                title = self._pop_nearest_heading(output)
                rows: list[list[str]] = []
                i += 2
                while i < len(lines) and self._is_markdown_table_row(lines[i]):
                    rows.append(self._split_markdown_table_row(lines[i]))
                    i += 1
                rendered = self._render_discord_numbered_list(title, rows)
                if rendered:
                    if output and output[-1].strip():
                        output.append("")
                    output.extend(rendered)
                continue
            output.append(line)
            i += 1
        return "\n".join(output).strip()

    @staticmethod
    def _is_markdown_table_row(line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|")

    @classmethod
    def _is_markdown_table_header(cls, line: str) -> bool:
        cells = cls._split_markdown_table_row(line)
        if len(cells) < 2:
            return False
        normalized = {cell.strip().lower() for cell in cells}
        return bool({"排名", "rank"} & normalized) or any(cell in normalized for cell in {"涨跌幅", "change"})

    @classmethod
    def _is_markdown_table_separator(cls, line: str) -> bool:
        cells = cls._split_markdown_table_row(line)
        if len(cells) < 2:
            return False
        return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)

    @staticmethod
    def _split_markdown_table_row(line: str) -> list[str]:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            return []
        return [cell.strip() for cell in stripped.strip("|").split("|")]

    @staticmethod
    def _pop_nearest_heading(output: list[str]) -> str:
        index = len(output) - 1
        while index >= 0 and not output[index].strip():
            index -= 1
        if index >= 0 and output[index].lstrip().startswith("#"):
            heading = re.sub(r"^#+\s*", "", output.pop(index)).strip()
            while output and not output[-1].strip():
                output.pop()
            return heading
        return "重点榜单"

    @staticmethod
    def _render_discord_numbered_list(title: str, rows: list[list[str]]) -> list[str]:
        items: list[str] = []
        for fallback_rank, cells in enumerate(rows, 1):
            if len(cells) < 2:
                continue
            rank = cells[0] or str(fallback_rank)
            name = cells[1]
            change = cells[2] if len(cells) >= 3 else ""
            suffix = f"：{change}" if change else ""
            items.append(f"{rank}. {name}{suffix}")
        if not items:
            return []
        icon = "📉" if any(keyword in title for keyword in ("领跌", "Lagging", "lagging")) else "📈"
        return [f"{icon} {title}", *items]

    def _compact_discord_summary(self, content: str) -> str:
        """Keep Discord content focused on summary/list highlights instead of the full report."""
        lines = [line.rstrip() for line in content.splitlines()]
        kept: list[str] = []
        list_headings = ("📈 ", "📉 ")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if kept and kept[-1]:
                    kept.append("")
                continue
            if stripped.startswith("#") and len([x for x in kept if x.strip()]) < 3:
                kept.append(stripped)
                continue
            if stripped.startswith(list_headings) or re.match(r"^\d+\.\s+", stripped):
                kept.append(stripped)
                continue
            if len([x for x in kept if x.strip() and not x.startswith("#")]) < 8:
                kept.append(stripped)

        compact = "\n".join(kept).strip()
        if compact and len(compact) > self._discord_max_words - len(DISCORD_ARTIFACT_HINT) - 8:
            compact = compact[: self._discord_max_words - len(DISCORD_ARTIFACT_HINT) - 9].rstrip() + "…"
        if compact and DISCORD_ARTIFACT_HINT not in compact:
            compact = f"{compact}\n\n{DISCORD_ARTIFACT_HINT}"
        return compact

    def _split_discord_content(self, content: str) -> list[str]:
        """按 Discord content 上限拆分消息。"""
        try:
            chunks = chunk_content_by_max_words(content, self._discord_max_words)
            if len(chunks) > 1:
                chunks = chunk_content_by_max_words(
                    content,
                    self._discord_max_words,
                    add_page_marker=True,
                )
            return chunks
        except ValueError as e:
            logger.error("分割 Discord 消息失败: %s", e)
            return chunk_content_by_max_words(
                content,
                DISCORD_MAX_CONTENT_LENGTH,
                add_page_marker=True,
            )

    def _send_discord_chunks(
        self,
        chunks: list[str],
        send_once,
        channel_name: str,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """逐片发送 Discord 消息；失败片不应阻断后续片尝试。"""
        total_chunks = len(chunks)
        success_count = 0

        if total_chunks > 1:
            logger.info("Discord %s 分批发送：共 %d 批", channel_name, total_chunks)

        for i, chunk in enumerate(chunks):
            if send_once(chunk, timeout_seconds=timeout_seconds):
                success_count += 1
                if total_chunks > 1:
                    logger.info("Discord %s 第 %d/%d 批发送成功", channel_name, i + 1, total_chunks)
            else:
                logger.error("Discord %s 第 %d/%d 批发送失败", channel_name, i + 1, total_chunks)

            if i < total_chunks - 1:
                time.sleep(DISCORD_CHUNK_SLEEP_SECONDS)

        return success_count == total_chunks

  
    def _send_discord_webhook(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool:
        """
        使用 Webhook 发送消息到 Discord
        
        Discord Webhook 支持 Markdown 格式
        
        Args:
            content: Markdown 格式的消息内容
            
        Returns:
            是否发送成功
        """
        payload = {
            'content': content,
            'username': 'A股分析机器人',
            'avatar_url': 'https://picsum.photos/200'
        }

        return self._post_discord_message(
            self._discord_config['webhook_url'],
            payload,
            success_statuses=(200, 204),
            verify=self._webhook_verify_ssl,
            timeout_seconds=timeout_seconds,
            channel_name="Webhook",
        )
    
    def _send_discord_bot(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool:
        """
        使用 Bot API 发送消息到 Discord
        
        Args:
            content: Markdown 格式的消息内容
            
        Returns:
            是否发送成功
        """
        headers = {
            'Authorization': f'Bot {self._discord_config["bot_token"]}',
            'Content-Type': 'application/json'
        }
        payload = {'content': content}
        url = f'https://discord.com/api/v10/channels/{self._discord_config["channel_id"]}/messages'

        return self._post_discord_message(
            url,
            payload,
            headers=headers,
            success_statuses=(200,),
            timeout_seconds=timeout_seconds,
            channel_name="Bot",
        )

    def _post_discord_message(
        self,
        url: str,
        payload: dict,
        *,
        success_statuses: tuple[int, ...],
        headers: Optional[dict] = None,
        verify: Optional[bool] = None,
        timeout_seconds: Optional[float] = None,
        channel_name: str,
    ) -> bool:
        """发送单条 Discord 消息，并复用 Telegram 的有限重试思路处理 429/5xx。"""
        request_kwargs = {
            'json': payload,
            'timeout': timeout_seconds or 10,
        }
        if headers:
            request_kwargs['headers'] = headers
        if verify is not None:
            request_kwargs['verify'] = verify

        for attempt in range(1, DISCORD_MAX_RETRIES + 1):
            try:
                response = requests.post(url, **request_kwargs)
            except requests.exceptions.RequestException as e:
                if attempt < DISCORD_MAX_RETRIES:
                    delay = 2 ** attempt
                    logger.warning(
                        "Discord %s 请求异常（%d/%d）：%s，%s 秒后重试",
                        channel_name,
                        attempt,
                        DISCORD_MAX_RETRIES,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                logger.error("Discord %s 请求重试后仍失败: %s", channel_name, e)
                return False

            if response.status_code in success_statuses:
                logger.info("Discord %s 消息发送成功", channel_name)
                return True

            if response.status_code == 429 and attempt < DISCORD_MAX_RETRIES:
                retry_after = self._get_retry_after_seconds(response, attempt)
                logger.warning(
                    "Discord %s 触发限流，%s 秒后重试（%d/%d）",
                    channel_name,
                    retry_after,
                    attempt,
                    DISCORD_MAX_RETRIES,
                )
                time.sleep(retry_after)
                continue

            if response.status_code >= 500 and attempt < DISCORD_MAX_RETRIES:
                delay = 2 ** attempt
                logger.warning(
                    "Discord %s 服务端错误 HTTP %s（%d/%d），%s 秒后重试",
                    channel_name,
                    response.status_code,
                    attempt,
                    DISCORD_MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
                continue

            logger.error(
                "Discord %s 发送失败: %s %s",
                channel_name,
                response.status_code,
                response.text,
            )
            return False

        return False

    @staticmethod
    def _get_retry_after_seconds(response, attempt: int) -> float:
        try:
            retry_after = response.json().get('retry_after')
            if retry_after is not None:
                return max(0.0, float(retry_after))
        except (AttributeError, TypeError, ValueError):
            pass

        try:
            retry_after = response.headers.get('Retry-After')
            if retry_after is not None:
                return max(0.0, float(retry_after))
        except AttributeError:
            pass

        return float(2 ** attempt)
