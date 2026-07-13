# Web-P32 mock 报告 schema 说明

## 1. 阶段定位

Web-P32 是“股票基金质量分析系统”的 mock 报告 schema 文档阶段，只描述 Web-P31 已统一的 mock-only 日报 fixture 结构与页面字段契约。Web-P34 在此基础上新增前端兼容映射层，将 mock 原始结构转换为页面稳定消费的展示模型。Web-P35 继续新增轻量展示模型契约守卫，用于测试当前 `DailyReportViewModel` 是否保持 mock-only 标识、脱敏标签、section 顺序和敏感边界；该守卫只验证静态展示契约，不代表真实 provider 接入、真实日报 schema 定稿或真实数据来源授权。当前日报 / 推送显示名称固定为“AI股票基金每日信息报告”。

本阶段明确不做以下事项：

- 不生成真实日报。
- 不读取真实持仓、真实账户、支付宝、基金平台或券商平台数据。
- 不连接真实行情 provider。
- 不调用 OpenAI、DeepSeek、智谱、本地大模型或任何 AI / Agent 真实运行链路。
- 不发送日报、提醒或任何通知。
- 不执行交易。
- 不读取 `.env`、token、webhook、API 凭据或任何密钥配置。
- 不读取数据库、本地真实日报文件或用户本地文件。
- 不写入本地配置、localStorage、sessionStorage、indexedDB，也不上传日志。

Web-P32 的边界仍然是 mock-only、127.0.0.1 only、只使用静态脱敏 fixture；本文档不是未来真实日报接入授权，也不是 provider、AI、通知、账户、数据库或交易接入方案。

## 2. Schema 来源

当前 mock 报告 schema 参考以下前端 mock-only 文件和类型：

- `apps/dsa-web/src/mocks/preview/fixtures/dailyReportFixture.ts`
- `apps/dsa-web/src/mocks/preview/fixtures/index.ts`（fixture 目录统一导出入口，mock-only 页面模型应从该入口导入 fixture）
- `apps/dsa-web/src/mocks/preview/adapters/dailyReportAdapter.ts`（Web-P34 兼容映射层，将 fixture 转换为展示模型）
- `apps/dsa-web/src/mocks/preview/adapters/index.ts`（adapter 目录统一导出入口）
- `apps/dsa-web/src/mocks/preview/guards/dailyReportViewModelGuard.ts`（Web-P35 展示模型契约守卫，只用于 mock-only 测试）
- `apps/dsa-web/src/mocks/preview/guards/index.ts`（guard 目录统一导出入口）
- `apps/dsa-web/src/mocks/preview/mockOnlyPreviewTypes.ts`
- `MockOnlyDailyReportFixture`
- `MockOnlyDailyReportSectionFixture`
- `DailyReportViewSection`
- `DailyReportViewModel`

Web-P31 已经建立统一 fixture，用于集中定义“AI股票基金每日信息报告”的 mock-only 字段、脱敏标签和安全边界。Web-P33 增加 `fixtures/index.ts` 作为目录统一导出入口，后续 mock-only 页面模型应通过该入口复用 fixture；类型仍集中在 `mockOnlyPreviewTypes.ts`。Web-P34 新增 `adaptMockOnlyDailyReportFixture` 作为同步纯函数 adapter，负责把 `MockOnlyDailyReportFixture` 映射为 `DailyReportViewModel`，让仪表盘、历史报告和详情预览优先消费稳定展示契约。Web-P35 新增 `validateMockOnlyDailyReportViewModel` 作为同步纯函数 guard，在测试中检查展示模型是否保留固定项目名、报告名、mock-only 模式、`REDACTED FIXTURE DATA`、四个固定 section 顺序、安全标签、旧真实精确值禁用和敏感文本禁用。Web-P34 / Web-P35 均不修改真实运行链路，不设计或接入真实 provider。

## 3. 顶层字段说明

`MockOnlyDailyReportFixture` 是当前 mock-only 日报预览的顶层结构。除非后续单独小步变更并完成复核，以下字段均只允许来自静态脱敏 fixture，不得由真实 API、provider、AI、通知、账户、数据库或本地真实日报文件填充。

