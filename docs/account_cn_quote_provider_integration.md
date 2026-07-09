# 账户 A股 / ETF provider 汇总 dry-run 接入

## 1. 设计目标

P5-Q7 只把 A股 / ETF provider 的 dry-run、local-only 和 gated real-provider 结果接入账户行情汇总层，用于验证账户模型中的 active assets 能否按规则分流、审计并转换成安全展示模型。

本阶段不请求真实行情、不联网、不读取真实 `user_config`、不接日报 / 周报 / Discord、不做真实 Web UI，也不写文件或保存真实行情值。

## 2. provider_mode

- `dry_run`：默认模式，调用 `cn_quote_dry_run_provider`，只生成请求计划和 dry-run 结果，不请求真实行情。
- `local_only`：调用 `cn_quote_local_only_provider`，只使用本地 fixture，不联网。
- `real_gated`：调用 `cn_quote_real_provider` 的 gated 路径；本阶段仅允许测试注入 fake provider，配置保持 network disabled，不允许真实网络请求。

## 3. 资产分流规则

- 只读取账户 group 中的 active assets，即 `holding` 和 `watching`。
- `cleared`、`archived`、`deleted` 默认不参与 provider 汇总。
- CN `stock`、CN `etf`、CN `official_index` 进入 provider 汇总。
- `fund` 返回 `unsupported`，继续由 `fund_nav_provider` 负责后续净值路径。
- `company` 返回 `unsupported`。
- `industry` / `theme` 返回 `unsupported`。
- `computed_indicator` 返回 `unsupported`。
- `unknown` 返回 `invalid_request`。
- 非 CN 市场资产返回 `unsupported`。

## 4. 审计与展示适配规则

所有 provider result 在进入汇总展示前必须先经过 `cn_quote_result_audit`，再经过 `cn_quote_display_adapter`。默认 display policy 使用 `redacted`，不展示行情数值。

`blocked` / `failed` audit 结果只能生成 blocked display model，不得显示行情字段。unsupported 或 invalid request 结果也会生成安全展示模型，用于账户层统计。

## 5. 安全规则

- 默认 `provider_mode=dry_run`。
- dry-run 不请求真实行情。
- local-only 不联网。
- real-gated 只允许 fake provider 测试，不联网。
- 不写文件，不保存行情值、涨跌幅、成交额、基金净值或估算净值。
- 不读取真实 `user_config`，不输出 Token、API Key 或 Webhook。
- 汇总结构固定标记 `has_real_market_data=false`，默认 `display_mode=redacted`。

## 6. 后续路线

P5-R 将评估场外基金真实净值 provider 接入。该阶段应独立评估净值源、估算净值边界、缓存和展示策略，并继续保证真实净值、估算净值与账户敏感信息不会写入仓库。
