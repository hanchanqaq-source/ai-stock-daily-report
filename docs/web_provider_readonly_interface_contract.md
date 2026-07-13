# Web-P44 provider 只读接口契约文档

## 1. 阶段定位

Web-P44 是“股票基金质量分析系统”在 Web dry-run 链路上的 provider 只读接口契约文档阶段。本阶段只定义未来接口的文档级形状和安全约束，用于约束后续候选数据进入“AI股票基金每日信息报告”前的只读边界。

Web-P44 仅做以下事项：

- 只写接口契约文档。
- 不新增 provider client。
- 不新增 API client。
- 不新增真实请求。
- 不读取真实账户。
- 不读取真实行情。
- 不调用 AI / Agent。
- 不发送通知。
- 不读取数据库。
- 不执行交易。
- 不读取 `.env`、token、webhook、API key。
- 不改变当前 mock-only 页面链路。

Web-P44 完成后，也不代表可以开始真实 provider 接入。真实 provider 接入必须另开阶段、另开设计、另开 PR，并在凭证、只读权限、feature flag、CI、脱敏、schema normalization、validator、adapter、日志和人工确认等前置条件全部满足后再讨论。

## 2. 与 Web-P43 的关系

- Web-P43 定义 provider 只读设计原则，说明 provider 未来只能作为只读候选输入来源。
- Web-P44 在 Web-P43 的基础上定义未来 provider 接口契约形状。
- Web-P44 不实现接口，只描述未来接口应满足什么约束。

因此，Web-P44 不改变 Web-P43 的安全结论：当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易，也不改变 mock-only 页面链路。

## 3. provider 接口总原则

provider 未来只能输出候选输入，不允许直接输出页面 viewModel，也不允许把 provider 原始完整响应直接进入页面、测试快照或 mock-only fixture。

未来允许讨论的链路必须保持为：

```text
provider readonly request
→ provider readonly response
→ redaction
→ schema normalization
→ RealDailyReportDryRunInput
→ validateRealDailyReportDryRunInput
→ adaptRealDailyReportDryRunInputToViewModel
→ DailyReportViewModel
```

接口总原则：

- provider 只读接口只产出低敏候选数据。
- provider 输出不是 `DailyReportViewModel`。
- provider 输出不是 `RealDailyReportDryRunInput`。
- provider 输出必须先经过 redaction 和 schema normalization。
- validator 未明确通过时，不允许调用 adapter。
- adapter 只消费通过校验的 `RealDailyReportDryRunInput`。
- 任意失败、阻断、超时、schema mismatch 或 redaction 失败都必须允许 fallback mock-only。

## 4. ProviderReadonlyRequest 契约草案

`ProviderReadonlyRequest` 是未来只读 provider 请求的文档级输入形状。Web-P44 不编写 TypeScript 代码，也不实现真实请求。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `requestId` | 低敏请求标识；不得包含真实账户、手机号、邮箱、token、webhook 或 API key。 |
| `requestMode` | 请求模式；当前只能是 `design` / `dry-run-readonly`。 |
| `providerType` | provider 类型标签；只能使用低敏分类，不写真实 endpoint。 |
| `purpose` | 请求用途；应限定为生成候选日报输入。 |
| `requestedFields` | 最小化字段清单；只允许声明生成候选输入所需字段。 |
| `timeRange` | 低敏时间范围标签；不得包含真实账户查询语句或 provider 私有参数。 |
| `dryRun` | 必须为 `true`。 |
| `allowNetwork` | 当前文档阶段不得作为真实联网许可；后续阶段也必须由单独 feature flag 控制。 |
| `allowAccountWrite` | 必须为 `false`。 |
| `allowTrading` | 必须为 `false`。 |
| `allowNotification` | 必须为 `false`。 |
| `allowAiCall` | 必须为 `false`。 |
| `credentialMode` | 当前必须是 `not-configured` / `external-disabled` / `redacted-placeholder`。 |
| `redactionRequired` | 必须明确要求脱敏。 |
| `traceLabel` | 低敏追踪标签；不得携带可识别个人、账户、凭证或真实 provider endpoint 的信息。 |

必须规则：

