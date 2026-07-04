# 资产信息自动补全框架说明

## 1. 设计目标

资产信息自动补全框架用于在代码自动识别之后，按可查证规则补全资产 `name`、`type`、`market`、`tags`、`industry`、`concept`、`fund_theme`、`sources`、`confidence` 和 `needs_user_confirmation` 等字段。

框架目标是让后续真实 provider 能够提供结构化补全建议，并且每个字段都保留状态、置信度、原因和来源证据。能查到才写；查不到为 `unknown`；不确定为 `pending_confirmation`；多来源冲突为 `conflict`。

## 2. 本阶段不做什么

P5-G 只建立可查证补全框架，不提供真实市场数据能力：

- 不联网搜索。
- 不接入真实第三方 API。
- 不编造真实股票、基金、企业、行业、概念或标签。
- 不把代码格式猜测写成确定事实。
- 不把 example fixture 当成真实数据。
- 不保存金额、成本价、账户资产、Webhook、Token、API Key、个人邮箱、手机号或身份证。

## 3. 与信息来源可查证规则的关系

补全结果必须遵守 `docs/source_verification.md` 中的信息来源可查证规则。所有补全字段都必须带 `status`、`confidence`、`reason`；可验证字段必须保留来源证据；未验证字段不能进入正式分析结论。

`fixture` 与 `manual_user_input` 只能作为测试、示例或用户输入来源，不能伪装为 `official` 或 `public_web`。

## 4. provider 机制

provider 只返回结构化补全结果，不直接修改 asset。每个 provider 结果必须包含：

- `provider_name`
- `provider_type`
- `code`
- `fields`

后续允许接入的 provider 类型包括：

- `official`
- `public_web`
- `market_data`
- `fund_data`
- `manual_user_input`
- `internal_history`
- `fixture`

本阶段提供的 `config/examples/asset_enrichment.example.json` 只用于 demo 和测试，其中示例名称、示例标签都不是可用于正式日报或周报的真实公开数据。

## 5. 多来源冲突规则

多个 provider 对同一字段给出相同值时，可以合并来源并取较高置信度。多个 provider 对同一字段给出不同值时，补全结果必须标记为 `conflict`，`needs_user_confirmation` 必须为 `true`，并在 `conflicts` 中记录冲突字段、冲突值和相关 provider。

`unknown`、`pending_confirmation` 和 `conflict` 均不得进入正式分析结论。

## 6. 用户确认原则

自动补全只是建议，用户可以确认、修改或删除。只有用户确认或真实可查证公开来源提供证据后，字段才可以从候选状态提升为可用状态。手动输入的标签可以作为用户自定义标签，但不能伪装为公开事实。

## 7. 后续路线

- P5-G 后续可接入真实可查证来源。
- P5-H 建设资产状态管理。
- P5-I 建设持有 vs 收藏对比。
- Web-P8 支持代码批量导入与自动识别。
