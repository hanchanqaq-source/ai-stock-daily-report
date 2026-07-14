# App-M4.2.3A.1 Windows DPAPI / safeStorage 本地实机 Smoke 验收工具

App-M4.2.3A 已建立 Windows 桌面端安全凭证存储基础。进入 App-M4.2.3B（接入设置页或更靠近用户真实配置路径）前，必须先在真实 Windows 用户会话中确认 Electron `safeStorage` 能经由 Windows DPAPI 完成加密、跨进程解密和清除。本工具只做本地验收，不接入正式运行链路。

## 安全边界

- 使用真实 Electron `safeStorage`，不是 fake/mock safeStorage。
- 只在 `%TEMP%` / `os.tmpdir()` 下创建 `dsa-secure-credential-smoke-<random>` 临时目录，并把该目录作为子进程 `LOCALAPPDATA` 参数传给 `createSecureCredentialStore`。
- 不读取、不备份、不复制、不迁移、不删除正式凭证库：`%LOCALAPPDATA%\Daily Stock Analysis\secure\credentials.v1.json`。
- 测试 key 固定为 `DSA_SMOKE_TEST_KEY`，测试 value 为运行时临时生成的明显虚构值，只通过当前子进程环境变量传递，不写入命令行参数、日志、文档或 PR 描述。
- 不打印测试值、密文、Buffer、文件内容、环境变量内容、正式路径或异常堆栈。
- 不启动后端、不打开 BrowserWindow、不访问网络、不连接 Provider、不调用 AI、不发送通知、不读取账户/持仓、不写业务数据库、不交易。
- 当前仍未接 SettingsPage，未注入后端，未迁移 `.env`，未启用 Provider 或连接测试。

## 两阶段实机验收流程

### 阶段一：write

Electron 子进程在 `app.whenReady()` 后执行：

1. 确认 `process.platform === "win32"`。
2. 确认 `safeStorage.isEncryptionAvailable() === true`。
3. 使用临时 `LOCALAPPDATA` 创建当前 `secureCredentialStore`。
4. 写入虚构测试值。
5. 验证 `setCredential` 成功、`getCredentialStatus` 仅返回 configured 状态、主进程内部可解密为原测试值。
6. 检查临时 `credentials.v1.json` 不包含测试明文。
7. 检查 `encryptedValues` 中存在合法非空密文。
8. 只输出固定低敏 JSON 阶段结果。

### 阶段二：restart-read-clear

Controller 使用相同临时目录重启新的 Electron 子进程：

1. 重新创建 `secureCredentialStore`。
2. 验证重启后 `status.configured === true`。
3. 验证主进程内部解密结果与原测试值一致。
4. 执行 `clearCredential`。
5. 验证清除成功、`status.configured === false`、读取结果为未配置且 value 为 `null`。
6. 再次检查磁盘文件中不存在测试明文。
7. 只输出固定低敏 JSON 阶段结果。

Controller 只有 write、restart-read-clear 和临时目录清理全部成功时才返回退出码 0。

## 固定低敏输出

Controller 最终输出摘要只包含：

- `PASS` / `FAIL`
- write 是否通过
- restart-read 是否通过
- clear 是否通过
- cleanup 是否通过
- 固定错误码

子进程阶段结果只允许包含低敏布尔字段，例如 `success`、`encryptionAvailable`、`configured`、`plaintextAbsent`、`statusConfiguredOnly`、`cleared` 和固定 `errorCode`。如果结果中出现 `value`、`ciphertext`、`buffer`、`encryptedValues`、路径、环境变量或 stack 等字段，Controller 会阻断。

## 运行方式

### 命令行

在 Windows 上先安装桌面端依赖：

```bat
cd /d <repo>\apps\dsa-desktop
npm ci
npm run smoke:credential-store:windows
```

### 双击 BAT

也可以双击运行：

```bat
scripts\windows_secure_credential_store_smoke.bat
```

BAT 会自动定位仓库根目录，检查 `node.exe`、`npm.cmd`、桌面端 `package.json`、`secureCredentialStore.js` 和本地 Electron 依赖。若 Electron 未安装，只提示用户手动执行：

```bat
cd /d <repo>\apps\dsa-desktop
npm ci
```

BAT 不会自动全局安装工具，不会运行 `npm audit fix`，并会用 `pause` 保留窗口。

## PASS 判断标准

必须同时满足：

1. 当前平台为 Windows。
2. Electron `safeStorage` 可用。
3. write 阶段成功保存虚构测试值。
4. 临时磁盘文件无测试明文。
5. 同一 Electron 进程内可正确解密。
6. 重启 Electron 子进程后仍可正确解密。
7. status 结果只暴露 configured 状态。
8. clear 后状态为未配置，读取 value 为 `null`。
9. clear 后磁盘仍无测试明文。
10. 临时目录完成清理。

## 常见失败

- `Electron dependency is missing`：进入 `apps\dsa-desktop` 手动执行 `npm ci` 后重试。
- `unsupported_platform`：当前不是 Windows；Linux/macOS/mock 测试不能证明 Windows DPAPI 实机通过。
- `encryption_unavailable`：当前 Windows 用户会话下 Electron safeStorage/DPAPI 不可用，需要检查系统凭据环境或 Electron 运行方式。
- `child_process_failed`：Electron 子进程未能正常完成，保留 BAT 窗口截图供排查。
- `plaintext_detected`：临时文件中出现测试明文，必须阻断后续接入。
- `cleanup_failed`：临时目录清理失败；工具只输出低敏告警，不输出文件内容。

## 单元测试说明

仓库中的 mock 单元测试只验证 Controller 控制流、低敏结果协议、临时目录清理和 Runner 静态隔离边界。**mock 测试不等同于 Windows DPAPI 实机通过。**

云端/Linux 环境不能伪造 Windows DPAPI 结论；PR 中 Windows Smoke 必须标记为“待用户本机执行”。

## 进入 App-M4.2.3B 前置条件

只有用户在 Windows 本机执行本 Smoke 并取得 PASS 后，才允许继续 App-M4.2.3B。App-M4.2.3A.1 仍不接 SettingsPage、不注入后端、不迁移 `.env`、不启用 Provider/连接测试/AI/通知/账户/数据库/交易。