- `requestMode` 当前只能是 `design` / `dry-run-readonly`，不得是 `production`。
- `dryRun` 必须是 `true`。
- `allowAccountWrite` 必须是 `false`。
- `allowTrading` 必须是 `false`。
- `allowNotification` 必须是 `false`。
- `allowAiCall` 必须是 `false`。
- `credentialMode` 当前必须是 `not-configured` / `external-disabled` / `redacted-placeholder`。
- `requestedFields` 必须最小化，不得用宽泛字段要求 provider 返回完整响应。
- `traceLabel` 必须低敏。

## 5. ProviderReadonlyResponse 契约草案

`ProviderReadonlyResponse` 是未来 provider 只读响应的文档级输出形状。它不是页面 viewModel，也不是 dry-run schema 的最终输入。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `requestId` | 与请求对应的低敏标识。 |
| `providerType` | 低敏 provider 类型标签。 |
| `responseStatus` | 响应状态，建议为 `unavailable` / `redacted` / `candidate-ready` / `blocked`。 |
| `collectedAtLabel` | 低敏采集时间标签；不写 provider 私有时间戳或账户查询参数。 |
| `sourceLabel` | 低敏来源标签；不得包含真实 endpoint、账号、联系方式或凭证片段。 |
| `redactionStatus` | 脱敏状态。 |
| `candidatePayload` | 低敏候选数据；仅在允许时出现。 |
| `errors` | 低敏错误结构列表。 |
| `warnings` | 低敏警告结构列表。 |
| `fallback` | fallback 策略说明，必须允许 mock-only。 |

`responseStatus` 建议枚举：

- `unavailable`：provider 不可用或当前未启用。
- `redacted`：响应已脱敏，但仍需后续 normalization 和 validator。
- `candidate-ready`：候选数据可进入 schema normalization。
- `blocked`：响应被安全策略阻断。

必须规则：

- `candidatePayload` 只能是低敏候选数据。
- 不得包含 provider 原始完整响应。
- 不得包含 token / webhook / API key。
- 不得包含真实联系方式。
- 不得包含可执行交易字段。
- `sourceLabel` 必须低敏。
- `providerName` 必须脱敏，例如使用 `REDACTED_PROVIDER_LABEL` 同等级标签。
- `responseStatus` 为 `blocked` 时不得有 `candidatePayload`。
- `fallback` 必须允许 mock-only。

## 6. ProviderCandidatePayload 契约草案

`ProviderCandidatePayload` 是 provider 响应中的候选 payload，不是页面展示模型，也不是最终 dry-run 输入。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `candidateId` | 低敏候选标识。 |
| `candidateType` | 候选类型标签。 |
| `providerType` | 低敏 provider 类型标签。 |
| `sourceLabel` | 低敏来源标签。 |
| `dataFreshnessLabel` | 低敏数据新鲜度标签。 |
| `sections` | 候选段落数据；仍需 schema normalization。 |
| `metrics` | 候选指标数据；不得包含真实精确资产值或敏感比例。 |
| `riskSignals` | 候选风险信号；不得包含可执行交易指令。 |
| `redactionLabels` | 脱敏标签。 |
| `safetyLabels` | 安全边界标签。 |

必须规则：

- `candidatePayload` 不是页面 viewModel。
- `candidatePayload` 不是 `RealDailyReportDryRunInput`。
- `candidatePayload` 必须先经过 schema normalization 才能变成 `RealDailyReportDryRunInput`。
- `candidatePayload` 不允许绕过 validator / adapter。
- `candidatePayload` 不允许写入 mock-only fixture。
- `candidatePayload` 不允许进入测试快照，除非完全虚构且脱敏。

## 7. 错误结构

`ProviderReadonlyError` 用于描述低敏错误，不得泄漏 provider 原始响应、凭证、账户或个人联系方式。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `code` | 低敏错误枚举。 |
| `severity` | 错误级别标签。 |
| `safeMessage` | 可展示或可记录的低敏信息。 |
| `retryable` | 是否可有限重试。 |
| `fallbackRequired` | 是否必须 fallback mock-only。 |
| `traceLabel` | 低敏追踪标签。 |

错误 `code` 可设计为低敏枚举：

- `provider.unavailable`
- `provider.timeout`
- `provider.rate_limited`
- `provider.auth_not_configured`
- `provider.schema_mismatch`
- `provider.redaction_failed`
- `provider.blocked_sensitive_content`

要求：

- `safeMessage` 不得包含真实 token、webhook、API key、账户标识、联系方式、原始响应。
- `fallbackRequired` 如果为 `true`，必须 fallback mock-only。
- `auth_not_configured` 不代表可以读取 `.env`，只表示未配置真实凭证。

