import logging

import pytest

from src.config import (
    MODEL_PROFILE_DEFAULT,
    RUN_MODE_DEFAULT,
    parse_model_profile,
    parse_run_mode,
    resolve_dispatch_run_parameters,
    resolve_model_profile,
    resolve_run_mode,
)


@pytest.mark.parametrize("profile", ["free", "daily", "pro", "auto", "final"])
def test_resolve_model_profile_accepts_supported_values(monkeypatch, profile):
    monkeypatch.setenv("MODEL_PROFILE", profile)

    assert resolve_model_profile() == profile


def test_resolve_model_profile_normalizes_supported_value(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", " Pro ")

    assert resolve_model_profile() == "pro"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("daily｜日常版｜默认推荐", "daily"),
        ("pro｜增强版｜重大行情", "pro"),
        ("最终版", "final"),
        ("非法值", MODEL_PROFILE_DEFAULT),
    ],
)
def test_parse_model_profile_accepts_labeled_values_and_aliases(value, expected):
    resolved, _ = parse_model_profile(value)

    assert resolved == expected


def test_resolve_model_profile_falls_back_for_invalid_value(monkeypatch, caplog):
    monkeypatch.setenv("MODEL_PROFILE", "vip")

    with caplog.at_level(logging.INFO, logger="src.config"):
        assert resolve_model_profile() == MODEL_PROFILE_DEFAULT

    assert "[MODEL] requested_profile=vip" in caplog.text
    assert "[MODEL] invalid profile, fallback to daily" in caplog.text
    assert "[MODEL] resolved_profile=daily" in caplog.text


@pytest.mark.parametrize("value", ["", "   "])
def test_resolve_model_profile_falls_back_for_blank_value(monkeypatch, value):
    monkeypatch.setenv("MODEL_PROFILE", value)

    assert resolve_model_profile() == MODEL_PROFILE_DEFAULT


def test_resolve_model_profile_falls_back_when_missing(monkeypatch):
    monkeypatch.delenv("MODEL_PROFILE", raising=False)

    assert resolve_model_profile() == MODEL_PROFILE_DEFAULT


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("full｜完整日报｜大盘+股票+推送", "full"),
        ("market-only｜只看大盘｜仅市场复盘", "market-only"),
        ("stocks-only｜只看股票｜仅股票/持仓", "stocks-only"),
        ("完整日报", "full"),
        ("只看大盘", "market-only"),
        ("只看股票", "stocks-only"),
        ("非法值", RUN_MODE_DEFAULT),
    ],
)
def test_parse_run_mode_accepts_labeled_values_and_aliases(value, expected):
    resolved, _ = parse_run_mode(value)

    assert resolved == expected


def test_resolve_run_mode_logs_invalid_fallback(caplog):
    with caplog.at_level(logging.INFO, logger="src.config"):
        assert resolve_run_mode("abc") == RUN_MODE_DEFAULT

    assert "[RUN] requested_mode=abc" in caplog.text
    assert "[RUN] invalid run mode, fallback to full" in caplog.text
    assert "[RUN] resolved_mode=full" in caplog.text


def test_resolve_run_context_generates_local_request_id(monkeypatch):
    from src.config import resolve_run_context

    for key in (
        "REQUEST_ID",
        "TRIGGER_SOURCE",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
        "GITHUB_EVENT_NAME",
        "RUN_MODE",
        "MODE",
        "MODEL_PROFILE",
    ):
        monkeypatch.delenv(key, raising=False)

    context = resolve_run_context()

    assert context.request_id.startswith("local-")
    assert context.trigger_source == "unknown"
    assert context.resolved_mode == "full"
    assert context.resolved_profile == "daily"


def test_resolve_run_context_maps_workflow_dispatch(monkeypatch):
    from src.config import resolve_run_context

    monkeypatch.delenv("REQUEST_ID", raising=False)
    monkeypatch.delenv("TRIGGER_SOURCE", raising=False)
    monkeypatch.setenv("GITHUB_RUN_ID", "123456789")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("RUN_MODE", "完整日报")
    monkeypatch.setenv("MODEL_PROFILE", "日常版")

    context = resolve_run_context()

    assert context.request_id == "gh-123456789-1"
    assert context.trigger_source == "manual_action"
    assert context.resolved_mode == "full"
    assert context.resolved_profile == "daily"


