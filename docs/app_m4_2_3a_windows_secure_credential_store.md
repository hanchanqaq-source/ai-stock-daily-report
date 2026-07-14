# App-M4.2.3A Windows 桌面端安全凭证存储基础

## 目标

本阶段只为 Electron 桌面端建立 Windows 本地安全凭证存储基础。它不接入真实设置页，不保存后端配置，不启动 Provider，不做连接测试，也不迁移现有 `.env`。

## Windows safeStorage / DPAPI 边界

Windows 下主进程使用 Electron `safeStorage`，由系统能力对敏感字符串加密。保存前必须确认 `safeStorage.isEncryptionAvailable()` 可用；不可用、检查异常或加密返回非法数据时，`set` 和主进程内部读取均返回低敏错误，不回退为明文文件。

非 Windows 平台当前返回 `unsupported_platform`，本阶段不擅自实现 macOS 或 Linux 凭证方案。

## 存储位置

凭证文件固定解析到当前用户 `%LOCALAPPDATA%` 下的应用子目录：

```text
%LOCALAPPDATA%\Daily Stock Analysis\secure\credentials.v1.json
```

路径解析要求：

- `%LOCALAPPDATA%` 缺失、为空或不是绝对路径时不可用。
- 不写入安装目录、仓库目录、当前工作目录、`.env`、localStorage、sessionStorage 或 IndexedDB。
- 仅创建凭证存储目录，不迁移数据库、日志、普通配置或其他运行文件。
- 该文件不加入桌面端更新备份列表，因为它位于 `%LOCALAPPDATA%`，应独立于安装目录更新流程持续存在。

## 文件格式

JSON 文件只保存低敏元数据和 `safeStorage.encryptString()` 返回 Buffer 的 Base64 表示：

```json
{
  "schemaVersion": 1,
  "encryptedValues": {
    "OPENAI_API_KEY": "base64-ciphertext"
  },
  "updatedAt": "2026-07-14T00:00:00.000Z"
}
```

禁止保存明文、明文备份、previousValue、密钥长度、密钥前后缀或可推断凭证内容的摘要。清除最后一个凭证后，当前实现保留空的版本化文件，并将 `encryptedValues` 写为空对象。

## 主进程和 renderer 边界

`readCredentialForMainProcess(key)` 只能作为 Electron 主进程内部函数使用，不通过 preload、IPC 或 `window.dsaDesktop` 暴露。

桌面入口使用 `secureMain.js` 先注册凭证 IPC 边界，再加载既有 `main.js`。这样不把凭证逻辑继续堆入原有桌面启动文件，也不改变既有启动、更新、后端和窗口生命周期实现。

preload 仅暴露：

- `window.dsaDesktop.getCredentialStatus(key)`
- `window.dsaDesktop.setCredential(key, value)`
- `window.dsaDesktop.clearCredential(key)`

renderer 只能查询是否已配置、保存新值、清除值，不能获取解密后的凭证、原始存储路径、原始加密 Buffer 或 `safeStorage` 对象。

## IPC 来源边界

固定 IPC 通道为：

- `desktop:credential-status`
- `desktop:set-credential`
- `desktop:clear-credential`

IPC 不是简单信任所有 localhost 页面。控制器只接受：

1. 当前已登记桌面 BrowserWindow 的 `webContents`；
2. 该窗口的主 frame，不接受 iframe 或其他 frame；
3. 打包内 `renderer/` 目录的本地文件页；或
4. 由桌面启动流程首次登记的精确 `http://127.0.0.1:<port>` origin。

可信后端 origin 只会从主 frame 的标准启动 URL 中登记一次，要求端口位于桌面端既有 `8000..8100` 范围、路径为 `/`，并带有 `desktop_version` 和数字 `cache_bust` 参数。其他 localhost 端口、外部页面、不同 BrowserWindow、子 frame 或来源不明页面均返回固定 `forbidden_source`。

handler 还会校验 payload 必须是精确结构：status/clear 只能包含 `key`，set 只能包含 `key` 和非空字符串 `value`。返回值只包含 `success`、`configured`、`supported` 和固定低敏 `errorCode`，不回显提交值。

凭证键只允许匹配 `^[A-Z][A-Z0-9_]{1,127}$`。本阶段不复制完整敏感字段业务白名单，避免与后端 `schema.is_sensitive` 真源漂移。后续 App-M4.2.3B 接入设置页时，调用方必须只允许服务端 `schema.is_sensitive=true` 的字段进入安全存储。

## 写入、错误和日志

写入使用同目录临时文件加 `rename` 的原子替换方式，尽量设置目录 `0700`、文件 `0600` 权限。写入失败会清理临时文件并保留旧文件；随机临时文件名生成失败、损坏 JSON、非法加密输出和解密异常均返回固定低敏错误，不直接覆盖或静默重置，也不返回原始文件内容。

错误和日志不得拼接敏感原文。加密失败、解密失败、存储不可用和损坏文件均返回固定低敏错误码。

## 当前明确未接入范围

当前 App-M4.2.3A 未：

- 接入 SettingsPage 或修改 Web 保存流程。
- 注入后端环境变量或修改 `SystemConfigService`。
- 启动真实 Provider、连接测试、AI、通知、账户、数据库写入、定时任务或交易。
- 迁移现有 `.env`。
- 修改配置导入导出。

下一步 App-M4.2.3B 才考虑在设置页和后端运行时中安全接入该存储基础。

## App-M4.2.3A.1 Windows DPAPI 实机 Smoke 验收

App-M4.2.3A.1 在安全凭证存储基础之上新增独立 Windows 本地 Smoke 验收工具，用于在进入 App-M4.2.3B 前确认真实 Electron `safeStorage` / Windows DPAPI 行为。该工具不接入设置页，不修改后端运行时，不读取或使用真实凭证。

- 入口脚本：`apps/dsa-desktop/scripts/windowsCredentialSmokeController.js`。
- Electron Runner：`apps/dsa-desktop/scripts/windowsCredentialSmokeElectron.js`，只加载 Electron `app` / `safeStorage` 和当前 `secureCredentialStore`，不加载 `main.js`，不创建窗口。
- Windows 双击入口：`scripts/windows_secure_credential_store_smoke.bat`。
- npm 入口：在 `apps/dsa-desktop` 运行 `npm run smoke:credential-store:windows`。
- 临时目录：Controller 在 `%TEMP%` / `os.tmpdir()` 下创建 `dsa-secure-credential-smoke-<random>`，并通过显式环境参数作为临时 `LOCALAPPDATA` 传给 Store；不会读取、备份、迁移或删除正式 `%LOCALAPPDATA%\Daily Stock Analysis\secure\credentials.v1.json`。
- 测试值：仅使用运行时生成的虚构值，不进入命令行参数、日志、文档、PR 描述或仓库文件。
- 验收阶段：write 阶段验证加密保存、同进程解密、磁盘无明文和合法密文；restart-read-clear 阶段通过新 Electron 子进程验证跨进程解密、clear 后未配置和清除后磁盘仍无明文。
- 输出协议：只输出 PASS/FAIL、阶段布尔结果和固定错误码；禁止输出测试值、密文、Buffer、文件内容、路径、环境变量或异常堆栈。

详细流程、PASS 标准和 Windows 本机操作见 [App-M4.2.3A.1 Windows DPAPI / safeStorage 本地实机 Smoke 验收工具](app_m4_2_3a_1_windows_dpapi_smoke.md)。mock 单元测试只验证控制流和隔离边界，**不等同于 Windows DPAPI 实机通过**。
