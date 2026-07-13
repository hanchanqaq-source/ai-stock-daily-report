# Core-M2 首个真实只读 Provider 本地 Dry-Run 基础框架

> Core-M3.1 交叉引用：Core-M3.1 在 Core-M2 框架之后增加 AkShare 单源真实只读 Dry-Run，仍默认关闭、仅 localhost 人工批准、不可读取账户/通知/AI/交易/数据库，并通过前后端固定超时回退 mock-only。

Core-M2 属于“股票基金质量分析系统”的本地 dry-run 基础设施里程碑，日报显示名称固定为“AI股票基金每日信息报告”。本阶段只搭建未来真实只读 Provider 接入前的类型、Port、凭证状态边界、默认禁用 Provider 和 Provider → candidate → gate 的本地管线；真实 Provider 继续 **NO-GO**。

## Provider Port 接口

`ProviderReadonlyPort` 是未来真实只读 Provider 的唯一接口形状，但当前仅用于本地 dry-run。接口固定声明：

- `mode: local-dry-run`
- `providerLabel: REDACTED_PROVIDER_LABEL`
- `networkEnabled: false`
- `credentialReadEnabled: false`
- `accountReadEnabled: false`
- `readCandidate(request)` 返回统一的 `ProviderReadonlyPortResult`

接口不包含 endpoint、baseUrl、headers、Authorization、token、API key、cookie 或 secret，也不引入 HTTP 客户端或 Provider SDK。

## 默认禁用 Provider

`createDisabledProviderReadonlyPort()` 返回冻结对象，所有真实能力均关闭。`readCandidate()` 固定返回 `unavailable`，错误码为 `provider-readonly.unavailable`，允许后续管线降级到固定 mock-only fixture。该实现不读取请求内容、不联网、不读取环境变量或浏览器存储、不使用时间与随机数、不抛异常，也不返回真实 Provider 名称或 candidate。

## Credential Boundary

`inspectProviderCredentialBoundary()` 只描述凭证状态，不读取任何凭证内容。当前固定返回：

- `status: not-configured`
- `hasCredential: false`
- `secretMaterialAccessible: false`
- `environmentReadAllowed: false`
- `storageReadAllowed: false`
- 空 `errors` 与 `warnings`

真实凭证加载、密钥读取、GitHub Secrets、`.env`、浏览器存储或系统凭据管理器访问都不属于 Core-M2，必须留到未来单独里程碑并重新获得人工批准。

## Pipeline 流程

`runProviderReadonlyDryRunPipeline(input)` 只接受 `featureFlag`、`request`、`provider` 三个顶层字段，未知字段会 blocked，并只返回低敏字段路径。

执行顺序：

1. 先校验 input 类型。
2. 使用 `Object.keys(input)` 检查顶层字段白名单，只允许 `featureFlag`、`request`、`provider`；未知字段或敏感未知字段立即 `blocked`，错误只包含字段路径。
3. 再调用 `evaluateProviderDryRunFeatureFlag(input.featureFlag)`。
4. flag disabled 时立即返回 `disabled`，不读取 request getter、provider getter、candidate 或凭证边界。
5. flag blocked 时立即返回 `blocked`，不读取 request getter、provider getter，也不调用 Provider。
6. flag enabled-mock-only 后才验证 request；缺失 request 使用冻结的 `DEFAULT_PROVIDER_READONLY_REQUEST`。
7. request 必须保持 dry-run、readOnly、固定项目名、固定日报名、全部真实能力关闭、需要人工批准；未知字段或敏感字段 blocked。
8. 调用 Credential Boundary，仅确认当前 `not-configured` 状态。
9. 调用 Provider Port；默认 Provider 是禁用 Provider。
10. Provider 原始结果必须先经过 `sanitizeProviderReadonlyPortResult()` 运行时 sanitizer。
11. Provider candidate 成功时进入既有 `runProviderDryRunGate`，继续执行 candidate validator、normalizer 和 dry-run validator。
12. Provider transport 类失败允许使用固定 mock-only fixture fallback。

## Provider outcome 状态

Provider Port 结果支持：

- `candidate`
- `unavailable`
- `timeout`
- `credential-unavailable`
- `invalid-response`
- `blocked`

Pipeline 额外使用 `invalid-provider-result`、`not-attempted` 和 `unexpected` 描述非法 Provider Result、未调用 Provider 或 Provider 抛异常。

## fallback 与阻断规则

`unavailable`、`timeout`、`credential-unavailable` 视为 transport / 可用性类失败，可降级为 `MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE`，再进入现有 gate。成功后 Pipeline 返回 `completed-mock-only`，`fallbackUsed: true`，并包含低敏 warning：

- `provider-readonly.fallback-after-unavailable`
- `provider-readonly.fallback-after-timeout`
- `provider-readonly.fallback-after-credential-unavailable`

`invalid-response`、`blocked` 与 `invalid-provider-result` 不会伪装成成功，不会自动返回 `normalizedInput`。Provider 抛异常时返回低敏 `provider-readonly-pipeline.failed`，不回显 Error message、stack、Provider 名称、请求内容或路径。

## normalizedInput 存在条件

只有 `completed-mock-only` 可以包含 `normalizedInput`。`disabled` 与 `blocked` 结果不得包含 `normalizedInput`、candidate、raw response、请求 URL、headers、cookies、凭证、token、webhook、apiKey 或 accountId。

## Web-M1B 语义修复

Core-M2 同步修复 Web-M1B 两项非阻塞语义：

1. enabled 状态下 `candidate` 为 `undefined` 或 `null` 时，gate 返回 `provider-dry-run-gate.candidate-required`，不调用 normalizer。
2. normalizer 已开始后发生异常时，gate 返回 `candidateChainExecuted: true`、`featureFlagState: enabled-mock-only`、`blockedStage: unexpected`，并保持低敏错误码。

## Runtime 隔离

Core-M2 框架只位于 mock-only preview provider 目录，未接入页面、preview model、`mockOnlyPreviewEntry.ts`、React runtime、API、stores、contexts、utils、Windows 脚本、后端、通知、AI、账户、数据库或交易链路。

## Core-M3 前置人工批准

Core-M3 如要推进首个真实只读数据源端到端接入，必须再次获得用户人工批准，并重新评估真实网络、Provider SDK、凭证读取、日志脱敏、只读权限、回滚方案和端到端验证。Core-M2 的真实 Provider 最终结论仍为 **NO-GO**。


## Core-M3 AkShare 公开 A 股真实只读 Dry-Run

Core-M3 新增默认关闭的 AkShare 公开 A 股单标的真实只读 Dry-Run 链路。该链路仅允许本地人工批准后经 127.0.0.1 FastAPI endpoint 复用 Python data_provider/AkShare 日线入口，并通过后端与 Web 双重 sanitizer 生成 sourceType=real-readonly 的 RealDailyReportDryRunInput；Provider unavailable/timeout 可回退 mock-only，invalid-response/非法结构必须 blocked。当前不读取账户、不使用凭证、不调用 AI/通知/交易、不写数据库、不接正式页面或定时 runtime。详见 core_m3_akshare_public_market_readonly_dry_run.md。