| 字段名 | 类型 | 是否必填 | 当前 mock 示例 | 用途 | 脱敏/安全要求 |
| --- | --- | --- | --- | --- | --- |
| `reportId` | `string` | 是 | `mock-daily-report-2026-07-12-local-preview` | 标识当前 mock 报告，供历史报告列表与详情关联。 | 必须体现 mock / local preview 语义；不得包含真实用户、账户、数据库主键或真实报告文件路径。 |
| `projectName` | `string` | 是 | `股票基金质量分析系统` | 标识项目名称。 | 固定为“股票基金质量分析系统”；不得写入账户名、平台名或用户身份信息。 |
| `reportDateLabel` | `string` | 是 | `2026-07-12 本地静态预览` | 展示报告日期标签。 | 日期必须标注本地静态预览；不得暗示真实生成、真实交易日或真实历史日报。 |
| `title` | `string` | 是 | `AI股票基金每日信息报告` | 页面标题与历史报告标题。 | 固定为“AI股票基金每日信息报告”；不得包含真实账户、真实通知目标或真实收益信息。 |
| `displayName` | `string` | 是 | `AI股票基金每日信息报告` | 详情页显示名称。 | 固定为“AI股票基金每日信息报告”；与 `title` 保持一致。 |
| `modeLabel` | `string` | 是 | `mock-only 本地预览` | 告知用户当前运行模式。 | 必须表示 mock-only 本地预览；不得描述为真实日报、正式推送或线上数据。 |
| `dataSourceLabel` | `string` | 是 | `REDACTED FIXTURE DATA - 静态脱敏 fixture` | 展示数据来源边界。 | 必须包含 `REDACTED FIXTURE DATA`；必须说明静态脱敏 fixture；不得出现真实 provider、真实接口或真实文件来源。 |
| `generatedAtLabel` | `string` | 是 | `2026-07-12 08:30 本地静态预览` | 展示 mock 报告生成时间标签。 | 必须标注本地静态预览；不得表示真实调度、真实发送或真实日报生成时间。 |
| `deliveryStatus` | `string` | 是 | `未发送` | 展示日报 / 推送发送状态。 | 当前固定为未发送；不得包含真实通知渠道、webhook、手机号、邮箱或 IM 目标。 |
| `marketMood` | `string` | 是 | `震荡观察` | 仪表盘和历史报告展示的市场情绪摘要。 | 只能使用静态脱敏文案；不得读取真实行情、真实指数、真实新闻或真实 AI 总结。 |
| `headline` | `string` | 是 | `科技方向保持震荡，模拟组合以观察为主，暂不进行主动调仓。` | 仪表盘摘要与详情页头条。 | 必须保持模拟、观察、非投资建议语义；不得包含真实交易建议、真实持仓或收益承诺。 |
| `portfolioAction` | `string` | 是 | `不调仓` | 历史报告列表展示的组合动作摘要。 | 只能作为 mock 展示；不得触发交易、自动下单或真实调仓流程。 |
| `riskLevel` | `string` | 是 | `中等` | 仪表盘和历史报告展示风险等级。 | 仅为 mock 风险标签；不得作为真实风险评估或投资建议。 |
| `sections` | `MockOnlyDailyReportFixture['sections']` | 是 | 见“sections 字段说明” | 承载日报正文分区。 | 只允许静态脱敏文案；不得读取真实行情、真实持仓、真实 AI 总结或真实报告内容。 |
| `safetyLabels` | `readonly string[]` | 是 | `模拟数据`、`非真实账户`、`127.0.0.1 only` | 页面安全边界展示与测试保护。 | 必须覆盖 mock-only、非真实账户、非投资建议、不会通知、不会交易、不会调用模型等语义。 |
| `redactionLabels` | `readonly string[]` | 是 | `REDACTED FIXTURE DATA`、`不读取数据库`、`不读取 .env` | 展示脱敏与不读取敏感来源的声明。 | 必须覆盖不读取 `.env`、token、webhook、API 凭据、数据库、真实历史日报文件等语义。 |
| `mockOnlyNotes` | `readonly string[]` | 是 | `当前仍不得接真实 API、provider、AI、通知、账户、数据库或交易。` | 记录 fixture 用途、日期性质、虚构数据和阶段边界。 | 必须继续声明 mock-only；不得写入真实金额、真实收益、真实账户或真实通知目标。 |

