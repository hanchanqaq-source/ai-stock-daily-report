import json
from pathlib import Path

from src.data_fallback import find_latest_market_snapshot, data_mode_label


def test_loads_latest_valid_snapshot_and_skips_future(tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    (history / "market_snapshot_2026-07-03.json").write_text(json.dumps({"rise_ratio": 55}), encoding="utf-8")
    (history / "market_snapshot_2026-07-05.json").write_text(json.dumps({"rise_ratio": 99}), encoding="utf-8")

    result = find_latest_market_snapshot(history, as_of="2026-07-04")

    assert result.data_mode == "history_fallback"
    assert result.snapshot_date == "2026-07-03"
    assert result.snapshot_data == {"rise_ratio": 55}


def test_skips_corrupt_snapshot(tmp_path, caplog):
    history = tmp_path / "history"
    history.mkdir()
    (history / "market_snapshot_2026-07-03.json").write_text("{broken", encoding="utf-8")
    (history / "market_snapshot_2026-07-02.json").write_text(json.dumps({"turnover": 1}), encoding="utf-8")

    result = find_latest_market_snapshot(history, as_of="2026-07-04")

    assert result.snapshot_date == "2026-07-02"
    assert result.data_mode == "history_fallback"
    assert "market_snapshot_2026-07-03.json" in caplog.text


def test_returns_insufficient_when_no_snapshot(tmp_path):
    result = find_latest_market_snapshot(tmp_path / "missing", as_of="2026-07-04")

    assert result.data_mode == "insufficient_data"
    assert result.snapshot_data is None
    assert data_mode_label("skipped_non_trading_day") == "非交易日跳过"
