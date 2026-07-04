# 账户 / 分组模型说明

> 项目级产品规则见 `docs/product_rules.md`。

统一资产模型见 `docs/asset_model.md`，后续账户分组、个人雷达、网页工作台均应复用该模型。资产状态管理见 `docs/asset_status_manager.md`，所有清仓、归档、删除操作必须先预览再确认。

## 1. 设计目标

账户不是实名用户，只是观察分组 / 投资组合。P5-D 阶段把“多用户”的公开仓库形态收敛为轻量 account group：每个账户分组代表一组关注资产，例如基金组、股票组、基金股票混合组、企业观察组或主题观察组。

本阶段只提供 example 配置、读取、校验、资产筛选、动态页面判断和结构化摘要；不做真实网页页面，不读取真实私人配置，不做股票 / 基金代码自动识别，不做名称或标签自动补全。

## 2. 为什么不用真实用户资料

公开仓库阶段不需要邮箱、手机号、身份证、登录密码，也不应收集这些资料。账户分组仅用于组织观察资产，避免把系统误建成复杂实名账号系统，并降低隐私泄露风险。

因此 example 配置必须使用 demo 数据，不写真实姓名、邮箱、手机号、身份证、webhook URL、Token、API Key 或其他 secret。

## 3. 账户结构

示例配置位于 `config/examples/account_groups.example.json`。顶层结构包含：

- `config_version`：配置版本。
- `account_groups`：账户 / 分组列表。

每个账户分组包含：

- `account_id`：示例账户分组 ID。
- `account_name`：示例账户分组名称。
- `enabled`：是否启用。
- `risk_profile`：风险偏好，沿用 `conservative` / `balanced` / `aggressive`。
- `description`：说明。
- `assets`：统一资产列表。

每个账户有一个 `assets` 列表。账户中的 `assets` 将作为后续个人雷达和网页工作台的主要输入。

## 4. 资产类型

统一资产字段包含：

- `asset_id`：资产 ID。
- `type`：资产类型。
- `code`：代码；example 可使用 `000000`。
- `name`：示例名称，避免伪装成真实识别结果。
- `market`：`CN` / `HK` / `US` / `JP` / `KR` / `GLOBAL` / `unknown`。
- `tags`：手工标签列表。
- `status`：资产状态。
- `weight_level`：1 到 5 的粗略关注程度 / 权重等级。
- `source_status`：信息来源状态。

支持的 `type`：

- `fund`：基金。
- `stock`：股票。
- `etf`：ETF。
- `company`：企业。
- `industry`：行业。
- `theme`：主题。
- `index`：指数。
- `unknown`：暂未确认。

## 5. 资产状态

支持的 `status`：

- `holding`：持有中。
- `watching`：收藏 / 观察。
- `cleared`：已清仓。
- `archived`：已归档。
- `deleted`：真正删除，后续谨慎使用。

资产必须支持状态管理。`holding` / `watching` 可显示在主页面相关模块；`cleared` 可后续进入历史页；`archived` / `deleted` 默认不显示在主页面。

## 6. 动态页面规则

账户分组的可显示页面由当前活跃资产自动判断：

- 有 `fund` 且无 `stock`：显示 `overview`、`funds`。
- 有 `stock` 且无 `fund`：显示 `overview`、`stocks`。
- 同时有 `fund` 和 `stock`：显示 `overview`、`funds`、`stocks`。
- 没有活跃资产：显示 `empty_state`，页面文案可表达为“请添加资产”。
- 后续有 `company`：可以显示 `overview`、`companies`。

`cleared` / `archived` / `deleted` 默认不算当前主页面活跃资产；只有 `holding` / `watching` 参与主页面判断。

## 7. 金额处理原则

public 仓库阶段只允许 `weight_level` 这种粗略权重等级。`weight_level` 只代表关注程度 / 权重等级，不是金额，不代表成本价、账户资产、收益金额或持仓市值。

public 仓库阶段不要保存真实金额、成本价、账户资产、收益金额、持仓金额或仓位金额。真实金额只能后续在 private 配置或本地网页工作台中可选启用，并且默认不上传 GitHub。

## 8. 信息来源规则

本阶段 example 默认使用 `source_status: manual_user_input`，表示用户手工输入的 demo 数据，不伪装成公开来源。

后续代码识别和标签补全必须遵守 `docs/source_verification.md`：

- 查得到且来源可核验时，才可标记为 `verified`。
- 查不到时标记为 `unknown`。
- 不确定时标记为 `pending_confirmation`。
- 多来源冲突时标记为 `conflict`。

所有自动识别、名称补全和标签推荐都必须保留可查证来源，不得把模型猜测伪装成事实。

## 9. 后续路线

- P5-E：统一资产模型增强。
- P5-F：代码自动识别。
- P5-G：标签自动建议。
- P5-H：资产状态管理。
- P5-I：持有 vs 收藏对比。
- Web-P7：账户配置页。
- Web-P8：代码批量导入与自动识别。
- Web-P9：基金 / 股票动态标签页。
