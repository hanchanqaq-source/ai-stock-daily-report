# Provider Registry 说明

## 1. 设计目标

Provider registry 用于登记 A股 / ETF / 官方指数行情候选数据源，提前固化候选范围、字段映射计划、启用策略、缓存策略、失败兜底和 dry-run 路线。

该 registry 只代表“接入前评估结构”，不代表已经接入真实 provider，也不代表候选 provider 已验证。本阶段不发起网络请求，不读取真实 `user_config`，不保存真实价格、涨跌幅或成交额。

## 2. Provider 类型

- `fixture`：本地离线测试数据，只能用于结构验证和自动化测试。
- `mock`：模拟 provider，不应冒充真实行情。
- `public_web`：公开网页或公开接口候选源，默认关闭，后续必须显式打开网络开关和 provider 配置。
- `api`：API provider 候选源，默认关闭；如后续需要凭据，只能从运行环境读取。
- `public_web_or_library`：公开网页或公开库封装的候选源，默认关闭，必须先通过安全审查。

## 3. 候选 Provider

当前 registry 仅登记以下候选，不表示已接入或已验证：

| Provider | 类型 | 市场 | 资产类型 | 状态 |
| --- | --- | --- | --- | --- |
| `akshare` | `public_web_or_library` | CN | stock / etf / index | `candidate_only` |
| `eastmoney` | `public_web` | CN | stock / etf / index | `candidate_only` |
| `sina_finance` | `public_web` | CN | stock / etf | `candidate_only` |
| `tencent_finance` | `public_web` | CN | stock / etf | `candidate_only` |
| `local_fixture` | `fixture` | CN | stock / etf / index | `supported_for_tests` |

## 3.1 P5-Q1 dry-run adapter

P5-Q1 已新增 A股 / ETF provider dry-run adapter，用于在真实接入前验证请求计划和安全边界。dry-run 只读取 registry 中的候选状态、字段映射、缓存策略和失败兜底策略，不请求真实行情，不保存真实数据。

## 4. 启用策略

真实 provider 默认关闭，必须显式启用 `network_enabled` 和 provider config，且必须通过 provider safety、字段映射、timeout、retry、cache policy 和 source metadata 检查。

后续真实接入必须从 `dry_run` / `local_only` 开始，不允许默认写入 public 仓库，不允许在测试中保存真实行情。

## 5. 字段映射

字段映射统一规划到 `QuoteResult` 字段：

- `last_price`
- `change_pct`
- `change_amount`
- `volume`
- `turnover`
- `open`
- `high`
- `low`
- `previous_close`
- `checked_at`
- `source_provider`
- `source_status`

本阶段只定义统一字段需求，不写真实 provider 返回字段、真实行情值或真实数据样本。字段不确定时应保持 `pending_review`，直到 dry-run adapter 单独验证。

## 6. 缓存策略

真实行情缓存默认 `local_only`，不提交 public repo。缓存策略必须保留 `checked_at`、`expires_at`、`ttl_seconds`、provider 和 data kind。

stale 数据不能冒充 available；过期缓存只能标记为 `stale_data` 或 unavailable。fixture 可以作为仓库测试资产提交，但不能冒充真实 provider 输出。

## 7. 失败兜底

统一失败状态包括：

- `provider_timeout`
- `provider_error`
- `rate_limited`
- `invalid_response`
- `stale_data`
- `conflict`
- `unsupported`

provider 失败不能让整个账户页面崩溃；单资产失败不影响其他资产。真实 provider 失败时不能用 fixture 冒充真实数据，也不能用 stale 数据冒充 available。多 provider 数据冲突必须标记 `conflict` 并保留 warning。
