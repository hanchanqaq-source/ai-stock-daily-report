# 真实数据源接入前安全审查说明

## 1. 设计目标

本模块用于在真实 provider 接入前定义安全边界。当前阶段只定义安全规则、配置规则、缓存规则、失败兜底规则、来源标记规则和测试约束，不接入真实行情源，不联网，不读取真实用户配置，也不保存真实价格、涨跌幅、净值、估算净值或成交额。

## 2. provider 类型

- `fixture`：测试数据，不联网，`source_status=fixture_only`，`has_real_market_data=false`。
- `mock`：模拟 provider，不联网，`source_status=mock_only`，`has_real_market_data=false`。
- `public_web`：公开网页或公开接口，必须显式开启 `network_enabled=true`，默认不启用，并必须配置 timeout、retry、rate_limit。
- `api`：API provider，默认不启用；如后续需要 token，只能通过环境变量读取，不能写入仓库配置示例。
- `local_cache`：本地缓存，只能用于本地，不能提交到 GitHub public 仓库，并必须保留 `expires_at`、`checked_at` 和 `source`。

## 3. data_mode 规则

支持的 `data_mode` 包括：`fixture_only`、`mock_only`、`model_only`、`real_provider`、`real_provider_cached`、`mixed_real_and_fixture` 和 `unsupported`。

- `fixture_only` 不能被标成 `real_provider`。
- `mock_only` 不能被标成 `real_provider`。
- `real_provider` 必须保留 `provider`、`checked_at` 和 `source_status`。
- `real_provider_cached` 必须保留 `cache_checked_at` 和 `cache_expires_at`。
- `mixed_real_and_fixture` 必须带 warning，避免把 fixture 当真实数据。
- public 仓库中默认禁止保存 `real_provider` 原始数据。

## 4. 网络权限规则

真实 provider 默认不启用。`public_web` 和 `api` provider 必须显式配置 `enabled=true` 与 `network_enabled=true` 后才能进入真实网络访问路径；fixture、mock 和本地缓存不需要网络权限。

## 5. Secret 规则

Token、API Key、Webhook、authorization、bearer、cookie、session、password、private_key、client_secret 等敏感字段不能写入仓库、docs、tests 或 fixtures。后续如必须引用 token，只允许写环境变量名，例如 `AKSHARE_TOKEN_ENV`、`YFINANCE_TOKEN_ENV`、`EASTMONEY_TOKEN_ENV`，真实值只能从运行环境读取。

## 6. 缓存规则

真实行情和真实基金净值缓存默认 `local_only`，不能提交到 public 仓库。缓存策略必须保留 provider、data_kind、ttl_seconds、checked_at / expires_at 要求，并默认 `allow_commit_to_repo=false`。仓库可以保存 fixture、结构化 schema 和不含真实数据的 example config。

## 7. 失败兜底规则

失败状态包括 `provider_error`、`provider_timeout`、`rate_limited`、`invalid_response`、`stale_data`、`conflict` 和 `unsupported`。

- provider 失败不能让整个账户页面崩。
- 单个资产失败不影响其他资产。
- 失败结果必须带 reason。
- `stale_data` 必须显示 `checked_at`，不能把旧数据冒充新数据。
- 多来源冲突必须标 `conflict` 并带 warning。
- 不能把 `unavailable` 写成 `available`。

## 8. 场外基金规则

场外基金不能称为实时涨跌，只能使用：单位净值、累计净值、日涨跌幅、估算净值、估算涨跌、净值日期、估算更新时间。估算净值必须提示：盘中估算仅供观察，最终以基金公司公布净值为准。`fund_nav_provider` 不能输出 `realtime_quote`。

## 9. 后续路线

- P5-Q：真实 A股 / ETF provider 接入评估。
- P5-R：真实场外基金净值 provider 接入评估。
- P5-S：真实 provider dry-run 模式。

个人观察点位卡片见 `docs/personal_signal_cards.md`。Web 页面布局参考见 `docs/ui_layout_reference.md`。点位卡片仅用于个人观察和记录，不会自动执行任何操作。

真实 A股 / ETF provider 接入评估见 `docs/cn_quote_provider_evaluation.md`。Provider registry 见 `docs/provider_registry.md`。候选 provider 不代表已接入或已验证，真实 provider 默认关闭。
