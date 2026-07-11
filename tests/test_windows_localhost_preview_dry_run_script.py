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


def _label_block(text: str, label: str) -> str:
    marker = f"\n:{label}\n"
    start = text.index(marker) + len(marker)
    next_label = text.find("\n:", start)
    if next_label == -1:
        return text[start:]
    return text[start:next_label]


def test_script_uses_unified_fatal_exit_without_call_fail_pattern() -> None:
    text = script_text()
    lower_text = text.lower()

    assert "call :fail" not in lower_text
    assert ":fatal_exit" in lower_text
    assert "exit /b 1" in lower_text
    assert "if not defined ci pause" in lower_text


def test_check_helpers_do_not_swallow_failures_with_exit_zero() -> None:
    text = script_text().lower()

    check_file_block = _label_block(text, "check_file")
    check_no_env_file_block = _label_block(text, "check_no_env_file")

    assert "exit /b 1" in check_file_block
    assert "exit /b 1" in check_no_env_file_block

    for block in [check_file_block, check_no_env_file_block]:
        failure_branch = block.split("exit /b 1", maxsplit=1)[0]
        assert "exit /b 0" not in failure_branch


def test_success_banner_exists_only_after_build_success_gate() -> None:
    text = script_text().lower()

    passed_index = text.index("dry run passed")
    build_index = text.index("npm run build")
    build_failure_gate_index = text.index("fail_reason=npm run build failed", build_index)
    fatal_after_build_index = text.index("goto :fatal_exit", build_failure_gate_index)

    assert build_index < build_failure_gate_index < fatal_after_build_index < passed_index


def test_npm_test_and_build_commands_fail_fast_to_fatal_exit() -> None:
    text = script_text().lower()

    commands = [
        "npm run test -- tests/mocks/preview-entry/mockonlypreviewentry.test.ts",
        "npm run test -- tests/mocks/preview/mockonlypreviewnetworkboundary.test.ts",
        "npm run test -- tests/mocks/preview/mockonlypreview.test.ts",
        "npm run build",
    ]

    for command in commands:
        command_index = text.index(command)
        next_command_indexes = [text.find(other, command_index + len(command)) for other in commands]
        next_command_indexes = [index for index in next_command_indexes if index != -1]
        block_end = min(next_command_indexes) if next_command_indexes else text.index("dry run passed")
        command_block = text[command_index:block_end]
        assert "if errorlevel 1" in command_block
        assert "goto :fatal_exit" in command_block


def test_protected_runtime_files_not_modified_by_this_task() -> None:
    changed_files = {
        "scripts/windows_localhost_web_safe_preview_dry_run.bat",
        "docs/windows_localhost_web_safe_preview_dry_run.md",
        "tests/test_windows_localhost_preview_dry_run_script.py",
        "docs/CHANGELOG.md",
    }

    assert changed_files.isdisjoint(PROTECTED_PATHS)
