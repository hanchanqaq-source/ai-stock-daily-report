# Web-P43 provider 只读设计文档

## 1. 阶段定位

Web-P43 是“股票基金质量分析系统”在 Web dry-run 链路上的 provider 只读设计阶段。本阶段只补充设计文档，用于约束未来 provider 进入 dry-run 候选输入前的安全边界。

Web-P43 仅做以下事项：

- 只写 provider 只读设计文档。
- 不新增真实 provider。
- 不新增真实 API client。
- 不读取真实账户。
- 不读取真实行情。
- 不调用 AI / Agent。
- 不发送通知。
- 不读取数据库。
- 不执行交易。
- 不读取 `.env`、token、webhook、API key。
- 不改变当前 mock-only 页面链路。
- 不把 dry-run adapter 接入页面入口。

Web-P43 完成后，也不代表可以开始真实 provider 接入。真实 provider 接入必须另开阶段、另开设计、另开 PR，并经过凭证、权限、校验、脱敏、降级、日志、CI 和人工确认等前置条件复核。

## 2. 当前链路基线

当前 Web 日报预览链路仍然保持 mock-only：

```text
mock fixture
→ RealDailyReportDryRunInput 类型草案
→ validator
→ dry-run adapter
→ DailyReportViewModel 兼容展示模型
→ mock-only fallback
```

provider 未来只能作为候选输入来源，不能直接喂给页面。任何来自 provider 的候选数据都必须先完成脱敏、schema normalization、类型约束、validator 阻断判断和 adapter 映射，最终才可能形成 `DailyReportViewModel` 兼容展示模型。

当前页面仍以 mock fixture 和 mock-only fallback 为安全基线。provider 不应改变页面入口、预览入口、mock-only fixture、preview model、HTML 或运行脚本。

## 3. provider 只读原则

未来 provider 只能被设计为只读候选输入来源，并且必须遵守以下原则：

- provider 只能只读。
- provider 不允许写账户。
- provider 不允许交易。
- provider 不允许触发通知。
- provider 不允许调用 AI。
- provider 不允许修改本地配置。
- provider 不允许写入 mock-only fixture。
- provider 不允许把原始响应写入测试快照。
- provider 不允许把真实数据直接拼进页面 viewModel。
- provider 失败必须可回退 mock-only。

provider 只读不等于真实接入已经开始。Web-P43 不创建 provider client、不创建 API client、不发起真实请求，也不声明任何 provider 已经可用于生产或本地真实 dry-run。

## 4. provider 类型分层

未来如需设计 provider，可以按只读候选输入来源分层，但 Web-P43 不实现这些 provider：

| provider 类型 | 未来候选职责 | Web-P43 状态 |
| --- | --- | --- |
| `market-data-provider` | 行情 / 指数 / 行业观察，只读候选输入 | 仅文档说明，不实现 |
| `portfolio-readonly-provider` | 账户 / 持仓只读候选输入 | 当前不启用，仅文档说明 |
| `report-source-provider` | 历史日报来源候选输入 | 当前不启用，仅文档说明 |
| `notification-status-provider` | 通知状态候选输入 | 当前不启用，仅文档说明 |

以上分层只用于未来设计讨论，不代表可以读取真实行情、账户、历史日报、通知状态、数据库或任何外部服务。

## 5. 最小字段原则

provider 未来只允许返回生成“AI股票基金每日信息报告”所需的最小字段。字段应面向 dry-run 输入契约，而不是面向 provider 原始响应结构。

禁止读取或透传以下内容：

- 无关账户明细。
- 真实交易流水。
- 身份信息。
- 手机号。
- 邮箱。
- webhook。
- token。
- API key。
- 完整 provider 原始响应。
- 数据库导出。
- 真实历史日报原文。
- 交易权限字段。
- 可执行交易字段。

如果某字段不是生成日报候选输入的必要字段，应默认不读取、不缓存、不记录、不进入 schema normalization，也不进入测试 fixture。

## 6. provider 输出边界

provider 输出必须先进入候选 payload，不得直接进入页面。未来允许讨论的链路只能是：

```text
provider raw candidate
→ redaction
→ schema normalization
→ RealDailyReportDryRunInput
→ validateRealDailyReportDryRunInput
→ adaptRealDailyReportDryRunInputToViewModel
→ DailyReportViewModel
```

输出边界规则：

- provider 原始响应不能直接进入 `DailyReportViewModel`。
- `providerName` 必须脱敏，例如固定为 `REDACTED_PROVIDER_LABEL` 或同等级低敏标签。
- `dataSourceLabel` 只能显示低敏来源标签，不得携带真实账户、真实 provider 标识、密钥片段、URL、token、webhook 或可追溯身份的信息。
- schema 校验失败必须 `blocked`。
- `blocked` 时必须 fallback mock-only。
- 不能展示半真半假的日报。
- validator 未明确通过时，不允许调用 adapter 生成页面展示模型。
- adapter 只消费已通过校验的 `RealDailyReportDryRunInput`，不得消费 provider raw candidate。

