# A股 / ETF 行情 Provider 接入评估

## 1. 评估目标

P5-Q 阶段只做真实 A股 / ETF provider 接入前评估，不接真实行情，不联网，不调用候选数据源，不保存真实价格、涨跌幅、成交额或账户数据。

本阶段目标是先明确候选 provider、适用范围、字段映射计划、启用策略、缓存策略、失败兜底、public 仓库安全边界和后续 dry-run 路线。

## 2. 候选数据源

以下数据源仅作为候选，不表示已经接入或已验证：

- AKShare：候选 `public_web_or_library`，覆盖 CN stock / etf / index，默认关闭。
- 东方财富：候选 `public_web`，覆盖 CN stock / etf / index，默认关闭。
- 新浪财经：候选 `public_web`，覆盖 CN stock / etf，默认关闭。
- 腾讯财经：候选 `public_web`，覆盖 CN stock / etf，默认关闭。
- 本地 fixture：离线测试 provider，仅用于结构验证和测试。

## 3. 接入前条件

后续任何真实 provider 接入前必须通过：

- `provider_safety`：确认网络、凭据、缓存、来源标记和失败语义边界。
- `field_mapping`：只映射到统一 `QuoteResult` 字段，禁止直接透传未审查 payload。
- `timeout`：必须定义请求超时。
- `retry`：必须定义有限重试次数。
- `cache_policy`：真实行情缓存默认 local-only，禁止提交 public repo。
- `source_metadata`：必须保留 provider、checked_at、source_status 等来源信息。

## 4. dry-run 路线

接入路线为 dry-run → local-only → real-provider minimal gated adapter → local manual smoke test；P5-Q4 在该路线末端新增本地手动 smoke 脚本，CI 仍不联网、不请求真实行情。

后续路线必须按以下顺序推进：

1. 先使用 fixture 验证 registry、字段映射和失败状态。
2. 增加 dry-run adapter，只验证配置、字段计划和错误路径，不发起真实请求。
3. 增加 local-only adapter，在显式配置下进行本地验证，产物不进入 public repo。
4. 增加 real-provider minimal gated adapter，必须显式开启 network_enabled / provider_enabled / allow_real_request 后才允许调用注入 fetcher。
5. 增加 local manual smoke test，只允许用户本地显式开启真实请求，CI 默认禁止真实 provider。

## 4.1 P5-Q1 dry-run adapter

P5-Q1 已新增 dry-run adapter，用于在真实接入前验证 A股 stock / ETF / official index 的请求计划和安全边界。dry-run 不请求真实行情，不保存真实数据，也不会把结果标记为 available real data。

## 5. public 仓库安全边界

public 仓库不得保存：

- 真实行情数据、真实价格、真实涨跌幅、真实成交额。
- 凭据、API key、webhook、cookie、authorization 或 bearer 信息。
- 真实账户资产、成本价、金额、个人邮箱、手机号、身份证等隐私数据。

仓库只能保存 registry、字段映射计划、安全规则、离线 fixture 和不含真实数据的测试。

## 6. 后续路线

- P5-Q1：A股 / ETF provider dry-run adapter。
- P5-Q2：A股 / ETF provider local-only 测试。
- P5-Q3：A股 / ETF provider 真实请求最小闭环 adapter，默认关闭。
- P5-Q4：A股 / ETF provider 本地手动试跑脚本。
- P5-R：场外基金真实净值 provider 接入评估。
