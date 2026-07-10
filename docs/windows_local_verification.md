# Windows 本地验证脚本

本文说明如何在真实 Windows 电脑上验证“股票基金质量分析系统”的本地程序运行状态。

本验证对应的报告/推送名称为“AI股票基金每日信息报告”。当前阶段只做 Windows 本地程序运行验证，不部署本地模型、不部署 NAS、不建设模型网关、不做 Docker 正式部署、不接真实数据、不发送真实通知、不自动交易。

## 脚本位置

```bat
scripts\windows_local_verify.bat
```

可以双击运行，也可以在项目根目录打开 `cmd` 或 PowerShell 后运行：

```bat
scripts\windows_local_verify.bat
```

## 运行前准备

1. 请安装 Python 3.11.x。
2. 如果使用 python.org 安装包，请勾选 `Add python.exe to PATH`。
3. 请在包含 `main.py` 和 `requirements.txt` 的项目根目录运行脚本。
4. 不需要填写真实 API Key、Token、Webhook 或股票列表。

## 脚本会做什么

脚本会按顺序执行：

1. 检查是否位于项目根目录。
2. 先检查 `py -3.11`，不可用时再检查 `python`。
3. 确认 Python 版本是 3.11.x。
4. 检查或创建 `.venv` 本地虚拟环境。
5. 检查 `.venv\Scripts\python.exe` 是否可用。
6. 询问是否安装/更新 `requirements.txt`，只有输入 `Y` 才执行安装。
7. 运行 `python main.py --help`。
8. 运行 `python main.py --local-smoke`。
9. 运行 `python -m pytest tests/test_windows_local_smoke.py -q`。
10. 运行 `python -m py_compile main.py src/notification.py tests/test_windows_local_smoke.py`。
11. 输出总体结果并保留窗口，方便截图。

## 脚本不会做什么

脚本不会：

- 读取或打印 `.env` 内容。
- 要求输入真实 API Key、Token 或 Webhook。
- 创建真实 `STOCK_LIST`。
- 调用真实 provider。
- 调用模型。
- 发送通知。
- 写正式日报。
- 删除文件。
- 修改 Git 配置。
- 执行 `git commit` 或 `git push`。
- 修改 `requirements.txt`。
- 自动安装 Python、模型、CUDA 或 Docker。

## 依赖安装说明

脚本创建或发现 `.venv` 后，会明确询问一次：

```text
是否安装/更新 requirements.txt？输入 Y 执行，其他输入跳过
```

- 输入 `Y`：执行 `.venv\Scripts\python.exe -m pip install -r requirements.txt`。
- 输入其他内容：跳过安装，但继续后续验证；最终结果会提示依赖可能未安装或未更新。

如果安装依赖失败，不一定是程序代码错误，常见原因包括网络、代理、GitHub 访问或 PyPI 镜像问题。可以稍后重试，不要因此修改项目代码，也不要关闭安全检查。

## 如何提交复核证据

脚本结束后会停留在窗口中。请不要立即关闭窗口，截图完整输出后发送给复核员。

如果总体结果未通过，请同时保留上方 `[失败]`、`[提示]` 和原始命令输出，方便判断是环境问题、依赖问题还是代码问题。
