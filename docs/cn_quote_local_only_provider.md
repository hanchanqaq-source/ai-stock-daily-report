# A股 / ETF Provider Local-only 测试说明

## 1. 设计目标

P5-Q2 local-only provider 用于在不联网的情况下验证未来 A股 / ETF provider response 的字段映射、结果标准化与安全边界。它只处理本地 fixture / demo provider response，不请求真实行情，不读取真实 `user_config`，不保存真实价格、涨跌幅或成交额。

## 2. 和 dry-run 的区别

- dry-run：验证请求计划、provider registry 候选状态和安全前置条件，不处理 provider response。
- local-only：验证本地 fixture response 到统一 quote 字段的映射，以及 `local_only_available`、`provider_error`、`invalid_response`、`stale_data`、`conflict` 等结果标准化。

## 3. 支持范围

local-only provider 仅支持 CN 市场的 A股 stock、A股 ETF 和 official index。`market` 可使用 `CN`、`cn` 或 `A股`，official index 需要显式标记为官方指数。

## 4. 不支持范围

以下资产不进入 A股 / ETF quote provider：

- fund：应使用 `fund_nav_provider`。
- company：企业本身不是可直接报价对象，需关联 stock asset。
- industry / theme：后续通过指数或系统计算指标实现。
- computed_indicator：由市场广度模块生成，不直接请求 provider 行情。
- unknown：返回 `invalid_request`。
- 非 CN 市场资产：返回 `unsupported`。

## 5. 数据状态

local-only result 支持以下状态：

- `local_only_available`
- `local_only_unavailable`
- `unsupported`
- `invalid_request`
- `provider_error`
- `invalid_response`
- `stale_data`
- `conflict`

local-only result 不允许使用 `available`，也不允许把 `source_status` 标记为 `real_provider`。

## 6. 安全规则

local-only provider 必须满足以下规则：

- 不联网，`network_enabled=false`。
- 不抓取、不保存真实行情，`will_fetch_real_data=false` 且 `has_real_market_data=false`。
- fixture quote 字段只允许为空值，用于验证字段是否存在，不代表真实价格、涨跌幅或成交额。
- config、fixture 和 result 不允许包含 凭据、回调地址、会话标识或鉴权字段等 secret 字段。
- local-only 结果不得被当作 real_provider 数据。

## 7. 后续路线

- P5-Q3：A股 / ETF provider 真实请求最小闭环。
- P5-R：场外基金真实净值 provider 接入评估。
