@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "FAIL_COUNT=0"
set "DEPENDENCIES_STATUS=未安装/未更新（用户跳过或安装失败时验证可能受影响）"
set "PYTHON_CMD="
set "VENV_PYTHON=.venv\Scripts\python.exe"

cls
echo ========================================
echo 股票基金质量分析系统 - Windows 本地验证
echo ========================================
echo 本脚本只做本地安全检查。
echo 脚本不会打印、修改、上传或要求填写 .env 内容。
echo main.py 启动阶段可能会将本地 .env 加载到当前进程环境。
echo local-smoke 不会输出密钥、不调用真实 provider、模型或通知。
echo 不会生成正式日报、删除文件、修改 Git 配置、提交或推送。
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
echo [检查] 项目根目录
if not exist "main.py" goto root_fail
if not exist "requirements.txt" goto root_fail
if not exist "tests\test_windows_local_smoke.py" goto root_fail
if not exist "src\notification.py" goto root_fail
echo [通过] 已位于项目根目录
echo.
exit /b 0

:root_fail
echo [失败] 当前目录不是项目根目录，或缺少必要文件
echo [提示] 请在包含 main.py、requirements.txt、tests\test_windows_local_smoke.py 的项目根目录中运行本脚本
echo.
set /a FAIL_COUNT+=1
exit /b 1

:select_python
echo [检查] Python 解释器
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    echo [通过] 已找到 py -3.11
    py -3.11 --version
    echo.
    exit /b 0
)

echo [提示] py -3.11 不可用，继续检查 python
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    echo [通过] 已找到 python
    python --version
    echo.
    exit /b 0
)

echo [失败] 未找到 Python
echo [提示] 请安装 Python 3.11.x，并确保安装时勾选 Add python.exe to PATH
echo [提示] 本脚本不会自动安装 Python
echo.
set /a FAIL_COUNT+=1
exit /b 1

:check_python_version
echo [检查] Python 版本是否为 3.11.x
for /f "usebackq delims=" %%V in (`%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul`) do set "PYTHON_VERSION=%%V"
if not defined PYTHON_VERSION (
    echo [失败] 无法读取 Python 版本
    echo [提示] 请确认 Python 可正常运行
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [提示] 当前 Python 版本：%PYTHON_VERSION%
echo %PYTHON_VERSION% | findstr /r "^3\.11\." >nul
if errorlevel 1 (
    echo [失败] 当前 Python 版本不是 3.11.x
    echo [提示] 请切换到 Python 3.11.x 后重试
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [通过] Python 3.11.x
echo.
exit /b 0

:ensure_venv
echo [检查] 本地虚拟环境 .venv
if exist "%VENV_PYTHON%" (
    echo [通过] 已发现 .venv
    echo.
    exit /b 0
)

echo [提示] 未发现 .venv，正在创建
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    echo [失败] 创建 .venv 失败
    echo [提示] 请确认 Python venv 模块可用，并保留上方原始输出
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [通过] 已创建 .venv
echo.
exit /b 0

:check_venv_python
echo [检查] .venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo [失败] 未找到 %VENV_PYTHON%
    echo [提示] 虚拟环境可能创建失败，请保留本窗口截图发给复核员
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
"%VENV_PYTHON%" --version
if errorlevel 1 (
    echo [失败] .venv 中的 Python 无法运行
    echo [提示] 请保留上方原始输出
    echo.
    set /a FAIL_COUNT+=1
    exit /b 1
)
echo [通过] .venv Python 可用
echo.
exit /b 0

:prompt_requirements
echo [检查] requirements.txt 安装/更新
echo 是否安装/更新 requirements.txt？输入 Y 执行，其他输入跳过
set /p INSTALL_REQ="请输入选择 [Y/N]: "
if /i not "%INSTALL_REQ%"=="Y" (
    echo [提示] 已跳过 requirements.txt 安装/更新
    echo [提示] 后续验证仍会继续，但最终结果会标记依赖可能未安装
    set "DEPENDENCIES_STATUS=可能未安装/未更新（用户选择跳过）"
    echo.
    exit /b 0
)

echo [检查] 安装/更新 requirements.txt
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [失败] requirements.txt 安装/更新失败
    echo [提示] 网络问题不等于程序代码错误，可能是代理、GitHub 访问或 PyPI 镜像问题
    echo [提示] 可以稍后重试；不要因此修改项目代码；不要关闭安全检查
    set "DEPENDENCIES_STATUS=安装/更新失败（可能是网络或代理问题）"
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [通过] requirements.txt 已安装/更新
set "DEPENDENCIES_STATUS=已安装/更新"
echo.
exit /b 0

:run_help
echo [检查] main.py --help
"%VENV_PYTHON%" main.py --help
if errorlevel 1 (
    echo [失败] main.py --help
    echo [提示] 请查看上方原始命令输出；如提示缺少模块，请先安装 requirements.txt
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [通过] main.py --help
echo.
exit /b 0

:run_local_smoke
echo [检查] local-smoke
"%VENV_PYTHON%" main.py --local-smoke
if errorlevel 1 (
    echo [失败] local-smoke
    echo [提示] 请查看上方原始命令输出；如提示缺少模块，请先安装 requirements.txt
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [通过] local-smoke
echo.
exit /b 0

:run_pytest
echo [检查] pytest windows local smoke
"%VENV_PYTHON%" -m pytest tests/test_windows_local_smoke.py -q
if errorlevel 1 (
    echo [失败] pytest windows local smoke
    echo [提示] 请查看上方原始命令输出；如提示缺少模块，请先安装 requirements.txt
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [通过] pytest windows local smoke
echo.
exit /b 0

:run_py_compile
echo [检查] py_compile
"%VENV_PYTHON%" -m py_compile main.py src/notification.py tests/test_windows_local_smoke.py
if errorlevel 1 (
    echo [失败] py_compile
    echo [提示] 请查看上方原始命令输出；如提示缺少模块，请先安装 requirements.txt
    set /a FAIL_COUNT+=1
    echo.
    exit /b 1
)
echo [通过] py_compile
echo.
exit /b 0

:summary
echo ========================================
echo [总体结果]
echo 依赖状态：%DEPENDENCIES_STATUS%
if "%FAIL_COUNT%"=="0" (
    echo 结果：通过
    echo 所有 Windows 本地验证步骤已完成。
) else (
    echo 结果：未通过
    echo 失败步骤数量：%FAIL_COUNT%
    echo 请先查看上方 [失败] 和 [提示] 内容。
    echo 如果是网络或依赖安装问题，不等于程序代码错误。
)
echo 请截图本窗口，发送给复核员。
echo ========================================
pause
exit /b %FAIL_COUNT%
