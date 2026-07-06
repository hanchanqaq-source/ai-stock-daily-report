# A股 / ETF Provider 结果审计说明

## 1. 设计目标

`src/cn_quote_result_audit.py` 用于审计本地真实 provider 手动试跑后的 `QuoteResult`。模块只处理调用方传入的内存对象，不主动请求真实行情、不联网、不读取真实 `user_config`，也不写真实结果文件。

核心目标是：在结果进入后续本地展示或调试说明前，确认真实行情值和 secrets 不会被写入 public 仓库，并生成可追踪、已脱敏的审计摘要。

## 2. 审计范围

审计范围包括：

- `QuoteResult` 的基础字段：`asset_id`、`code`、`type`、`market`、`data_status`、`data_mode`、`has_real_market_data`。
- `quote` 字段是否包含价格、涨跌幅、成交额等真实行情值。
- `source` metadata：`provider`、`source_status`、`checked_at`。
- `provider_checks`：`allow_commit_to_repo`、`cache_scope`、`network_enabled`、`allow_real_request`。
- freshness：根据 `checked_at` 判断结果是否新鲜、过期、缺失或无法识别。
- repository safety：判断该结果是否允许提交到仓库。
- secret scan：扫描 Token、API Key、Webhook、cookie、authorization 等敏感字段。

## 3. 脱敏规则

审计输出中的 `redacted_result` 会保留资产标识、代码、类型、市场、provider、`source_status` 和 `checked_at`，但会脱敏真实行情值。

以下 `quote` 字段只允许存在于本地内存对象中，审计输出统一显示为 `<redacted>`：

- `last_price`
- `change_pct`
- `change_amount`
- `volume`
- `turnover`
- `open`
- `high`
- `low`
- `previous_close`

审计函数不会修改原始输入对象。

## 4. Freshness 规则

`check_quote_result_freshness(result, policy)` 使用 policy 中的 `max_age_seconds` 判断 freshness：

- 缺少 `checked_at`：`freshness_status=missing_checked_at`。
- `checked_at` 不是合法时间：`freshness_status=unknown`。
- `checked_at` 超过 `max_age_seconds`：`freshness_status=stale`。
- 未超过 `max_age_seconds`：`freshness_status=fresh`。

过期数据不能被标记为 fresh，也不应作为可用的新鲜行情展示。

## 5. Repository Safety 规则

真实 provider 结果不能提交到 public 仓库：

- `has_real_market_data=true` 时，`commit_safe=false`。
- `data_mode=real_provider` 时，`commit_safe=false`。
- 若真实行情结果同时出现 `allow_commit_to_repo=true`，审计会阻断并报告 `real_provider_result_must_not_be_committed`。
- 真实 provider 结果的 `cache_scope` 应为 `local_only`，非 `local_only` 会产生安全 warning。
- `fixture_only` / `model_only` 结果在不含 secret 且不含真实行情时可以作为 commit-safe 结果。

## 6. Secret 规则

审计会扫描字段名中的敏感标识，包括 Token、API Key、Webhook、cookie、authorization、bearer、password、client_secret、private_key 等。

一旦发现 secret 字段：

- `audit_status=blocked`。
- `severity=blocker`。
- `issues` 只记录字段路径，不记录原值。
- `redacted_result` 中对应值显示为 `<redacted>`。

## 7. 后续路线

- P5-Q6：A股 / ETF provider 本地页面展示安全适配。
- P5-R：场外基金真实净值 provider 接入评估。
