# A股 / ETF Provider Dry-run Adapter 说明

P5-Q2 新增 local-only provider，用于在不联网情况下验证字段映射和结果标准化；dry-run 仍只验证请求计划，不处理 provider response。

## 1. 设计目标

A股 / ETF provider dry-run adapter 用于在真实 provider 接入前验证请求计划和安全检查。它只读取 `provider_registry` 中的候选 provider 元数据，检查 provider 是否默认关闭、是否需要 `network_enabled`、是否允许写入 public repo，以及是否具备字段映射、缓存策略和失败兜底策略。

本 adapter 不请求真实行情、不联网、不导入候选 provider SDK、不读取真实 `user_config`，也不保存真实价格、涨跌幅或成交额。返回结果只能标记为 dry-run / unsupported / invalid request 等状态，不能标记为 available real data。

## 2. 支持范围

本阶段仅支持以下 CN 市场对象生成 dry-run plan：

- A股 `stock`
- A股 `etf`
- A股 `official index`

`market` 可使用 `CN`、`cn` 或 `A股`，内部统一按 `CN` 处理。官方指数需要通过 `item_type=official_index`、`is_official_index=true` 或等价字段显式标记。

## 3. 不支持范围

以下对象不进入 A股 / ETF quote provider：

- `fund`：场外基金应使用 `fund_nav_provider`。
- `company`：企业本身不是可直接报价对象，需要关联 stock asset。
- `industry` / `theme`：后续通过指数或系统计算指标实现。
- `computed_indicator`：由市场广度模块生成，不直接请求 provider 行情。
- `unknown`：视为非法 dry-run request。
- 非 CN 市场资产：返回 `unsupported`。

## 4. Dry-run 结果

dry-run 结果可返回以下状态：

- `dry_run_only`：请求计划和安全边界验证通过，但不抓取真实行情。
- `disabled_by_default`：provider 默认关闭，不允许自动进入真实请求。
- `unsupported`：资产类型或市场不属于本 adapter 支持范围。
- `invalid_request`：请求结构无效，例如 `unknown` 类型。
- `provider_not_registered`：provider 不存在于 `provider_registry`。

结果中的 `has_real_market_data` 和 `will_fetch_real_data` 必须为 `false`；`quote.last_price`、`quote.change_pct`、`quote.change_amount`、`quote.volume`、`quote.turnover` 必须为 `null`。

## 5. Provider registry 关系

候选 provider 来自 `src/provider_registry.py`。dry-run adapter 通过 registry 读取候选状态、provider 类型、默认启用策略、字段映射计划、缓存策略和失败兜底策略，不重复硬编码完整候选 provider。

候选 provider 仍保持 `candidate_only`，不代表已验证或已接入真实行情。

## 6. Provider safety 关系

安全规则来自 `src/provider_safety.py`。dry-run adapter 会复用 provider config secret 扫描、真实 provider 默认关闭、真实 provider 不允许写 public repo、fixture 不得标记为 real provider 等安全边界。

本阶段所有 provider 结果都必须保持 `data_mode=dry_run`，不能输出 `source_status=real_provider`，也不能把 fixture 或 dry-run 结果冒充真实数据。

## 7. 后续路线

- P5-Q2：A股 / ETF provider local-only 测试。
- P5-Q3：A股 / ETF provider 真实请求最小闭环。
- P5-R：场外基金真实净值 provider 接入评估。
