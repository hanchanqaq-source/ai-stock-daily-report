import json
from datetime import date, timedelta

from src.history_store import (
    CSV_FILENAME,
    build_market_snapshot,
    load_latest_snapshot,
    load_market_history_csv,
    load_recent_snapshots,
    load_snapshot_by_date,
    save_market_history,
)


def _payload(data_date="2026-01-02", score=56, webhook="https://discord.com/api/webhooks/secret"):
    return {
        "date": data_date,
        "report_date": data_date,
        "data_mode": "realtime",
        "data_quality": {"coverage_percent": 76, "missing_fields": [], "partial_fields": []},
        "region": "cn",
        "indices": [{"code": "000001", "name": "上证指数", "current": 3000, "change_pct": 1.2}],
        "breadth": {
            "rising_count": 2219,
            "falling_count": 3161,
            "flat_count": 0,
            "rise_ratio": 0.412,
            "turnover": 34733,
            "limit_up_count": 88,
            "limit_down_count": 5,
            "limit_diff": 83,
        },
        "market_light": {"label": "偏强", "score": score, "status": "green"},
        "sectors": {"top": [{"name": "半导体", "change_pct": 2.1}], "bottom": [{"name": "煤炭", "change_pct": -1.3}]},
        "concepts": {"top": [{"name": "AI", "change_pct": 3.0}], "bottom": [{"name": "黄金", "change_pct": -2.0}]},
        "private": {"webhook": webhook, "amount": 123456, "cost_price": 9.9, "token": "secret-token"},
    }


def test_save_creates_dir_snapshot_and_csv_without_duplicate_rows(tmp_path):
    assert save_market_history(_payload(score=56), history_dir=tmp_path)
    snapshot_path = tmp_path / "market_snapshot_2026-01-02.json"
    assert snapshot_path.exists()
    assert (tmp_path / CSV_FILENAME).exists()

    assert save_market_history(_payload(score=61), history_dir=tmp_path)
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["a_share"]["market_score"] == 61

    rows = load_market_history_csv(history_dir=tmp_path)
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-01-02"
    assert rows[0]["market_score"] == "61"


def test_csv_rows_are_sorted_by_date(tmp_path):
    assert save_market_history(_payload("2026-01-03"), history_dir=tmp_path)
    assert save_market_history(_payload("2026-01-01"), history_dir=tmp_path)
    assert [row["date"] for row in load_market_history_csv(history_dir=tmp_path)] == ["2026-01-01", "2026-01-03"]


def test_missing_fields_do_not_break_save(tmp_path):
    assert save_market_history({"date": "2026-01-04", "region": "cn"}, history_dir=tmp_path)
    snapshot = load_snapshot_by_date("2026-01-04", history_dir=tmp_path)
    assert snapshot is not None
    assert snapshot["a_share"]["turnover"] is None


def test_broken_json_is_skipped_and_latest_reads_recent_valid_snapshot(tmp_path):
    assert save_market_history(_payload("2026-01-01"), history_dir=tmp_path)
    assert save_market_history(_payload("2026-01-02"), history_dir=tmp_path)
    (tmp_path / "market_snapshot_2026-01-03.json").write_text("{broken", encoding="utf-8")

    latest = load_latest_snapshot(history_dir=tmp_path)
    assert latest is not None
    assert latest["data_date"] == "2026-01-02"


def test_recent_snapshots_returns_newest_first_with_limit(tmp_path):
    for day in range(1, 7):
        assert save_market_history(_payload(f"2026-01-0{day}"), history_dir=tmp_path)
    recent = load_recent_snapshots(limit=5, history_dir=tmp_path)
    assert [item["data_date"] for item in recent] == ["2026-01-06", "2026-01-05", "2026-01-04", "2026-01-03", "2026-01-02"]


def test_snapshot_whitelist_excludes_webhook_amount_cost_and_token():
    snapshot = build_market_snapshot(_payload())
    rendered = json.dumps(snapshot, ensure_ascii=False)
    assert "discord.com/api/webhooks" not in rendered
    assert "secret-token" not in rendered
    assert "cost_price" not in rendered
    assert "123456" not in rendered


def test_future_dates_are_not_read_or_written(tmp_path):
    future = (date.today() + timedelta(days=1)).isoformat()
    assert not save_market_history(_payload(future), history_dir=tmp_path)
    assert load_snapshot_by_date(future, history_dir=tmp_path) is None
