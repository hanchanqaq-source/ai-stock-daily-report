import csv
import json
from datetime import date, timedelta

from src.weekly_report import generate_weekly_report, save_weekly_report
from src.history_store import CSV_COLUMNS


def _write_snapshot(root, day, **overrides):
    payload = {
        "date": day.isoformat(),
        "market_signal": 50 + day.weekday(),
        "up_ratio": 40 + day.weekday() * 3,
        "turnover": 10000 + day.weekday() * 1000,
        "limit_diff": 10 + day.weekday(),
        "data_quality": {"coverage_percent": 80 + day.weekday()},
        "strong_sectors": [{"name": "AI", "change_pct": 2.0}, {"name": "半导体", "change_pct": 1.5}],
        "weak_sectors": [{"name": "地产", "change_pct": -1.0}],
    }
    payload.update(overrides)
    (root / f"market_snapshot_{day.isoformat()}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_history_csv(root, monday, days=20):
    with (root / "market_history.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        start = monday - timedelta(days=days - 5)
        for offset in range(days):
            day = start + timedelta(days=offset)
            writer.writerow(
                {
                    "date": day.isoformat(),
                    "report_date": day.isoformat(),
                    "data_mode": "realtime",
                    "coverage_percent": 82,
                    "market_status": "震荡",
                    "market_score": 50 + min(offset, 10),
                    "rise_ratio": 40 + min(offset, 12),
                    "turnover": 9000 + offset * 100,
                    "limit_diff": 5 + offset,
                    "top_leading_industry": "AI" if offset >= days - 4 else "半导体",
                    "top_lagging_industry": "地产" if offset >= days - 2 else "煤炭",
                    "top_leading_concept": "机器人" if offset >= days - 1 else "PCB",
                    "top_lagging_concept": "白酒",
                }
            )


def test_weekly_report_shows_insufficient_history(tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    monday = date(2026, 6, 29)
    _write_snapshot(history, monday)

    result = generate_weekly_report(history, today=monday + timedelta(days=4))

    assert result.insufficient_history is True
    assert result.structured_result["status"] == "insufficient_data"
    assert "历史样本不足" in result.report
    assert "历史样本不足" in result.discord_summary


def test_weekly_report_generates_enhanced_markdown_and_structured_result(tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    monday = date(2026, 6, 29)
    _write_history_csv(history, monday)
    for offset in range(5):
        _write_snapshot(history, monday + timedelta(days=offset))

    result = generate_weekly_report(history, today=monday + timedelta(days=4))

    assert result.loaded_snapshots == 5
    assert result.structured_result["status"] == "available"
    assert result.structured_result["trading_days"] == 5
    assert result.structured_result["metrics"]["average_rise_ratio"] == 46.0
    assert result.structured_result["market_temperature"] in {"升温", "降温", "震荡", "数据不足"}
    assert "# AI 股票基金市场周报" in result.report
    assert "## 2. 本周市场温度" in result.report
    assert "- 本周交易日数量：5" in result.report
    assert "- 平均上涨占比：46.0%" in result.report
    assert "- 平均成交额：12000.0 亿" in result.report
    assert "- 市场温度：" in result.report
    assert "近 5 日趋势" in result.report
    assert "近 20 日趋势" in result.report
    assert "持续走强方向" in result.report
    assert "数据质量说明" in result.report
    assert "下周观察重点" in result.report
    assert "买入" not in result.report
    assert "卖出" not in result.report
    assert "加仓" not in result.report
    assert "减仓" not in result.report
    assert "webhook" not in result.report.lower()
    assert "token" not in result.report.lower()
    assert "📊 本周市场周报" in result.discord_summary


def test_weekly_report_handles_missing_history_without_secrets(tmp_path):
    result = generate_weekly_report(tmp_path / "missing", today=date(2026, 7, 3))

    assert result.loaded_snapshots == 0
    assert result.insufficient_history is True
    assert result.structured_result["data_quality"]["insufficient_data_days"] == []
    assert "历史样本不足" in result.report
    assert "webhook" not in result.report.lower()
    assert "token" not in result.report.lower()


def test_weekly_artifact_does_not_use_daily_filename(tmp_path):
    result = generate_weekly_report(tmp_path / "missing", today=date(2026, 7, 3))
    path = save_weekly_report(result, tmp_path / "reports")

    assert "AI股票基金每周复盘报告_2026-W27.md" in path
    assert "ai-investment-daily-report" not in path
