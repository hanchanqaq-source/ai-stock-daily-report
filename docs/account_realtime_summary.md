# 账户资产行情 / 基金净值汇总说明

## 1. 设计目标

`src/account_realtime_summary.py` 用于把账户 / 分组中的 active 资产分流到股票 / ETF / 官方指数行情框架和场外基金净值框架，并生成账户级结构化汇总与 Markdown Demo。

本阶段只验证账户行情 / 净值汇总框架：不联网、不接真实 provider、不读取真实 `user_config`、不保存真实行情或基金净值、不接入日报 / 周报 / Discord，也不输出任何交易建议。

## 2. 资产分流规则

- `stock` / `etf` / `official index` → `realtime_quote_provider`。
- `fund` → `fund_nav_provider`。
- `computed_indicator` → 市场指标模块生成，本模块不直接抓 quote。
- `company` 暂不直接抓行情；后续可通过关联 `stock` asset 展示行情。
- `industry` / `theme` 暂不直接抓行情；后续可通过指数或系统计算指标实现。
- `unknown` 返回 `invalid_request` 或不支持状态，不进入真实 provider。

`cleared` / `archived` / `deleted` 默认不参与当前行情 / 净值汇总，只在资产数量统计中体现。

## 3. holding / watching 规则

`holding` 表示当前持有资产，`watching` 表示收藏 / 观察资产。账户汇总必须将两者分开统计、分开展示，不混淆持有和收藏。

本模块只做观察：不计算真实盈亏、不计算仓位金额、不根据涨跌或净值变化输出操作动作。

## 4. 场外基金规则

场外基金不能叫实时涨跌，只能展示净值 / 估算净值。盘中估算仅供观察，最终以基金公司公布净值为准。

账户汇总中 `fund` 的结果必须标注为 `fund_nav`，不能写成 `realtime_quote`；股票 / ETF / 官方指数的结果必须标注为 `realtime_quote`，不能写成 `fund_nav`。

## 5. 数据状态

账户级 `status` 支持：

- `available`：active 资产结果均可用。
- `partial_available`：部分 active 资产可用，部分为不支持、无效或 provider 错误。
- `unsupported`：单项结果不支持状态，常见于 `company` / `industry` / `theme` / `computed_indicator`。
- `provider_error`：provider 层错误已被隔离，不影响批量中其他资产。
- `invalid_request`：资产类型或请求无效。
- `empty`：没有 active 资产可汇总。

本阶段 `data_mode` 仅使用 `fixture_only` / `model_only` / `mixed_fixture_only` 语义，且 `has_real_market_data=false`。

## 6. 安全规则

本阶段不保存真实价格、涨跌幅、净值、估算净值、金额、成本价、账户资产、Token、Webhook、API Key 或其他隐私信息。

结构化输出只保留 public-safe 资产字段、provider 名称、`checked_at`、`source_status`、状态统计和必要说明，不包含真实价格、真实涨跌幅、真实净值、真实估算净值或真实成交额。

## 7. 后续路线

- P5-N1：账户汇总接入真实 provider 前安全审查。
- P5-O：行情 / 净值结果写入页面模型。
- Web-P15：实时行情与基金净值看板。
