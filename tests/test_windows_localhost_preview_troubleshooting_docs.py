from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "windows_localhost_web_safe_preview_troubleshooting.md"


def doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_windows_localhost_preview_troubleshooting_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_windows_localhost_preview_troubleshooting_doc_covers_l2p_failures() -> None:
    text = doc_text()

    required_phrases = [
        "Node is not available",
        "node_modules is missing",
        "PASS Node version",
        "call npm",
        "MOCK_ONLY_PREVIEW_BLOCKED",
        "127.0.0.1:5174/mock-only-preview/",
        "Ctrl+C",
        "禁止 npm audit fix",
        "禁止 npm approve-scripts",
        "禁止 0.0.0.0",
        "禁止真实 API/provider/AI/通知/正式日报",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_windows_localhost_preview_troubleshooting_doc_uses_cause_fix_verify_structure() -> None:
    text = doc_text()

    for heading in ["### 原因", "### 处理", "### 验证标准"]:
        assert heading in text
