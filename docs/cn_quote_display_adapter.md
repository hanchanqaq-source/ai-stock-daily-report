# A股 / ETF Provider 页面展示安全适配说明

## 1. 设计目标

`src/cn_quote_display_adapter.py` 负责把审计后的 A股 / ETF provider `QuoteResult` 转换为本地页面展示模型。模块只接收调用方传入的内存对象和审计结果，不请求真实行情、不联网、不读取真实 `user_config`，也不写文件。

本模块位于 P5-Q5 结果审计之后、后续页面汇总接入之前：只有审计通过或 `passed_with_warnings` 的结果，才允许进入页面展示模型；审计失败、被阻断或发现 secret 的结果只生成错误状态，不展示行情值。

## 2. 展示模式

- `redacted`：默认模式。价格、涨跌幅、成交额等行情字段统一显示为 `<redacted>`，用于 CI、文档、测试和安全预览。
- `local_real_allowed`：仅允许本地页面显式开启真实值展示后使用。该模式仍然标记 `commit_safe=false`，不得提交真实行情值。
- `blocked`：审计失败、审计阻断、发现 secret 或安全条件不满足时使用。页面只展示原因和安全提示，不显示真实行情值。
- `unavailable`：provider error、invalid response、stale data 等不可展示状态。页面保留来源信息和状态，不展示真实行情值。

## 3. 默认脱敏

默认策略 `build_cn_quote_display_policy()` 使用 `default_display_mode=redacted` 且 `allow_real_values_on_local_page=false`。因此默认不展示真实价格、涨跌幅、成交额、成交量、开高低收等行情字段。

默认 Markdown demo 也只展示脱敏字段，避免把本地 provider 结果复制进文档、测试快照或 public 仓库。

## 4. 本地真实展示条件

`local_real_allowed` 必须同时满足：

- 审计状态为 `passed` 或 `passed_with_warnings`。
- `display_safe=true`。
- `has_real_market_data=true`。
- `commit_safe=false`。
- `cache_scope=local_only`。
- `checked_at` 存在。
- `source_status` 存在。
- 未发现 secret 字段。
- policy 显式设置 `allow_real_values_on_local_page=true`。

即使本地页面展示真实值，展示模型也必须保留 `commit_safe=false`，并提示真实行情值不得提交到 public 仓库。

## 5. blocked 规则

以下情况必须生成 `blocked`，且 `quote_display` 为空或不包含真实行情值：

- `audit_status=failed`。
- `audit_status=blocked`。
- 审计结果或输入对象包含 Token、API Key、Webhook、cookie、authorization、bearer 等 secret 字段。
- 真实行情结果被标记为可提交仓库。
- 显式开启真实展示时，`cache_scope` 不是 `local_only`，或缺少 `checked_at` / `source_status`。

## 6. 和审计模块关系

页面展示必须依赖 `src/cn_quote_result_audit.py`：

- 如果调用方传入 audit result，展示适配器使用传入的审计结果。
- 如果调用方未传 audit result，展示适配器会调用 `audit_cn_quote_result(result)`。
- `passed` / `passed_with_warnings` 可进入默认脱敏展示。
- `failed` / `blocked` 不允许展示真实行情值。

## 7. 后续路线

- P5-Q7：A股 / ETF provider 接入账户行情汇总 dry-run。
- P5-R：场外基金真实净值 provider 接入评估。
