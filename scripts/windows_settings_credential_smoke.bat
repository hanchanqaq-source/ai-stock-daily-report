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
echo Daily Stock Analysis - Settings Credential Smoke
echo ========================================
echo App-M4.2.3B.1 validates the real Settings page to Electron IPC to Windows DPAPI path.
echo Uses only a random fake runtime value and an isolated temporary LOCALAPPDATA.
echo Does not read .env, start the Python backend, call providers, call AI, access accounts, databases, trading, notifications, or the public network.
echo.

pushd "%REPO_ROOT%" >nul 2>nul
if errorlevel 1 (
    echo [FAIL] stage: preflight errorCode: repository_root_unavailable
    echo.
    echo This window will stay open. Do not paste secrets here.
    pause
    exit /b 1
)

if not exist "apps\dsa-desktop\package.json" (
    echo [FAIL] stage: preflight errorCode: desktop_package_missing
    set /a FAIL_COUNT+=1
)
if not exist "static\index.html" (
    echo [FAIL] stage: preflight errorCode: web_dist_missing
    echo [TIP] Run: cd apps\dsa-web ^&^& npm run build
    set /a FAIL_COUNT+=1
)
for /f "delims=" %%N in ('where node.exe 2^>nul') do if not defined NODE_EXE set "NODE_EXE=%%N"
if not defined NODE_EXE (
    echo [FAIL] stage: preflight errorCode: node_missing
    set /a FAIL_COUNT+=1
)
for /f "delims=" %%N in ('where npm.cmd 2^>nul') do if not defined NPM_CMD set "NPM_CMD=%%N"
if not defined NPM_CMD (
    echo [FAIL] stage: preflight errorCode: npm_missing
    set /a FAIL_COUNT+=1
)
if not exist "apps\dsa-desktop\node_modules\electron" (
    echo [FAIL] stage: preflight errorCode: electron_dependency_missing
    echo [TIP] Run: cd apps\dsa-desktop ^&^& npm ci
    set /a FAIL_COUNT+=1
)

if not "!FAIL_COUNT!"=="0" goto fail

pushd "apps\dsa-desktop" >nul 2>nul
call "%NPM_CMD%" run smoke:settings-credential:windows
set "SMOKE_EXIT=!ERRORLEVEL!"
popd >nul 2>nul
if not "!SMOKE_EXIT!"=="0" (
    echo [FAIL] stage: app-m4.2.3b.1 errorCode: smoke_failed
    set /a FAIL_COUNT+=1
)

if "!FAIL_COUNT!"=="0" goto pass

:fail
echo.
echo App-M4.2.3B.1 FAIL
echo This window will stay open. Do not paste secrets here.
pause
popd >nul 2>nul
exit /b 1

:pass
echo.
echo App-M4.2.3B.1 PASS
echo This window will stay open. Do not paste secrets here.
pause
popd >nul 2>nul
exit /b 0
