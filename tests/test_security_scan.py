from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import security_scan


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def severities(result: dict) -> set[str]:
    return {item["severity"] for item in result["findings"]}


def test_example_config_does_not_trigger_blocker(tmp_path: Path) -> None:
    write(tmp_path / "config/examples/users.example.json", '{"user_id":"demo_public_user","webhook_secret":"DISCORD_WEBHOOK_DEMO_USER"}')
    result = security_scan.scan_repository(tmp_path)
    assert "BLOCKER" not in severities(result)
    assert "HIGH" not in severities(result)


def test_docs_security_words_do_not_trigger_high(tmp_path: Path) -> None:
    write(tmp_path / "docs/security.md", "不要保存 Webhook / Token / API Key，API Key 应放 GitHub Secrets。")
    result = security_scan.scan_repository(tmp_path)
    assert "BLOCKER" not in severities(result)
    assert "HIGH" not in severities(result)


def test_discord_webhook_url_triggers_blocker(tmp_path: Path) -> None:
    write(tmp_path / "config/prod.yaml", "url: https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz")
    result = security_scan.scan_repository(tmp_path)
    assert any(item["rule_id"] == "discord_webhook_url" and item["severity"] == "BLOCKER" for item in result["findings"])


def test_github_tokens_trigger_blocker(tmp_path: Path) -> None:
    write(tmp_path / "scripts/token.txt", "ghp_abcdefghijklmnopqrstuvwxyz1234567890\ngithub_pat_abcdefghijklmnopqrstuvwxyz1234567890")
    result = security_scan.scan_repository(tmp_path)
    blockers = [item for item in result["findings"] if item["rule_id"] == "github_token" and item["severity"] == "BLOCKER"]
    assert len(blockers) == 2


def test_sk_api_key_triggers_high(tmp_path: Path) -> None:
    write(tmp_path / "config/api.env", "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456")
    result = security_scan.scan_repository(tmp_path)
    assert any(item["rule_id"] in {"api_key", "env_api_key"} and item["severity"] in {"HIGH", "BLOCKER"} for item in result["findings"])


def test_real_user_config_path_triggers_high(tmp_path: Path) -> None:
    write(tmp_path / "data/user_config/real_user.json", '{"user_id":"real"}')
    result = security_scan.scan_repository(tmp_path)
    assert any(item["rule_id"] == "private_config_path" and item["severity"] == "HIGH" for item in result["findings"])


def test_secret_json_path_triggers_high(tmp_path: Path) -> None:
    write(tmp_path / "config/prod.secret.json", '{}')
    result = security_scan.scan_repository(tmp_path)
    assert any(item["rule_id"] == "private_config_path" and item["severity"] == "HIGH" for item in result["findings"])


def test_financial_fields_with_numeric_values_trigger_medium(tmp_path: Path) -> None:
    write(tmp_path / "config/portfolio.json", '{"amount": 12000, "cost_price": 8.5, "account_value": 20000}')
    result = security_scan.scan_repository(tmp_path)
    assert any(item["rule_id"] == "sensitive_financial_field" and item["severity"] in {"MEDIUM", "HIGH"} for item in result["findings"])


def test_secret_name_placeholder_does_not_trigger_high(tmp_path: Path) -> None:
    write(tmp_path / "config/examples/task_groups.example.json", '{"discord_webhook_secret":"DISCORD_WEBHOOK_DEMO_USER"}')
    result = security_scan.scan_repository(tmp_path)
    assert "BLOCKER" not in severities(result)
    assert "HIGH" not in severities(result)


def test_github_actions_bot_email_allowed(tmp_path: Path) -> None:
    write(tmp_path / ".github/workflows/report.yml", "email: 41898282+github-actions[bot]@users.noreply.github.com")
    result = security_scan.scan_repository(tmp_path)
    assert not any(item["rule_id"] == "email" for item in result["findings"])


def test_masked_value_does_not_contain_full_secret(tmp_path: Path) -> None:
    secret = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    write(tmp_path / "token.txt", secret)
    result = security_scan.scan_repository(tmp_path)
    masked_values = [item["masked_value"] for item in result["findings"]]
    assert masked_values
    assert all(secret not in value for value in masked_values)


def test_fail_on_high_returns_non_zero(tmp_path: Path) -> None:
    write(tmp_path / "token.txt", "ghp_abcdefghijklmnopqrstuvwxyz1234567890")
    proc = subprocess.run(
        [sys.executable, str(Path(security_scan.__file__)), "--root", str(tmp_path), "--fail-on-high", "--json"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0
    assert json.loads(proc.stdout)["status"] == "failed"


def test_clean_scan_returns_zero(tmp_path: Path) -> None:
    write(tmp_path / "config/examples/users.example.json", '{"user_id":"demo_public_user"}')
    proc = subprocess.run(
        [sys.executable, str(Path(security_scan.__file__)), "--root", str(tmp_path), "--json"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["status"] == "pass"


def test_scan_does_not_modify_files(tmp_path: Path) -> None:
    path = write(tmp_path / "config/prod.yaml", "token: ghp_abcdefghijklmnopqrstuvwxyz1234567890")
    before = path.read_text(encoding="utf-8")
    security_scan.scan_repository(tmp_path)
    assert path.read_text(encoding="utf-8") == before


def test_scan_does_not_delete_files(tmp_path: Path) -> None:
    path = write(tmp_path / "data/user_config/real_user.json", '{"user_id":"real"}')
    security_scan.scan_repository(tmp_path)
    assert path.exists()
