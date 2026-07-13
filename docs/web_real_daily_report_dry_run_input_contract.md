# Web-P39 真实日报 dry-run 输入契约设计

## 1. 阶段定位

Web-P39 是“股票基金质量分析系统”的真实日报 dry-run 输入契约设计阶段，仅用于定义未来 dry-run 输入结构和安全阻断边界。日报 / 推送显示名称固定为“AI股票基金每日信息报告”。

本阶段只做文档设计，明确未来候选输入如何被描述、标记、校验和阻断；不把任何真实输入接入当前 Web mock-only 页面链路。Web-P39 完成后，也不代表可以开始真实 provider 接入；真实 provider、账户、通知、AI、Agent、数据库或交易能力必须经过后续人工确认和单独 PR。

Web-P39 明确不做以下事项：

- 不读取真实账户。
- 不连接真实行情 provider。
- 不调用 AI / Agent。
- 不发送通知。
- 不执行交易。
- 不读取数据库。
- 不读取 `.env`、token、webhook、API key。
- 不生成真实日报。
- 不改变当前 mock-only 页面运行链路。
- 不读取支付宝、基金平台、券商平台或用户本地文件。
- 不写入本地配置、`localStorage` 或 `sessionStorage`。
- 不上传日志、发送日报或发送提醒。

## 2. dry-run 输入契约目标

真实日报 dry-run 输入契约用于未来在真实日报接入前做安全检查。它不是生产 schema，不代表 provider / API / AI / 通知 / 账户 / 数据库 / 交易已经可用。

契约目标包括：

- 接收候选日报 payload。
- 明确字段语义。
- 标明数据来源。
- 标明 dry-run 模式。
- 标明是否脱敏。
- 标明是否允许展示。
- 标明是否允许通知。
- 标明是否允许交易。
- 标明 schema 校验结果。
- 标明错误和回滚策略。

该契约的默认结果应是“先校验、再决定是否允许进入后续 mock-only 或 dry-run 处理”，而不是自动展示、自动通知或自动交易。

## 3. 建议契约结构

以下 `RealDailyReportDryRunInput` 只是文档级 schema 示例，不写入运行代码，不进入生产逻辑。

### 3.1 顶层字段

| 字段 | 建议类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `contractVersion` | string | 是 | dry-run 输入契约版本，缺失必须阻断。 |
| `mode` | string | 是 | 当前只能表达 `dry-run` 设计，不得启用 `production`。 |
| `dryRun` | boolean | 是 | 必须为 `true`。 |
| `projectName` | string | 是 | 必须等于“股票基金质量分析系统”。 |
| `reportDisplayName` | string | 是 | 必须等于“AI股票基金每日信息报告”。 |
| `source` | object | 是 | 候选输入来源说明。 |
| `report` | object | 是 | 候选日报展示字段。 |
| `safety` | object | 是 | 真实能力禁用开关和人工确认要求。 |
| `redaction` | object | 是 | 敏感字段与脱敏状态。 |
| `validation` | object | 是 | schema 校验状态、错误和警告。 |
| `rollback` | object | 是 | 回退策略。 |

### 3.2 `source`

| 字段 | 建议类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `sourceType` | string | 是 | 必须清晰标明 `mock-only` / `dry-run` / `real-readonly` 之一，不能含糊。 |
| `providerName` | string | 是 | dry-run 阶段只能使用低敏说明或占位名称，不得包含真实凭据、账户或 provider 原始响应。 |
| `isMock` | boolean | 是 | 标明是否为 mock 数据。 |
| `isRealReadOnly` | boolean | 是 | 仅表示候选只读语义，不代表真实 provider 已接入。 |
| `isRedacted` | boolean | 是 | 必须明确候选 payload 是否完成脱敏。 |
| `collectedAtLabel` | string | 是 | 使用低敏时间标签，不包含外部 URL、token、webhook 或 provider 原始响应。 |

### 3.3 `report`

| 字段 | 建议类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `reportId` | string | 是 | 使用不可追溯真实账户或资产的低敏 ID。 |
| `reportDateLabel` | string | 是 | 报告日期标签。 |
| `generatedAtLabel` | string | 是 | 生成时间标签。 |
| `title` | string | 是 | 必须等于“AI股票基金每日信息报告”。 |
| `headline` | string | 是 | 低敏摘要，不包含真实账户、精确资产或联系方式。 |
| `marketMood` | string | 是 | 可读市场情绪标签，格式必须可判断。 |
| `riskLevel` | string | 是 | 风险等级标签，格式必须可判断。 |
| `portfolioAction` | string | 是 | 仅允许观察类表达，不得包含自动交易或强制买卖表达。 |
| `sections` | array | 是 | section 顺序必须稳定可映射。 |

