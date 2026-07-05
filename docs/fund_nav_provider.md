# 场外基金净值 / 估算涨跌抓取框架说明
账户资产行情 / 基金净值汇总见 `docs/account_realtime_summary.md`。股票 / ETF / 官方指数走 `realtime_quote_provider`；场外基金走 `fund_nav_provider`；持有和收藏必须分开汇总；场外基金不能称为实时涨跌。

## 1. 设计目标

`src/fund_nav_provider.py` 只定义场外基金净值 / 估算净值框架、Provider 接口和标准化结果结构。本阶段不默认接入真实数据源，不联网，不读取真实 `user_config`，不保存真实净值、真实估算净值或真实涨跌幅。

## 2. 支持范围

- `fund`：可进入本框架，按 `quote_capability` 的 `daily_nav_supported` 或 `intraday_estimate_supported` 生成 `FundNavRequest`。
- `stock` / `etf` / `index`：不进入本框架。
- `company` / `industry` / `theme`：不是直接基金净值对象，不进入本框架。
- `unknown`：返回 `invalid_request`。

ETF 属于交易所交易品种，应使用股票 / ETF 实时行情框架；场外 fund 不进入股票 / ETF 实时行情框架。

## 3. FundNavRequest

`FundNavRequest` 是单个场外基金净值请求，稳定字段包括：`request_id`、`asset_id`、`code`、`name`、`type`、`market`、`price_mode`、`requires_realtime`、`requires_daily_nav`、`requires_estimated_nav`、`provider_hint`。

其中 `type` 必须为 `fund`，`price_mode` 默认为 `estimated_nav_or_daily_nav`，`requires_realtime` 固定为 `false`。

## 4. FundNavResult

`FundNavResult` 是单个场外基金净值结果，稳定字段包括：`request_id`、`asset_id`、`code`、`name`、`type`、`market`、`price_mode`、`data_status`、`nav`、`estimate`、`source`、`warnings`、`disclaimer`、`reason`。

`nav` 包含单位净值、累计净值、净值日期和日涨跌幅；`estimate` 包含估算净值、估算涨跌、估算变化额和估算更新时间。`source` 必须包含 `provider`、`provider_type`、`source_status` 和 `checked_at`。

## 5. Provider 接口

`FundNavProvider` 定义 `name`、`provider_type`、`supports_market()`、`supports_item()`、`fetch_one()`、`fetch_many()`。本阶段提供 `MockFundNavProvider` / `FixtureFundNavProvider`，只返回离线 fixture 结果，`source_status=fixture_only`。

真实 provider 后续可以评估接入天天基金、东方财富、基金公司官网等来源，但本阶段不接入这些来源。

## 6. 数据状态

- `available`：每日净值和估算净值 fixture 均可用。
- `unavailable`：每日净值和估算净值 fixture 均不可用。
- `unsupported`：资产类型不进入场外基金净值框架。
- `stale`：数据过期状态预留。
- `provider_error`：Provider 层异常已被捕获。
- `invalid_request`：请求无效或资产类型未知。
- `estimate_only`：仅估算净值 fixture 可用。
- `daily_nav_only`：仅每日净值 fixture 可用。

## 7. 场外基金规则

场外基金不能叫实时涨跌，场外 fund 只能展示净值 / 估算净值，不能称为实时涨跌。估算净值不等于最终净值；盘中估算仅供观察，最终以基金公司公布净值为准。

## 8. 和实时行情框架关系

`realtime_quote_provider` 负责 `stock` / `etf` / `official_index`。`fund_nav_provider` 负责 `fund` 的净值 / 估算净值。两个框架不互相混用；后续 P5-N 可在账户视图汇总两侧结果，但本阶段不做汇总。

## 9. 安全规则

本阶段不保存真实净值、真实估算净值、真实涨跌幅，不保存真实价格、成交额、金额、成本价、账户资产，也不保存 token / key / webhook。测试数据只能使用示例基金和 fixture-only 占位值。

## 10. 后续路线

- P5-M1：真实基金净值数据源接入评估。
- P5-N：账户资产实时涨跌 / 净值汇总。
- Web-P15：实时行情与基金净值看板。
真实 provider 接入前安全规则见 `docs/provider_safety.md`。真实行情和真实基金净值默认不写入 public 仓库。真实 provider 必须显式启用网络权限，并保留来源、checked_at、source_status。