## 4. `sections` 字段说明

`sections` 当前包含四个固定分区：

| Section key | 类型 | 是否必填 | 当前标题示例 | 用途 | 安全要求 |
| --- | --- | --- | --- | --- | --- |
| `marketOverview` | `MockOnlyDailyReportSectionFixture` | 是 | `市场概览` | 展示 mock 市场概览。 | 只允许静态脱敏文案，不能读取真实行情、provider、新闻、AI 总结或真实报告内容。 |
| `portfolioObservation` | `MockOnlyDailyReportSectionFixture` | 是 | `组合观察` | 展示 mock 组合观察。 | 只允许虚构组合描述，不能读取真实持仓、真实账户、真实收益或真实目标仓位。 |
| `riskWarnings` | `MockOnlyDailyReportSectionFixture` | 是 | `风险提示` | 展示 mock 风险提示。 | 必须保持模拟数据、非真实账户、非投资建议语义。 |
| `actionSuggestions` | `MockOnlyDailyReportSectionFixture` | 是 | `动作建议` | 展示 mock 动作建议。 | 不得触发通知、交易或模型调用；不得表达强制买入、卖出或自动执行。 |

每个 `MockOnlyDailyReportSectionFixture` 包含：

| 字段名 | 类型 | 是否必填 | 用途 | 脱敏/安全要求 |
| --- | --- | --- | --- | --- |
| `title` | `string` | 是 | 分区标题。 | 不得包含真实账户、真实通知目标或真实 provider 名称。 |
| `content` | `string` | 是 | 分区正文。 | 只能来自静态脱敏 fixture；不得读取真实行情、真实持仓、真实 AI 总结或真实日报原文。 |

## 5. `safetyLabels` / `redactionLabels` / `mockOnlyNotes` 说明

这些字段用于页面安全边界展示和测试保护，帮助确认 Web-P32 仍处于 mock-only 阶段，而不是正式日报、真实分析或真实推送能力。

字段语义必须包含或覆盖：

- 模拟数据。
- `REDACTED FIXTURE DATA`。
- 静态脱敏 fixture。
- 非真实账户。
- 非投资建议。
- 不会发送通知。
- 不会交易。
- 不会调用模型。
- 不读取 `.env`。
- 不读取 token。
- 不读取 webhook。
- 不读取 API 凭据。
- 不读取数据库。
- 不读取真实历史日报文件。

如果后续新增页面模块继续消费这些标签，必须保持上述语义，不得因为 UI 展示需要而弱化安全边界文案。

## 6. 字段映射说明

当前 unified daily report fixture 主要被以下 mock-only 页面模块消费：

### 仪表盘摘要

仪表盘摘要消费：

- `headline`
- `marketMood`
- `riskLevel`
- `safetyLabels` / `redactionLabels`

用途是展示“AI股票基金每日信息报告”的 mock 摘要、安全标签与风险等级。该模块不得从真实 API、provider、AI、账户或历史日报文件补数据。

### 历史报告预览

历史报告预览消费：

- `reportId`
- `reportDateLabel`
- `title`
- `generatedAtLabel`
- `deliveryStatus`
- `marketMood`
- `portfolioAction`
- `riskLevel`
- `sections`

用途是展示 mock 报告列表、预览摘要与报告正文分区。`deliveryStatus` 当前固定为未发送，不能映射到真实通知状态。

### 历史报告详情

历史报告详情消费：

- `title`
- `displayName`
- `generatedAtLabel`
- `headline`
- `sections`
- `safetyLabels`
- `redactionLabels`

用途是展示 mock 报告详情和安全边界。详情页不得读取真实历史日报原文、数据库内容或本地文件。

