# 统一资产模型说明

## 1. 为什么需要统一资产模型

资产自动补全框架见 `docs/asset_enrichment.md`，所有补全结果必须保留来源、状态和置信度，并先转换为通过统一资产模型校验的安全草稿。
后续基金、股票、ETF、企业、行业、主题、指数都统一使用 `asset` 对象表达。账户分组、个人雷达、持有 / 收藏管理、持有 vs 收藏对比和本地网页工作台都应复用同一套资产字段、枚举、校验、摘要和公开安全视图，避免为基金、股票或企业观察分别维护平行结构。

本模型只定义结构和校验边界，不联网搜索、不自动补全真实名称、不自动补全标签。代码自动识别框架见 `docs/code_identifier.md`，所有识别结果必须遵守信息来源可查证规则。

## 2. 标准字段

标准 `asset` 字段如下：

- `asset_id`：唯一资产 ID。
- `type`：资产类型。
- `code`：基金代码、股票代码、企业代码或主题代码；可以为空字符串，但字段必须存在。
- `name`：资产名称；example 阶段允许示例名称。
- `market`：市场。
- `tags`：标签数组；手动输入标签不得伪装为自动验证结果。
- `status`：资产状态。
- `weight_level`：1 到 5 的关注权重，不是金额。
- `source_status`：来源状态，后续对接信息来源可查证规则。
- `notes`：可选备注，不能包含敏感信息、金额、成本价、账户资产或 secret。

## 3. 资产类型

`type` 只允许以下值：

- `fund`：基金。
- `stock`：股票。
- `etf`：ETF。
- `company`：企业。
- `industry`：行业。
- `theme`：主题。
- `index`：指数。
- `unknown`：暂未确认。

本阶段不根据代码自动判断资产类型。

## 4. 资产状态

`status` 只允许以下值：

- `holding`：持有中。
- `watching`：收藏 / 观察。
- `cleared`：已清仓。
- `archived`：已归档。
- `deleted`：真正删除，后续谨慎使用。

`holding` / `watching` 视为 active；`cleared` / `archived` / `deleted` 默认不算主页面 active。资产状态管理见 `docs/asset_status_manager.md`，所有清仓、归档、删除操作必须先预览再确认。当前阶段不实现物理删除。

## 5. 市场字段

`market` 只允许以下值：

- `CN`：A 股 / 中国基金。
- `HK`：港股。
- `US`：美股。
- `JP`：日本市场。
- `KR`：韩国市场。
- `GLOBAL`：全球或跨市场。
- `unknown`：暂未确认。

本阶段不联网识别市场。

## 6. 来源状态

`source_status` 只允许以下值：

- `manual_user_input`：用户手动输入。
- `verified`：已验证。
- `unknown`：未知。
- `pending_confirmation`：待确认。
- `conflict`：来源冲突。

用户手动输入可以保存，但必须标记为 `manual_user_input`；`unknown` 不能当成 `verified`；`pending_confirmation` 不能当成正式事实；不得编造来源或标签。

## 7. public 阶段金额规则

public 仓库不保存真实金额、成本价、账户资产、收益金额、Webhook、Token、API Key、邮箱、手机号、身份证等敏感信息。资产模型只允许使用 `weight_level` 表达 1 到 5 的粗略关注权重；`weight_level` 不是金额，也不能反推出真实仓位。

公开安全视图只输出 `asset_id`、`type`、`code`、`name`、`market`、`tags`、`status`、`weight_level`、`source_status`。

## 8. 信息来源规则

后续自动识别、自动补全名称、类型、市场、标签、来源和置信度时，必须遵守 `docs/source_verification.md`。不能把未知值写成已验证事实，不能把待确认值用于正式结论，不能编造来源、名称或标签。

## 9. 后续路线

- P5-F：代码自动识别框架。
- P5-G：自动补全名称、类型、市场、标签、来源、置信度。
- P5-H：资产状态管理。
- P5-I：持有 vs 收藏对比。
- P5-J：动态基金 / 股票页面逻辑。
