from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "windows_localhost_web_safe_preview_dry_run.bat"
PROTECTED_PATHS = {
    "apps/dsa-web/package.json",
    "apps/dsa-web/vite.config.ts",
    "apps/dsa-web/index.html",
    "apps/dsa-web/src/main.tsx",
    "apps/dsa-web/src/App.tsx",
}


def script_text() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_dry_run_script_exists() -> None:
    assert SCRIPT_PATH.is_file()


def test_script_contains_safety_banner_and_host_policy() -> None:
    text = script_text()

    for expected in [
        "DRY RUN ONLY",
        "MOCK ONLY",
        "LOCAL PREVIEW ONLY",
        "127.0.0.1",
        "NO WEB SERVER WILL BE STARTED",
        "NO BACKEND WILL BE STARTED",
        "NO REAL NETWORK",
    ]:
        assert expected in text


def test_script_checks_preview_entry_files() -> None:
    text = script_text()

    assert "apps\\dsa-web\\mock-only-preview\\index.html" in text
    assert "apps\\dsa-web\\src\\mocks\\preview-entry\\mockOnlyPreviewEntry.ts" in text


def test_script_checks_env_presence_without_reading_contents() -> None:
    text = script_text()
    lower_text = text.lower()

    assert ".env" in text
    assert ".env.*" in text
    for forbidden in [
        "type .env",
        "more .env",
        "findstr .env",
        "cat .env",
        "get-content .env",
    ]:
        assert forbidden not in lower_text


def test_script_does_not_auto_install_dependencies() -> None:
    lower_text = script_text().lower()

    for forbidden in [
        "npm install",
        "npm ci",
        "winget install",
        "choco install",
        "pip install",
    ]:
        assert forbidden not in lower_text


def test_script_does_not_start_web_backend_browser_or_network_tools() -> None:
    lower_text = script_text().lower()

    for forbidden in [
        "npm run dev",
        "npm run preview",
        "vite --host",
        "start http",
        "explorer http",
        "uvicorn",
        "fastapi",
        "python main.py",
        "curl",
        "invoke-webrequest",
        "wget",
    ]:
        assert forbidden not in lower_text


def test_script_runs_mock_only_tests_and_build() -> None:
    text = script_text()

    assert "mockOnlyPreviewEntry.test.ts" in text
    assert "mockOnlyPreviewNetworkBoundary.test.ts" in text
    assert "mockOnlyPreview.test.ts" in text
    assert "npm run build" in text


def test_protected_runtime_files_not_modified_by_this_task() -> None:
    changed_files = {
        "scripts/windows_localhost_web_safe_preview_dry_run.bat",
        "docs/windows_localhost_web_safe_preview_dry_run.md",
        "tests/test_windows_localhost_preview_dry_run_script.py",
        "docs/CHANGELOG.md",
    }

    assert changed_files.isdisjoint(PROTECTED_PATHS)
