@echo off
setlocal EnableExtensions

set "START_HOST=127.0.0.1"
set "START_PORT=5174"
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "START_PUSHED_ROOT="
set "START_PUSHED_WEB="
set "FAIL_REASON=Unexpected start failure."
set "DRY_RUN_SCRIPT=scripts\windows_localhost_web_safe_preview_dry_run.bat"
set "PREVIEW_CONFIG=apps\dsa-web\mock-only-preview\vite.config.ts"
set "LOCAL_VITE=apps\dsa-web\node_modules\.bin\vite.cmd"

echo ============================================================
echo Windows localhost web safe preview start
echo MOCK ONLY
echo LOCAL PREVIEW ONLY
echo LOOPBACK ONLY
echo HOST: 127.0.0.1
echo NO BACKEND WILL BE STARTED
echo NO BROWSER WILL BE OPENED
echo NO REAL API WILL BE USED
echo ============================================================

pushd "%REPO_ROOT%" >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Cannot locate repository root from script path."
  goto :fatal_exit
)
set "START_PUSHED_ROOT=1"
call :pass "Repository root located."

if not "%START_HOST%"=="127.0.0.1" (
  set "FAIL_REASON=START_HOST must be 127.0.0.1."
  goto :fatal_exit
)
call :pass "Host is fixed to 127.0.0.1."

if not "%START_PORT%"=="5174" (
  set "FAIL_REASON=START_PORT must be 5174."
  goto :fatal_exit
)
call :pass "Port is fixed to 5174."

call :check_file "%DRY_RUN_SCRIPT%" "L2N dry-run script" || goto :fatal_exit
call :check_file "%PREVIEW_CONFIG%" "mock-only preview Vite config" || goto :fatal_exit
call :check_file "%LOCAL_VITE%" "local Vite command" || goto :fatal_exit
call :pass "Required local files found."

echo Running L2N dry-run before starting preview...
call "%DRY_RUN_SCRIPT%"
if errorlevel 1 (
  set "FAIL_REASON=L2N dry-run failed. Web preview was not started."
  goto :fatal_exit
)
call :pass "L2N dry-run passed."

pushd "apps\dsa-web" >nul 2>nul
if errorlevel 1 (
  set "FAIL_REASON=Cannot enter apps\dsa-web."
  goto :fatal_exit
)
set "START_PUSHED_WEB=1"
call :pass "Entered apps\dsa-web."

echo ============================================================
echo Open manually:
echo http://127.0.0.1:5174/mock-only-preview/
echo.
echo Stop with Ctrl+C.
echo ============================================================

call node_modules\.bin\vite.cmd ^
  --config mock-only-preview\vite.config.ts ^
  --host 127.0.0.1 ^
  --port 5174 ^
  --strictPort
set "VITE_EXIT_CODE=%ERRORLEVEL%"

if defined START_PUSHED_WEB (
  popd >nul 2>nul
  set "START_PUSHED_WEB="
)
if defined START_PUSHED_ROOT (
  popd >nul 2>nul
  set "START_PUSHED_ROOT="
)

if not "%VITE_EXIT_CODE%"=="0" (
  echo FAIL Vite exited with code %VITE_EXIT_CODE%.
  if not defined CI pause
  exit /b %VITE_EXIT_CODE%
)

echo PASS Preview server stopped.
exit /b 0

:check_file
if not exist "%~1" (
  set "FAIL_REASON=Missing %~2: %~1"
  exit /b 1
)
exit /b 0

:pass
echo PASS %~1
exit /b 0

:fatal_exit
echo FAIL %FAIL_REASON%
echo Preview start stopped before Web startup when safety checks failed.
if defined START_PUSHED_WEB (
  popd >nul 2>nul
  set "START_PUSHED_WEB="
)
if defined START_PUSHED_ROOT (
  popd >nul 2>nul
  set "START_PUSHED_ROOT="
)
if not defined CI pause
exit /b 1
