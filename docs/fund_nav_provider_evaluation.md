# 场外基金真实净值 Provider 接入评估

## 1. 评估目标

P5-R 只做场外基金真实净值 provider 接入评估：定义候选 provider registry、字段映射计划、启用条件、缓存策略、失败兜底、来源元数据要求和 public 仓库安全边界。本阶段不接真实基金净值，不联网，不读取真实 `user_config`，不保存真实净值、估算净值或涨跌幅。

## 2. 候选数据源

以下来源均为候选或测试来源，不写成已验证：

- 东方财富基金 / 天天基金：候选 `public_web` 来源，待评估每日净值与估算净值字段。
- 天天基金：候选 `public_web` 来源，待评估每日净值与估算净值字段。
- 基金公司官网：候选 `public_web` 来源，待评估每日净值字段。
- 支付宝 / 蚂蚁基金手动来源：`manual_or_app_only`，仅用于人工评估；不默认接入，不抓取个人支付宝数据，不读取真实账户。
- 本地 fixture：离线测试来源，仅验证结构和安全边界，不代表真实基金净值。

## 3. 接入前条件

真实 provider 进入下一阶段前必须完成：

- `provider_safety`：确认默认关闭、显式网络开关、无敏感信息、无 public 仓库真实数据写入。
- `field_mapping`：确认 daily_nav、estimated_nav 与 source metadata 字段契约。
- `timeout`：定义超时语义，并将超时映射为 `provider_timeout`。
- `retry`：默认重试上限为 0，避免在未评估阶段扩大请求风险。
- `cache_policy`：确认缓存默认关闭、`local_only`、stale 数据不可冒充 available。
- `source_metadata`：保留 provider、provider_type、source_status、checked_at、delay_note。
- `fund disclaimer`：估算净值必须提示“盘中估算仅供观察，最终以基金公司公布净值为准”。

## 4. dry-run 路线

后续路线必须逐步推进：

1. 先使用本地 fixture 验证结构化字段和失败语义。
2. 再做 dry-run adapter，只生成请求计划，不发起真实请求。
3. 再做 local-only 测试，使用本地 fixture 或人工构造的非真实样例验证标准化结果。
4. 最后才考虑真实 provider 最小闭环，并继续保持默认关闭和显式开关。

## 5. public 仓库安全边界

Public 仓库不得保存真实基金净值、真实估算净值、真实涨跌幅、账户信息、成本价、账户资产、token、API key、webhook、cookie、authorization、bearer、个人邮箱、手机号或身份证信息。

真实 provider 的缓存默认只能是 `local_only`。Fixture 可以进入仓库测试，但必须清楚标记为 fixture，不能冒充真实数据。

## 6. 后续路线

- P5-R1：场外基金净值 provider dry-run adapter
- P5-R2：场外基金净值 provider local-only 测试
- P5-R3：场外基金净值真实请求最小闭环

## P5-R1 Dry-run Adapter

P5-R1 已新增 dry-run adapter，用于在真实接入前验证请求计划和安全边界。dry-run 不请求真实基金净值，不保存真实数据。
