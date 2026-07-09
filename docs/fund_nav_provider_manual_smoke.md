# 场外基金净值 Provider 本地手动试跑说明

## 1. 设计目标

`scripts/run_fund_nav_provider_smoke.py` 用于在本地手动验证场外基金净值 provider 接入链路。脚本默认不联网、不读取真实 `user_config`、不保存真实基金净值，也不在 CI / GitHub Actions 中请求真实基金净值。

该脚本只覆盖本地 smoke test：CLI 参数解析、provider 开关校验、安全边界提示、dry-run / local-only / real-provider gated adapter 路由。日报、周报、Discord、Web UI 和持久化链路不接入本脚本。

## 2. 默认 dry-run

默认命令等价于 `--dry-run`，走 `fund_nav_dry_run_provider`，只验证请求计划和安全边界，不请求真实基金净值。

```bash
python scripts/run_fund_nav_provider_smoke.py --provider eastmoney_fund --code 000000 --type fund --market CN --dry-run
```

默认输出会明确包含 `data_mode`、`source_status`、`has_real_nav_data=false`、`allow_commit_to_repo=false` 和 `will_fetch_real_data=false`。

## 3. local-only 模式

`--local-only` 走 `fund_nav_local_only_provider`，使用本地 fixture 验证字段映射，不联网、不请求真实基金净值、不保存真实单位净值、累计净值、估算净值或涨跌幅。

```bash
python scripts/run_fund_nav_provider_smoke.py --provider local_fund_nav_fixture --code 000000 --type fund --market CN --local-only
```

## 4. real 模式

`--real` 仅限开发者在本地电脑手动执行。真实请求必须同时满足：

- CLI 参数包含 `--real`。
- `FUND_NAV_ENABLE_REAL_PROVIDER=1`。
- `FUND_NAV_NETWORK_ENABLED=1`。
- `FUND_NAV_ALLOW_REAL_REQUEST=1`。
- 当前不是 CI 环境（`CI=true` 或 `GITHUB_ACTIONS=true` 会被拒绝）。
- provider config 中 `network_enabled=true`。
- provider config 中 `provider_enabled=true`。
- provider config 中 `allow_real_request=true`。
- `allow_commit_to_repo=false`。
- `cache_scope=local_only`。

如果任一条件不满足，脚本返回 `data_status=provider_policy_blocked` 或 `data_status=disabled_by_default`，并说明缺少的条件。

## 5. 安全边界

- 不写 public repo。
- 不保存真实基金净值。
- 不保存真实单位净值、累计净值、估算净值、估算涨跌或日涨跌幅。
- 不保存 token、API Key、Webhook、cookie、authorization、bearer、password 或 secret。
- 真实结果只打印到控制台。
- 输出默认脱敏，并保持 `allow_commit_to_repo=false`。
- 脚本不读取真实 `user_config`，不接日报 / 周报 / Discord，不做真实网页 UI。

## 6. 场外基金说明

场外基金不支持真正实时价格。场外基金只能使用：单位净值、累计净值、净值日期、日涨跌幅、估算净值、估算涨跌、估算更新时间。

盘中估算仅供观察，最终以基金公司公布净值为准。

## 7. 示例命令

Dry-run 示例：

```bash
python scripts/run_fund_nav_provider_smoke.py --provider eastmoney_fund --code 000000 --type fund --market CN --dry-run
```

Local-only 示例：

```bash
python scripts/run_fund_nav_provider_smoke.py --provider local_fund_nav_fixture --code 000000 --type fund --market CN --local-only
```

Real 示例（仅限本地手动运行，禁止在 CI / GitHub Actions 中执行）：

```bash
FUND_NAV_ENABLE_REAL_PROVIDER=1 FUND_NAV_NETWORK_ENABLED=1 FUND_NAV_ALLOW_REAL_REQUEST=1 python scripts/run_fund_nav_provider_smoke.py --provider eastmoney_fund --code 000000 --type fund --market CN --real --no-save
```

## 8. 后续路线

P5-R5：场外基金净值结果审计。

P5-R6：场外基金净值页面展示安全适配。
