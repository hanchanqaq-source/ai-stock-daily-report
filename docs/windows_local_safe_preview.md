# Windows 本地安全预览启动入口

这个脚本是给已完成 L1 Windows 本地基础验证用户准备的一键安全预览入口，文件路径是 `scripts\windows_local_safe_preview.bat`。它只使用项目根目录下现有的 `.venv\Scripts\python.exe` 运行：

```bat
main.py --local-smoke
```

它的目标是让零基础用户在后续日常确认本地环境是否还能安全启动时，不需要每次重新执行完整验证流程。

## 适合什么时候用

适合以下场景：

- 你已经完成过 L1 Windows 本地验证。
- 你只想快速确认本地安全预览入口还能运行。
- 你不想重新安装依赖、运行 pytest 或执行完整验证。
- 你需要保留命令窗口，方便截图给维护者排查。

## 使用前提

使用前请先完成 L1 Windows 本地验证，并确认下面这些基础条件已经通过：

- Windows 本地 Python 可用。
- Git 可用。
- `.venv` 虚拟环境可用。
- `requirements.txt` 已经安装完成。
- `main.py --local-smoke` 在本地验证阶段可以运行。

如果还没有完成 L1 验证，请先在项目根目录运行：

```bat
scripts\windows_local_verify.bat
```

## 运行方式

在项目根目录双击或通过命令行运行：

```bat
scripts\windows_local_safe_preview.bat
```

脚本会检查当前目录是否像项目根目录，并检查 `.venv\Scripts\python.exe` 是否存在。检查通过后，它会运行 `main.py --local-smoke`，最后显示 PASS 或 FAIL，并用 `pause` 保留窗口，方便截图。

## 它不会做什么

这个脚本只做本地安全预览，不会执行真实业务流程：

- 不接真实数据。
- 不调用 AI。
- 不发通知。
- 不写正式日报。
- 不改 Git。
- 不删除文件。
- 不安装或更新 `requirements.txt`。
- 不运行 pytest。
- 不启动 Web 服务或调度任务。
- 不读取、打印或要求填写 `.env` 内容。

## 如果提示 `.venv` 不存在

如果脚本提示 `.venv\Scripts\python.exe` 不存在，请先回到项目根目录运行：

```bat
scripts\windows_local_verify.bat
```

完成 L1 验证后，再重新运行：

```bat
scripts\windows_local_safe_preview.bat
```
