# 场外基金净值页面展示安全适配说明

## 1. 设计目标

`src/fund_nav_display_adapter.py` 负责把审计后的场外基金净值 `FundNavResult` 转换为页面展示模型。模块只接收内存中的 result 与 `fund_nav_result_audit` 审计结果，不请求真实基金净值、不联网、不读取真实 `user_config`、不写文件，也不接真实 Web UI。

页面展示适配层的核心目标是：在结果进入页面模型前统一判断 `audit_status`、`display_safe`、`commit_safe`、`cache_scope`、`checked_at` 和 `source_status`，保证真实单位净值、累计净值、估算净值、涨跌幅默认不会进入可提交内容。

## 2. 展示模式

支持四种展示模式：

- `redacted`：默认模式。单位净值、累计净值、日涨跌幅、估算净值和估算涨跌统一显示 `<redacted>`，保留 `provider`、`source_status`、`checked_at`、`nav_date` 和 `estimate_time` 等追踪字段。
- `local_real_allowed`：仅限本地页面显式开启后使用。即使本地展示真实值，展示模型也必须标记 `commit_safe=false`。
- `blocked`：审计失败、审计阻断或发现 secret 时使用。页面不显示真实基金净值，只显示阻断原因和安全提示。
- `unavailable`：provider 错误、无效响应、过期数据、每日净值不可用或估算不可用等状态。页面不显示真实值。

## 3. 默认脱敏

默认策略为 `default_display_mode=redacted` 且 `allow_real_values_on_local_page=false`。因此默认不展示：

- 单位净值
- 累计净值
- 日涨跌幅
- 估算净值
- 估算涨跌

默认 Markdown Demo 也只展示 `<redacted>`，用于 CI、文档、测试和安全预览。

## 4. 本地真实展示条件

`local_real_allowed` 必须同时满足：

- 审计状态为 `passed` 或 `passed_with_warnings`。
- `display_safe=true`。
- `has_real_nav_data=true`。
- `commit_safe=false`。
- `cache_scope=local_only`。
- `source.checked_at` 存在。
- `source.source_status` 存在。
- 未发现 token、API key、webhook、cookie、authorization、bearer 等 secret 字段。
- display policy 显式设置 `allow_real_values_on_local_page=true`。

任一条件不满足时，适配层会回退到 `blocked` 或 `redacted`，不会输出真实净值字段。

## 5. blocked 规则

当审计结果为 `failed` / `blocked`，或发现 secret 字段，或本地真实展示安全条件不满足时，展示模型使用 `blocked`。`blocked` 模型中的 `nav_display` 与 `estimate_display` 为空，不显示真实基金净值、估算净值或涨跌幅。

## 6. 和审计模块关系

页面展示必须依赖 `src/fund_nav_result_audit.py`。调用方可以传入已有 audit；若未传入，`build_fund_nav_display_model()` 会在内存中调用 `audit_fund_nav_result()`。展示适配不会修改原始 result，也不会绕过审计直接展示真实值。

P5-R6 使用审计结果生成页面展示模型，默认脱敏；真实 provider 结果进入页面前必须先通过审计和展示适配。

## 7. 场外基金说明

场外基金不支持真正实时价格，页面文案不能称为实时涨跌。可展示字段仅限：单位净值、累计净值、净值日期、日涨跌幅、估算净值、估算涨跌和估算更新时间。

盘中估算仅供观察，最终以基金公司公布净值为准。

## 8. 后续路线

- P5-R7：场外基金净值接入账户基金汇总 dry-run。
- P5-S：股票 / ETF / 基金真实数据统一汇总安全适配。
