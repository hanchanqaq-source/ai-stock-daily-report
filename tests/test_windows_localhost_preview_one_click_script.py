from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "windows_localhost_web_safe_preview_one_click.bat"
PROTECTED_PATHS = {
    "apps/dsa-web/package.json",
}


def one_click_text() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_one_click_script_exists() -> None:
    assert SCRIPT_PATH.is_file()


def test_one_click_script_keeps_safe_preview_boundary() -> None:
    text = one_click_text()

    for expected in [
        "MOCK ONLY",
        "LOCAL PREVIEW ONLY",
        "HOST POLICY: 127.0.0.1 ONLY",
        "NO BACKEND WILL BE STARTED",
        "NO REAL API / PROVIDER / NOTIFICATION",
        "http://127.0.0.1:5174/mock-only-preview/",
    ]:
        assert expected in text

    lower_text = text.lower()
    for forbidden in [
        "0.0.0.0",
        "uvicorn",
        "fastapi",
        "python main.py",
        ".env",
    ]:
        assert forbidden not in lower_text


def test_one_click_npm_ci_uses_delayed_expansion_for_exit_code_inside_block() -> None:
    text = one_click_text()
    lower_text = text.lower()

    assert "setlocal EnableExtensions EnableDelayedExpansion" in text
    assert "call npm ci" in text
    assert "set \"NPM_CI_EXIT=!ERRORLEVEL!\"" in text
    assert "echo npm ci exit code: !NPM_CI_EXIT!" in text
    assert "if not \"!NPM_CI_EXIT!\"==\"0\" (" in text
    assert "set \"FAIL_REASON=npm ci failed with exit code !NPM_CI_EXIT!.\"" in text

    npm_ci_index = lower_text.index("call npm ci")
    exit_capture_index = lower_text.index('set "npm_ci_exit=!errorlevel!"')
    exit_echo_index = lower_text.index("echo npm ci exit code: !npm_ci_exit!")
    fail_fast_index = lower_text.index('if not "!npm_ci_exit!"=="0" (')
    start_index = lower_text.index('call "scripts\\windows_localhost_web_safe_preview_start.bat"')

    assert npm_ci_index < exit_capture_index < exit_echo_index < fail_fast_index < start_index


def test_one_click_invokes_start_script_after_successful_dependency_gate() -> None:
    lower_text = one_click_text().lower()

    fail_fast_index = lower_text.index('if not "!npm_ci_exit!"=="0" (')
    start_banner_index = lower_text.index("echo starting safe preview script...")
    start_call_index = lower_text.index('call "scripts\\windows_localhost_web_safe_preview_start.bat"')

    assert fail_fast_index < start_banner_index < start_call_index


def test_one_click_task_does_not_touch_protected_web_package_manifest() -> None:
    changed_files = {
        "scripts/windows_localhost_web_safe_preview_one_click.bat",
        "tests/test_windows_localhost_preview_one_click_script.py",
    }

    assert changed_files.isdisjoint(PROTECTED_PATHS)
