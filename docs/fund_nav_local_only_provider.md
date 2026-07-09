# 场外基金净值 Provider Local-only 测试说明

## 1. 设计目标

`src/fund_nav_local_only_provider.py` 用于在不联网的情况下验证未来场外基金净值 provider 的 response 字段映射、结果标准化和安全边界。它只读取本地 fixture / demo provider response，不请求天天基金、东方财富、支付宝或基金公司官网，不读取真实 `user_config`，也不保存真实单位净值、累计净值、估算净值或涨跌幅。

## 2. 和 dry-run 的区别

- dry-run：验证请求计划、provider registry 和 safety preflight，不处理 provider response。
- local-only：验证本地 fixture response 映射，将 provider 风格响应标准化为统一 `nav` / `estimate` 字段。

P5-R2 local-only 不是真实 provider；它不会请求网络，也不会产生真实基金净值。

## 3. 支持范围

仅支持 CN 场外 `fund`，用于验证：

- `daily_nav` 映射：`unit_nav`、`accumulated_nav`、`daily_change_pct`、`nav_date`
- `estimated_nav` 映射：`estimated_nav`、`estimated_change_pct`、`estimated_change_amount`、`estimate_time`
- `provider_checks`、`checked_at`、`warnings`、`disclaimer` 等标准结果字段

## 4. 不支持范围

以下资产类型不会进入场外基金净值 local-only provider：

- `stock`
- `etf`
- `index`
- `company`
- `industry`
- `theme`
- `computed_indicator`
- `unknown`
- 非 CN 市场基金

其中 `unknown` 返回 `invalid_request`，其他非支持类型返回 `unsupported`。

## 5. 数据状态

local-only result 支持以下 `data_status`：

- `local_only_available`
- `local_only_unavailable`
- `unsupported`
- `invalid_request`
- `provider_error`
- `invalid_response`
- `stale_data`
- `conflict`
- `estimate_unavailable`
- `daily_nav_unavailable`

local-only result 不允许使用 `available`，也不允许标记为 `real_provider`。

## 6. 安全规则

- `network_enabled` 必须为 `false`。
- `will_fetch_real_data` 必须为 `false`。
- `has_real_nav_data` 必须为 `false`。
- `source_status` 只能是 `local_fixture_only` 或 `fixture_only`。
- `allow_commit_to_repo` 必须为 `false`。
- fixture 定义可以入库，但只允许示例基金和空字段，不允许真实 provider response 样本。
- config、fixture 和 result 不允许包含 token、API key、webhook、cookie、authorization、bearer 等敏感字段。
- local-only 结果不得被当作 `real_provider` 数据。

## 7. 场外基金说明

场外基金不能称为实时涨跌，只能使用单位净值、累计净值、净值日期、日涨跌幅、估算净值、估算涨跌和估算更新时间等表述。

盘中估算仅供观察，最终以基金公司公布净值为准。

## 8. 后续路线

- P5-R3：场外基金净值真实请求最小闭环。
- P5-R4：场外基金净值本地手动试跑脚本。