def test_resolve_run_context_prefers_repository_dispatch_payload_env(monkeypatch):
    from src.config import resolve_run_context

    monkeypatch.setenv("REQUEST_ID", "dispatch-abc")
    monkeypatch.setenv("TRIGGER_SOURCE", "channel_command")
    monkeypatch.setenv("GITHUB_RUN_ID", "123456789")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "repository_dispatch")
    monkeypatch.setenv("RUN_MODE", "只看大盘")
    monkeypatch.setenv("MODEL_PROFILE", "最终版")

    context = resolve_run_context()

    assert context.request_id == "dispatch-abc"
    assert context.trigger_source == "channel_command"
    assert context.resolved_mode == "market-only"
    assert context.resolved_profile == "final"


def test_resolve_run_context_falls_back_invalid_values(monkeypatch, caplog):
    from src.config import resolve_run_context

    monkeypatch.setenv("REQUEST_ID", "req-invalid")
    monkeypatch.setenv("TRIGGER_SOURCE", "manual_action")
    monkeypatch.setenv("RUN_MODE", "bad-mode")
    monkeypatch.setenv("MODEL_PROFILE", "vip")

    with caplog.at_level(logging.INFO, logger="src.config"):
        context = resolve_run_context()

    assert context.resolved_mode == "full"
    assert context.resolved_profile == "daily"
    assert "request_id=req-invalid" in caplog.text
    assert "trigger_source=manual_action" in caplog.text
    assert "resolved_mode=full" in caplog.text
    assert "resolved_profile=daily" in caplog.text


def test_dispatch_parameters_accept_client_payload_profiles():
    daily = resolve_dispatch_run_parameters(client_payload_model_profile="daily")
    pro = resolve_dispatch_run_parameters(client_payload_model_profile="pro")

    assert daily.resolved_profile == "daily"
    assert daily.profile_source == "client_payload"
    assert pro.resolved_profile == "pro"
    assert pro.profile_source == "client_payload"


@pytest.mark.parametrize(
    ("command_text", "expected_profile"),
    [
        ("@AI日报助手 增强版重跑", "pro"),
        ("@AI日报助手 最终版重跑", "final"),
        ("@AI日报助手 免费版重跑", "free"),
        ("@AI日报助手 日常版重跑", "daily"),
        ("@AI日报助手 自动版重跑", "auto"),
    ],
)
def test_dispatch_parameters_parse_command_text_profiles(command_text, expected_profile):
    result = resolve_dispatch_run_parameters(command_text=command_text)

    assert result.resolved_profile == expected_profile
    assert result.profile_source == "command_text"


@pytest.mark.parametrize(
    ("command_text", "expected_mode"),
    [
        ("@AI日报助手 只看大盘", "market-only"),
        ("@AI日报助手 只看股票", "stocks-only"),
        ("@AI日报助手 完整日报", "full"),
    ],
)
def test_dispatch_parameters_parse_command_text_modes(command_text, expected_mode):
    result = resolve_dispatch_run_parameters(command_text=command_text)

    assert result.resolved_mode == expected_mode
    assert result.mode_source == "command_text"


def test_dispatch_parameters_fall_back_for_invalid_values():
    result = resolve_dispatch_run_parameters(
        client_payload_run_mode="bad-mode",
        client_payload_model_profile="vip",
    )

    assert result.resolved_mode == "full"
    assert result.mode_valid is False
    assert result.resolved_profile == "daily"
    assert result.profile_valid is False


def test_dispatch_parameters_client_payload_wins_over_command_text():
    result = resolve_dispatch_run_parameters(
        client_payload_run_mode="stocks-only",
        client_payload_model_profile="daily",
        command_text="@AI日报助手 增强版重跑 只看大盘",
    )

    assert result.resolved_mode == "stocks-only"
    assert result.mode_source == "client_payload"
    assert result.resolved_profile == "daily"
    assert result.profile_source == "client_payload"


def test_dispatch_parameters_truncates_command_text_for_logs():
    result = resolve_dispatch_run_parameters(command_text="a" * 130)

    assert result.safe_command_text == f"{'a' * 120}..."