## 8. 超时、重试、缓存字段契约

`ProviderReadonlyPolicy` 用于描述未来只读 provider 的超时、重试、缓存和降级策略。Web-P44 只写文档，不实现策略代码。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `timeoutMs` | 有限超时时间。 |
| `maxRetries` | 有限重试次数。 |
| `retryBackoffLabel` | 低敏退避策略标签。 |
| `cacheMode` | 缓存模式标签。 |
| `cacheTtlLabel` | 缓存有效期标签。 |
| `cacheRedactionRequired` | 缓存前是否必须脱敏。 |
| `fallbackOnTimeout` | 超时是否 fallback mock-only。 |
| `fallbackOnSchemaError` | schema 错误是否 fallback mock-only。 |
| `fallbackOnRedactionError` | redaction 错误是否 fallback mock-only。 |

必须规则：

- 不允许无限重试。
- 不允许缓存 provider 原始完整响应。
- 不允许缓存真实账户原文。
- schema 错误必须 fallback mock-only。
- redaction 错误必须 fallback mock-only。
- timeout 必须 fallback mock-only。

## 9. 日志字段契约

`ProviderReadonlyLogEvent` 只能记录低敏诊断信息，用于定位状态、降级和 schema / redaction 结果，不得成为凭证、账户或真实资产信息的旁路泄漏渠道。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `traceLabel` | 低敏追踪标签。 |
| `providerType` | 低敏 provider 类型标签。 |
| `eventType` | 低敏事件类型。 |
| `safeCode` | 低敏诊断码。 |
| `fallbackMode` | fallback 模式标签。 |
| `schemaStatus` | schema normalization / validation 状态。 |
| `redactionStatus` | 脱敏状态。 |

禁止日志字段：

- token。
- webhook。
- API key。
- 手机号。
- 邮箱。
- 真实账户 ID。
- 真实交易流水。
- provider 原始响应。
- 精确资产金额。
- 精确收益率。
- 可追溯用户真实资产的比例。

## 10. 禁止内容

provider 接口契约、示例和文档不得包含：

- 真实 API URL。
- 真实 provider endpoint。
- 真实 token。
- 真实 webhook。
- 真实 API key。
- `.env` 内容。
- 真实账户明细。
- 真实持仓明细。
- 真实基金代码。
- 真实交易记录。
- 真实手机号。
- 真实邮箱。
- provider 原始完整响应。
- 数据库导出内容。
- 真实历史日报原文。
- 可追溯真实资产的精确金额、收益率和比例。

不要重新明文列出已移除的旧真实精确值。示例只能使用完全虚构、脱敏、不可真实运行的占位符。

## 11. 示例 JSON

以下示例仅用于说明文档级契约形状，完全虚构、脱敏、不可真实运行。示例不包含真实 URL、真实代码、真实账号、真实金额或真实 key。

```json
{
  "request": {
    "requestId": "REQUEST_ID_PLACEHOLDER",
    "requestMode": "dry-run-readonly",
    "providerType": "PROVIDER_TYPE_PLACEHOLDER",
    "purpose": "MOCK_FIELD",
    "requestedFields": ["MOCK_FIELD"],
    "timeRange": "MOCK_FIELD",
    "dryRun": true,
    "allowNetwork": false,
    "allowAccountWrite": false,
    "allowTrading": false,
    "allowNotification": false,
    "allowAiCall": false,
    "credentialMode": "redacted-placeholder",
    "redactionRequired": true,
    "traceLabel": "TRACE_LABEL_PLACEHOLDER"
  },
  "response": {
    "requestId": "REQUEST_ID_PLACEHOLDER",
    "providerType": "PROVIDER_TYPE_PLACEHOLDER",
    "responseStatus": "candidate-ready",
    "collectedAtLabel": "MOCK_FIELD",
    "sourceLabel": "REDACTED_PROVIDER_LABEL",
    "redactionStatus": "REDACTED_VALUE",
    "candidatePayload": {
      "candidateId": "REQUEST_ID_PLACEHOLDER",
      "candidateType": "MOCK_FIELD",
      "providerType": "PROVIDER_TYPE_PLACEHOLDER",
      "sourceLabel": "REDACTED_PROVIDER_LABEL",
      "dataFreshnessLabel": "MOCK_FIELD",
      "sections": ["MOCK_FIELD"],
      "metrics": [{ "label": "MOCK_METRIC", "value": "MOCK_AMOUNT" }],
      "riskSignals": [{ "label": "MOCK_FIELD", "ratio": "MOCK_RATIO" }],
      "redactionLabels": ["REDACTED_VALUE"],
      "safetyLabels": ["MOCK_FIELD"]
    },
    "errors": [],
    "warnings": [
      {
        "code": "provider.unavailable",
        "severity": "MOCK_FIELD",
        "safeMessage": "REDACTED_VALUE",
        "retryable": false,
        "fallbackRequired": true,
        "traceLabel": "TRACE_LABEL_PLACEHOLDER"
      }
    ],
    "fallback": "MOCK_FIELD"
  }
}
```

