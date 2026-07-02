import logging

import pytest

from src.config import MODEL_PROFILE_DEFAULT, resolve_model_profile


@pytest.mark.parametrize("profile", ["free", "daily", "pro", "auto", "final"])
def test_resolve_model_profile_accepts_supported_values(monkeypatch, profile):
    monkeypatch.setenv("MODEL_PROFILE", profile)

    assert resolve_model_profile() == profile


def test_resolve_model_profile_normalizes_supported_value(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", " Pro ")

    assert resolve_model_profile() == "pro"


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
