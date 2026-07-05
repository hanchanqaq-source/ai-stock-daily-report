# 账户页面行情 / 净值展示模型说明

## 1. 设计目标

`src/account_market_page_adapter.py` 用于把 `src/account_realtime_summary.py` 生成的账户行情 / 基金净值汇总结果写入账户页面模型。模块只做页面展示结构适配，不读取真实 `user_config`，不接真实 provider，不保存真实价格、涨跌幅、净值或估算净值。

## 2. 页面接入范围

当前接入范围为：

- `overview`：展示账户层面的行情 / 净值状态总览。
- `funds`：展示基金净值 / 估算净值摘要。
- `stocks`：展示股票、ETF、官方指数行情摘要。
- `watching`：展示收藏资产的行情 / 净值摘要。
- `holding_vs_watching`：展示持有与收藏的状态统计对比。

`empty_state` 不展示行情数据；`history` 默认不展示当前行情数据，只说明历史资产默认不参与当前行情 / 净值汇总。

## 3. 页面过滤规则

- `funds` 页面只展示 `result_kind = fund_nav` 的结果。
- `stocks` 页面只展示 `result_kind = realtime_quote` 且资产类型为 `stock`、`etf`、`index` 的结果。
- `watching` 页面只展示 `status = watching` 的资产结果。
- `holding_vs_watching` 页面只展示持有 / 收藏的状态统计，不生成任何交易动作。
- `empty_state` 不展示行情。

页面适配不会改变 `account_page_model` 的 `visible_pages` 规则，也不会新增空的 `funds` 或 `stocks` 页面。

## 4. 场外基金规则

场外基金不能叫实时涨跌，只能展示净值 / 估算净值摘要。盘中估算仅供观察，最终以基金公司公布净值为准。

## 5. 安全规则

本阶段不保存真实价格、涨跌幅、净值、估算净值、金额、成本价、账户资产、Token、Webhook。页面模型中的 `has_real_market_data` 必须为 `false`，`data_mode` 仅允许 `fixture_only`、`model_only` 或 `mixed_fixture_only`。

## 6. 后续路线

- P5-P：真实 provider 接入前安全审查。
- Web-P15：实时行情与基金净值看板。