### 仍保留模块级 mock 文案的区域

提醒预览、Agent 对话预览、空状态与错误示例中仍有部分模块级 mock 文案。这些文案当前仍是静态 mock-only，不代表真实提醒、真实 Agent、真实 AI、真实错误上报或真实恢复能力。

后续如需把这些文案统一到 report schema，必须单独小步处理，并继续保持 mock-only；不得顺手接真实服务、真实 provider、真实 AI、通知、账户、数据库或交易。


## 6.1 Web-P34 兼容映射层与展示模型

Web-P34 将日报 mock-only 数据拆成三层语义：

1. `MockOnlyDailyReportFixture`：mock 原始结构，只能来自静态脱敏 fixture。它保留 `reportId`、`sections` 对象、`mockOnlyNotes` 等现有字段与兼容别名，不代表真实 provider 返回结构。
2. `adaptMockOnlyDailyReportFixture`：前端兼容映射层，是同步纯函数。它不修改输入对象，不读取配置、密钥、数据库、本地真实日报或任何运行时真实数据，也不调用网络、AI、Agent、provider、通知或交易能力。
3. `DailyReportViewModel`：页面展示契约，页面预览应依赖该稳定模型消费日报字段。它将 `reportId` 映射为 `id`，将 `mockOnlyNotes` 映射为 `notes`，并将 `sections` 固定顺序转换为只读数组：`marketOverview`、`portfolioObservation`、`riskWarnings`、`actionSuggestions`。

`DailyReportViewModel` 当前字段包括：`id`、`projectName`、`reportDateLabel`、`title`、`displayName`、`modeLabel`、`dataSourceLabel`、`generatedAtLabel`、`deliveryStatus`、`marketMood`、`headline`、`portfolioAction`、`riskLevel`、`sections`、`safetyLabels`、`redactionLabels`、`notes`。

本阶段的 adapter 只是 mock-only 前端展示兼容层，不定义未经确认的真实 provider 返回结构，不提供真实数据切换，不代表真实 API、provider、AI、通知、账户、数据库或交易已经设计或接入。

## 6.2 Web-P35 展示模型契约守卫

Web-P35 新增 `validateMockOnlyDailyReportViewModel(viewModel)`，用于 mock-only preview 测试阶段守住页面展示模型边界。该函数是同步纯函数，只接收已经构造好的 `DailyReportViewModel`，只返回 violation 文案数组；它不发起网络请求，不读取文件，不读取环境变量，不连接真实 API、provider、AI、通知、账户、数据库或交易链路。

当前 guard 覆盖以下边界：

- `projectName` 固定为“股票基金质量分析系统”。
- `title` / `displayName` 固定为“AI股票基金每日信息报告”。
- `dataSourceLabel` 必须包含 `REDACTED FIXTURE DATA`。
- `modeLabel` 必须表达 mock-only 或本地预览语义。
- `sections` 必须保持四个固定分区，并按“市场概览 / 组合观察 / 风险提示 / 动作建议”排序。
- `safetyLabels`、`redactionLabels`、`notes` 的合并文本必须保留 mock-only、脱敏 fixture、非真实账户、非投资建议、不会发送通知和不会交易等安全边界。
- 展示模型全文不得出现旧真实精确值或密钥相关敏感文本。

该 guard 是 mock-only 展示模型契约守卫，不是未来真实日报 provider 返回结构，不代表真实 provider、AI、通知、账户、数据库或交易已经设计、授权或接入。

## 7. 脱敏规则

mock 报告 schema 和 fixture 不得包含：

- 用户真实持仓金额。
- 用户真实目标仓位。
- 用户真实收益率。
- 真实基金代码。
- 真实交易记录。
- 真实账户明细。
- 真实通知目标。
- 真实手机号。
- 真实邮箱。
- 真实 webhook。
- 真实 token。
- 真实 API 凭据。
- `.env` 内容。
- 真实历史日报原文。
- 数据库内容。

特别禁止出现以下旧精确值：

