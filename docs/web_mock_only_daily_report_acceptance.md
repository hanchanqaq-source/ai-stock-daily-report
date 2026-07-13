# Web-P36 mock-only 日报链路阶段收口与验收清单

## 1. 阶段定位

Web-P36 是 Web-P31 到 Web-P35 的 mock-only 日报链路阶段收口文档，用于梳理当前已经完成的 fixture、schema、导出入口、展示模型适配层、契约守卫、测试边界和本地验收流程。

当前阶段只整理既有 mock-only 日报链路，不改变页面视觉设计，不改变运行逻辑，不接入真实数据，也不新增真实日报 JSON 示例。

当前项目名必须保持为“股票基金质量分析系统”，当前日报名 / 推送显示名称必须保持为“AI股票基金每日信息报告”。

## 2. Web-P31 到 Web-P35 完成清单

| 阶段 | 完成内容 | 当前状态 |
| --- | --- | --- |
| Web-P31 | 统一 mock-only 日报 fixture 结构，集中定义“AI股票基金每日信息报告”的字段、脱敏标签、安全边界和固定 mock 日期。 | 已完成；仍只使用静态脱敏 fixture。 |
| Web-P32 | 新增 mock 报告 schema 文档，说明 `MockOnlyDailyReportFixture` 字段契约、字段映射、脱敏规则和未来真实日报接入前置条件。 | 已完成；文档不授权真实 provider / API / AI / 通知 / 账户 / 数据库 / 交易接入。 |
| Web-P33 | 统一 fixture 导出入口，页面模型通过 `fixtures/index.ts` 复用 mock-only fixture。 | 已完成；避免后续新增平行 fixture 入口。 |
| Web-P34 | 新增 `DailyReportViewModel` 适配层，将 mock 原始 fixture 同步映射为页面稳定展示模型。 | 已完成；adapter 是同步纯函数，不读取运行时配置或真实数据。 |
| Web-P35 | 新增 `DailyReportViewModel` mock-only guard 契约守卫，并纳入 mock-only preview 测试与网络边界测试。 | 已完成；guard 用于测试展示契约，不代表真实 schema 定稿。 |
| Web-P36 | 汇总当前链路、核心文件、安全边界、Windows 本地验收命令和 PR 复核清单。 | 本文档完成；仍不进入 Web-P37 或真实日报接入。 |

## 3. 当前 mock-only 日报数据链路

当前日报链路固定为：

```text
mock fixture → adapter → DailyReportViewModel → guard → preview model/tests
```

### 3.1 mock fixture

`dailyReportFixture.ts` 是唯一的 mock-only 日报 fixture 来源，定义固定项目名、固定日报名、静态脱敏数据来源、固定 sections、安全标签、脱敏标签和 mock-only notes。fixture 不读取真实历史日报文件，不读取数据库，不读取 `.env`、token、webhook 或 API 凭据。

### 3.2 adapter

`dailyReportAdapter.ts` 通过 `adaptMockOnlyDailyReportFixture` 将 `MockOnlyDailyReportFixture` 映射为 `DailyReportViewModel`。adapter 只做同步字段映射和固定 section 顺序转换，不发起网络请求，不调用 provider、AI、Agent、通知、账户、数据库或交易能力。

### 3.3 DailyReportViewModel

`DailyReportViewModel` 是页面预览消费的稳定展示模型。它将 `reportId` 映射为 `id`，将 `mockOnlyNotes` 映射为 `notes`，并将 `sections` 对象转换为固定顺序数组：`市场概览`、`组合观察`、`风险提示`、`动作建议`。

### 3.4 guard

`dailyReportViewModelGuard.ts` 通过 `validateMockOnlyDailyReportViewModel` 检查展示模型是否保留以下核心契约：

- 项目名仍为“股票基金质量分析系统”。
- `title` / `displayName` 仍为“AI股票基金每日信息报告”。
- `dataSourceLabel` 包含 `REDACTED FIXTURE DATA`。
- `modeLabel` 表达 mock-only 或本地预览语义。
- sections 数量与顺序保持固定。
- 安全标签、脱敏标签和 notes 继续声明 mock-only、非真实账户、非投资建议、不会发送通知、不会交易等边界。
- 展示模型不包含旧真实精确值或敏感文本。

### 3.5 preview model/tests

`mockOnlyPreviewModel.ts` 消费统一 fixture 导出入口和 adapter，生成页面预览需要的 mock-only 模型。`mockOnlyPreview.test.ts` 覆盖 fixture、adapter、guard、页面预览模型和脱敏边界。`mockOnlyPreviewNetworkBoundary.test.ts` 静态覆盖 mock-only preview 文件的网络边界，防止新增真实 API、provider、AI、通知、账户、数据库或交易接入。

## 4. 核心文件说明

