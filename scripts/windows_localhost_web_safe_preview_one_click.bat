@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "ONE_CLICK_PUSHED_ROOT="
set "ONE_CLICK_PUSHED_WEB="
set "FAIL_REASON=Unexpected one-click preview failure."

echo ============================================================
echo Windows localhost web safe preview one-click
echo MOCK ONLY
echo LOCAL PREVIEW ONLY
echo HOST POLICY: 127.0.0.1 ONLY
echo NO BACKEND WILL BE STARTED
echo NO REAL API / PROVIDER / NOTIFICATION
echo ============================================================

pushd "%REPO_ROOT%" >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Cannot locate repository root from script path."
  goto :fatal_exit
)
set "ONE_CLICK_PUSHED_ROOT=1"

if not exist "apps\dsa-web\package-lock.json" (
  set "FAIL_REASON=Missing apps\dsa-web\package-lock.json."
  goto :fatal_exit
)

where node.exe >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Node is not available. Install Node manually, then rerun."
  goto :fatal_exit
)

call npm --version >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=npm is not available. Install npm manually, then rerun."
  goto :fatal_exit
)

pushd "apps\dsa-web" >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Cannot enter apps\dsa-web."
  goto :fatal_exit
)
set "ONE_CLICK_PUSHED_WEB=1"

if not exist "node_modules" (
  echo apps\dsa-web\node_modules is missing.
  echo Running npm ci...
  call npm ci
  set "NPM_CI_EXIT=%ERRORLEVEL%"
  echo npm ci exit code: %NPM_CI_EXIT%
  if not "%NPM_CI_EXIT%"=="0" (
    set "FAIL_REASON=npm ci failed with exit code %NPM_CI_EXIT%."
    goto :fatal_exit
  )
) else (
  echo PASS apps\dsa-web\node_modules exists. Skipping npm ci.
)

if defined ONE_CLICK_PUSHED_WEB (
  popd >nul 2>nul
  set "ONE_CLICK_PUSHED_WEB="
)

echo ============================================================
echo Starting safe preview script...
echo Open manually after ready:
echo http://127.0.0.1:5174/mock-only-preview/
echo Stop with Ctrl+C.
echo ============================================================

call "scripts\windows_localhost_web_safe_preview_start.bat"
set "START_EXIT=%ERRORLEVEL%"
echo one-click preview exit code: %START_EXIT%

if defined ONE_CLICK_PUSHED_ROOT (
  popd >nul 2>nul
  set "ONE_CLICK_PUSHED_ROOT="
)
exit /b %START_EXIT%

:fatal_exit
echo FAIL %FAIL_REASON%
echo One-click preview stopped before unsafe startup.
echo Do not run npm audit fix for this step.
if defined ONE_CLICK_PUSHED_WEB (
  popd >nul 2>nul
  set "ONE_CLICK_PUSHED_WEB="
)
if defined ONE_CLICK_PUSHED_ROOT (
  popd >nul 2>nul
  set "ONE_CLICK_PUSHED_ROOT="
)
if not defined CI pause
exit /b 1
