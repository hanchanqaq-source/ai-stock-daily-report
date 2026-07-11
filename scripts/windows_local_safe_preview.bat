@echo off
setlocal EnableExtensions

set "FAIL_COUNT=0"
set "VENV_PYTHON=.venv\Scripts\python.exe"

cls
echo ========================================
echo Daily Stock Analysis - Safe Preview
echo ========================================
echo Safe preview started
echo No real data provider
echo No AI model call
echo No notification
echo No official report
echo No Git change
echo.

call :check_root
if errorlevel 1 goto summary
call :check_venv_python
if errorlevel 1 goto summary
call :run_local_smoke

goto summary

:check_root
echo [CHECK] Repository root
if not exist "main.py" goto root_fail
if not exist "requirements.txt" goto root_fail
if not exist "scripts\windows_local_verify.bat" goto root_fail
echo [OK] Repository root found
echo.
exit /b 0

:root_fail
echo [FAIL] Repository root not found or required files are missing
echo [TIP] Run this script from the repository root that contains main.py, requirements.txt, and scripts\windows_local_verify.bat
echo.
set /a FAIL_COUNT+=1
exit /b 1

:check_venv_python
echo [CHECK] .venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo [FAIL] %VENV_PYTHON% not found
    echo [TIP] Run scripts\windows_local_verify.bat first
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
"%VENV_PYTHON%" --version
if errorlevel 1 (
    echo [FAIL] Python inside .venv cannot run
    echo [TIP] Run scripts\windows_local_verify.bat first
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [OK] .venv Python is available
echo.
exit /b 0

:run_local_smoke
echo [CHECK] main.py --local-smoke
"%VENV_PYTHON%" main.py --local-smoke
if errorlevel 1 (
    echo [FAIL] main.py --local-smoke
    echo [TIP] Keep this window open and take a screenshot for review
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [OK] main.py --local-smoke
echo.
exit /b 0

:summary
echo ========================================
echo Safe Preview Summary
echo ========================================
if "%FAIL_COUNT%"=="0" (
    echo PASS: Safe preview finished
    echo Safe preview started
    echo No real data provider
    echo No AI model call
    echo No notification
    echo No official report
    echo No Git change
) else (
    echo FAIL: Safe preview did not finish
    echo [TIP] Fix the failed check above and retry
)
echo.
echo This window will stay open for screenshots.
pause
exit /b %FAIL_COUNT%
