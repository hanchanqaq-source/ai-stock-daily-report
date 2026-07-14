@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "DESKTOP_DIR=%REPO_ROOT%\apps\dsa-desktop"
set "ELECTRON_EXE=%DESKTOP_DIR%\node_modules\electron\dist\electron.exe"
set "SMOKE_BAT=%REPO_ROOT%\scripts\windows_secure_credential_store_smoke.bat"
set "NODE_EXE="
set "NPM_CMD="
set "FAIL_COUNT=0"
set "INSTALL_EXIT=1"
set "SMOKE_EXIT=1"

cls
echo ========================================
echo Daily Stock Analysis - First Setup
echo ========================================
echo Checks the local desktop runtime, installs repository-local dependencies only when needed,
echo then runs the Windows DPAPI credential smoke test.
echo Does not install global tools, run npm audit fix, read credentials, or start backend/network flows.
echo.

pushd "%REPO_ROOT%" >nul 2>nul
if errorlevel 1 (
    echo [FAIL] Repository root could not be located from this script path
    echo.
    echo This window will stay open. Do not paste secrets here.
    pause
    exit /b 1
)

echo [CHECK] repository files
if not exist "AGENTS.md" (
    echo [FAIL] Missing repository AGENTS.md
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Found repository AGENTS.md
)
if not exist "apps\dsa-desktop\package.json" (
    echo [FAIL] Missing desktop package.json
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Found desktop package.json
)
if not exist "apps\dsa-desktop\package-lock.json" (
    echo [FAIL] Missing desktop package-lock.json; npm ci cannot run safely
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Found desktop package-lock.json
)
if not exist "scripts\windows_secure_credential_store_smoke.bat" (
    echo [FAIL] Missing Windows credential smoke BAT
    set /a FAIL_COUNT+=1
) else (
    echo [OK] Found Windows credential smoke BAT
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

if not "!FAIL_COUNT!"=="0" (
    echo.
    echo ========================================
    echo First Setup Summary
    echo ========================================
    echo FAIL: prerequisites are incomplete
    echo [TIP] Fix the failed check above and rerun this same BAT.
    echo.
    echo This window will stay open. Do not paste secrets here.
    pause
    popd >nul 2>nul
    exit /b 1
)

echo [CHECK] Electron runtime
if exist "%ELECTRON_EXE%" (
    echo [OK] Electron runtime already exists; dependency installation skipped
) else (
    echo [INSTALL] Electron runtime is missing
    echo [INSTALL] Running npm ci in apps\dsa-desktop
    echo [INFO] This may download packages from the npm registry and only writes inside this repository.
    pushd "apps\dsa-desktop" >nul 2>nul
    if errorlevel 1 (
        echo [FAIL] Cannot enter apps\dsa-desktop
        set /a FAIL_COUNT+=1
    ) else (
        call "%NPM_CMD%" ci
        set "INSTALL_EXIT=!ERRORLEVEL!"
        popd >nul 2>nul
        if not "!INSTALL_EXIT!"=="0" (
            echo [FAIL] npm ci failed with exit code !INSTALL_EXIT!
            set /a FAIL_COUNT+=1
        )
    )

    if exist "%ELECTRON_EXE%" (
        echo [OK] Electron runtime installed successfully
    ) else (
        echo [FAIL] Electron executable is still missing after npm ci
        echo [TIP] Keep this window open and capture only the non-sensitive error lines above.
        set /a FAIL_COUNT+=1
    )
)

if not "!FAIL_COUNT!"=="0" (
    echo.
    echo ========================================
    echo First Setup Summary
    echo ========================================
    echo FAIL: desktop runtime setup did not complete
    echo [TIP] Rerun this same BAT after fixing the error above.
    echo.
    echo This window will stay open. Do not paste secrets here.
    pause
    popd >nul 2>nul
    exit /b 1
)

echo.
echo [RUN] Starting Windows DPAPI credential smoke
call "%SMOKE_BAT%"
set "SMOKE_EXIT=!ERRORLEVEL!"
popd >nul 2>nul
exit /b !SMOKE_EXIT!