## 12. 接入前置条件

未来真正把 provider 接口契约转为代码前，必须先满足：

- Web-P44 文档通过复核。
- provider 凭证方案完成。
- provider 只读权限确认。
- feature flag 默认关闭。
- CI 禁用真实凭证。
- mock-only fallback 已测试。
- schema normalization 设计完成。
- validator 覆盖 candidate payload。
- adapter blocked fallback 已测试。
- 日志脱敏方案完成。
- 用户人工确认。
- 单独 PR。

未满足以上条件前，不得实现真实 provider，不得发起真实请求，不得读取凭证，不得把 candidate payload 接入页面入口、正式日报生成链路、通知链路、账户链路、数据库或交易相关能力。

## 13. 后续阶段建议

建议后续阶段：

- Web-P45：provider candidate payload mock-only fixture。
- Web-P46：provider candidate validator 测试。
- Web-P47：provider candidate schema normalization mock-only 草案。
- Web-P48：后续真实 provider 接入前复核文档。

Web-P44 不做这些事项。Web-P44 只完成 provider 只读接口契约文档，不新增 TypeScript 运行代码、不新增 provider client、不新增 API client、不新增真实请求，也不改变当前 mock-only 页面运行链路。

## 14. Web-P45 mock-only candidate fixture 说明

Web-P45 新增完全虚构、静态、脱敏的 `ProviderCandidatePayload` mock-only fixture，仅作为后续 validator 与 schema normalization 测试准备。

边界确认：

- 该 fixture 不是 `RealDailyReportDryRunInput`。
- 该 fixture 不是 `DailyReportViewModel`。
- 该 fixture 没有接入页面入口、preview model 或正式 runtime。
- 该 fixture 不接 provider，不读取任何外部来源。
- 后续若要进入日报 dry-run 链路，必须先经过 schema normalization；normalization 后才可能形成 `RealDailyReportDryRunInput`。
- `RealDailyReportDryRunInput` 仍必须经过 validator；validator passed 后才允许 adapter 映射。
- 任意失败、阻断、schema mismatch 或 validator 未通过时必须 fallback mock-only。
- 当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易。

## 15. Web-P46 provider candidate validator mock-only 说明

Web-P46 新增 `ProviderCandidatePayload` mock-only validator 纯函数，仅用于校验完全虚构、静态、脱敏的 candidate payload 是否仍满足 Web-P45 边界。

边界确认：

- validator 只校验完全虚构、脱敏的 candidate payload。
- validator `passed` 只代表允许进入后续 schema normalization 设计阶段，不代表已经完成 normalization。
- validator `blocked` 时 `normalizationAllowed=false`，并固定 fallback mock-only。
- validator 不实现 schema normalization。
- validator 不生成 `RealDailyReportDryRunInput`。
- validator 不生成 `DailyReportViewModel`。
- validator 不接入页面入口、preview model 或正式 runtime。
- 当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易。


## 16. Web-P47 provider candidate schema normalization mock-only 说明

Web-P47 新增 `ProviderCandidatePayload` → `RealDailyReportDryRunInput` mock-only normalizer 草案，仅用于完全虚构、静态、脱敏的 provider candidate schema normalization。

边界确认：

- normalizer 必须先调用 candidate validator，只有 `validateProviderCandidatePayload` passed 后才允许构造 dry-run 输入。
- normalization 后必须调用 dry-run validator，只有 `validateRealDailyReportDryRunInput` passed 后才返回 `normalizedInput`。
- 任意 validator blocked 时不返回 `normalizedInput`，并固定 fallback mock-only。
- normalizer 不调用 dry-run adapter。
- normalizer 不生成 `DailyReportViewModel`。
- normalizer 未接入页面入口、preview model 或正式 runtime。
- 当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易。

