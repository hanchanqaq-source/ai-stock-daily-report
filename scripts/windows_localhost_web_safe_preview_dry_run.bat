@echo off
setlocal EnableExtensions

set "DRY_RUN_HOST=127.0.0.1"
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "DRY_RUN_PUSHED_ROOT="
set "DRY_RUN_PUSHED_WEB="
set "FAIL_REASON=Unexpected dry-run failure."

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

node --version >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Node is not available. Install Node manually, then rerun."
  goto :fatal_exit
)
for /f "delims=" %%V in ('node --version') do echo PASS Node version: %%V

npm --version >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=npm is not available. Install npm manually, then rerun."
  goto :fatal_exit
)
for /f "delims=" %%V in ('npm --version') do echo PASS npm version: %%V

if not exist "apps\dsa-web\node_modules" (
  set "FAIL_REASON=apps\dsa-web\node_modules is missing. Install dependencies manually before dry-run."
  goto :fatal_exit
)
call :pass "apps\dsa-web\node_modules exists."

pushd "apps\dsa-web" >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Cannot enter apps\dsa-web."
  goto :fatal_exit
)
set "DRY_RUN_PUSHED_WEB=1"

echo Running mock-only preview-entry test...
npm run test -- tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts
if errorlevel 1 (
  set "FAIL_REASON=mockOnlyPreviewEntry.test.ts failed."
  goto :fatal_exit
)

echo Running mock-only network-boundary test...
npm run test -- tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
if errorlevel 1 (
  set "FAIL_REASON=mockOnlyPreviewNetworkBoundary.test.ts failed."
  goto :fatal_exit
)

echo Running mock-only preview model test...
npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts
if errorlevel 1 (
  set "FAIL_REASON=mockOnlyPreview.test.ts failed."
  goto :fatal_exit
)

echo Running web build dry-run check...
npm run build
if errorlevel 1 (
  set "FAIL_REASON=web build dry-run check failed."
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