| 文件 | 角色 | 复核重点 |
| --- | --- | --- |
| `apps/dsa-web/src/mocks/preview/fixtures/dailyReportFixture.ts` | mock-only 日报 fixture 唯一来源。 | 固定项目名、固定日报名、`REDACTED FIXTURE DATA`、静态脱敏 fixture、安全标签和 notes 不得弱化。 |
| `apps/dsa-web/src/mocks/preview/fixtures/index.ts` | fixture 目录统一导出入口。 | 后续 mock-only 预览应复用该入口，不新增平行 fixture 导出路径。 |
| `apps/dsa-web/src/mocks/preview/adapters/dailyReportAdapter.ts` | fixture 到 `DailyReportViewModel` 的同步适配层。 | 只做纯映射；不得读取配置、文件、网络、provider、AI、通知、账户、数据库或交易链路。 |
| `apps/dsa-web/src/mocks/preview/adapters/index.ts` | adapter 目录统一导出入口。 | 后续 adapter 复用该入口，避免页面直接散落导入实现细节。 |
| `apps/dsa-web/src/mocks/preview/guards/dailyReportViewModelGuard.ts` | `DailyReportViewModel` mock-only 契约守卫。 | 必须继续守住项目名、日报名、数据来源、section 顺序、安全标签、旧真实精确值和敏感文本边界。 |
| `apps/dsa-web/src/mocks/preview/guards/index.ts` | guard 目录统一导出入口。 | 测试和后续 mock-only 验收应从该入口复用 guard。 |
| `apps/dsa-web/src/mocks/preview/mockOnlyPreviewModel.ts` | mock-only preview 展示模型组装。 | 应继续通过 fixture barrel 和 adapter 消费日报数据，不绕过 `DailyReportViewModel`。 |
| `apps/dsa-web/src/mocks/preview/mockOnlyPreviewTypes.ts` | mock-only fixture 与展示模型类型。 | 字段变更需同步 schema 文档、guard、测试和本验收文档。 |
| `apps/dsa-web/tests/mocks/preview/mockOnlyPreview.test.ts` | mock-only preview 主测试。 | 覆盖 fixture、adapter、guard、固定标题、脱敏、不可变性和页面模型消费路径。 |
| `apps/dsa-web/tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts` | mock-only 网络边界静态测试。 | 新增 preview / service / adapter / guard 文件后，应确认是否纳入扫描范围。 |

## 5. 安全边界

当前阶段必须继续满足以下安全边界：

- 不接真实 API。
- 不接 provider。
- 不接 AI / Agent。
- 不接通知。
- 不接账户。
- 不接数据库。
- 不交易。
- 不读取 `.env`、token、webhook、API 凭据。
- 不读取真实历史日报文件。
- 不使用真实金额、真实收益率、真实基金持仓。

如果后续改动触碰任一边界，不能作为 Web-P36 的延续处理，必须单独提出新阶段目标、风险评估、schema 高规格复核、凭证管理方案、脱敏方案和用户确认流程。

## 6. Windows 本地验证命令

在 Windows 本地复核 Web-P31 到 Web-P36 的 mock-only 日报链路时，建议执行：

```bash
git diff --check
```

```bash
cd apps/dsa-web && npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
```

```bash
cd apps/dsa-web && npm run build
```

```bash
cd apps/dsa-web && npm run lint
```

如果仅修改文档，可以不跑完整前端 build，但交付说明必须写明原因，并至少执行 `git diff --check`。

如果修改 TypeScript、测试文件、fixture、adapter、guard、preview model 或网络边界扫描范围，应执行 mock-only preview 测试；如改动可能影响 Web 构建入口或类型检查，应执行 `npm run build`；如改动可能影响 lint 规则覆盖范围，应执行 `npm run lint`。

## 7. PR 复核清单

提交或审查相关 PR 时，至少确认：

- [ ] 项目名是否仍为“股票基金质量分析系统”。
- [ ] 日报名是否仍为“AI股票基金每日信息报告”。
- [ ] 是否仍为 mock-only。
- [ ] 是否没有新增真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易。
- [ ] guard 是否通过。
- [ ] network boundary 是否覆盖新文件。
- [ ] 是否没有读取或打印 `.env`、token、webhook、API 凭据。
- [ ] 是否没有新增真实日报 JSON 示例。
- [ ] 是否没有使用真实金额、真实收益率、真实基金持仓。
- [ ] 如涉及字段或展示契约变化，是否同步更新 schema 文档、测试与 changelog。

## 8. 后续建议

- Web-P37 可以考虑 mock-only 页面预览入口和验收脚本说明，但仍必须保持 mock-only，不启动后端，不打开浏览器，不读取真实 `.env`，不接真实 API、provider、AI、通知、账户、数据库或交易。
- Web-P38 以后再考虑真实日报接入前的 schema 高规格复核，包括字段语义、兼容性、错误态、脱敏、provider 授权、凭证管理、通知 dry-run、账户授权、日志脱敏和回滚方案；但不能在 Web-P36 阶段接入真实数据。