## 7. 凭证与密钥边界

Web-P43 不新增任何凭证读取，也不新增任何密钥相关代码或配置：

- 不新增 `.env` 字段。
- 不新增 token。
- 不新增 webhook。
- 不新增 API key。
- 不新增密钥管理代码。
- 不读取 `.env`、token、webhook、API key。

未来如果要接真实 provider，必须另开阶段设计并至少明确：

- 凭证来源。
- 最小权限。
- 只读权限。
- CI 禁用真实凭证。
- 本地 dry-run 默认禁用真实 provider。
- 日志不得打印密钥。
- PR 描述不得写密钥。
- fixture / 测试 / 文档示例不得包含密钥。

真实 provider 接入 PR 不得复用 Web-P43 作为“已完成凭证方案”的证明。

## 8. 超时、重试、缓存、降级

Web-P43 只记录未来设计要求，不编写实现代码。未来 provider 必须具备：

- 明确超时。
- 有限重试。
- 错误分类。
- 退避策略。
- 缓存范围。
- 缓存过期时间。
- 缓存脱敏规则。
- provider 失败时降级。
- schema 校验失败时阻断。
- 回退 mock-only。

禁止以下行为：

- 无限重试。
- provider 失败后继续展示半真数据。
- 缓存真实原始账户响应。
- 把缓存内容写入 mock fixture。
- 把错误栈打印出 token / webhook / API key。

降级优先级必须以安全和一致性为准：provider 失败、超时、返回异常、redaction 失败、schema normalization 失败或 validator blocked 时，都应回退 mock-only，而不是拼接部分真实数据继续展示。

## 9. 日志脱敏规则

日志只能记录低敏诊断信息：

- provider 类型。
- 低敏错误类别。
- trace id。
- schema 状态。
- fallback 状态。

日志不得记录：

- token。
- webhook。
- API key。
- 真实账户标识。
- 真实联系方式。
- provider 原始完整响应。
- 真实持仓明细。
- 真实交易流水。
- 可追溯真实资产的精确金额 / 收益率 / 比例。

日志语义应支持排障，但不能成为真实数据、账户信息或凭证的旁路泄漏渠道。

## 10. provider 接入前置条件

未来真正 provider 接入前必须满足：

- Web-P43 设计文档通过复核。
- provider 凭证方案完成。
- provider 只读权限确认。
- dry-run 默认禁用真实 provider。
- schema validator 覆盖 provider 候选输入。
- adapter blocked fallback 已测试。
- 日志脱敏方案完成。
- CI 不使用真实凭证。
- 用户人工确认。
- 单独 PR。

未满足以上条件时，不得开始真实 provider 接入，也不得把 provider candidate 接入页面入口、正式日报生成链路、通知链路、账户链路、数据库或交易相关能力。

## 11. 与 Web-P39～P42.1 的关系

Web-P43 只补 provider 只读设计，不实现 provider。它与前序阶段关系如下：

- Web-P39 定义 dry-run 输入契约。
- Web-P40 定义 TypeScript 类型草案。
- Web-P41 定义 validator mock-only 测试。
- Web-P42 定义 adapter 草案。
- Web-P42.1 完成 P39～P42 dry-run 链路小总复核。
- Web-P43 只补 provider 只读设计，不实现 provider。

因此，Web-P43 不改变 P39～P42.1 的 mock-only、dry-run design only、安全阻断和 fallback 结论。

## 12. 后续阶段建议

后续阶段可以考虑继续拆分为：

- Web-P44：provider 只读接口契约文档。
- Web-P45：provider candidate payload mock-only fixture。
- Web-P46：provider candidate validator 测试。
- Web-P47：provider dry-run feature flag 文档。

Web-P43 不做以上事项，不新增 fixture、不新增测试、不新增 feature flag、不接入 provider、不接入 API client、不发起真实请求。

## 13. 安全边界确认

Web-P43 交付后仍必须保持：

- docs-only。
- mock-only。
- dry-run design only。
- 不启动后端。
- 不自动打开浏览器。
- 不接真实 API。
- 不接 provider。
- 不接 OpenAI。
- 不接 DeepSeek。
- 不接智谱。
- 不接本地大模型。
- 不接真实 Agent。
- 不接通知。
- 不读取 `.env`。
- 不读取 token / webhook / API key。
- 不读取真实账户。
- 不读取支付宝、基金平台、券商平台。
- 不读取真实历史日报文件。
- 不读取数据库。
- 不读取用户本地文件。
- 不写入本地配置。
- 不写 localStorage/sessionStorage。
- 不上传日志。
- 不发送日报。
- 不发送提醒。
- 不执行交易。
