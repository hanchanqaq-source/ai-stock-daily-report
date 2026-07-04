import csv
import json
from datetime import date

from src.history_archive import (
    generate_delete_candidates,
    generate_monthly_archive,
    generate_monthly_sector_stats,
    load_archive_manifest,
)


def _write_history(root):
    history = root / "data" / "history"
    history.mkdir(parents=True)
    with (history / "market_history.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "coverage_percent", "rise_ratio", "turnover", "limit_diff", "private_amount", "token"])
        writer.writeheader()
        writer.writerow({"date": "2026-07-01", "coverage_percent": "82", "rise_ratio": "48", "turnover": "12345", "limit_diff": "12", "private_amount": "999999", "token": "secret-token"})
        writer.writerow({"date": "2026-07-02", "coverage_percent": "60", "rise_ratio": "30", "turnover": "10000", "limit_diff": "-3"})
        writer.writerow({"date": "2099-07-01", "coverage_percent": "100", "rise_ratio": "100", "turnover": "99999", "limit_diff": "99"})
    snapshot = {
        "data_date": "2026-07-01",
        "data_quality": {"coverage_percent": 82},
        "breadth": {"rise_ratio": 0.48, "turnover": 12345, "limit_diff": 12},
        "sectors": {"top": [{"name": "PCB"}, {"name": "半导体"}], "bottom": [{"name": "地产"}]},
        "concepts": {"top": [{"name": "AI硬件"}], "bottom": [{"name": "黄金"}]},
        "private": {"webhook": "https://discord.com/api/webhooks/secret", "cost_price": 9.9},
    }
    (history / "market_snapshot_2026-07-01.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    (history / "market_snapshot_2026-07-02.json").write_text("{broken", encoding="utf-8")
    return history


def test_no_history_does_not_fail_and_writes_empty_outputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = generate_monthly_archive("2026-07", today=date(2026, 7, 4))
    assert (tmp_path / result["markdown_summary"]).exists()
    payload = json.loads((tmp_path / result["json_summary"]).read_text(encoding="utf-8"))
    assert payload["trading_days"] == 0
    assert payload["source"]["snapshot_count"] == 0
    assert (tmp_path / result["sector_stats_csv"]).read_text(encoding="utf-8").startswith("month,category,name,direction,count,rank")


def test_monthly_archive_generates_markdown_json_csv_and_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_history(tmp_path)
    result = generate_monthly_archive("2026-07", today=date(2026, 7, 4))

    md = (tmp_path / result["markdown_summary"]).read_text(encoding="utf-8")
    assert "# 2026-07 历史数据归档摘要" in md
    assert "领涨行业 Top 10" in md

    payload = json.loads((tmp_path / result["json_summary"]).read_text(encoding="utf-8"))
    assert payload["trading_days"] == 2
    assert payload["source"]["snapshot_count"] == 1
    assert payload["sectors"]["leading_industries_frequency"] == {"PCB": 1, "半导体": 1}
    rendered = json.dumps(payload, ensure_ascii=False)
    assert "discord.com/api/webhooks" not in rendered
    assert "secret-token" not in rendered
    assert "999999" not in rendered
    assert "cost_price" not in rendered

    csv_rows = list(csv.DictReader((tmp_path / result["sector_stats_csv"]).open(encoding="utf-8")))
    assert csv_rows[0]["month"] == "2026-07"
    assert csv_rows[0]["direction"] == "leading"
    assert csv_rows[0]["rank"] == "1"

    manifest = load_archive_manifest(archive_dir=tmp_path / "data" / "archive_summaries")
    assert len(manifest["monthly_summaries"]) == 1
    generate_monthly_archive("2026-07", today=date(2026, 7, 4))
    manifest = load_archive_manifest(archive_dir=tmp_path / "data" / "archive_summaries")
    assert len(manifest["monthly_summaries"]) == 1


def test_delete_candidates_manifest_and_no_delete(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reports = tmp_path / "data" / "reports"
    reports.mkdir(parents=True)
    report = reports / "old.md"
    report.write_text("old report", encoding="utf-8")
    cache = tmp_path / "cache"
    cache.mkdir()
    cached = cache / "item.tmp"
    cached.write_text("tmp", encoding="utf-8")

    path = generate_delete_candidates(today=date(2026, 7, 4))
    text = path.read_text(encoding="utf-8")
    assert "当前不会自动删除重要文件" in text
    assert report.exists()
    assert cached.exists()
    manifest = load_archive_manifest(archive_dir=tmp_path / "data" / "archive_summaries")
    assert manifest["delete_candidates"][0]["manual_confirm_required"] is True


def test_sector_stats_missing_data_writes_header_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = generate_monthly_sector_stats("2026-07", today=date(2026, 7, 4))
    assert path.read_text(encoding="utf-8") == "month,category,name,direction,count,rank\n"
