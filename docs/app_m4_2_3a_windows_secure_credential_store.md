# App-M4.2.3A Windows 桌面端安全凭证存储基础

## 目标

本阶段只为 Electron 桌面端建立 Windows 本地安全凭证存储基础。它不接入真实设置页，不保存后端配置，不启动 Provider，不做连接测试，也不迁移现有 `.env`。

## Windows safeStorage / DPAPI 边界

Windows 下主进程使用 Electron `safeStorage`，由系统能力对敏感字符串加密。保存前必须确认 `safeStorage.isEncryptionAvailable()` 可用；不可用时 `set` 和主进程内部读取均返回低敏错误，不回退为明文文件。

非 Windows 平台当前返回 `unsupported_platform`，本阶段不擅自实现 macOS 或 Linux 凭证方案。

## 存储位置

凭证文件固定解析到当前用户 `%LOCALAPPDATA%` 下的应用子目录：

```text
%LOCALAPPDATA%\Daily Stock Analysis\secure\credentials.v1.json
```

路径解析要求：

- `%LOCALAPPDATA%` 缺失时不可用。
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

preload 仅暴露：

- `window.dsaDesktop.getCredentialStatus(key)`
- `window.dsaDesktop.setCredential(key, value)`
- `window.dsaDesktop.clearCredential(key)`

renderer 只能查询是否已配置、保存新值、清除值，不能获取解密后的凭证、原始存储路径、原始加密 Buffer 或 `safeStorage` 对象。

## IPC 边界

固定 IPC 通道为：

- `desktop:credential-status`
- `desktop:set-credential`
- `desktop:clear-credential`

IPC handler 会校验 payload 类型、凭证键格式、`set` 的非空字符串值、`clear` 不携带 value，并校验调用来源只允许桌面端本地页面。返回值只包含 `success`、`configured`、`supported` 和固定低敏 `errorCode`，不回显提交值。

凭证键只允许匹配 `^[A-Z][A-Z0-9_]{1,127}$`。本阶段不复制完整敏感字段业务白名单，避免与后端 `schema.is_sensitive` 真源漂移。后续 App-M4.2.3B 接入设置页时，调用方必须只允许服务端 `schema.is_sensitive=true` 的字段进入安全存储。

## 写入、错误和日志

写入使用同目录临时文件加 `rename` 的原子替换方式，尽量设置目录 `0700`、文件 `0600` 权限。写入失败会清理临时文件并保留旧文件；损坏 JSON 返回固定错误，不直接覆盖或静默重置，也不返回原始文件内容。

错误和日志不得拼接敏感原文。加密失败、解密失败、存储不可用和损坏文件均返回固定低敏错误码。

## 当前明确未接入范围

当前 App-M4.2.3A 未：

- 接入 SettingsPage 或修改 Web 保存流程。
- 注入后端环境变量或修改 `SystemConfigService`。
- 启动真实 Provider、连接测试、AI、通知、账户、数据库写入、定时任务或交易。
- 迁移现有 `.env`。
- 修改配置导入导出。

下一步 App-M4.2.3B 才考虑在设置页和后端运行时中安全接入该存储基础。
