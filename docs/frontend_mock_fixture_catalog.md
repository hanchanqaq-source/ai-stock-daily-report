# 前端 mock fixture 数据目录说明（L2E）

本目录说明 `apps/dsa-web/src/mocks/fixtures/` 下新增的静态 JSON fixture。当前 L2E 只新增 demo / mock / redacted 数据文件，不接入 Web 运行代码，不修改 API client、页面、store、组件、Vite 配置或启动脚本。

## 安全边界

- 所有 fixture 仅用于 `local_preview_only`。
- 所有根对象都包含 `metadata`，并声明 `contains_real_data: false`、`contains_secrets: false`。
- 禁止放入真实账户、真实持仓、真实资产金额、真实收益率、真实交易记录、手机号、邮箱、身份证、地址、真实 token、webhook、API key、provider URL 或模型绑定配置。
- 示例敏感值只允许使用 `REDACTED_TOKEN`、`REDACTED_WEBHOOK`、`REDACTED_API_KEY`、`DEMO_AMOUNT`、`MOCK_PERCENT`、`MOCK_API_PATH_ONLY` 等明显占位符。
- 当前文件不会自动请求真实网络，不会启动后端，不会调用 AI 模型，不会发送通知。

## 文件清单

| Fixture | 对应模块 / 页面 | 用途 |
| --- | --- | --- |
| `auth.json` | `authApi`、登录页、`AuthProvider` | 认证关闭、认证开启未登录、mock 登录用户、401 / 403 示例。 |
| `dashboard.json` | 首页、`analysisApi`、`historyApi`、`agentApi` | 顶部统计卡、mock 市场状态、自选列表、技能列表、loading / empty / error 示例。 |
| `analysis_tasks.json` | `analysisApi`、任务列表、run-flow | accepted、running、completed、failed、duplicate、market review mock。 |
| `history_reports.json` | `historyApi`、报告组件 | 报告列表、详情、Markdown、news、diagnostics、stock bar、empty 示例。 |
| `portfolio.json` | `portfolioApi`、账户页 | mock 账户、持仓、风险、现金流水、交易记录；金额均为 `DEMO_AMOUNT` 或 `0.00 MOCK`。 |
| `alerts.json` | `alertsApi`、告警页 | 告警规则、触发历史、通知历史、test success / failed、empty list。 |
| `system_config.json` | `systemConfigApi`、设置页、聊天页 | masked config、setup status、scheduler status、watchlist、LLM / notification test mock。 |
| `agent_chat.json` | `agentApi`、聊天页、agent store | skills、sessions、messages、streaming chunks、abort / error 示例。 |
| `alphasift.json` | `alphasiftApi`、选股页 | enabled / disabled status、strategy list、hotspots、screen task、candidates。 |
| `usage.json` | `usageApi`、Token 用量页 | token usage dashboard、by model、by call type、recent calls、empty usage；不反映真实 token 用量。 |
| `backtest.json` | `backtestApi`、回测页 | run result、result list、overall performance、stock performance、failed / empty 示例。 |
| `decision_signals.json` | `decisionSignalsApi`、决策信号页 | signal list、latest signal、outcome stats、timeline、feedback。 |
| `stocks_import.json` | `stocksApi`、智能导入组件 | text import parse result、image extract result、low confidence、error fixture。 |
| `errors.json` | API 错误处理 | network、validation、unauthorized、forbidden、conflict、rate limited、server error 示例。 |
| `empty_states.json` | 各页面空态 | empty dashboard、portfolio、history、alerts、chat、usage。 |

## 后续 L2F 使用方式

后续如新增 mock API adapter，应显式启用 mock-only 模式后读取这些 fixture，并额外测试证明 axios / fetch / streaming 入口不会穿透到真实 `/api/v1/**`、本地后端、外网、provider、AI 或通知服务。
