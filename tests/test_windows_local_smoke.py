import builtins
import sys
from pathlib import Path

import pytest


def test_local_smoke_returns_success_without_pipeline_or_external_services(
    monkeypatch,
    tmp_path,
    capsys,
):
    import main

    monkeypatch.setattr(sys, "argv", ["main.py", "--local-smoke"])
    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))

    def forbidden_call(*args, **kwargs):
        raise AssertionError("local-smoke must not enter production runtime")

    monkeypatch.setattr(main, "get_config", forbidden_call)
    monkeypatch.setattr(main, "_get_stock_analysis_pipeline", forbidden_call)
    monkeypatch.setattr(main, "_run_analysis_with_runtime_scheduler_lock", forbidden_call)
    monkeypatch.setattr(main, "_run_market_review_with_shared_lock", forbidden_call)
    monkeypatch.setattr(main, "_send_non_trading_day_skip_notice", forbidden_call)

    exit_code = main.main()

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "运行模式：local-smoke" in output
    assert "真实数据源：skipped" in output
    assert "AI 模型：skipped" in output
    assert "通知：skipped" in output
    assert "大盘复盘：skipped" in output
    assert "正式数据写入：skipped" in output
    assert "最终结果：success" in output
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "reports").is_dir()


def test_save_report_to_file_writes_report_atomically_and_cleans_temp(
    monkeypatch,
    tmp_path,
):
    from src.notification import NotificationService
    import src.notification as notification

    monkeypatch.setattr(notification, "__file__", str(tmp_path / "src" / "notification.py"))
    service = NotificationService.__new__(NotificationService)
    replaced_names = []
    original_replace = Path.replace

    def recording_replace(self, target):
        replaced_names.append(self.name)
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", recording_replace)

    saved_path = Path(service.save_report_to_file("正常报告内容", "daily_report.md"))

    assert saved_path.name == "daily_report.md"
    assert saved_path.read_text(encoding="utf-8") == "正常报告内容"
    assert replaced_names
    assert all(":" not in name for name in replaced_names)
    assert not list(saved_path.parent.glob("*.tmp"))


def test_save_report_to_file_rejects_blank_content_without_overwriting(
    monkeypatch,
    tmp_path,
):
    from src.notification import NotificationService
    import src.notification as notification

    monkeypatch.setattr(notification, "__file__", str(tmp_path / "src" / "notification.py"))
    service = NotificationService.__new__(NotificationService)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    target = reports_dir / "daily_report.md"
    target.write_text("旧报告", encoding="utf-8")

    with pytest.raises(ValueError):
        service.save_report_to_file("   \n\t", "daily_report.md")

    assert target.read_text(encoding="utf-8") == "旧报告"
    assert not list(reports_dir.glob("*.tmp"))


def test_save_report_to_file_preserves_old_report_when_temp_write_fails(
    monkeypatch,
    tmp_path,
):
    from src.notification import NotificationService
    import src.notification as notification

    monkeypatch.setattr(notification, "__file__", str(tmp_path / "src" / "notification.py"))
    service = NotificationService.__new__(NotificationService)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    target = reports_dir / "daily_report.md"
    target.write_text("旧报告", encoding="utf-8")
    original_open = builtins.open

    def failing_temp_open(file, mode="r", *args, **kwargs):
        if "w" in mode and Path(file).name.startswith(".report-"):
            raise OSError("simulated temp write failure")
        return original_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", failing_temp_open)

    with pytest.raises(OSError):
        service.save_report_to_file("新报告", "daily_report.md")

    assert target.read_text(encoding="utf-8") == "旧报告"
    assert not list(reports_dir.glob("*.tmp"))