- `¥59,167.78`
- `¥180,000.00`
- `32.9%`
- `¥14,879.70`
- `+18.33%`
- `¥6,877.54`
- `-0.46%`
- `¥2,115.71`
- `-4.01%`
- `¥2,292.78`
- `-1.61%`

如需展示金额、比例或收益率，只能使用明显虚构、不可追溯到真实账户的示例，并在页面或字段中标注模拟数据、静态脱敏 fixture 或本地静态预览。

## 8. 未来真实日报接入前置条件

未来如果要从 mock schema 走向真实日报，必须先完成：

- Schema 高规格复核，包括字段含义、必填性、兼容性、默认值、错误态和脱敏策略。
- Provider 边界设计，包括数据源授权、请求范围、降级路径、超时、重试和缓存策略。
- `.env` / token / webhook 管理方案，包括读取时机、最小权限、日志脱敏和本地 / CI / 部署差异。
- 通知发送 dry-run 方案，先证明不会误发、不会泄露真实目标、失败不会拖垮主流程。
- 真实账户数据读取授权边界，明确用户确认、平台限制、字段最小化和不可写入交易动作。
- 错误日志脱敏方案，确保异常、调试输出、CI 日志和前端展示不泄露账户、密钥或原始日报。
- 用户确认后才能进入真实 provider 或通知阶段。

当前 Web-P32 不做上述工作，也不提供任何默认真实接入路径。

## 9. 示例 JSON

以下示例仅用于说明字段形状，内容必须视为明显虚构的 mock-only 数据：

```json
{
  "reportId": "mock-daily-report-demo-local-preview",
  "projectName": "股票基金质量分析系统",
  "reportDateLabel": "2026-07-12 本地静态预览",
  "title": "AI股票基金每日信息报告",
  "displayName": "AI股票基金每日信息报告",
  "modeLabel": "mock-only 本地预览",
  "dataSourceLabel": "REDACTED FIXTURE DATA - 静态脱敏 fixture",
  "generatedAtLabel": "2026-07-12 08:30 本地静态预览",
  "deliveryStatus": "未发送",
  "marketMood": "模拟观察",
  "headline": "模拟组合保持观察，仅用于本地页面预览。",
  "portfolioAction": "不调仓",
  "riskLevel": "中等",
  "sections": {
    "marketOverview": {
      "title": "市场概览",
      "content": "静态脱敏 fixture 示例，不接真实行情或 provider。"
    },
    "portfolioObservation": {
      "title": "组合观察",
      "content": "示例组合为虚构内容，不读取真实账户。"
    },
    "riskWarnings": {
      "title": "风险提示",
      "content": "模拟数据，非真实账户，非投资建议。"
    },
    "actionSuggestions": {
      "title": "动作建议",
      "content": "不会发送通知、不会交易、不会调用模型。"
    }
  },
  "safetyLabels": ["模拟数据", "非真实账户", "非投资建议", "不会发送通知", "不会交易"],
  "redactionLabels": ["REDACTED FIXTURE DATA", "不读取 .env", "不读取 token", "不读取 webhook", "不读取 API 凭据", "不读取数据库"],
  "mockOnlyNotes": ["当前仍保持 mock-only，不接真实 API、provider、AI、通知、账户、数据库或交易。"]
}
```

该示例不包含真实基金代码、真实金额、真实通知目标、token、webhook、API 凭据或外部 URL。

## 10. 与后续阶段的关系

- Web-P33 已完成 fixture 目录统一导出入口，继续保持静态脱敏 fixture 的文件边界、命名、复用与测试保护。
- Web-P34 已建立前端 mock 原始结构到 `DailyReportViewModel` 的兼容层，重点是字段语义、固定 sections 顺序、脱敏标签与页面展示契约稳定性。
- Web-P34 不代表真实 provider 已设计或接入；后续真实日报接入必须另行完成 schema 高规格复核、provider 边界、凭证管理、通知 dry-run、账户授权和日志脱敏设计。
- 后续阶段仍然不得接真实 API、provider、AI、通知、账户、数据库或交易，除非任务明确改变阶段边界并完成高规格复核与用户确认。