### 3.4 `safety`

| 字段 | 建议类型 | 必填 | 必须值 |
| --- | --- | --- | --- |
| `allowRealProvider` | boolean | 是 | `false` |
| `allowRealAccountRead` | boolean | 是 | `false` |
| `allowNotificationSend` | boolean | 是 | `false` |
| `allowTrading` | boolean | 是 | `false` |
| `allowAiCall` | boolean | 是 | `false` |
| `requiresHumanApproval` | boolean | 是 | `true` |

### 3.5 `redaction`

| 字段 | 建议类型 | 必填 | 必须值或规则 |
| --- | --- | --- | --- |
| `containsRealAccountData` | boolean | 是 | dry-run 设计阶段必须为 `false`。 |
| `containsSecrets` | boolean | 是 | 必须为 `false`。 |
| `containsWebhook` | boolean | 是 | 必须为 `false`。 |
| `containsToken` | boolean | 是 | 必须为 `false`。 |
| `containsApiKey` | boolean | 是 | 必须为 `false`。 |
| `containsPersonalContact` | boolean | 是 | 必须为 `false`。 |
| `redactionStatus` | string | 是 | 必须明确为已脱敏、无需脱敏或阻断状态，不能留空。 |

### 3.6 `validation`

| 字段 | 建议类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `schemaVersion` | string | 是 | 未来校验器版本。 |
| `status` | string | 是 | 建议为 `pending` / `passed` / `blocked`，错误态不得缺失。 |
| `errors` | array | 是 | 低敏错误类别列表，不记录敏感原文。 |
| `warnings` | array | 是 | 低敏警告列表，不记录敏感原文。 |

### 3.7 `rollback`

| 字段 | 建议类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `fallbackMode` | string | 是 | 默认回退到 `mock-only`。 |
| `fallbackReason` | string | 是 | 使用低敏原因，不包含敏感原文。 |
| `canFallbackToMockOnly` | boolean | 是 | 必须为 `true`。 |

## 4. dry-run 默认禁用开关

未来 dry-run 输入即使进入校验阶段，也必须默认禁用所有真实副作用：

- 不发送通知。
- 不交易。
- 不调用 AI。
- 不写账户。
- 不修改持仓。
- 不保存真实账户明细。
- 不上传日志。
- 不把 provider 原始响应直接给页面。
- 不把真实数据混入 mock-only fixture。
- 不把真实数据写入测试快照。
- 不读取 `.env`、token、webhook、API key。
- 不连接 OpenAI、DeepSeek、智谱、本地大模型或真实 Agent。

## 5. 字段安全规则

以下安全规则必须全部满足；任何一项不满足都必须阻断：

- `projectName` 必须等于“股票基金质量分析系统”。
- `reportDisplayName` 必须等于“AI股票基金每日信息报告”。
- `report.title` 必须等于“AI股票基金每日信息报告”。
- `source.sourceType` 必须标明 `mock-only` / `dry-run` / `real-readonly`，不能含糊。
- `dryRun` 必须为 `true`。
- `safety.allowTrading` 必须为 `false`。
- `safety.allowNotificationSend` 必须为 `false`。
- `safety.allowAiCall` 必须为 `false`。
- `redaction.containsSecrets` 必须为 `false`。
- `redaction.containsWebhook` 必须为 `false`。
- `redaction.containsToken` 必须为 `false`。
- `redaction.containsApiKey` 必须为 `false`。
- `redaction.containsPersonalContact` 必须为 `false`。
- `safety.requiresHumanApproval` 必须为 `true`。
- `rollback.canFallbackToMockOnly` 必须为 `true`。

## 6. 禁止字段和禁止内容

dry-run 输入契约、示例和文档不得包含以下内容。本节只定义规则，不重新明文列出任何已经移除的旧真实精确值。

- 真实账户明细。
- 真实持仓明细。
- 真实基金代码。
- 真实交易记录。
- 真实手机号。
- 真实邮箱。
- 真实 webhook。
- 真实 token。
- 真实 API key。
- `.env` 内容。
- provider 原始完整响应。
- 数据库导出内容。
- 真实历史日报原文。
- 可追溯到用户真实资产的精确金额、收益率和比例。
- 外部 URL 或可回溯到真实 provider 请求的完整路径。

## 7. schema 校验失败处理

遇到以下情况必须阻断：

