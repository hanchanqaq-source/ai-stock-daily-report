import csv
import json
from pathlib import Path

from src.trend_analyzer import analyze_multi_window_persistence, render_persistence_summary_text

FIELDS = [
    "date", "report_date", "data_mode", "coverage_percent", "market_status", "market_score",
    "rise_ratio", "rising_count", "falling_count", "flat_count", "turnover", "limit_up_count",
    "limit_down_count", "limit_diff", "top_leading_industry", "top_lagging_industry",
    "top_leading_concept", "top_lagging_concept",
]


def write_history(tmp_path: Path, rows):
    history = tmp_path / "data" / "history"
    history.mkdir(parents=True)
    with (history / "market_history.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return history


def row(day, lead="", lag="", concept_lead="", concept_lag=""):
    return {
        "date": f"2026-01-{day:02d}", "report_date": f"2026-01-{day:02d}", "data_mode": "realtime",
        "coverage_percent": 80, "market_status": "neutral", "market_score": 50, "rise_ratio": 50,
        "rising_count": 1, "falling_count": 1, "flat_count": 0, "turnover": 100,
        "limit_up_count": 1, "limit_down_count": 0, "limit_diff": 1,
        "top_leading_industry": lead, "top_lagging_industry": lag,
        "top_leading_concept": concept_lead, "top_lagging_concept": concept_lag,
    }


def test_no_history_and_less_than_three_are_insufficient(tmp_path):
    missing = analyze_multi_window_persistence([5], history_dir=tmp_path / "missing")["5"]
    assert missing["status"] == "insufficient_data"
    history = write_history(tmp_path, [row(1, lead="PCB"), row(2, lead="PCB")])
    result = analyze_multi_window_persistence([5], history_dir=history)["5"]
    assert result["status"] == "insufficient_data"


def test_five_and_twenty_windows_are_independent(tmp_path):
    history = write_history(tmp_path, [row(i, lead="PCB" if i >= 2 else "机器人") for i in range(1, 6)])
    result = analyze_multi_window_persistence([5, 20], history_dir=history)
    assert result["5"]["status"] == "available"
    assert result["20"]["status"] == "insufficient_data"
    assert "近 20 日历史数据不足" in render_persistence_summary_text(result)


def test_classifies_persistent_leader_breakout_pullback_and_lagger(tmp_path):
    rows = [
        row(1, lead="有色金属", lag="地产", concept_lead="算力链"),
        row(2, lead="PCB", lag="地产", concept_lead="光模块"),
        row(3, lead="PCB", lag="地产", concept_lead="算力链"),
        row(4, lead="PCB", lag="白酒", concept_lead="光模块"),
        row(5, lead="PCB", lag="有色金属", concept_lead="机器人"),
    ]
    history = write_history(tmp_path, rows)
    result = analyze_multi_window_persistence([5], history_dir=history)["5"]
    industries = result["industries"]
    concepts = result["concepts"]
    assert industries["persistent_leaders"][0]["name"] == "PCB"
    assert any(x["name"] == "机器人" for x in concepts["short_term_breakouts"])
    assert any(x["name"] == "有色金属" for x in industries["pullback_risks"])
    assert any(x["name"] == "地产" for x in industries["persistent_laggers"])
    assert any(x["name"] == "算力链" for x in concepts["rotation_candidates"])
    for bucket in industries.values():
        for item in bucket:
            assert item["reason"]


def test_missing_fields_and_bad_json_do_not_fail_or_capture_secrets(tmp_path, caplog):
    rows = [row(i, lead="PCB" if i > 1 else "") for i in range(1, 6)]
    history = write_history(tmp_path, rows)
    (history / "market_snapshot_2026-01-05.json").write_text("{broken", encoding="utf-8")
    (history / "market_snapshot_2026-01-04.json").write_text(json.dumps({"sectors": {"leading_concepts": [{"name": "AI硬件"}]}}), encoding="utf-8")
    result = analyze_multi_window_persistence([5], history_dir=history)["5"]
    assert result["status"] == "available"
    text = json.dumps(result, ensure_ascii=False)
    assert "webhook" not in text.lower()
    assert "token" not in text.lower()
    assert "金额" not in text
    assert "bad_json" in caplog.text
