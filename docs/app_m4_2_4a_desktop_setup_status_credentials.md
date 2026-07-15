# App-M4.2.4A 桌面 Setup Status 安全凭证状态接入

App-M4.2.4A 在已有 Windows Electron `safeStorage` / DPAPI 安全凭证存储和设置页敏感字段叠加基础上，让首次设置 Setup Status 能识别桌面安全凭证库中的“已配置”状态。

## 契约

新增只读低敏接口：

```http
POST /api/v1/system/config/setup/status/overlay
```

请求体只允许：

```json
{
  "configured_secret_keys": ["GEMINI_API_KEY"]
}
```

该接口只接收键名，不接收 `value` 或任何凭证明文。后端只接受当前 Web 设置 schema 中标记为敏感字段的键；未知键、非敏感键或多余字段会被拒绝。

## 数据流

1. 普通 Web 继续调用 `GET /api/v1/system/config/setup/status`，行为不变。
2. Electron 设置页先通过现有 `systemConfigApi.getConfig()` 获得已叠加 DPAPI 状态的配置项。
3. 前端只从已加载配置中收集 `schema.isSensitive && rawValueExists && isMasked` 的字段名。
4. 桌面端将这些低敏字段名提交到 overlay 接口。
5. 后端将这些字段名作为独立 presence set 传入 Setup Status 计算，只在凭证存在性判断处查询该 set；不会把统一 sentinel 写入 URL、JSON、header 或凭证字段。

## 安全边界

- 不返回凭证明文给 renderer。
- 不把 DPAPI 凭证注入 Python 后端、Provider、AI、通知、账户、数据库、交易或正式日报。
- 不读取、打印、修改、上传或提交 `.env`、token、API key 或 webhook。
- 不修改 `os.environ`，不写 `.env`，不 reload runtime。
- 不修改 DPAPI 文件格式、`safeStorage` 实现或 Windows Smoke 工具。
- Electron overlay 请求失败时 fail closed：前端保留原始后端 GET 结果，不伪造 configured。
- `ready_for_smoke` 仍沿用后端既有规则，只由 `llm_primary` 和 `stock_list` 阻断项决定。

## 非目标

本阶段不做 Provider 连接测试、不验证凭证可用性、不启动真实模型或通知渠道；只把桌面安全凭证库的低敏“存在性”交给后端既有规则参与 Setup Status 计算。
