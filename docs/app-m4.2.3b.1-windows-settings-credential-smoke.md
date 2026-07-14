# App-M4.2.3B.1 Windows 设置页安全凭证 Smoke

本验收工具覆盖 Windows 桌面端真实设置页链路：Web 设置页 → Electron preload → IPC → Windows `safeStorage` / DPAPI → 关闭 Electron → 重新启动 Electron → 设置页仍显示“已配置” → 清除凭证 → 设置页显示“未配置” → 清理临时目录。

## 入口

双击运行：

```bat
scripts\windows_settings_credential_smoke.bat
```

或在桌面端目录运行：

```bash
npm run smoke:settings-credential:windows
```

## 安全边界

- 不读取、复制、打印或修改 `.env`。
- 只使用运行时随机生成的虚构测试值，且测试值不会输出到终端、日志或结果协议。
- 使用隔离的临时 `LOCALAPPDATA`，不接触用户真实 `%LOCALAPPDATA%\Daily Stock Analysis` 凭证目录。
- Mock 服务仅监听 `127.0.0.1`，端口只在桌面信任范围 `8000`～`8100` 内选择空闲端口。
- 不启动正式 Python 后端，不调用真实 Provider、AI、通知、账户、数据库、交易或正式日报。
- 失败输出仅包含固定阶段和低敏 `errorCode`，不输出本机路径、环境变量、堆栈或测试值。

## 验证语义

Mock 后端的敏感字段始终返回 `value=''`、`raw_value_exists=false`、`is_masked=false`，因此页面中的“已配置”只能来自 Electron preload / IPC 查询 Windows DPAPI 后叠加的状态。重启阶段复用同一个临时 `LOCALAPPDATA`，用于验证跨 Electron 进程的 DPAPI 持久化，而不是由 Mock 后端制造已配置状态。

Electron 驱动只通过 `bootstrapDesktopMain({ loadMain: () => undefined })` 注册既有凭证 IPC，不加载正式 `main.js`，不启动 Python 后端、更新检查或正式桌面窗口。子进程要求标准 `LOCALAPPDATA` 与 `DSA_SETTINGS_CREDENTIAL_SMOKE_LOCALAPPDATA` 完全一致，并在不把覆盖后的 `LOCALAPPDATA` 误判为用户真实目录的前提下继续执行绝对路径、系统临时目录、smoke 前缀和防逃逸校验。

## 成功输出

成功时 BAT / npm 输出包含：

- `Settings page set: PASS`
- `Restart configured state: PASS`
- `Plaintext not returned: PASS`
- `Settings page clear: PASS`
- `Mock backend secret leak check: PASS`
- `Temp cleanup: PASS`
- `App-M4.2.3B.1 PASS`

## 前置条件

- Windows 环境。
- 已安装仓库本地桌面端依赖：`cd apps/dsa-desktop && npm ci`。
- 已生成 Web 构建产物：`cd apps/dsa-web && npm run build`。

