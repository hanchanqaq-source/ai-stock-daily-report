# A股 / ETF Provider 真实请求最小闭环说明

## 1. 设计目标

`src/cn_quote_real_provider.py` 用于在安全边界下提供 A股 / ETF 真实 provider 最小闭环 adapter。该模块只负责显式开关、请求校验、可注入 fetcher 调用、结果标准化和失败状态返回；默认关闭，不读取真实 `user_config`，不接日报 / 周报 / Discord，不做 Web UI，也不把真实 provider 结果写入仓库。

## 2. 启用条件

真实请求必须同时满足以下三个条件：

- `network_enabled=true`
- `provider_enabled=true`
- `allow_real_request=true`

默认配置保持：

- `network_enabled=false`
- `provider_enabled=false`
- `allow_real_request=false`
- `default_enabled=false`
- `allow_commit_to_repo=false`
- `cache_scope=local_only`

任一条件未满足时，adapter 返回 `disabled_by_default` 或 `provider_policy_blocked`，不会调用 fetcher。

## 3. 和 dry-run / local-only 的区别

- dry-run：验证请求计划，不处理 provider response，不请求真实行情。
- local-only：使用本地 fixture response 验证字段映射，不联网。
- real-provider：只有显式开启 `network_enabled` / `provider_enabled` / `allow_real_request` 后，才允许调用注入的真实 fetcher；CI 测试使用 fake fetcher，不请求真实网络。

## 4. 支持范围

P5-Q4 提供 `scripts/run_cn_quote_provider_smoke.py` 本地手动 smoke 脚本；脚本默认 dry-run，CI 默认禁止真实 provider 请求，真实请求必须由用户本地显式开启。

P5-Q3 最小闭环仅支持：

- A股 stock
- A股 ETF
- A股 official index

## 5. 不支持范围

以下对象不进入 A股 / ETF quote provider：

- fund：场外基金应使用 `fund_nav_provider`。
- company：企业本身不是可直接报价对象，需关联 stock asset。
- industry / theme：后续通过指数或系统计算指标实现。
- computed_indicator：系统计算指标由市场广度模块生成，不直接请求 provider 行情。
- unknown：返回 `invalid_request`。
- 非 CN 市场资产：返回 `unsupported`。

## 6. 安全规则

- 真实 provider 默认关闭，必须显式开启 `network_enabled`、`provider_enabled` 和 `allow_real_request`。
- provider 必须来自 `provider_registry`，且不得标记为 verified。
- provider config 必须通过 `provider_safety` 检查。
- 明文 token / api_key / webhook 等敏感字段会被拦截。
- `allow_commit_to_repo` 必须为 `false`。
- `cache_scope` 必须为 `local_only`。
- 真实 provider 结果只允许返回到内存，不写入 public 仓库。
- 禁止在仓库中保存真实价格、真实涨跌幅、真实成交额、真实净值、真实金额或 secrets。

## 7. 测试规则

CI 测试使用 fake_fetcher / monkeypatch，不请求真实网络，不 import 真实 provider SDK，不保存真实行情样本。测试只使用示例资产、空 quote 字段或明显 demo 状态验证：

- 默认配置不会调用 fetcher。
- 三个开关全开才调用 fake_fetcher。
- provider_error / provider_timeout / invalid_response / stale_data / conflict 均返回结构化状态，不让整体崩溃。
- 结果必须包含 provider、checked_at、source_status 和 provider_checks。

## 8. 后续路线

- P5-Q4：A股 / ETF provider 本地手动试跑脚本，默认 dry-run，CI 禁止真实请求。
- P5-R：场外基金真实净值 provider 接入评估。
