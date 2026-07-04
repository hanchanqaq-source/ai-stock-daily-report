import csv
import json
from pathlib import Path

from src.trend_analyzer import (
    analyze_multi_window_trends,
    analyze_recent_trends,
    calculate_trend_direction,
    render_trend_summary_text,
)

FIELDS = [
    "date",
    "report_date",
    "data_mode",
    "coverage_percent",
    "market_status",
    "market_score",
    "rise_ratio",
    "rising_count",
    "falling_count",
    "flat_count",
    "turnover",
    "limit_up_count",
    "limit_down_count",
    "limit_diff",
    "top_leading_industry",
    "top_lagging_industry",
    "top_leading_concept",
    "top_lagging_concept",
]


def write_history(tmp_path: Path, rows):
    history = tmp_path / "data" / "history"
    history.mkdir(parents=True)
    with (history / "market_history.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return history


def row(i, **kw):
    base = {
        "date": f"2026-01-{i:02d}",
        "report_date": f"2026-01-{i:02d}",
        "data_mode": "realtime",
        "coverage_percent": 80,
        "market_status": "neutral",
        "market_score": 50 + i,
        "rise_ratio": 40 + i * 2,
        "rising_count": 2000,
        "falling_count": 1800,
        "flat_count": 100,
        "turnover": 10000 + i * 500,
        "limit_up_count": 40 + i,
        "limit_down_count": 20,
        "limit_diff": 20 + i,
        "top_leading_industry": "PCB" if i < 5 else "半导体",
        "top_lagging_industry": "地产",
        "top_leading_concept": "AI硬件",
        "top_lagging_concept": "ST板块",
    }
    base.update(kw)
    return base


def test_no_history_returns_insufficient_data(tmp_path):
    result = analyze_recent_trends(5, history_dir=tmp_path / "missing")
    assert result["status"] == "insufficient_data"
    assert result["data_points"] == 0


def test_less_than_five_rows_does_not_raise(tmp_path):
    history = write_history(tmp_path, [row(1), row(2), row(3), row(4)])
    result = analyze_recent_trends(5, history_dir=history)
    assert result["status"] == "insufficient_data"
    assert result["data_points"] == 4


def test_five_day_trends_and_metric_directions(tmp_path):
    history = write_history(tmp_path, [row(i) for i in range(1, 6)])
    result = analyze_recent_trends(5, history_dir=history)
    assert result["status"] == "available"
    assert result["rise_ratio"]["direction"] == "上升"
    assert result["turnover"]["direction"] == "放量"
    assert result["limit_diff"]["direction"] == "改善"
    assert result["market_score"]["direction"] == "改善"


def test_twenty_day_insufficient_when_less_than_twenty(tmp_path):
    history = write_history(tmp_path, [row(i) for i in range(1, 9)])
    result = analyze_multi_window_trends([5, 20], history_dir=history)
    assert result["5"]["status"] == "available"
    assert result["20"]["status"] == "insufficient_data"


def test_persistence_for_industries_and_concepts_with_bad_json_skipped(tmp_path, caplog):
    rows = [row(i) for i in range(1, 6)]
    history = write_history(tmp_path, rows)
    snapshot = {
        "sectors": {
            "leading_industries": [{"name": "PCB"}],
            "lagging_industries": [{"name": "地产"}],
            "leading_concepts": [{"name": "AI硬件"}],
            "lagging_concepts": [{"name": "ST板块"}],
        }
    }
    for i in range(1, 5):
        (history / f"market_snapshot_2026-01-{i:02d}.json").write_text(
            json.dumps(snapshot, ensure_ascii=False), encoding="utf-8"
        )
    (history / "market_snapshot_2026-01-05.json").write_text("{broken", encoding="utf-8")
    result = analyze_recent_trends(5, history_dir=history)
    sectors = result["sectors"]
    assert sectors["persistent_leading_industries"][0]["name"] == "PCB"
    assert sectors["persistent_lagging_industries"][0]["name"] == "地产"
    assert sectors["persistent_leading_concepts"][0]["name"] == "AI硬件"
    assert sectors["persistent_lagging_concepts"][0]["name"] == "ST板块"
    assert "bad_json" in caplog.text


def test_missing_fields_and_summary_rendering_do_not_fail(tmp_path):
    rows = [row(i) for i in range(1, 5)] + [row(5, turnover="", market_score="", top_leading_industry="")]
    history = write_history(tmp_path, rows)
    result = analyze_recent_trends(5, history_dir=history)
    text = render_trend_summary_text({"5": result, "20": analyze_recent_trends(20, history_dir=history)})
    assert "近 5 日 / 20 日趋势观察" in text
    assert "历史数据不足" in text


def test_calculate_trend_direction_data_insufficient():
    assert calculate_trend_direction([1]) == "数据不足"