- `contractVersion` 缺失。
- `mode` 非 `dry-run`。
- `dryRun` 非 `true`。
- 项目名称不匹配。
- 日报名称不匹配。
- `allowTrading` 为 `true`。
- `allowNotificationSend` 为 `true`。
- `allowAiCall` 为 `true`。
- `containsSecrets` 为 `true`。
- `containsWebhook` 为 `true`。
- `containsToken` 为 `true`。
- `containsApiKey` 为 `true`。
- `containsPersonalContact` 为 `true`。
- `source` 未标明来源类型。
- `sections` 顺序无法稳定映射。
- 金额 / 收益率 / 风险等级格式无法判断。
- 错误态缺失。
- 无法 fallback 到 mock-only。

阻断后必须执行以下策略：

- 回退 mock-only。
- 记录低敏错误类别。
- 不展示半真半假的混合日报。
- 不发送通知。
- 不交易。
- 不上传敏感日志。
- 不把敏感原文写入测试快照、fixture、日志或 PR 描述。

## 8. 示例 JSON

以下示例只用于说明字段形状，明显是 dry-run，不包含真实金额、真实基金代码、真实联系方式、webhook、token、API key、外部 URL、provider 原始响应或真实历史日报原文。

```json
{
  "contractVersion": "web-p39-draft-1",
  "mode": "dry-run",
  "dryRun": true,
  "projectName": "股票基金质量分析系统",
  "reportDisplayName": "AI股票基金每日信息报告",
  "source": {
    "sourceType": "dry-run",
    "providerName": "REDACTED_PROVIDER_LABEL",
    "isMock": false,
    "isRealReadOnly": false,
    "isRedacted": true,
    "collectedAtLabel": "DRY_RUN_TIME_LABEL"
  },
  "report": {
    "reportId": "DRY_RUN_REPORT_ID",
    "reportDateLabel": "DRY_RUN_DATE_LABEL",
    "generatedAtLabel": "DRY_RUN_GENERATED_LABEL",
    "title": "AI股票基金每日信息报告",
    "headline": "DRY_RUN_HEADLINE_REDACTED",
    "marketMood": "REDACTED_VALUE",
    "riskLevel": "REDACTED_VALUE",
    "portfolioAction": "仅观察，不交易",
    "sections": [
      {
        "sectionId": "market-overview",
        "title": "市场概览",
        "summary": "REDACTED_VALUE",
        "amountLabel": "MOCK_AMOUNT",
        "ratioLabel": "MOCK_RATIO"
      }
    ]
  },
  "safety": {
    "allowRealProvider": false,
    "allowRealAccountRead": false,
    "allowNotificationSend": false,
    "allowTrading": false,
    "allowAiCall": false,
    "requiresHumanApproval": true
  },
  "redaction": {
    "containsRealAccountData": false,
    "containsSecrets": false,
    "containsWebhook": false,
    "containsToken": false,
    "containsApiKey": false,
    "containsPersonalContact": false,
    "redactionStatus": "redacted"
  },
  "validation": {
    "schemaVersion": "web-p39-validation-draft-1",
    "status": "pending",
    "errors": [],
    "warnings": []
  },
  "rollback": {
    "fallbackMode": "mock-only",
    "fallbackReason": "dry-run validation fallback is always available",
    "canFallbackToMockOnly": true
  }
}
```

## 9. 与当前 mock-only 链路关系

当前真实代码仍保持以下 mock-only 链路：

```text
mock fixture → adapter → DailyReportViewModel → guard → preview model/tests
```

Web-P39 只设计未来 dry-run 输入契约，不改变这条链路，不新增真实运行能力，不修改 provider、通知、交易、账户读取、AI / model 配置、Agent 真实运行代码、正式日报生成代码或 mock-only 页面代码。

未来如果要让 dry-run 输入进入代码，需要单独阶段和单独 PR，例如：

- Web-P40：dry-run schema 类型草案，但仍不接 provider。
- Web-P41：dry-run validator mock-only 测试。
- Web-P42：dry-run adapter 草案。
- Web-P43：人工确认后的 provider 只读设计。

Web-P39 不做上述实现工作。

## 10. 后续阶段建议

后续阶段建议继续保持小步、可回滚、mock-only 优先：

- Web-P40：dry-run schema 类型草案，但仍不接 provider。
- Web-P41：dry-run validator mock-only 测试。
- Web-P42：dry-run adapter 草案。
- Web-P43：provider 只读设计文档。

每一步都必须保持：

