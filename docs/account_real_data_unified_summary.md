# 股票 / ETF / 基金真实数据统一汇总安全适配说明

## 1. 设计目标

`src/account_real_data_unified_summary.py` 用于把股票 / ETF 行情汇总和场外基金净值汇总合并为账户级统一展示模型。它只做安全编排、统一 section、统一计数、统一 warnings 和统一 Markdown Demo，不请求真实行情或真实基金净值，也不保存真实数据。

该模块为后续账户页消费统一数据结构做准备：当前默认 `dry_run`、默认 `redacted`、`commit_safe=false`，输出只包含展示适配后的脱敏模型与安全状态。

## 2. 数据来源

- A股 / ETF 走 `account_cn_quote_provider_integration`。
- 场外基金走 `account_fund_nav_provider_integration`。

统一汇总模块不重复实现 provider 逻辑，不直接调用 AKShare / 东方财富 / 天天基金 / 支付宝 / 基金公司官网，也不读取真实 `user_config`。

## 3. 字段边界

股票 / ETF 与场外基金字段必须分开治理：

- 股票 / ETF 可使用：最新价、涨跌幅、涨跌额、成交量、成交额、`checked_at`、`source_status`。
- 场外基金可使用：单位净值、累计净值、净值日期、日涨跌幅、估算净值、估算涨跌、估算更新时间、`checked_at`、`source_status`。

场外基金不能写成“实时涨跌”“实时行情”“盘中实时净值”或“实时价格”。场外基金估算必须提示：盘中估算仅供观察，最终以基金公司公布净值为准。

## 4. 审计和展示适配

所有结果必须先经过既有审计和展示适配层：

1. 股票 / ETF：`cn_quote_result_audit` + `cn_quote_display_adapter`。
2. 场外基金：`fund_nav_result_audit` + `fund_nav_display_adapter`。

统一汇总只检查审计数量和展示模型数量是否与 provider 结果对齐，并汇总为 `safety_summary.all_results_audited` 与 `safety_summary.all_display_models_checked`。

## 5. 安全规则

- 默认 `stock_provider_mode=dry_run`。
- 默认 `fund_provider_mode=dry_run`。
- 默认 `display_mode=redacted`。
- `has_real_market_data=false`。
- `has_real_nav_data=false`。
- `commit_safe=false`。
- 不保存真实价格、涨跌幅、成交额、单位净值、累计净值、估算净值或基金涨跌幅。
- 不写 public repo，不输出 Token / API Key / Webhook 等 secrets。
- blocked / failed display model 不显示真实行情或真实净值字段。

## 6. 后续路线

- P5-T：真实数据进入账户页面模型前最终安全闸门。
- Web-P15：实时行情与基金净值看板。
- Web-P17：账户首页综合看板。
