# 代码自动识别框架说明

## 1. 设计目标

代码自动识别框架用于在用户输入基金 / 股票 / 指数等代码后，先根据代码格式给出可能的资产类型和市场候选，并返回稳定的结构化结果。该结果面向后续本地网页工作台、配置录入和 P5-G 自动补全流程复用。

识别结果包含状态、置信度、候选项、是否需要用户确认、来源证据和能否进入正式分析等字段。

## 2. 不做什么

本阶段只做格式规则识别：

- 不联网搜索。
- 不接入真实基金库或股票库。
- 不编造真实名称。
- 不编造标签。
- 不编造行业。
- 不编造基金主题。
- 不把格式猜测当成确定事实。
- 不读取真实 `user_config`。
- 不保存金额、成本价、账户资产、Webhook、Token、API Key 等敏感信息。

## 3. 状态说明

- `verified`：已有可查证来源或明确用户确认，可作为已确认结果。仅靠格式规则不能进入该状态。
- `unknown`：无法根据当前规则识别，或缺少必要信息。
- `pending_confirmation`：格式规则给出候选，但仍需用户确认或后续可查证来源补全。
- `conflict`：多个来源或规则结果互相冲突，需要人工处理。

## 4. 置信度说明

- `high`：高置信度。当前格式规则通常不直接产生可正式分析的高置信已验证结论。
- `medium`：中等置信度。适用于常见格式候选，例如 6 位数字、`.HK`、`.US`、纯英文字母等。
- `low`：低置信度。适用于无法识别、非法输入或冲突结果。

## 5. 格式规则

当前基础规则保持保守：

- 6 位纯数字：候选 `CN stock` / `CN fund` / `CN etf`，状态为 `pending_confirmation`。
- 以 `.HK` 结尾：候选 `HK stock`，状态为 `pending_confirmation`。
- 纯英文字母 1-5 位：候选 `US stock`，状态为 `pending_confirmation`。
- 以 `.US` 结尾：候选 `US stock`，状态为 `pending_confirmation`。
- 以 `.JP` 结尾：候选 `JP stock` / `JP index`，状态为 `pending_confirmation`。
- 以 `.KR` 结尾：候选 `KR stock` / `KR index`，状态为 `pending_confirmation`。
- 空字符串、`None`、非法字符：状态为 `unknown`。
- 无法识别的格式：状态为 `unknown`，候选为空。

这些规则的来源只能标记为内部格式规则，例如 `code_format_rule` / `internal_history`，不能伪装为官方来源或公开网页来源。

## 6. 用户确认原则

- 多候选时必须设置 `needs_user_confirmation=true`。
- 查不到或无法按格式识别时标记为 `unknown`。
- 只有格式候选、但未接入可查证来源时标记为 `pending_confirmation`。
- 未达到 `verified` 前，`usable_for_formal_analysis` 必须为 `false`。
- 未接入真实来源时，`name` 必须保持未知，`tags` 必须为空。

## 7. 后续路线

P5-G 会在该结构基础上接入可查证来源，补全名称、类型、市场、标签、来源证据和置信度。接入后仍需遵守信息来源可查证规则，不能把格式猜测升级为已验证事实。
