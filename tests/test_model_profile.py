import logging

import pytest

from src.config import (
    MODEL_PROFILE_DEFAULT,
    RUN_MODE_DEFAULT,
    parse_model_profile,
    parse_run_mode,
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
