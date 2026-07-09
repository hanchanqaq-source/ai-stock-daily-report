# 场外基金净值 Provider Dry-run Adapter 说明

## 1. 设计目标

`src/fund_nav_dry_run_provider.py` 用于在真实基金净值 provider 接入前验证请求计划和安全检查。它只生成 dry-run request / result，不请求真实净值，不读取真实 `user_config`，不请求天天基金、东方财富、支付宝或基金公司官网，也不保存真实单位净值、累计净值、估算净值或涨跌幅。

## 2. 支持范围

当前 dry-run adapter 仅支持 `CN` 场外 `fund`，并只规划以下数据：

- 单位净值
- 累计净值
- 净值日期
- 日涨跌幅
- 估算净值
- 估算涨跌
- 估算更新时间

## 3. 不支持范围

以下对象不进入场外基金净值 provider：

- `stock`
- `etf`
- `index`
- `company`
- `industry`
- `theme`
- `computed_indicator`
- `unknown`
- 非 CN 市场基金

其中 `unknown` 会返回 `invalid_request`，其它非适用对象返回 `unsupported`。

## 4. Dry-run 结果

Dry-run 结果只允许以下状态：

- `dry_run_only`
- `disabled_by_default`
- `unsupported`
- `invalid_request`
- `provider_not_registered`
- `provider_policy_blocked`
- `provider_error`

结果必须满足：

- `data_mode = dry_run`
- `has_real_nav_data = false`
- `will_fetch_real_data = false`
- `source.source_status = dry_run_only`
- `nav` 和 `estimate` 字段值保持为空
- 不保存真实单位净值、累计净值、估算净值、估算涨跌幅或日涨跌幅

## 5. Provider registry 关系

候选 provider 来自 `fund_nav_provider_registry`。Dry-run adapter 通过 registry 读取 provider 的候选状态、字段映射、启用策略、缓存策略和失败策略，不重复硬编码完整候选 provider。

若 provider 未登记，结果返回 `provider_not_registered`。若真实 provider 默认关闭，dry-run 仍可生成计划，但 `provider_checks.default_enabled` 保持 `false`。

## 6. Provider safety 关系

安全规则来自 `provider_safety`：

- 扫描 provider config 是否包含 secret-like 字段。
- 真实 provider 不允许默认启用。
- 真实 provider 不允许写入 public repo。
- fixture 不得标记为 `real_provider`。

Dry-run adapter 默认 `network_enabled = false`、`allow_commit_to_repo = false`、`will_fetch_real_data = false`，只验证接入计划和安全边界。

## 7. 场外基金文案规则

场外基金不能称为实时涨跌。场外基金只使用净值和估算净值相关文案。

盘中估算仅供观察，最终以基金公司公布净值为准。

## 8. 后续路线

- P5-R2：场外基金净值 provider local-only 测试。
- P5-R3：场外基金净值真实请求最小闭环。
