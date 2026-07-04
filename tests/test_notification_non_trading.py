from src.notification import format_non_trading_day_discord_notice


def test_format_non_trading_day_discord_notice_is_short_and_explicit():
    notice = format_non_trading_day_discord_notice(
        report_date="2026-07-04",
        latest_trading_day="2026-07-03",
        run_mode="scheduled_cron",
        request_id="req-1",
        trigger_source="scheduled_cron",
    )
    assert "今日判断为非交易日" in notice
    assert "最近交易日：2026-07-03" in notice
    assert "force_run" in notice
    assert "skipped_non_trading_day" in notice
