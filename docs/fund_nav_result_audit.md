# 场外基金净值 Provider 结果审计说明

## 1. 设计目标

`src/fund_nav_result_audit.py` 用于审计本地真实基金净值 provider 试跑后的 `FundNavResult`。它不请求真实基金净值、不联网、不读取真实 `user_config`、不写真实结果文件，目标是在结果进入后续本地展示前检查其是否安全、可用、可追踪，并防止真实净值或 secrets 被写入 public 仓库。

## 2. 审计范围

审计范围包括：

- `FundNavResult` 基础结构和 `data_status`。
- `source metadata`：`provider`、`source_status`、`checked_at`。
- `provider_checks`：`allow_commit_to_repo`、`cache_scope`、`network_enabled`、`allow_real_request`。
- `daily_nav freshness`：基于 `checked_at` 和 `nav.nav_date` 判断每日净值是否新鲜。
- `estimated_nav freshness`：基于 `checked_at` 和 `estimate.estimate_time` 判断估算净值是否新鲜。
- `repository safety`：确认真实场外基金净值结果不能提交到仓库。
- `secret scan`：扫描 Token、API Key、Webhook、cookie、authorization 等敏感字段。

## 3. 脱敏规则

审计输出必须脱敏真实基金净值字段。以下字段在 `redacted_result` 中统一替换为 `<redacted>`：

- `nav.unit_nav`
- `nav.accumulated_nav`
- `nav.daily_change_pct`
- `estimate.estimated_nav`
- `estimate.estimated_change_pct`
- `estimate.estimated_change_amount`

`asset_id`、`code`、`type`、`market`、`source.provider`、`source.source_status`、`source.checked_at`、`nav.nav_date`、`estimate.estimate_time` 可以保留，便于本地审计追踪。审计函数不会修改原始输入对象。

## 4. Freshness 规则

`daily_nav` 和 `estimated_nav` 使用不同过期规则：

- `daily_nav_max_age_seconds` 默认为 86400 秒。
- `estimated_nav_max_age_seconds` 默认为 300 秒。

如果缺少 `checked_at`，返回 `missing_checked_at`；如果每日净值缺少 `nav_date`，返回 `missing_nav_date`；如果估算净值缺少 `estimate_time`，返回 `missing_estimate_time`；如果 `checked_at` 超过对应阈值，返回 `stale`。过期数据不能标记为 `fresh`。

## 5. Repository Safety 规则

当 `has_real_nav_data=true` 或 `data_mode=real_provider` 时，`commit_safe=false`。如果真实基金净值结果同时出现 `provider_checks.allow_commit_to_repo=true`，审计会阻断并给出 `real_fund_nav_result_must_not_be_committed` issue。

真实基金净值仅允许本地内存使用，不得提交到 public 仓库。`cache_scope` 应为 `local_only`；真实结果使用其他 cache scope 时会产生警告或阻断。

## 6. Secret 规则

审计会扫描 Token、API Key、Webhook、cookie、authorization、bearer、password、secret、client_secret、private_key 等字段。发现 secret 字段时：

- `audit_status=blocked`。
- `severity=blocker`。
- issue 只记录字段路径，不记录原值。
- `redacted_result` 不包含 secret 原值。

## 7. 场外基金说明

场外基金不能称为实时涨跌，只能按单位净值、累计净值、日涨跌幅、估算净值、估算涨跌等语义展示。盘中估算仅供观察，最终以基金公司公布净值为准。

## 8. 后续路线

- P5-R6：场外基金净值页面展示安全适配。
- P5-S：股票 / ETF / 基金真实数据统一汇总安全适配。