- 默认禁用真实接入。
- 不读 `.env`。
- 不读 token / webhook / API key。
- 不发送通知。
- 不交易。
- 不调用真实 AI。
- 不读取真实账户、数据库、支付宝、基金平台或券商平台。
- 不上传日志。
- 不把真实数据写入 mock-only fixture 或测试快照。
- 真实接入前必须先经过人工确认和单独 PR。

## 11. Web-P40 TypeScript 类型草案

Web-P40 在 Web mock-only preview 范围内新增 `apps/dsa-web/src/mocks/preview/dry-run/realDailyReportDryRunTypes.ts`，把 Web-P39 的 `RealDailyReportDryRunInput` 文档设计转换为 TypeScript 类型草案。该文件只提供静态契约类型，不包含 validator、adapter、parser、guard、fixture、示例 payload 运行代码或任何真实 provider / API / AI / Agent / 通知 / 账户 / 数据库 / 交易接入。

Web-P40 类型草案的边界如下：

- `mode` 固定为 `dry-run`，`dryRun` 固定为 `true`。
- `projectName` 固定为“股票基金质量分析系统”。
- `reportDisplayName` 与 `report.title` 固定为“AI股票基金每日信息报告”。
- `safety` 里的真实 provider、真实账户读取、通知发送、交易和 AI 调用开关全部以字面量类型锁定为禁用，并要求 `requiresHumanApproval: true`。
- `redaction` 里的 secret、webhook、token、API key 和个人联系方式标记全部以字面量类型锁定为 `false`。
- `rollback.fallbackMode` 固定为 `mock-only`，`canFallbackToMockOnly` 固定为 `true`。
- `source.sourceType` 只允许 `mock-only` / `dry-run` / `real-readonly`。
- `validation.status` 只允许 `pending` / `passed` / `blocked`。
- 所有字段使用只读结构和只读数组表达，避免把未来 dry-run 输入误设计成可变运行对象。

这些类型不代表 schema validator 已实现，不代表 dry-run 可以接真实 provider，也不代表当前 mock-only 页面链路发生变化。真实接入仍需要后续 Web-P41 / Web-P42 / Web-P43 分阶段完成，并继续经过人工确认和单独 PR。当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易。

Web-P40 同时把新增类型文件纳入 `apps/dsa-web/tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts` 的 mock-only boundary 静态扫描范围，用于确认该类型草案不包含网络、存储、通知、provider、AI、环境变量读取、真实请求目标或被正式 runtime 入口导入的风险。

## 12. Web-P39 / Web-P40 Judge 结论

- Web-P39 是 dry-run design only；Web-P40 只新增 TypeScript 类型草案。
- 本阶段仍保持 mock-only。
- 本阶段不启动后端、不自动打开浏览器、不接真实 API / provider / OpenAI / DeepSeek / 智谱 / 本地大模型 / Agent / 通知 / 账户 / 数据库 / 交易。
- 本阶段不读取 `.env`、token、webhook、API key、真实历史日报文件或用户本地文件。
- Web-P40 类型草案不代表 validator、adapter 或真实 provider 接入已经实现，不新增真实运行能力。
## 13. Web-P41 mock-only validator 草案

Web-P41 在 Web mock-only preview 范围内新增 `apps/dsa-web/src/mocks/preview/dry-run/realDailyReportDryRunValidator.ts`，用于把 Web-P40 的 `RealDailyReportDryRunInput` 类型草案补充为纯函数 validator 草案。该 validator 只做静态输入校验，不接真实 provider，不读取真实账户，不读取数据库，不调用 AI / Agent，不发送通知，不交易，也不改变当前 mock-only 页面渲染链路。

Web-P41 validator 的默认结果仍固定为 mock-only 回退边界：

- 校验通过时返回 `passed`，并保留 `fallbackMode: mock-only` 与 `canFallbackToMockOnly: true`。
- 校验失败时返回 `blocked`，不抛真实运行异常，不触发任何真实能力，并且必须 fallback mock-only。
- validator 不读取 `.env`，不读取 token / webhook / API key，不从浏览器存储、文件或外部服务加载数据。
- validator 不使用网络、通知、交易、AI、provider、账户或数据库能力；Web-P41 不代表真实日报接入已经开始。

Web-P41 同时新增 `apps/dsa-web/tests/mocks/preview/realDailyReportDryRunValidator.test.ts`，使用明显虚构的静态测试 payload 覆盖 dry-run 模式、安全禁用开关、脱敏标记、mock-only 回退、sections 非空、可疑外部地址与可疑密钥/联系方式文案阻断。新增 validator 文件也被纳入 `apps/dsa-web/tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts` 的静态扫描范围，继续确认 mock-only preview 范围不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易。
