# App-M4.2.1 服务端敏感字段契约和统一脱敏

本阶段只实现服务端敏感字段契约和统一脱敏基础，不接入前端设置页的新交互，也不改变真实 Provider、导入导出或本地凭证存储方案。

## 服务端返回边界

- 所有 schema 中 `is_sensitive=true` 的字段，服务端配置读取响应都不得返回原始值。
- 敏感字段未配置或为空时，响应使用安全空状态：`value=""`、`raw_value_exists=false`、`is_masked=false`。
- 敏感字段已配置时，响应只返回统一 `mask_token` 作为 `value`，并设置 `raw_value_exists=true`、`is_masked=true`。
- 旧的服务端掩码白名单仍可作为额外保护，但 `schema.is_sensitive` 是最低安全边界。
- API 响应、校验错误和服务端更新结果不得回显提交的敏感字段原值。

## 更新操作语义

`SystemConfigUpdateItem` 在兼容旧 `{ key, value }` 的基础上增加可选 `action`：

- `keep`：保持原值，不需要 `value`；敏感字段即使带值也不得保存为新值。
- `set`：设置新值；敏感字段必须提供新的非空值。
- `clear`：明确清除；空字符串本身不等于清除。

敏感字段禁止把以下掩码占位保存为真实值：

- 当前响应中的 `mask_token`
- `masked-value`
- `********`

旧版 `{ key, value }` 请求仍尽量兼容：敏感字段提交当前 `mask_token`、`masked-value`、`********` 或空字符串时按保持原值处理；提交非空普通字符串时按旧兼容路径视为 `set`。普通非敏感字段保持既有保存行为。

## 本阶段未实现内容

- 暂未实现 Windows DPAPI。
- 暂未迁移到 `%LOCALAPPDATA%`。
- 暂未修改安全导出或导入功能。
- 未启用真实 Provider 或连接测试。
- 未接入 AkShare 正式页面、Longbridge、Tushare、账户读取或基金真实净值接口。
- 未调用 AI、通知、定时任务、交易或数据库写入。
- App-M4.2.2、App-M4.2.3 和 App-M4.3 尚未开始。
