@echo off
setlocal EnableExtensions

set "DRY_RUN_HOST=127.0.0.1"
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "DRY_RUN_PUSHED_ROOT="
set "DRY_RUN_PUSHED_WEB="
set "FAIL_REASON=Unexpected dry-run failure."
set "NODE_EXE="
set "LAST_EXIT="
set "TEST_TIMEOUT_SECONDS=60"
set "BUILD_TIMEOUT_SECONDS=180"

echo ============================================================
echo Windows localhost web safe preview dry-run
echo DRY RUN ONLY
echo MOCK ONLY
echo LOCAL PREVIEW ONLY
echo HOST POLICY: 127.0.0.1 ONLY
echo NO WEB SERVER WILL BE STARTED
echo NO BACKEND WILL BE STARTED
echo NO REAL NETWORK
echo ============================================================

pushd "%REPO_ROOT%" >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Cannot locate repository root from script path."
  goto :fatal_exit
)
set "DRY_RUN_PUSHED_ROOT=1"

call :check_file "docs\CHANGELOG.md" "repository marker docs\CHANGELOG.md" || goto :fatal_exit
call :check_file "apps\dsa-web\package.json" "repository marker apps\dsa-web\package.json" || goto :fatal_exit
call :pass "Repository markers found."

call :check_file "apps\dsa-web\mock-only-preview\index.html" "mock-only preview HTML entry" || goto :fatal_exit
call :check_file "apps\dsa-web\src\mocks\preview-entry\mockOnlyPreviewEntry.ts" "mock-only preview TypeScript entry" || goto :fatal_exit
call :pass "Mock-only preview entry files found."

call :check_no_env_file ".env" || goto :fatal_exit
for %%F in (.env.*) do if /I not "%%~nxF"==".env.example" if exist "%%F" (
  set "FAIL_REASON=Environment file exists at repository root. Remove it before dry-run."
  goto :fatal_exit
)
call :check_no_env_file "apps\dsa-web\.env" || goto :fatal_exit
for %%F in (apps\dsa-web\.env.*) do if /I not "%%~nxF"==".env.example" if exist "%%F" (
  set "FAIL_REASON=Environment file exists under apps\dsa-web. Remove it before dry-run."
  goto :fatal_exit
)
call :pass "No .env files detected. Contents were not read."

if not "%DRY_RUN_HOST%"=="127.0.0.1" (
  set "FAIL_REASON=DRY_RUN_HOST must be 127.0.0.1."
  goto :fatal_exit
)
call :pass "Host policy is fixed to 127.0.0.1."

for /f "delims=" %%N in ('where node.exe') do (
  set "NODE_EXE=%%N"
  goto :node_found
)
:node_found
if not defined NODE_EXE (
  set "FAIL_REASON=Node is not available. Install Node manually, then rerun."
  goto :fatal_exit
)
"%NODE_EXE%" --version >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Node is not available. Install Node manually, then rerun."
  goto :fatal_exit
)
for /f "delims=" %%V in ('"%NODE_EXE%" --version') do echo PASS Node version: %%V

call npm --version >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=npm is not available. Install npm manually, then rerun."
  goto :fatal_exit
)
for /f "delims=" %%V in ('call npm --version') do echo PASS npm version: %%V

where powershell.exe >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=PowerShell is not available. Cannot enforce dry-run timeouts."
  goto :fatal_exit
)
call :pass "PowerShell timeout runner is available."

if not exist "apps\dsa-web\node_modules" (
  set "FAIL_REASON=apps\dsa-web\node_modules is missing. Install dependencies manually before dry-run."
  goto :fatal_exit
)
call :pass "apps\dsa-web\node_modules exists."
call :check_file "apps\dsa-web\node_modules\vitest\vitest.mjs" "local Vitest CLI entry" || goto :fatal_exit
call :pass "Local Vitest CLI entry found."

pushd "apps\dsa-web" >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Cannot enter apps\dsa-web."
  goto :fatal_exit
)
set "DRY_RUN_PUSHED_WEB=1"

echo Running local Vitest version diagnostic...
"%NODE_EXE%" "node_modules\vitest\vitest.mjs" --version
set "LAST_EXIT=%ERRORLEVEL%"
echo Vitest local mjs --version exit code: %LAST_EXIT%
if not "%LAST_EXIT%"=="0" (
  set "FAIL_REASON=local Vitest version diagnostic failed."
  goto :fatal_exit
)

echo Running mock-only preview-entry test...
call :run_timed "mockOnlyPreviewEntry.test.ts" "%TEST_TIMEOUT_SECONDS%" "npm run test -- tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts"
set "LAST_EXIT=%ERRORLEVEL%"
echo npm run test exit code: %LAST_EXIT%
if "%LAST_EXIT%"=="124" (
  set "FAIL_REASON=mockOnlyPreviewEntry.test.ts timed out after %TEST_TIMEOUT_SECONDS% seconds."
  goto :fatal_exit
)
if not "%LAST_EXIT%"=="0" (
  set "FAIL_REASON=mockOnlyPreviewEntry.test.ts failed with exit code %LAST_EXIT%."
  goto :fatal_exit
)

