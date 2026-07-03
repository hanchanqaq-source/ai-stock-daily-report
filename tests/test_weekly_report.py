import json
from datetime import date, timedelta

from src.weekly_report import generate_weekly_report, save_weekly_report


def _write_snapshot(root, day, **overrides):
    payload = {
        "date": day.isoformat(),
        "market_signal": 50 + day.weekday(),
        "up_ratio": 40 + day.weekday() * 3,
        "turnover": 10000 + day.weekday() * 1000,
        "limit_diff": 10 + day.weekday(),
        "strong_sectors": [{"name": "AI", "change_pct": 2.0}, {"name": "半导体", "change_pct": 1.5}],
        "weak_sectors": [{"name": "地产", "change_pct": -1.0}],
    }
    payload.update(overrides)
    (root / f"market_snapshot_{day.isoformat()}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_weekly_report_shows_insufficient_history(tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    monday = date(2026, 6, 29)
    _write_snapshot(history, monday)

    result = generate_weekly_report(history, today=monday + timedelta(days=4))

    assert result.insufficient_history is True
    assert "历史样本不足" in result.report
    assert "历史样本不足" in result.discord_summary


def test_weekly_report_generates_five_day_metrics_and_sector_counts(tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    monday = date(2026, 6, 29)
    for offset in range(5):
        _write_snapshot(history, monday + timedelta(days=offset))

    result = generate_weekly_report(history, today=monday + timedelta(days=4))

    assert result.loaded_snapshots == 5
    assert "• 本周交易日数：5 天" in result.report
    assert "• 平均上涨占比：46.0%" in result.report
    assert "• 平均成交额：12000 亿" in result.report
    assert "变化 +4 分" in result.report
    assert "AI：出现 5 次" in result.report
    assert "| 日期 | 盘面信号 |" in result.report
    assert "|" not in result.discord_summary


def test_weekly_artifact_does_not_use_daily_filename(tmp_path):
    result = generate_weekly_report(tmp_path / "missing", today=date(2026, 7, 3))
    path = save_weekly_report(result, tmp_path / "reports")

    assert "AI股票基金每周复盘报告_2026-W27.md" in path
    assert "ai-investment-daily-report" not in path
