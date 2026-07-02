# -*- coding: utf-8 -*-
import logging

from src.command_executor import execute_command_text


def test_rerun_daily_dry_run_generates_dispatch_payload():
    result = execute_command_text("@AI日报助手 日常版重跑", dry_run=True, request_id="discord-test-001")

    assert result.status == "dry_run"
    assert result.action == "rerun_report"
    assert result.payload["event_type"] == "run-stock-report"
    client_payload = result.payload["client_payload"]
    assert client_payload["model_profile"] == "daily"
    assert client_payload["run_mode"] == "full"
    assert client_payload["trigger_source"] == "channel_command"
    assert client_payload["request_id"] == "discord-test-001"
    assert client_payload["command_text"] == "@AI日报助手 日常版重跑"


def test_rerun_request_id_is_generated_when_missing():
    result = execute_command_text("@AI日报助手 日常版重跑", dry_run=True)

    assert result.request_id
    assert result.request_id.startswith("discord-")
    assert result.payload["client_payload"]["request_id"] == result.request_id


def test_rerun_profiles_from_command_text():
    pro = execute_command_text("@AI日报助手 增强版重跑", dry_run=True, request_id="rid-pro")
    final = execute_command_text("@AI日报助手 最终版重跑", dry_run=True, request_id="rid-final")

    assert pro.payload["client_payload"]["model_profile"] == "pro"
    assert final.payload["client_payload"]["model_profile"] == "final"


def test_rerun_market_only_pro_from_command_text():
    result = execute_command_text("@AI日报助手 只看大盘 增强版重跑", dry_run=True, request_id="rid-market")

    assert result.payload["client_payload"]["run_mode"] == "market-only"
    assert result.payload["client_payload"]["model_profile"] == "pro"


def test_resend_latest_does_not_call_github_dispatch(monkeypatch):
    def fail_dispatch(_payload):  # pragma: no cover - should never run
        raise AssertionError("resend_latest must not dispatch")

    monkeypatch.setattr("src.command_executor.send_repository_dispatch", fail_dispatch)
    result = execute_command_text("@AI日报助手 重推", dry_run=False)

    assert result.action == "resend_latest"
    assert result.status == "planned"
    assert result.payload is None
    assert "实际重发将在 Discord Bot 接入后启用" in result.reply_text


def test_missing_token_returns_clear_status(monkeypatch):
    monkeypatch.delenv("GITHUB_DISPATCH_TOKEN", raising=False)

    result = execute_command_text("@AI日报助手 日常版重跑", dry_run=False, request_id="rid-missing-token")

    assert result.status == "missing_token"
    assert "缺少 GITHUB_DISPATCH_TOKEN" in result.message
    assert "缺少 GITHUB_DISPATCH_TOKEN" in result.reply_text
    assert result.payload["client_payload"]["request_id"] == "rid-missing-token"


def test_unknown_command_returns_unknown_command():
    result = execute_command_text("@AI日报助手 今天天气", dry_run=True)

    assert result.action == "unknown"
    assert result.status == "unknown_command"
    assert result.payload is None
    assert "未识别指令" in result.reply_text


def test_token_not_returned_or_logged(monkeypatch, caplog):
    secret = "ghp_1234567890abcdefSECRET"
    monkeypatch.setenv("GITHUB_DISPATCH_TOKEN", secret)

    caplog.set_level(logging.INFO)
    result = execute_command_text("@AI日报助手 日常版重跑", dry_run=True, request_id="rid-safe")

    returned_text = "\n".join([result.message, result.reply_text, str(result.payload)])
    logged_text = caplog.text
    assert secret not in returned_text
    assert secret not in logged_text
