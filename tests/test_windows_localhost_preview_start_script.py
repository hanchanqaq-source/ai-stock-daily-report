from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "windows_localhost_web_safe_preview_start.bat"
VITE_CONFIG_PATH = REPO_ROOT / "apps" / "dsa-web" / "mock-only-preview" / "vite.config.ts"
PROTECTED_PATHS = {
    "apps/dsa-web/package.json",
    "apps/dsa-web/vite.config.ts",
    "apps/dsa-web/index.html",
    "apps/dsa-web/src/main.tsx",
    "apps/dsa-web/src/App.tsx",
}


def start_script_text() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def vite_config_text() -> str:
    return VITE_CONFIG_PATH.read_text(encoding="utf-8")


def test_start_script_exists() -> None:
    assert SCRIPT_PATH.is_file()


def test_start_script_contains_safety_banner() -> None:
    text = start_script_text()

    for expected in [
        "MOCK ONLY",
        "LOCAL PREVIEW ONLY",
        "LOOPBACK ONLY",
        "127.0.0.1",
        "NO BACKEND WILL BE STARTED",
        "NO BROWSER WILL BE OPENED",
        "NO REAL API WILL BE USED",
    ]:
        assert expected in text


def test_start_script_calls_dry_run_before_vite() -> None:
    lower_text = start_script_text().lower()

    dry_run_index = lower_text.index('call "%dry_run_script%"')
    dry_run_failure_gate_index = lower_text.index("l2n dry-run failed. web preview was not started.", dry_run_index)
    fatal_after_dry_run_index = lower_text.index("goto :fatal_exit", dry_run_failure_gate_index)
    vite_start_index = lower_text.index("call npm exec --offline -- vite ^")

    assert dry_run_index < dry_run_failure_gate_index < fatal_after_dry_run_index < vite_start_index


def test_start_script_uses_npm_exec_local_vite_without_cmd_shim_startup() -> None:
    lines = [line.strip().lower() for line in start_script_text().splitlines()]

    assert "call npm exec --offline -- vite ^" in lines
    assert "npm exec --offline -- vite ^" not in lines
    assert "call npx vite" not in lines

    forbidden_invocations = [
        "call node_modules\\.bin\\vite.cmd",
        "node_modules\\.bin\\vite.cmd",
        "call node_modules\\.bin\\vite",
        "node_modules\\.bin\\vite",
        "call vite.cmd",
        "vite.cmd",
        "call vite ",
        "vite ",
    ]
    for line in lines:
        if any(line.startswith(invocation) for invocation in forbidden_invocations):
            raise AssertionError(
                "Vite must be launched via npm exec in the current CMD, "
                f"not a cmd shim/direct vite call: {line}"
            )


def test_start_script_uses_dedicated_config_and_loopback_command() -> None:
    text = start_script_text()

    assert "mock-only-preview\\vite.config.ts" in text
    assert "--host 127.0.0.1" in text
    assert "--port 5174" in text
    assert "--strictPort" in text
    assert "START_HOST=127.0.0.1" in text
    assert "START_PORT=5174" in text


def test_start_script_forbidden_commands_are_absent() -> None:
    lower_text = start_script_text().lower()

    for forbidden in [
        "0.0.0.0",
        "npm run dev",
        "npm run preview",
        "npx vite",
        "apps/dsa-web/vite.config.ts",
        "--open",
        "start http",
        "explorer http",
        "uvicorn",
        "fastapi",
        "python main.py",
        "curl",
        "wget",
        "invoke-webrequest",
        "npm install",
        "npm ci",
        "winget install",
        "choco install",
        "pip install",
    ]:
        assert forbidden not in lower_text


def test_vite_config_exists() -> None:
    assert VITE_CONFIG_PATH.is_file()


def test_vite_config_contains_localhost_server_and_block_message() -> None:
    text = vite_config_text()

    for expected in [
        "127.0.0.1",
        "5174",
        "strictPort",
        "open: false",
        "MOCK_ONLY_PREVIEW_BLOCKED",
    ]:
        assert expected in text


def test_vite_config_forbidden_runtime_surface_is_absent() -> None:
    text = vite_config_text()

    for forbidden in [
        "0.0.0.0",
        "proxy",
        "target",
        "/api/v1",
        "VITE_API_URL",
        "import.meta.env",
        "src/api",
        "src/pages",
        "src/stores",
        "src/components",
        "src/contexts",
        "src/utils",
    ]:
        assert forbidden not in text


def test_vite_config_contains_guard_rules() -> None:
    text = vite_config_text()

    for expected in [
        "/mock-only-preview",
        "/src/mocks",
        "/src/main.tsx",
        "/src/App.tsx",
        "/api",
    ]:
        assert expected in text


def test_start_task_does_not_touch_protected_runtime_files() -> None:
    changed_files = {
        "scripts/windows_localhost_web_safe_preview_start.bat",
        "apps/dsa-web/mock-only-preview/vite.config.ts",
        "docs/windows_localhost_web_safe_preview_start.md",
        "tests/test_windows_localhost_preview_start_script.py",
        "docs/CHANGELOG.md",
    }

    assert changed_files.isdisjoint(PROTECTED_PATHS)
