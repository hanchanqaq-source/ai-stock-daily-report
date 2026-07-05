# 股票 / ETF 实时行情抓取框架（离线完整版）
真实 A股 / ETF provider 接入评估见 `docs/cn_quote_provider_evaluation.md`。Provider registry 见 `docs/provider_registry.md`。候选 provider 不代表已接入或已验证，真实 provider 默认关闭。
账户资产行情 / 基金净值汇总见 `docs/account_realtime_summary.md`。股票 / ETF / 官方指数走 `realtime_quote_provider`；场外基金走 `fund_nav_provider`；持有和收藏必须分开汇总；场外基金不能称为实时涨跌。
场外基金净值 / 估算涨跌抓取框架见 `docs/fund_nav_provider.md`。场外 fund 不进入股票 / ETF 实时行情框架；场外 fund 只能展示净值 / 估算净值，不能称为实时涨跌。

`src/realtime_quote_provider.py` 定义 P5-L5 的实时行情抓取框架契约，但本阶段仍然是离线、fixture-only 能力：不联网，不接 AKShare / yfinance / 东方财富 / Yahoo Finance / TradingView，不读取真实 `user_config`，不保存真实价格、真实涨跌幅或真实成交额，也不接日报或 Discord。

## 核心对象

- `QuoteRequest`：单个行情请求，包含 `symbol`、`asset_type`、`market`、`request_id`、`item_type` 与低敏 `metadata`。
- `QuoteResult`：单个行情结果，固定包含 `provider`、`checked_at`、`source_status`、`disclaimer` 和 `fixture_only`。
- `QuoteProvider`：provider 接口，定义 `fetch_quote()` 与 `fetch_quotes()`。
- `MockQuoteProvider` / `FixtureQuoteProvider`：仅返回 fixture 状态的离线 provider，不返回真实价格字段。

## 支持范围

- `stock`：允许进入框架，返回 `fixture_only` 状态。
- `etf`：允许进入框架，返回 `fixture_only` 状态。
- `official_index`：允许进入框架，返回 `fixture_only` 状态。
- `fund`：禁止进入实时行情框架，返回 `unsupported`，提示后续走 NAV / 净值模块。
- `computed_indicator`：禁止直接抓 quote，返回 `unsupported`；此类指标以后应由系统基于市场数据计算。

## 批量与错误语义

`fetch_realtime_quotes()` 支持批量请求，并保留每个请求独立结果，因此允许部分成功、部分失败。当前稳定状态包括：

- `fixture_only`：离线占位成功，未抓真实行情。
- `provider_error`：provider 层错误。
- `invalid_request`：请求缺少必要字段或包含敏感信息。
- `unsupported`：资产类型或指标类型不允许进入实时 quote 框架。

## 数据安全边界

本模块不得保存或返回真实 `price`、`change_pct`、`turnover`。当前 `QuoteResult` 中这些字段固定为 `None`，所有 mock 数据必须通过 `fixture_only=true` 与 `source_status=fixture_only` 标记。
真实 provider 接入前安全规则见 `docs/provider_safety.md`。真实行情和真实基金净值默认不写入 public 仓库。真实 provider 必须显式启用网络权限，并保留来源、checked_at、source_status。
