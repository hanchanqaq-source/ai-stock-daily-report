# 账户场外基金净值 Provider 接入汇总说明

## 1. 设计目标

`src/account_fund_nav_provider_integration.py` 用于把场外基金净值 provider 结果接入账户级基金净值汇总结构。本阶段默认 `provider_mode=dry_run`，只验证账户资产分流、provider 编排、审计和展示安全适配链路，不请求真实基金净值，不读取真实 `user_config`，也不写入结果文件。

## 2. Provider mode

- `dry_run`：默认模式，走 `fund_nav_dry_run_provider`，不联网、不请求真实基金净值。
- `local_only`：走 `fund_nav_local_only_provider`，只使用本地 fixture，不联网，`has_real_nav_data=false`。
- `real_gated`：预留真实 provider 闸门；测试中只能传入 fake provider / fake fetcher，默认配置不开启真实请求。

## 3. 资产分流规则

账户 group 中只有 `holding` / `watching` 状态资产会参与本汇总；`cleared` / `archived` / `deleted` 默认不参与。

进入本模块的资产仅限 CN / 中国市场的场外 `fund`。以下资产不进入场外基金净值 provider：

- `stock`：应使用 A股 / ETF quote provider。
- `etf`：属于交易所交易品种，应使用股票 / ETF provider。
- `index` / `official_index`：应使用 index quote 或市场指数模块。
- `company`：企业本身不是基金净值对象。
- `industry` / `theme`：不直接请求基金净值 provider。
- `computed_indicator`：系统计算指标由市场广度模块生成，不直接请求基金净值 provider。
- `unknown`：返回 `invalid_request`。
- 非 CN 市场基金：返回 `unsupported`。

## 4. 审计与展示适配

所有基金净值 provider 结果进入账户汇总前都必须经过：

1. `fund_nav_result_audit`：检查 source metadata、freshness、repository safety、secret scan，并对单位净值、累计净值、估算净值、涨跌幅等字段做审计脱敏。
2. `fund_nav_display_adapter`：生成页面可消费的 display model，默认 `display_mode=redacted`；审计 blocked / failed 或 provider failed 时不展示真实基金净值。

## 5. 安全规则

- 默认不联网，不请求天天基金 / 东方财富 / 支付宝 / 基金公司官网。
- 不保存真实单位净值、累计净值、估算净值、日涨跌幅或估算涨跌。
- 不写 public repo，不输出 Token / API Key / Webhook / cookie / authorization / bearer。
- 默认脱敏展示，`has_real_nav_data=false`。
- 本模块只做账户级编排，不重复实现 provider、audit 或 display adapter 逻辑。

## 6. 场外基金说明

场外基金不支持真正实时价格；账户汇总中只能使用单位净值、累计净值、净值日期、日涨跌幅、估算净值、估算涨跌和估算更新时间等表述。

盘中估算仅供观察，最终以基金公司公布净值为准。

## 7. 后续路线

- P5-S：股票 / ETF / 基金真实数据统一汇总安全适配。
- P5-T：真实数据进入账户页面模型前最终安全闸门。
