# 账户动态页面模型说明
账户资产行情 / 基金净值汇总见 `docs/account_realtime_summary.md`。股票 / ETF / 官方指数走 `realtime_quote_provider`；场外基金走 `fund_nav_provider`；持有和收藏必须分开汇总；场外基金不能称为实时涨跌。
场外基金净值 / 估算涨跌抓取框架见 `docs/fund_nav_provider.md`。场外 fund 不进入股票 / ETF 实时行情框架；场外 fund 只能展示净值 / 估算净值，不能称为实时涨跌。
全球市场指数矩阵与页面切换模型见 `docs/market_index_matrix.md`。官方指数和系统计算指标必须分开展示，系统计算指标必须标注“非官方指数”。

资产实时行情能力标记见 `docs/quote_capability.md`。股票 / ETF 可展示实时或接近实时行情；场外基金只能展示净值或估算净值，不能称为实时涨跌。

## 1. 设计目标

账户动态页面模型用于根据账户 / 分组里的资产类型和状态生成结构化页面结果：账户里有什么资产，就显示什么页面，不显示空页面。

本阶段只提供后端页面结构模型、展示规则、文档和测试；不做真实网页 UI，不接入 Streamlit / React / Vue，不接入日报、周报或 Discord。

## 2. 页面类型

- `overview`：账户总览；存在 active asset 时默认显示。
- `funds`：基金分析页；存在 active `fund` / `etf` 时显示。
- `stocks`：股票分析页；存在 active `stock` 时显示。
- `companies`：企业观察页；存在 active `company` 时显示。
- `themes`：主题 / 行业观察页；存在 active `industry` / `theme` / `index` 时显示。
- `watching`：收藏 / 观察页；存在 `watching` 资产时显示。
- `holding_vs_watching`：持有 vs 收藏对比页；`holding` 和 `watching` 同时存在时显示。
- `history`：历史记录页；存在 `cleared` / `archived` 资产时显示。
- `empty_state`：空状态页；没有 active asset 时显示。

`settings` 是后续网页工作台可选页面，本阶段不默认输出。

## 3. 显示规则

- 有基金或 ETF 显示 `funds`。
- 有股票显示 `stocks`。
- 基金和股票都有时同时显示 `funds` 与 `stocks`。
- 有企业显示 `companies`。
- 有行业、主题或指数显示 `themes`。
- 有收藏资产显示 `watching`。
- 同时有持有和收藏资产显示 `holding_vs_watching`。
- 有已清仓或归档资产显示 `history`。
- 没有 active asset 时显示 `empty_state`；如果同时存在已清仓或归档资产，则显示 `empty_state` 和 `history`。
- 不显示空基金页、空股票页或其他无资产页面。

页面顺序固定为：`overview`、`funds`、`stocks`、`companies`、`themes`、`watching`、`holding_vs_watching`、`history`、`settings`、`empty_state`。空状态为特殊规则：没有 active asset 时只显示 `empty_state`，有历史资产时再追加 `history`。

## 4. active asset 规则

`holding` / `watching` 是 active asset。

`cleared` / `archived` / `deleted` 默认不算 active asset：

- `cleared` 可触发 `history` 页面。
- `archived` 可触发 `history` 页面。
- `deleted` 不显示在主页面，也不触发 `history` 页面。

页面模型只读生成，不修改资产状态，不执行清仓、归档或删除，不修改传入的 group。

## 5. 和网页工作台关系

后续 Web-P9 会使用该模型实现动态标签页：有基金才显示基金页，有股票才显示股票页，有收藏才显示收藏页，有已清仓或归档资产才显示历史页，没有资产时显示请添加资产。

当前阶段输出字段保持稳定，后续本地网页工作台可以直接复用 `visible_pages`、`default_page`、`tabs`、`asset_counts` 和 `pages`。

## 6. 安全规则

页面模型不输出金额、成本价、账户资产和 secrets。

允许输出公开安全字段：`asset_id`、`type`、`code`、`name`、`market`、`tags`、`status`、`weight_level`、`source_status`。`weight_level` 只是 1 到 5 的关注等级，不是金额；`balanced` 是风险偏好枚举，不是 `balance`。

禁止输出或保存：真实金额、成本价、账户资产、Webhook、Token、API Key、个人邮箱、手机号、身份证等敏感信息。

账户页面行情 / 净值展示模型见 docs/account_market_page_adapter.md。页面模型只展示结构化行情 / 净值摘要，不保存真实行情数据。场外基金不能称为实时涨跌。
