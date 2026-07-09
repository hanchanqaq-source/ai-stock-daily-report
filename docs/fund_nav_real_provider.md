# 场外基金净值 Provider 真实请求最小闭环说明

## 1. 设计目标

P5-R3 新增 `src/fund_nav_real_provider.py`，用于在安全边界下提供场外基金净值 provider 真实请求的最小闭环。该模块只定义 gated adapter、标准化结果、结构化错误和 Markdown demo；真实 provider 默认关闭，不在 CI 中联网，不保存真实基金净值到仓库。

## 2. 启用条件

真实请求必须同时满足：

- `network_enabled=true`
- `provider_enabled=true`
- `allow_real_request=true`

默认配置为 `network_enabled=false`、`provider_enabled=false`、`allow_real_request=false`、`default_enabled=false`、`allow_commit_to_repo=false`。三个开关未同时开启时，adapter 返回 `disabled_by_default` 或 `provider_policy_blocked`，不会调用 fetcher。

## 3. 和 dry-run / local-only 的区别

- dry-run：验证请求计划和 provider 安全边界，不处理 provider response，不请求网络。
- local-only：使用本地 fixture 验证 response 字段映射，不联网，不包含真实净值。
- real-provider：仅在显式开启 `network_enabled` / `provider_enabled` / `allow_real_request` 后，才允许调用注入的 fetcher，并将返回值标准化为内存中的基金净值结果。

## 4. 支持范围

当前仅支持 CN 场外 fund，字段名称限定为单位净值、累计净值、净值日期、日涨跌幅、估算净值、估算涨跌和估算更新时间。

## 5. 不支持范围

不支持 `stock` / `etf` / `index` / `company` / `industry` / `theme` / `computed_indicator` / `unknown`，非 CN 市场基金也不进入真实 provider。股票、ETF、指数和系统计算指标应进入对应 quote、index 或市场广度模块。

## 6. 安全规则

- 真实 provider 默认关闭。
- 真实结果只返回到内存，不写 public repo。
- 不保存真实单位净值、累计净值、估算净值、涨跌幅、账户资产或成本信息。
- 不保存 token、API key、webhook、cookie、authorization、bearer 等 secrets。
- `allow_commit_to_repo` 必须为 `false`。
- `cache_scope` 必须为 `local_only`。
- provider 必须来自 `fund_nav_provider_registry`，且必须经过 `provider_safety` 检查。

## 7. 测试规则

CI 测试只使用 `fake_fetcher` / monkeypatch，不请求真实网络，不请求天天基金 / 东方财富 / 支付宝 / 基金公司官网，不读取真实 `user_config`，不保存真实 provider 返回样本。

## 8. 场外基金说明

场外基金不能称为实时涨跌。盘中估算仅供观察，最终以基金公司公布净值为准。

## 9. 后续路线

- P5-R4：场外基金净值本地手动试跑脚本。
- P5-R5：场外基金净值结果审计。

## P5-R4 本地手动 smoke 脚本

P5-R4 提供 `scripts/run_fund_nav_provider_smoke.py` 作为本地手动 smoke 脚本。脚本默认 dry-run，不请求真实基金净值；CI / GitHub Actions 环境默认禁止真实请求。真实请求仅限本地手动执行，并必须显式设置 `--real`、`FUND_NAV_ENABLE_REAL_PROVIDER=1`、`FUND_NAV_NETWORK_ENABLED=1` 和 `FUND_NAV_ALLOW_REAL_REQUEST=1`。
