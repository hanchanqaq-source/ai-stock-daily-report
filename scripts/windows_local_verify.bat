@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

set "FAIL_COUNT=0"
set "DEPENDENCIES_STATUS=Not installed or not updated - validation may be affected if skipped or failed"
set "PYTHON_CMD="
set "PYTHON_VERSION="
set "INSTALL_REQ="
set "VENV_PYTHON=.venv\Scripts\python.exe"

cls
echo ========================================
echo Daily Stock Analysis - Windows Local Verify
echo ========================================
echo This script only runs local safe checks.
echo It will not print, edit, upload, or ask you to fill .env content.
echo main.py startup may load local .env into the current Python process environment.
echo local-smoke will not print secrets, call real providers, call models, or send notifications.
echo It will not generate official daily reports, delete files, change Git config, commit, or push.
echo.

call :check_root
if errorlevel 1 goto summary
call :select_python
if not defined PYTHON_CMD goto summary
call :check_python_version
if errorlevel 1 goto summary
call :ensure_venv
if errorlevel 1 goto summary
call :check_venv_python
if errorlevel 1 goto summary
call :prompt_requirements
call :run_help
call :run_local_smoke
call :run_pytest
call :run_py_compile

goto summary

:check_root
echo [CHECK] Repository root
if not exist "main.py" goto root_fail
if not exist "requirements.txt" goto root_fail
if not exist "tests\test_windows_local_smoke.py" goto root_fail
if not exist "src\notification.py" goto root_fail
echo [OK] Repository root found
echo.
exit /b 0

:root_fail
echo [FAIL] Repository root not found or required files are missing
echo [TIP] Run this script from the repository root that contains main.py, requirements.txt, and tests\test_windows_local_smoke.py
echo.
set /a FAIL_COUNT+=1
exit /b 1

:select_python
echo [CHECK] Python interpreter
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    echo [OK] py -3.11 found
    py -3.11 --version
    echo.
    exit /b 0
)

echo [TIP] py -3.11 is not available; checking python
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    echo [OK] python found
    python --version
    echo.
    exit /b 0
)

echo [FAIL] Python 3.11 not found
echo [TIP] Please install Python 3.11.x and enable Add python.exe to PATH during installation
echo [TIP] This script will not install Python automatically
echo.
set /a FAIL_COUNT+=1
exit /b 1

:check_python_version
echo [CHECK] Python 3.11.x
for /f "usebackq delims=" %%V in (`%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul`) do set "PYTHON_VERSION=%%V"
if not defined PYTHON_VERSION (
    echo [FAIL] Could not read Python version
    echo [TIP] Make sure Python can run normally
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [TIP] Current Python version: %PYTHON_VERSION%
echo %PYTHON_VERSION% | findstr /r "^3\.11\." >nul
if errorlevel 1 (
    echo [FAIL] Current Python version is not 3.11.x
    echo [TIP] Switch to Python 3.11.x and retry
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [OK] Python 3.11.x
echo.
exit /b 0

:ensure_venv
echo [CHECK] Local virtual environment .venv
if exist "%VENV_PYTHON%" (
    echo [OK] .venv found
    echo.
    exit /b 0
)

echo [TIP] .venv not found; creating it now
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    echo [FAIL] Failed to create .venv
    echo [TIP] Make sure the Python venv module is available and keep the raw output above
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [OK] .venv created
echo.
exit /b 0

:check_venv_python
echo [CHECK] .venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo [FAIL] %VENV_PYTHON% not found
    echo [TIP] The virtual environment may have failed to create; keep a screenshot of this window for review
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
"%VENV_PYTHON%" --version
if errorlevel 1 (
    echo [FAIL] Python inside .venv cannot run
    echo [TIP] Keep the raw output above
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [OK] .venv Python is available
echo.
exit /b 0

:prompt_requirements
echo [CHECK] requirements.txt install or update
echo Install or update requirements.txt? Type Y to run it; any other input skips it.
set /p INSTALL_REQ="Enter choice [Y/N]: "
if /i not "%INSTALL_REQ%"=="Y" (
    echo [TIP] Skipped requirements.txt install or update
    echo [TIP] Later checks will continue, but the final result will note that dependencies may be missing
    set "DEPENDENCIES_STATUS=May be missing or outdated - user skipped install or update"
    echo.
    exit /b 0
)

echo [CHECK] pip install -r requirements.txt
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [FAIL] requirements.txt install or update failed
    echo [TIP] Network issues do not necessarily mean a code problem; check proxy, GitHub access, or PyPI mirror settings
    echo [TIP] Retry later if needed; do not change project code or disable safety checks for this
    set "DEPENDENCIES_STATUS=Install or update failed - possible network or proxy issue"
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [OK] requirements.txt installed or updated
echo.

echo [CHECK] pytest install or update
"%VENV_PYTHON%" -m pip install pytest
if errorlevel 1 (
    echo [FAIL] pytest install or update failed
    echo [TIP] Network issues do not necessarily mean a code problem; check proxy, GitHub access, or PyPI mirror settings
    echo [TIP] Retry later if needed; pytest is required for the windows local smoke test
    set "DEPENDENCIES_STATUS=pytest install or update failed - possible network or proxy issue"
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [OK] pytest installed or updated
set "DEPENDENCIES_STATUS=Installed or updated, including pytest"
echo.
exit /b 0

:run_help
echo [CHECK] main.py --help
"%VENV_PYTHON%" main.py --help
if errorlevel 1 (
    echo [FAIL] main.py --help
    echo [TIP] Check the raw output above; if modules are missing, install requirements.txt first
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [OK] main.py --help
echo.
exit /b 0

:run_local_smoke
echo [CHECK] local-smoke
"%VENV_PYTHON%" main.py --local-smoke
if errorlevel 1 (
    echo [FAIL] local-smoke
    echo [TIP] Check the raw output above; if modules are missing, install requirements.txt first
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [OK] local-smoke
echo.
exit /b 0

:run_pytest
echo [CHECK] pytest windows local smoke
"%VENV_PYTHON%" -m pytest tests/test_windows_local_smoke.py -q
if errorlevel 1 (
    echo [FAIL] pytest windows local smoke
    echo [TIP] Check the raw output above; if modules are missing, install requirements.txt first
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [OK] pytest windows local smoke
echo.
exit /b 0

:run_py_compile
echo [CHECK] py_compile
"%VENV_PYTHON%" -m py_compile main.py src/notification.py tests/test_windows_local_smoke.py
if errorlevel 1 (
    echo [FAIL] py_compile
    echo [TIP] Check the raw output above; if modules are missing, install requirements.txt first
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [OK] py_compile
echo.
exit /b 0

:summary
echo ========================================
echo [SUMMARY]
echo Dependencies: %DEPENDENCIES_STATUS%
if "%FAIL_COUNT%"=="0" (
    echo Result: PASS
    echo All Windows local verification steps completed.
) else (
    echo Result: FAIL
    echo Failed steps: %FAIL_COUNT%
    echo Review the [FAIL] and [TIP] messages above first.
    echo Network or dependency install issues do not necessarily mean a code problem.
)
echo Take a screenshot of this window and send it to the reviewer.
echo ========================================
pause
exit /b %FAIL_COUNT%
