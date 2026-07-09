# 场外基金净值 Provider Registry 说明

## 1. 设计目标

`src/fund_nav_provider_registry.py` 用于登记场外基金净值候选数据源、字段映射计划、启用策略、缓存策略和失败兜底策略。Registry 只属于接入评估层，不代表已经接入真实 provider，不请求真实基金净值，不保存真实净值、估算净值或涨跌幅。

## 2. Provider 类型

- `fixture`：本地结构化测试来源，不联网，可用于离线测试和字段契约验证。
- `public_web`：公开网页或公开接口候选来源，默认关闭；后续进入真实请求前必须显式启用 `network_enabled`、`provider_enabled` 和 `allow_real_request`。
- `manual_or_app_only`：需要人工评估的手动或 App-only 来源，不默认接入，不抓取个人账户，不读取真实账户配置。

## 3. 候选 Provider

- 东方财富基金 / 天天基金：候选 `public_web` 来源，计划评估每日净值与估算净值字段，不代表已验证。
- 天天基金：候选 `public_web` 来源，计划评估每日净值与估算净值字段，不代表已验证。
- 基金公司官网：候选 `public_web` 来源，计划优先评估每日净值字段，不代表已验证。
- 支付宝 / 蚂蚁基金手动来源：`manual_or_app_only`，仅保留人工评估入口，不抓取个人支付宝数据，不读取真实账户。
- 本地基金净值 fixture：`fixture`，仅用于离线测试和结构验证，不代表真实基金净值。

## 4. 启用策略

真实 provider 默认关闭，必须显式满足：

- `network_enabled=true`
- `provider_enabled=true`
- `allow_real_request=true`
- provider safety 检查通过
- 字段映射、timeout、retry、cache policy、source metadata 和基金估算说明检查通过

后续真实接入必须先从 fixture、dry-run、local-only 路线推进，再考虑真实 provider 最小闭环。

## 5. 字段映射

统一 `FundNavResult` 字段计划分为三组：

- `nav`：`unit_nav`、`accumulated_nav`、`daily_change_pct`、`nav_date`
- `estimate`：`estimated_nav`、`estimated_change_pct`、`estimated_change_amount`、`estimate_time`
- `source`：`provider`、`provider_type`、`source_status`、`checked_at`、`delay_note`

本阶段只定义字段映射计划，不读取真实 provider 输出，不写真实 provider 返回样本。场外基金不支持真正实时价格，估算净值不等于最终净值。

## 6. 缓存策略

本阶段只定义策略，不生成缓存文件。

- `daily_nav`：默认不启用缓存，`cache_scope=local_only`，TTL 为 86400 秒，必须保留 `checked_at` 和 `nav_date`，stale 数据标记为不可用。
- `estimated_nav`：默认不启用缓存，`cache_scope=local_only`，TTL 为 300 秒，必须保留 `checked_at` 和 `estimate_time`，stale 数据标记为不可用。

真实基金净值和估算净值不得写入 public 仓库。Fixture 可用于仓库内结构化测试，但不能冒充真实数据。

## 7. 失败兜底

统一失败状态包括：`provider_timeout`、`provider_error`、`rate_limited`、`invalid_response`、`stale_data`、`conflict`、`unsupported`、`estimate_unavailable`、`daily_nav_unavailable`。

- provider 失败不能让账户页面崩。
- 单个基金失败不影响其他基金。
- 不能用 fixture 冒充真实数据。
- 不能用 stale 数据冒充 available。
- `conflict` 必须保留 warning。
- 估算净值不可用时，不影响每日净值字段。

盘中估算仅供观察，最终以基金公司公布净值为准。
