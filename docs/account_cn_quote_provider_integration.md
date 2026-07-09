# 账户 A股 / ETF Provider 汇总 Dry-run 接入

## 1. 设计目标

P5-Q7 将 P5-Q1 至 P5-Q6 已完成的 A股 / ETF provider dry-run、local-only、real-provider gated、结果审计和展示安全适配能力接入账户行情汇总层。

本阶段只验证账户模型到 provider 汇总的离线链路：

- 读取账户 group 中的 active assets。
- 只处理 `holding` / `watching`。
- 默认跳过 `cleared` / `archived` / `deleted`。
- 默认 `provider_mode=dry_run`，不请求真实行情。
- 所有 provider result 进入账户展示模型前必须经过 `cn_quote_result_audit`。
- 所有 provider result 进入页面展示前必须经过 `cn_quote_display_adapter`。
- 默认 `display_mode=redacted`，不展示真实价格、涨跌幅、成交额。
- 不读取真实 `user_config`，不写文件，不保存真实行情。

入口模块为 `src/account_cn_quote_provider_integration.py`，复用账户行情汇总和页面适配中的 active 资产语义，同时复用现有 CN quote provider / audit / display adapter。

## 2. provider_mode

### dry_run

默认模式，调用 `src/cn_quote_dry_run_provider.py`。

- 不联网。
- 不请求 AKShare、东方财富、新浪、腾讯或任何真实 provider。
- 不返回真实价格、涨跌幅、成交额。
- 返回 `data_mode=dry_run` 和 `has_real_market_data=false`。

### local_only

调用 `src/cn_quote_local_only_provider.py`。

- 仅使用仓库内安全 fixture。
- 不联网。
- 不读取真实用户配置。
- 结果仍必须经过审计和展示安全适配。

### real_gated

调用 `src/cn_quote_real_provider.py` 的 gated adapter。

- 本阶段测试只允许注入 fake provider。
- 默认 gate 关闭，不联网。
- 不允许通过账户汇总层默认开启真实请求。
- 即使 fake provider 返回结果，也必须经过审计和展示安全适配。

## 3. 资产分流规则

账户 group 中只有 active assets 进入本汇总：

- `holding`：参与汇总，并进入 holding 分组统计。
- `watching`：参与汇总，并进入 watching 分组统计。
- `cleared` / `archived` / `deleted`：默认不参与当前 provider 汇总。

资产类型分流：

- CN `stock`：进入 A股 / ETF quote provider。
- CN `etf`：进入 A股 / ETF quote provider。
- CN `official_index`：进入 A股 / ETF quote provider。
- `fund`：返回 `unsupported`，继续走 `fund_nav_provider` 路线。
- `company`：返回 `unsupported`。
- `industry` / `theme`：返回 `unsupported`。
- `computed_indicator`：返回 `unsupported`。
- `unknown`：返回 `invalid_request`。
- 非 CN 市场：返回 `unsupported`。

## 4. 审计与展示适配规则

账户 provider 汇总不得直接把 provider result 作为页面输出：

1. `fetch_account_cn_quote_provider_results(...)` 只负责生成 provider result。
2. `audit_account_cn_quote_provider_results(...)` 对每个 result 调用 `audit_cn_quote_result(...)`。
3. `build_account_cn_quote_display_models(...)` 对每个 result 调用 `build_cn_quote_display_model(...)`。
4. `build_account_cn_quote_provider_summary(...)` 同时返回 `results`、`audits` 和 `display_models`，并提供 holding / watching 分开统计。

默认 display policy 使用 `default_display_mode=redacted`。审计 `blocked` / `failed` 或 provider `unsupported` / `invalid_request` / `provider_error` 等结果不得显示真实行情值。

## 5. 安全规则

本阶段必须遵守以下安全边界：

- 不请求真实行情。
- 不联网。
- 不调用 AKShare / 东方财富 / 新浪 / 腾讯。
- 不保存真实价格、真实涨跌幅、真实成交额。
- 不保存真实净值或估算净值。
- 不读取真实 `user_config`。
- 不接日报、周报或 Discord。
- 不做真实 Web UI。
- Markdown demo 只展示状态、计数和脱敏说明。
- Markdown demo 禁止包含 Token、API Key、Webhook 或其他密钥内容。

## 6. 后续路线

P5-R 将评估场外基金真实净值 provider 接入：

- 明确 `fund_nav_provider` 的真实净值 / 估算净值安全边界。
- 评估本地 gated 请求、字段审计、展示脱敏和仓库提交安全规则。
- 与账户行情汇总保持分层：A股 / ETF quote provider 与场外基金 NAV provider 分别治理、分别审计。

P5-S 统一汇总衔接：`account_real_data_unified_summary` 会复用本模块生成 `stock_etf` section，并继续要求结果先经过 `cn_quote_result_audit` 与 `cn_quote_display_adapter`；统一层不重复实现 provider 逻辑，不请求真实行情，不保存真实价格、涨跌幅或成交额。
