@echo off
setlocal EnableExtensions

set "FAIL_COUNT=0"
set "DEMO_HTML=docs\demo\windows_local_demo_report_preview.html"

cls
echo ========================================
echo Demo report preview
echo ========================================
echo Offline demo only
echo No real data provider
echo No AI model call
echo No notification
echo No official report
echo No Git change
echo.

call :check_root
if errorlevel 1 goto summary
call :check_demo_html
if errorlevel 1 goto summary
call :open_demo_html

goto summary

:check_root
echo [CHECK] Repository root
if not exist "main.py" goto root_fail
if not exist "requirements.txt" goto root_fail
if not exist "scripts\windows_local_safe_preview.bat" goto root_fail
echo [OK] Repository root found
echo.
exit /b 0

:root_fail
echo [FAIL] Repository root not found or required files are missing
echo [TIP] Run this script from the repository root that contains main.py, requirements.txt, and scripts\windows_local_safe_preview.bat
echo.
set /a FAIL_COUNT+=1
exit /b 1

:check_demo_html
echo [CHECK] Demo HTML report
if not exist "%DEMO_HTML%" (
    echo [FAIL] %DEMO_HTML% not found
    echo [TIP] Restore the demo HTML file and retry
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [OK] Demo HTML report found
echo.
exit /b 0

:open_demo_html
echo [OPEN] Demo report preview
echo Offline demo only
echo No real data provider
echo No AI model call
echo No notification
echo No official report
echo No Git change
echo.
start "" "%DEMO_HTML%"
if errorlevel 1 (
    echo [FAIL] Could not open the demo HTML report
    echo [TIP] Open %DEMO_HTML% manually in a browser
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [OK] Browser open command sent
echo.
exit /b 0

:summary
echo ========================================
echo Demo Report Preview Summary
echo ========================================
if "%FAIL_COUNT%"=="0" (
    echo PASS: Demo report preview finished
    echo Offline demo only
    echo No real data provider
    echo No AI model call
    echo No notification
    echo No official report
    echo No Git change
) else (
    echo FAIL: Demo report preview did not finish
    echo [TIP] Fix the failed check above and retry
)
echo.
echo This window will stay open for screenshots.
pause
exit /b %FAIL_COUNT%
