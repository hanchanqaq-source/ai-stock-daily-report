@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "FAIL_COUNT=0"
set "NODE_EXE="
set "NPM_CMD="
set "SMOKE_EXIT=1"

cls
echo ========================================
echo Daily Stock Analysis - Windows DPAPI Smoke
echo ========================================
echo Uses Electron safeStorage / Windows DPAPI.
echo Uses only a temporary test directory and fake test value.
echo Does not start backend, browser window, provider, network, AI, notification, account, database, or trading flows.
echo.

pushd "%REPO_ROOT%" >nul 2>nul
if errorlevel 1 (
    echo [FAIL] Repository root could not be located from this script path
    set /a FAIL_COUNT+=1
    goto summary
)

call :check_file "AGENTS.md" "repository AGENTS.md" || goto summary
call :check_file "apps\dsa-desktop\package.json" "desktop package.json" || goto summary
call :check_file "apps\dsa-desktop\secureCredentialStore.js" "secure credential store" || goto summary

echo [CHECK] node.exe
for /f "delims=" %%N in ('where node.exe 2^>nul') do (
    set "NODE_EXE=%%N"
    goto node_found
)
:node_found
if not defined NODE_EXE (
    echo [FAIL] node.exe not found
    echo [TIP] Install Node.js manually, then rerun this script.
    set /a FAIL_COUNT+=1
    goto summary
)
"%NODE_EXE%" --version
if errorlevel 1 (
    echo [FAIL] node.exe cannot run
    set /a FAIL_COUNT+=1
    goto summary
)
echo [OK] node.exe found

echo [CHECK] npm.cmd
for /f "delims=" %%N in ('where npm.cmd 2^>nul') do (
    set "NPM_CMD=%%N"
    goto npm_found
)
:npm_found
if not defined NPM_CMD (
    echo [FAIL] npm.cmd not found
    echo [TIP] Install Node.js/npm manually, then rerun this script.
    set /a FAIL_COUNT+=1
    goto summary
)
call "%NPM_CMD%" --version
if errorlevel 1 (
    echo [FAIL] npm.cmd cannot run
    set /a FAIL_COUNT+=1
    goto summary
)
echo [OK] npm.cmd found

echo [CHECK] Electron dependency
if not exist "apps\dsa-desktop\node_modules\electron" (
    echo [FAIL] Electron dependency is missing
    echo [TIP] Run this command manually, then rerun this script:
    echo cd /d "%CD%\apps\dsa-desktop"
    echo npm ci
    set /a FAIL_COUNT+=1
    goto summary
)
echo [OK] Electron dependency found

echo [CHECK] Running Windows credential store smoke
cd /d "%CD%\apps\dsa-desktop"
call "%NPM_CMD%" run smoke:credential-store:windows
set "SMOKE_EXIT=!ERRORLEVEL!"
if not "!SMOKE_EXIT!"=="0" (
    echo [FAIL] Smoke command failed
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Smoke command passed
)
cd /d "%REPO_ROOT%"

goto summary

:check_file
if not exist "%~1" (
    echo [FAIL] Missing %~2: %~1
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [OK] Found %~2
exit /b 0

:summary
echo.
echo ========================================
echo Windows DPAPI Smoke Summary
echo ========================================
if "%FAIL_COUNT%"=="0" (
    echo PASS: Windows DPAPI smoke completed
    echo Write phase: see npm smoke summary above
    echo Restart-read phase: see npm smoke summary above
    echo Clear phase: see npm smoke summary above
    echo Temp cleanup: see npm smoke summary above
) else (
    echo FAIL: Windows DPAPI smoke did not complete
    echo Write phase: FAIL or not reached
    echo Restart-read phase: FAIL or not reached
    echo Clear phase: FAIL or not reached
    echo Temp cleanup: FAIL, warning, or not reached
    echo [TIP] Fix the failed check above and retry.
)
echo.
echo This window will stay open. Do not paste secrets here.
pause
popd >nul 2>nul
exit /b %FAIL_COUNT%
