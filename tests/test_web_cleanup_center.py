import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "web_cleanup_center.md"
INDEX = ROOT / "web" / "static" / "index.html"
APP = ROOT / "web" / "static" / "app.js"
PAYLOAD = ROOT / "web" / "static" / "demo_final_page_payload.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cleanup_center_doc_exists_and_declares_rules():
    assert DOC.exists()
    text = read(DOC)
    assert "Web-P19" in text
    assert "默认只扫描，不删除" in text
    assert "先预览，再确认，再执行" in text
    assert "禁止清理 data/history" in text
    assert "禁止清理 data/user_config" in text
    assert "Token / API Key / Webhook" in text


def test_cleanup_center_static_page_hooks_exist():
    index = read(INDEX)
    assert "cleanup-center-section" in index
    assert "清理中心" in index
    assert "cleanup-summary" in index
    assert "cleanup-categories" in index
    assert "cleanup-preview-panel" in index
    assert "cleanup-protected-data-panel" in index
    assert "cleanup-action-preview" in index
    assert "cleanup-disclaimer" in index


def test_cleanup_center_render_functions_exist_and_are_demo_only():
    app = read(APP)
    assert "renderCleanupCenter" in app
    assert "getCleanupCenterFromPayload" in app
    assert "buildFallbackCleanupCenter" in app
    assert "renderCleanupSummary" in app
    assert "renderCleanupCategories" in app
    assert "renderCleanupCategory" in app
    assert "renderCleanupItem" in app
    assert "renderProtectedDataPanel" in app
    assert "renderCleanupPreviewPanel" in app
    assert "renderCleanupRiskBadge" in app
    assert "renderCleanupStatusBadge" in app
    assert "当前为 demo 模式，不会删除任何文件。" in app
    forbidden = [
        "fetch(\"/delete",
        "fetch('/delete",
        "method: \"DELETE\"",
        "method: 'DELETE'",
        "fs.unlink",
        "fs.rm",
        "rmSync",
        "unlinkSync",
        "rmdirSync",
    ]
    for token in forbidden:
        assert token not in app


def test_cleanup_center_payload_contract_and_categories():
    payload = json.loads(read(PAYLOAD))
    cleanup = payload["cleanup_center"]
    assert cleanup["data_mode"] == "dry_run"
    assert cleanup["can_delete_files"] is False
    assert cleanup["requires_preview"] is True
    assert cleanup["requires_user_confirm"] is True
    risk_levels = {category["risk_level"] for category in cleanup["categories"]}
    assert {"low", "medium", "blocked"}.issubset(risk_levels)
    blocked_text = json.dumps(
        [category for category in cleanup["categories"] if category["risk_level"] == "blocked"],
        ensure_ascii=False,
    )
    assert "data/history" in blocked_text
    assert "data/user_config" in blocked_text
    assert ".env" in blocked_text


def test_cleanup_center_payload_does_not_store_real_private_values():
    text = read(PAYLOAD)
    assert "<redacted>" in text
    forbidden_private_values = [
        "Token",
        "API Key",
        "Webhook",
        "真实金额",
        "成本价",
        "账户资产",
        "真实持仓",
        "sk-",
        "xoxb-",
        "discord.com/api/webhooks/",
        "https://hooks.slack.com/services/",
    ]
    for token in forbidden_private_values:
        assert token not in text
    required_public_safe_labels = ["本地凭据配置", "私人配置", "私人投资记录", "私人成本记录", "私人账户记录"]
    for label in required_public_safe_labels:
        assert label in text


def test_cleanup_center_doc_keeps_full_security_boundary():
    text = read(DOC)
    assert "Token / API Key / Webhook" in text
    assert "真实金额" in text
    assert "成本价" in text
    assert "账户资产" in text


def test_cleanup_center_does_not_add_delete_api_or_filesystem_logic():
    combined = read(INDEX) + "\n" + read(APP)
    forbidden = [
        "fetch(\"/delete",
        "fetch('/delete",
        "DELETE /",
        "method: \"DELETE\"",
        "method: 'DELETE'",
        "fs.unlink",
        "fs.rm",
        "unlinkSync",
        "rmSync",
    ]
    for token in forbidden:
        assert token not in combined
