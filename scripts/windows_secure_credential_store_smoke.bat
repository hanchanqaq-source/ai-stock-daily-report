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
    echo.
    echo ========================================
    echo Windows DPAPI Smoke Summary
    echo ========================================
    echo FAIL: Windows DPAPI smoke did not complete
    echo [TIP] Fix the failed check above and retry.
    echo.
    echo This window will stay open. Do not paste secrets here.
    pause
    exit /b 1
)

echo [CHECK] repository files
if not exist "AGENTS.md" (
    echo [FAIL] Missing repository AGENTS.md: AGENTS.md
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Found repository AGENTS.md
)
if not exist "apps\dsa-desktop\package.json" (
    echo [FAIL] Missing desktop package.json: apps\dsa-desktop\package.json
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Found desktop package.json
)
if not exist "apps\dsa-desktop\secureCredentialStore.js" (
    echo [FAIL] Missing secure credential store: apps\dsa-desktop\secureCredentialStore.js
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Found secure credential store
)

echo [CHECK] node.exe
for /f "delims=" %%N in ('where node.exe 2^>nul') do if not defined NODE_EXE set "NODE_EXE=%%N"
if not defined NODE_EXE (
    echo [FAIL] node.exe not found
    echo [TIP] Install Node.js manually, then rerun this script.
    set /a FAIL_COUNT+=1
) else (
    "%NODE_EXE%" --version
    if errorlevel 1 (
        echo [FAIL] node.exe cannot run
        set /a FAIL_COUNT+=1
    ) else (
        echo [OK] node.exe found
    )
)

echo [CHECK] npm.cmd
for /f "delims=" %%N in ('where npm.cmd 2^>nul') do if not defined NPM_CMD set "NPM_CMD=%%N"
if not defined NPM_CMD (
    echo [FAIL] npm.cmd not found
    echo [TIP] Install Node.js/npm manually, then rerun this script.
    set /a FAIL_COUNT+=1
) else (
    call "%NPM_CMD%" --version
    if errorlevel 1 (
        echo [FAIL] npm.cmd cannot run
        set /a FAIL_COUNT+=1
    ) else (
        echo [OK] npm.cmd found
    )
)

echo [CHECK] Electron dependency
if not exist "apps\dsa-desktop\node_modules\electron\dist\electron.exe" (
    echo [FAIL] Electron executable is missing
    echo [TIP] Double-click the one-click first setup tool, then retry:
    echo "%CD%\scripts\windows_desktop_first_setup.bat"
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Electron executable found
)

if not "!FAIL_COUNT!"=="0" (
    echo.
    echo ========================================
    echo Windows DPAPI Smoke Summary
    echo ========================================
    echo FAIL: Windows DPAPI smoke did not complete
    echo Write phase: FAIL or not reached
    echo Restart-read phase: FAIL or not reached
    echo Clear phase: FAIL or not reached
    echo Temp cleanup: FAIL, warning, or not reached
    echo [TIP] Fix the failed check above and retry.
    echo.
    echo This window will stay open. Do not paste secrets here.
    pause
    popd >nul 2>nul
    exit /b 1
)

echo [CHECK] Running Windows credential store smoke
pushd "apps\dsa-desktop" >nul 2>nul
if errorlevel 1 (
    echo [FAIL] Cannot enter apps\dsa-desktop
    set "SMOKE_EXIT=1"
) else (
    call "%NPM_CMD%" run smoke:credential-store:windows
    set "SMOKE_EXIT=!ERRORLEVEL!"
    popd >nul 2>nul
)

if not "!SMOKE_EXIT!"=="0" (
    echo [FAIL] Smoke command failed
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Smoke command passed
)

echo.
echo ========================================
echo Windows DPAPI Smoke Summary
echo ========================================
if "!FAIL_COUNT!"=="0" (
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
exit /b !FAIL_COUNT!
