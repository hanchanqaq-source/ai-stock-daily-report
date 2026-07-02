from dataclasses import dataclass

from src.discord_command_bot import handle_discord_message, parse_allowed_channel_ids, truncate_log_text


@dataclass(frozen=True)
class DummyResult:
    reply_text: str
    status: str = "submitted"


def _executor(calls):
    def fake(command_text, *, dry_run=False):
        calls.append((command_text, dry_run))
        return DummyResult(reply_text="ok reply")

    return fake


def test_bot_author_is_ignored():
    calls = []
    result = handle_discord_message(
        "@AI日报助手 日常版重跑",
        author_is_bot=True,
        channel_id="123",
        mentioned_bot=True,
        allowed_channel_ids={"123"},
        executor=_executor(calls),
    )
    assert not result.should_reply
    assert calls == []


def test_non_allowlisted_channel_is_ignored():
    calls = []
    result = handle_discord_message(
        "@AI日报助手 日常版重跑",
        author_is_bot=False,
        channel_id="999",
        mentioned_bot=True,
        allowed_channel_ids={"123"},
        executor=_executor(calls),
    )
    assert not result.should_reply
    assert calls == []


def test_message_without_mention_is_ignored():
    calls = []
    result = handle_discord_message(
        "日常版重跑",
        author_is_bot=False,
        channel_id="123",
        mentioned_bot=False,
        allowed_channel_ids={"123"},
        executor=_executor(calls),
    )
    assert not result.should_reply
    assert calls == []


def test_help_command_returns_help_text():
    result = handle_discord_message(
        "@AI日报助手 帮助",
        author_is_bot=False,
        channel_id="123",
        mentioned_bot=True,
        allowed_channel_ids={"123"},
    )
    assert result.should_reply
    assert "🧭" in result.reply_text
    assert "@AI日报助手 重推" in result.reply_text


def test_daily_rerun_calls_executor():
    calls = []
    result = handle_discord_message(
        "@AI日报助手 日常版重跑",
        author_is_bot=False,
        channel_id="123",
        mentioned_bot=True,
        allowed_channel_ids={"123"},
        executor=_executor(calls),
    )
    assert result.reply_text == "ok reply"
    assert calls == [("@AI日报助手 日常版重跑", False)]


def test_pro_rerun_calls_executor():
    calls = []
    result = handle_discord_message(
        "@AI日报助手 增强版重跑",
        author_is_bot=False,
        channel_id="123",
        mentioned_bot=True,
        allowed_channel_ids={"123"},
        executor=_executor(calls),
    )
    assert result.reply_text == "ok reply"
    assert calls == [("@AI日报助手 增强版重跑", False)]


def test_market_only_pro_rerun_is_passed_to_executor():
    calls = []
    result = handle_discord_message(
        "@AI日报助手 只看大盘 增强版重跑",
        author_is_bot=False,
        channel_id="123",
        mentioned_bot=True,
        allowed_channel_ids={"123"},
        executor=_executor(calls),
    )
    assert result.reply_text == "ok reply"
    assert calls == [("@AI日报助手 只看大盘 增强版重跑", False)]


def test_unknown_command_returns_unknown_text():
    result = handle_discord_message(
        "@AI日报助手 今天天气",
        author_is_bot=False,
        channel_id="123",
        mentioned_bot=True,
        allowed_channel_ids={"123"},
    )
    assert result.should_reply
    assert "未识别指令" in result.reply_text


def test_tokens_are_not_in_reply(monkeypatch):
    monkeypatch.setenv("GITHUB_DISPATCH_TOKEN", "ghp_very_secret_token")
    result = handle_discord_message(
        "@AI日报助手 日常版重跑",
        author_is_bot=False,
        channel_id="123",
        mentioned_bot=True,
        allowed_channel_ids={"123"},
    )
    assert "ghp_very_secret_token" not in result.reply_text


def test_long_command_preview_is_truncated():
    text = "x" * 160
    preview = truncate_log_text(text)
    assert len(preview) == 123
    assert preview.endswith("...")


def test_parse_allowed_channel_ids_supports_commas():
    assert parse_allowed_channel_ids("123, 987,,456 ") == {"123", "987", "456"}
