# Web-P31 mock-only 日报 fixture 结构

## 目标

Web-P31 将“AI股票基金每日信息报告”的前端 mock-only 日报数据收敛为统一 fixture，服务“股票基金质量分析系统”的本地静态预览页面。该阶段只准备数据结构，不接入真实 API、provider、AI、通知、账户、数据库或交易能力。

## 统一结构

统一 fixture 位于 `apps/dsa-web/src/mocks/preview/fixtures/dailyReportFixture.ts`，类型定义位于 `apps/dsa-web/src/mocks/preview/mockOnlyPreviewTypes.ts`。核心字段包括：

- `reportId`：本地静态预览日报标识。
- `projectName`：固定为“股票基金质量分析系统”。
- `reportDateLabel`：固定 mock 日期，并标注“本地静态预览”。
- `title` / `displayName`：固定为“AI股票基金每日信息报告”。
- `modeLabel`：标识 mock-only 本地预览。
- `dataSourceLabel`：必须包含 `REDACTED FIXTURE DATA`。
- `generatedAtLabel`：固定 mock 生成时间，并标注“本地静态预览”。
- `deliveryStatus`：固定为未发送。
- `marketMood` / `headline` / `portfolioAction` / `riskLevel`：用于仪表盘摘要和历史报告预览的统一展示字段。
- `sections`：包含 `marketOverview`、`portfolioObservation`、`riskWarnings`、`actionSuggestions` 四个静态段落。
- `safetyLabels` / `redactionLabels` / `mockOnlyNotes`：集中声明模拟数据、脱敏和安全边界。

## 脱敏规则

- fixture 必须明显标注“模拟数据”“非真实账户”“非投资建议”。
- `dataSourceLabel` 和相关标签必须包含 `REDACTED FIXTURE DATA`。
- 日期只允许作为固定 mock 日期展示，并标注为本地静态预览。
- 金额、收益率、比例只能使用明显虚构值，不得复用真实持仓精确值。
- 不得包含任何可识别的真实产品编号、成交流水、账户条目、通知收件目标、个人联系方式、凭证、接口地址或历史日报原文。

## mock-only 边界

当前 fixture 和预览模型必须保持以下边界：

- 只使用静态脱敏 fixture。
- 仅用于 `127.0.0.1 only` 的本地预览语义。
- 不启动后端，不自动打开浏览器。
- 不接真实 API、provider、OpenAI、DeepSeek、智谱、本地大模型或其他模型服务。
- 不接真实 Agent、通知、账户、数据库、历史日报文件或交易能力。
- 不读取 `.env`、token、webhook、API key、本地配置、用户本地文件、支付宝、基金平台或券商平台。
- 不写 localStorage/sessionStorage，不上传日志，不发送日报，不发送提醒，不执行交易。

## 与 Web-P21～Web-P30 的关系

Web-P21～Web-P30 已完成 mock-only 页面和模块预览阶段，Web-P30.1 修正了数据脱敏与模块状态一致性。Web-P31 不改变页面 UI 主体，只把分散在 preview model 中的日报相关字段统一到独立 fixture，再由仪表盘摘要、历史报告、提醒、Agent 对话、空状态与错误示例继续消费静态 mock 数据。

## 为 Web-P32 做准备

Web-P31 只建立 TypeScript fixture 和字段命名基础。后续 Web-P32 可在此基础上补充 mock 报告 schema 文档，明确字段契约、段落语义、渲染边界和兼容策略；在 Web-P32 之前仍不得接真实 API/provider/AI/通知/账户/数据库/交易。