## Web-P47.1 mock-only 链路小总复核

Web-P47.1 已完成 P45～P47 mock-only 链路小总复核，固定链路顺序为：

```text
ProviderCandidatePayload
→ validateProviderCandidatePayload
→ normalizeProviderCandidatePayloadToDryRunInput
→ validateRealDailyReportDryRunInput
```

复核结论：

- candidate validator 必须先于 normalization 执行；candidate blocked 时不执行 normalization，也不构造 dry-run input。
- normalized input 必须再次经过 dry-run validator；dry-run validator blocked 时不返回 `normalizedInput`。
- 全链路固定 fallback mock-only，blocked 结果只返回低敏错误码，不返回 candidate payload 或原始敏感值。
- normalizer 不调用 dry-run adapter，不生成 `DailyReportViewModel`。
- 当前未接入页面、preview model 或正式 runtime。
- 当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易。

## 17. Web-P48 接入前安全复核交叉引用

Web-P48 已补充真实 provider 接入前安全复核，详见 [Web-P48 真实 provider 接入前安全复核](web_provider_pre_integration_safety_review.md)。
该复核确认 P45～P47.1 mock-only 链路、blocked 传播、fallback 与 runtime 隔离边界仍成立。
当前真实 provider 接入结论保持 NO-GO；下一步仅允许默认关闭的 Web-P49 provider dry-run feature flag，且仍不得连接真实 provider。

## 18. Web-P49 mock-only provider dry-run feature flag

Web-P49 新增默认关闭的 mock-only provider dry-run feature flag 和纯函数 evaluator，用于在未来阶段进入 candidate 链路前先判断是否允许 mock-only dry-run。

边界确认：

- flag 默认 `disabled`，显式启用也只允许 `enabled-mock-only`。
- flag 不读取环境变量、浏览器存储或 URL 参数，不加载凭证，不发起网络请求。
- flag 不授权真实 provider、真实账户读取、真实行情、通知发送、AI 调用或交易能力。
- flag 尚未接入 candidate validator、normalizer、dry-run validator、adapter、页面或正式 runtime。
- 真实 provider 接入结论继续保持 **NO-GO**。

## Web-M1B 交叉引用

Provider 只读接口在进入真实实现前，需先满足 [Web-M1B Provider Dry-Run 安全门禁闭环](web_provider_dry_run_gate_closure.md) 中定义的 mock-only gate、feature flag、candidate 链路、`normalizedInput` 成功态隔离和 runtime 隔离要求。当前真实 provider 仍为 **NO-GO**，不得绕过该门禁直接接入页面或 runtime。


## Core-M2 交叉引用

Core-M2 已新增首个真实只读 Provider 本地 Dry-Run 基础框架，详见 [Core-M2 首个真实只读 Provider 本地 Dry-Run 基础框架](web_provider_readonly_local_dry_run_framework.md)。该框架继续保持不联网、不读取凭证、不接页面或 runtime，真实 Provider 状态仍为 **NO-GO**。


## Core-M2.1 交叉引用

Core-M2.1 已在 [Core-M2 首个真实只读 Provider 本地 Dry-Run 基础框架](web_provider_readonly_local_dry_run_framework.md#core-m21-provider-result-脱敏与输入契约收口) 中补充 Provider Result runtime sanitizer、固定低敏错误映射和 Pipeline 顶层未知字段优先阻断；真实 Provider 仍为 **NO-GO**。


## Core-M3 AkShare 公开 A 股真实只读 Dry-Run

Core-M3 新增默认关闭的 AkShare 公开 A 股单标的真实只读 Dry-Run 链路。该链路仅允许本地人工批准后经 127.0.0.1 FastAPI endpoint 复用 Python data_provider/AkShare 日线入口，并通过后端与 Web 双重 sanitizer 生成 sourceType=real-readonly 的 RealDailyReportDryRunInput；Provider unavailable/timeout 可回退 mock-only，invalid-response/非法结构必须 blocked。当前不读取账户、不使用凭证、不调用 AI/通知/交易、不写数据库、不接正式页面或定时 runtime。详见 core_m3_akshare_public_market_readonly_dry_run.md。
