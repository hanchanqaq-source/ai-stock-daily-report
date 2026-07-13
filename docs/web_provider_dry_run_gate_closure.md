# Web-M1B Provider Dry-Run 安全门禁闭环

## 定位

Web-M1B 将 Web-P49 默认关闭的 `ProviderDryRunFeatureFlag` 与既有 mock-only provider candidate 链路组合为一个安全门禁。该门禁只服务“股票基金质量分析系统”的前端 dry-run 验证，日报显示名称固定为“AI股票基金每日信息报告”。

当前阶段仍不接页面、runtime、真实 provider、账户、通知、AI、交易或后端接口，真实 provider 结论保持 **NO-GO**。

## 完整链路

```text
ProviderDryRunFeatureFlag
→ evaluateProviderDryRunFeatureFlag
→ disabled / blocked 时停止
→ enabled-mock-only 时调用 normalizeProviderCandidatePayloadToDryRunInput
→ validateProviderCandidatePayload
→ schema normalization
→ validateRealDailyReportDryRunInput
→ completed-mock-only / blocked
→ fallback mock-only
```

`providerDryRunGate` 不复制 candidate validator、normalization 或 dry-run validator 逻辑，只负责先检查 feature flag、控制是否进入既有 normalizer，并把结果封装为低敏门禁结果。

## 状态矩阵

| 状态 | 触发条件 | candidateChainExecuted | normalizedInput |
| --- | --- | --- | --- |
| `disabled` | 输入缺省、空配置或 `enabled=false` | `false` | 不存在 |
| `blocked` | gate 输入非法、feature flag 非法、candidate 缺失、candidate 链路 blocked 或异常 | 视阶段而定 | 不存在 |
| `completed-mock-only` | `enabled-mock-only` 且 candidate → normalizer → dry-run validator 全部通过 | `true` | 存在 |

## candidateChainExecuted 语义

- `false`：没有进入 candidate validator / normalizer / dry-run validator 链路。
- `true`：已经调用现有 `normalizeProviderCandidatePayloadToDryRunInput`，并由其内部执行 candidate validator、schema normalization 和 dry-run validator。

## blockedStage 语义

- `gate-input`：gate 根输入非法、顶层未知字段或 enabled 状态下缺少 candidate。
- `feature-flag`：feature flag evaluator 返回 blocked。
- `candidate-chain`：normalizer 返回 blocked，包括 candidate validator blocked 或 dry-run validator blocked。
- `unexpected`：未处理异常被 gate 捕获，统一返回低敏失败码。

## 成功输出边界

`normalizedInput` 只在 `completed-mock-only` 结果中存在。`disabled` 与 `blocked` 结果不得包含 `normalizedInput`、candidate 原文、ViewModel 或 raw provider 信息。

成功输出终点是 `RealDailyReportDryRunInput`，不会继续调用 dry-run adapter，也不会生成 `DailyReportViewModel`。

## mock-only fallback

所有结果固定：

- `fallbackMode: mock-only`
- `canFallbackToMockOnly: true`
- `allowRealProvider: false`
- `allowRealAccountRead: false`
- `allowNotificationSend: false`
- `allowTrading: false`
- `allowAiCall: false`
- `requiresHumanApproval: true`

任意失败、异常或未知错误均保持 mock-only fallback，不回显输入值、异常信息、provider 信息或凭证信息。

## Feature flag 收紧

Web-M1B 同步收紧 Web-P49：真实能力字段只要存在，就必须严格等于 `false`。`true`、字符串、数字、`null`、显式 `undefined`、对象和数组都会 blocked。

feature flag 只允许以下字段：`enabled`、`mode`、`allowRealProvider`、`allowRealAccountRead`、`allowNotificationSend`、`allowTrading`、`allowAiCall`、`requiresHumanApproval`、`fallbackMode`、`canFallbackToMockOnly`。普通未知字段返回低敏路径错误；敏感未知字段返回敏感未知字段错误，均不回显字段值。

## Runtime 隔离与下一阶段

`providerDryRunGate` 仍位于 mock-only provider 目录，未被 preview entry、preview model、React 页面、store、context、utils、API client 或正式 runtime 导入。

下一阶段如要进入真实只读 provider，仍必须先取得用户人工批准，并补齐凭证方案、只读权限、脱敏日志、网络边界、回滚方案与端到端验证。当前真实 provider 最终结论：**NO-GO**。


## Core-M2 交叉引用

Core-M2 已新增首个真实只读 Provider 本地 Dry-Run 基础框架，详见 [Core-M2 首个真实只读 Provider 本地 Dry-Run 基础框架](web_provider_readonly_local_dry_run_framework.md)。该框架继续保持不联网、不读取凭证、不接页面或 runtime，真实 Provider 状态仍为 **NO-GO**。