echo Running mock-only network-boundary test...
call :run_timed "mockOnlyPreviewNetworkBoundary.test.ts" "%TEST_TIMEOUT_SECONDS%" "npm run test -- tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts"
set "LAST_EXIT=%ERRORLEVEL%"
echo npm run test exit code: %LAST_EXIT%
if "%LAST_EXIT%"=="124" (
  set "FAIL_REASON=mockOnlyPreviewNetworkBoundary.test.ts timed out after %TEST_TIMEOUT_SECONDS% seconds."
  goto :fatal_exit
)
if not "%LAST_EXIT%"=="0" (
  set "FAIL_REASON=mockOnlyPreviewNetworkBoundary.test.ts failed with exit code %LAST_EXIT%."
  goto :fatal_exit
)

echo Running mock-only preview model test...
call :run_timed "mockOnlyPreview.test.ts" "%TEST_TIMEOUT_SECONDS%" "npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts"
set "LAST_EXIT=%ERRORLEVEL%"
echo npm run test exit code: %LAST_EXIT%
if "%LAST_EXIT%"=="124" (
  set "FAIL_REASON=mockOnlyPreview.test.ts timed out after %TEST_TIMEOUT_SECONDS% seconds."
  goto :fatal_exit
)
if not "%LAST_EXIT%"=="0" (
  set "FAIL_REASON=mockOnlyPreview.test.ts failed with exit code %LAST_EXIT%."
  goto :fatal_exit
)

echo Running web build dry-run check...
call :run_timed "npm run build" "%BUILD_TIMEOUT_SECONDS%" "npm run build"
set "LAST_EXIT=%ERRORLEVEL%"
echo npm run build exit code: %LAST_EXIT%
if "%LAST_EXIT%"=="124" (
  set "FAIL_REASON=web build dry-run check timed out after %BUILD_TIMEOUT_SECONDS% seconds."
  goto :fatal_exit
)
if not "%LAST_EXIT%"=="0" (
  set "FAIL_REASON=web build dry-run check failed with exit code %LAST_EXIT%."
  goto :fatal_exit
)

if defined DRY_RUN_PUSHED_WEB (
  popd >nul 2>nul
  set "DRY_RUN_PUSHED_WEB="
)
if defined DRY_RUN_PUSHED_ROOT (
  popd >nul 2>nul
  set "DRY_RUN_PUSHED_ROOT="
)

echo ============================================================
echo DRY RUN PASSED
echo No web server was started.
echo No backend was started.
echo No browser was opened.
echo No real network was requested by this script.
echo Next step is L2O or L2N follow-up, not direct production use.
echo ============================================================
exit /b 0

:check_file
if not exist "%~1" (
  set "FAIL_REASON=Missing %~2: %~1"
  exit /b 1
)
exit /b 0

:check_no_env_file
if exist "%~1" (
  set "FAIL_REASON=Environment file exists: %~1. Remove it before dry-run."
  exit /b 1
)
exit /b 0

:pass
echo PASS %~1
exit /b 0

:run_timed
set "DRY_RUN_TIMED_LABEL=%~1"
set "DRY_RUN_TIMED_TIMEOUT=%~2"
set "DRY_RUN_TIMED_COMMAND=%~3"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$label=$env:DRY_RUN_TIMED_LABEL; $timeout=[int]$env:DRY_RUN_TIMED_TIMEOUT; $cmd=$env:DRY_RUN_TIMED_COMMAND; $p=Start-Process -FilePath 'cmd.exe' -ArgumentList '/d','/s','/c',$cmd -NoNewWindow -PassThru; if (-not $p.WaitForExit($timeout * 1000)) { taskkill.exe /PID $p.Id /T /F > $null 2>&1; Write-Host ('FAIL ' + $label + ' timed out after ' + $timeout + ' seconds.'); exit 124 }; exit $p.ExitCode"
set "RUN_TIMED_EXIT=%ERRORLEVEL%"
set "DRY_RUN_TIMED_LABEL="
set "DRY_RUN_TIMED_TIMEOUT="
set "DRY_RUN_TIMED_COMMAND="
exit /b %RUN_TIMED_EXIT%

:fatal_exit
echo FAIL %FAIL_REASON%
echo Dry-run stopped before any web/backend/browser startup.
if defined DRY_RUN_PUSHED_WEB (
  popd >nul 2>nul
  set "DRY_RUN_PUSHED_WEB="
)
if defined DRY_RUN_PUSHED_ROOT (
  popd >nul 2>nul
  set "DRY_RUN_PUSHED_ROOT="
)
if not defined CI pause
exit /b 1
