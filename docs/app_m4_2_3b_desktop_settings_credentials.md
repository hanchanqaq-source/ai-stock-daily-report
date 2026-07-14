# App-M4.2.3B 桌面设置页安全凭证接入

App-M4.2.3A 已建立 Windows Electron `safeStorage` / DPAPI 安全凭证存储，App-M4.2.3A.1 已在真实 Windows 用户会话中完成写入、跨进程读取、清除和临时目录清理的 Smoke 验收。

App-M4.2.3B 将 Web 设置页既有的敏感字段 `keep / set / clear` 交互契约接入桌面安全凭证存储，但仍不启用真实 Provider、连接测试、AI、通知、账户、数据库、交易或正式日报。

## 运行时分流

### 普通 Web 运行时

- 保持现有服务端配置接口不变。
- 敏感字段继续使用服务端 `keep / set / clear` 契约。
- 本里程碑不改变 Web 部署行为。

### Electron 桌面运行时

当页面检测到 `window.dsaDesktop`：

1. `getConfig()` 仍从现有本地后端读取字段 schema 和非敏感配置。
2. 对 schema 标记为 `isSensitive` 的字段，通过桌面 IPC 查询本地 DPAPI 存储的 `configured` 状态。
3. 页面只获得 `configured / supported / success / errorCode` 等低敏状态，不获得已保存明文。
4. `action=set` 与 `action=clear` 从服务端校验和保存请求中分离。
5. 新值仅通过 Electron preload → IPC → 主进程安全存储写入 `%LOCALAPPDATA%` 下的加密凭证文件。
6. 非敏感字段仍使用现有服务端配置接口。
7. 保存完成后重新加载配置，并再次以桌面安全存储状态覆盖敏感字段的“已配置”显示。

## 保留 / 设置 / 清除语义

- `keep`：页面不产生更新项，不读取、不回显、不重写已有安全凭证。
- `set`：要求非空且不能是掩码占位符；值只传给桌面 IPC，不发送到 `/api/v1/system/config/validate` 或 `/api/v1/system/config`。
- `clear`：只提交字段 key，通过桌面 IPC 清除；不携带 value。

## 失败与边界

- 桌面运行时存在但安全凭证 IPC 不完整时，敏感字段保存会被阻断，不回退到服务端明文保存。
- IPC 异常只返回固定低敏错误码，不输出值、本地路径、环境变量或堆栈。
- 混合保存时，非敏感配置先通过现有后端更新，随后写入桌面安全凭证；若桌面写入失败，后端非敏感修改可能已经生效，用户可保留敏感字段草稿后重试。
- 设置页首次运行向后端读取 schema/非敏感配置的行为保持不变；本阶段不把 DPAPI 凭证注入后端 Provider 运行环境。
- Setup Status、Provider 连接测试、LLM/通知测试仍不能使用本地安全凭证，留待后续明确里程碑处理。

## 安全边界

- 不读取、打印、上传或提交 `.env`、token、webhook、API key、账号或真实凭证。
- 不把已保存值返回 renderer。
- 不写入 `localStorage`、`sessionStorage` 或 IndexedDB。
- 不启动新的后端、浏览器窗口、Provider、网络请求、AI、通知、账户、数据库或交易流程。
- 不修改安全凭证文件格式、DPAPI 加密实现或 Windows Smoke 工具。

## 验证

CI 应覆盖：

- 敏感 `set / clear` 与非敏感更新正确分流。
- 桌面 IPC 缺失时阻断敏感保存。
- 空值和掩码占位符被阻断。
- `set / clear` 只返回更新 key，不回显测试值。
- 桌面状态正确覆盖敏感字段的 `rawValueExists / isMasked / value` 展示元数据。
- Web TypeScript 构建和 lint 通过。

Windows 后续人工验收：在桌面设置页对一个虚构测试 key 执行设置、关闭并重启桌面端、确认仍显示“已配置”，再执行清除并确认变为“未配置”。该验收不得使用真实 Provider 密钥。
