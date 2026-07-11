# 前端 mock-only 数据层设计（L2D）

任务编号：`L2D-FRONTEND-MOCK-ONLY-DATA-LAYER-DESIGN`

## 1. 当前结论摘要

本轮只做设计与代码阅读，不新增 Web 启动脚本，不启动 Vite，不启动后端，不安装依赖，不读取或打印 `.env`。

- 当前 `apps/dsa-web` 是 Vite + React + TypeScript 前端；`package.json` 只提供 `dev`、`build`、`lint`、`test`、`test:smoke`、`preview` 等通用脚本，没有 mock-only / demo-only / redacted-only 脚本。
- 当前没有可直接使用的整站 mock-only 数据层。所有主要业务页面仍通过 `src/api/*.ts`、`AuthContext`、zustand store 或部分组件调用真实 `/api/v1/**` API。
- 当前不应直接新增 Windows Web 启动脚本：`vite.config.ts` 的 dev server 绑定 `0.0.0.0`，并把 `/api` 代理到 `http://127.0.0.1:8000`；同时 `API_BASE_URL` 可被 `VITE_API_URL` 覆盖，无法证明普通 `npm run dev` 不会连接真实后端。
- 本轮只新增设计文档并更新 `docs/CHANGELOG.md`，不修改 `apps/dsa-web/src/**` 运行代码、不修改 `package.json`、不修改 `vite.config.ts`。

## 2. 已检查文件与扫描范围

本轮检查了以下前端入口与目录：

- `apps/dsa-web/package.json`
- `apps/dsa-web/vite.config.ts`
- `apps/dsa-web/src/main.tsx`
- `apps/dsa-web/src/App.tsx`
- `apps/dsa-web/src/api/`
- `apps/dsa-web/src/utils/constants.ts`
- `apps/dsa-web/src/pages/`
- `apps/dsa-web/src/stores/`
- `apps/dsa-web/src/contexts/`
- `apps/dsa-web/src/components/`
- `apps/dsa-web/src/utils/`

同时用静态搜索检查了 `fetch(`、`axios`、`/api/`、`/api/v1/`、`VITE_API_URL`、`token`、`webhook`、`apiKey`、`secret` 等关键词。未读取、未打印 `.env` 或任何实际 secret 文件。

## 3. 前端运行与 API 基础结构

### 3.1 启动脚本与 Vite 代理

`apps/dsa-web/package.json` 中脚本为：

- `dev`: `vite`
- `build`: `tsc -b && vite build`
- `lint`: `eslint .`
- `test`: `vitest run`
- `test:smoke`: `playwright test`
- `preview`: `vite preview`

`apps/dsa-web/vite.config.ts` 的 dev server 当前配置：

- `host: '0.0.0.0'`
- `port: 5173`
- `proxy['/api'].target = 'http://127.0.0.1:8000'`

因此普通 dev server 不是安全 mock-only 入口。

### 3.2 API client 与环境变量

`apps/dsa-web/src/api/index.ts` 使用 `axios.create` 建立共享 `apiClient`，其 `baseURL` 来自 `API_BASE_URL`，并启用 `withCredentials: true`。`API_BASE_URL` 在 `apps/dsa-web/src/utils/constants.ts` 中由 `import.meta.env.VITE_API_URL?.trim()` 读取；未配置时为空字符串，表示同源 `/api/v1/**`。

这意味着后续 mock-only 模式必须显式阻断：

- `VITE_API_URL` 指向真实后端或外网；
- 同源 `/api/v1/**` 被 Vite proxy 转发到 `127.0.0.1:8000`；
- `fetch` 绕过 `apiClient` 直接发起请求。

## 4. API 模块清单

以下清单以 `apps/dsa-web/src/api/*.ts` 实际存在模块为准。

| 模块 | 文件 | 主要真实 API / 能力 | mock fixture 需求 |
| --- | --- | --- | --- |
| `apiClient` | `api/index.ts` | 共享 axios client、`baseURL`、`withCredentials`、响应错误解析拦截 | mock adapter 入口；网络阻断测试；统一错误 fixture |
| `authApi` | `api/auth.ts` | `/api/v1/auth/status`、登录、登出、改密码、认证设置 | auth enabled/disabled、logged in/out、首次设置密码、401/403、脱敏用户状态 |
| `analysisApi` | `api/analysis.ts` | 股票分析、异步任务、任务列表、任务状态、run-flow、市场复盘、任务 SSE URL | dashboard、分析任务 accepted/running/completed/failed、duplicate task、market review、run-flow |
| `historyApi` | `api/history.ts` | 历史报告列表、详情、新闻、Markdown、诊断、flow、删除、股票报告聚合 | report list/detail、markdown、news、diagnostics、stock bar、empty/error/loading |
| `agentApi` | `api/agent.ts` | chat、skills、session list/messages/delete/send、`fetch` streaming | skills、session、message stream、abort/error、空会话、安全问答内容 |
| `portfolioApi` | `api/portfolio.ts` | 账户、快照、风险、外汇刷新、交易/现金/公司行动、CSV 导入 | 脱敏账户、持仓、风险、交易、现金流水、导入预览、空账户 |
| `alertsApi` | `api/alerts.ts` | alert rule CRUD、enable/disable/test、trigger、notification | 规则列表、触发历史、通知结果、测试成功/失败、空列表 |
| `systemConfigApi` | `api/systemConfig.ts` | 系统配置、schema、setup、scheduler、env export/import、LLM 测试、通知测试、watchlist | 配置 schema、masked values、setup status、scheduler status、测试结果、watchlist |
| `alphasiftApi` | `api/alphasift.ts` | AlphaSift status、screen、async screen task、strategies、hotspots、install、enable/disable | enabled/disabled、策略列表、热点、筛选任务、候选股、安装状态 |
| `usageApi` | `api/usage.ts` | token / usage dashboard | today/month/all 用量、by model/by call type、recent calls、空用量 |
| `backtestApi` | `api/backtest.ts` | 回测运行、结果列表、整体/个股绩效 | 回测任务、结果分页、绩效曲线、404-null、失败态 |
| `decisionSignalsApi` | `api/decisionSignals.ts` | 决策信号生成/列表/详情/latest/status/outcomes/stats/feedback | 信号列表、最新信号、时间线、结果统计、反馈读写、空状态 |
| `stocksApi` | `api/stocks.ts` | 图片识别持仓、文本/文件导入解析 | 图片识别 mock、文本导入 mock、低置信度/错误 fixture |
| `error` / `utils` | `api/error.ts`、`api/utils.ts` | API 错误解析、snake_case 到 camelCase | 标准 HTTP/network/validation/conflict 错误 fixture |

## 5. 页面、store、组件调用关系

### 5.1 全局入口

- `main.tsx` 只挂载 React、`ThemeProvider` 和 `App`，不直接调用 API。
- `App.tsx` 挂载 `AuthProvider`，读取认证状态；路由变化会写入 `agentChatStore.currentRoute`。认证状态加载失败时显示 `ApiErrorAlert`。
- `AuthContext.tsx` 在加载时调用 `authApi.getStatus()`；登录、登出、改密码分别调用 `authApi.login()`、`authApi.logout()`、`authApi.changePassword()`，并会重置 `stockPoolStore` dashboard 状态。

### 5.2 页面调用关系

| 页面 | 主要调用 | 说明 |
| --- | --- | --- |
| `HomePage.tsx` | `systemConfigApi.getSetupStatus()`、`agentApi.getSkills()`、`historyApi.deleteByCode()`、`analysisApi.getStatus()`、`analysisApi.triggerMarketReview()`，并使用 `stockPoolStore` | 首页 / Dashboard、报告列表、分析任务、市场复盘入口 |
| `LoginPage.tsx` | 通过 `useAuth()` 间接调用 `authApi` | 登录、首次密码设置 |
| `ChatPage.tsx` | `agentApi.getSkills()`、`agentApi.deleteChatSession()`、`agentApi.sendChat()`、`systemConfigApi.getWatchlist()` / `addToWatchlist()` / `removeFromWatchlist()`、`systemConfigApi.getConfig(false)` / `update()`，并使用 `agentChatStore` | 聊天 / Agent、技能、会话、自选、压缩配置 |
| `PortfolioPage.tsx` | `portfolioApi`、`decisionSignalsApi.getLatest()` | 账户、持仓、交易、现金、风险、外汇刷新、持仓分析、最新决策信号 |
| `DecisionSignalsPage.tsx` | `decisionSignalsApi.list()`、`getOutcomeStats()`、`getSignalOutcomes()`、`getFeedback()`、`getLatest()`、`updateStatus()`、`putFeedback()` | 决策信号列表、详情、时间线、结果与反馈 |
| `StockScreeningPage.tsx` | `alphasiftApi.getStatus()`、`getStrategies()`、`getHotspots()`、`getHotspotDetail()`、`startScreen()`、`getScreenTask()`、`enable()` | 策略筛选 / AlphaSift |
| `BacktestPage.tsx` | `backtestApi.run()`、`getResults()`、`getOverallPerformance()`、`getStockPerformance()` | 回测运行与结果 |
| `AlertsPage.tsx` | `alertsApi.listRules()`、`createRule()`、`enableRule()`、`disableRule()`、`deleteRule()`、`testRule()`、`listTriggers()`、`listNotifications()` | 告警规则、触发历史、通知历史 |
| `SettingsPage.tsx` | `systemConfigApi.getSchedulerStatus()`、`runSchedulerNow()`、`getSetupStatus()`、`exportEnv()`、`importEnv()`、`update()`、`analysisApi.analyzeAsync()`、`alphasiftApi.enable()` | 系统设置、调度、配置备份、setup smoke、AlphaSift |
| `TokenUsagePage.tsx` | `usageApi.getDashboard()` | Token 用量面板 |
| `NotFoundPage.tsx` | 无直接 API | 404 页面 |

### 5.3 Store 调用关系

| Store | 主要调用 | 说明 |
| --- | --- | --- |
| `stockPoolStore.ts` | `historyApi.getList()`、`historyApi.getDetail()`、`historyApi.deleteRecords()`、`historyApi.getStockBarList()`、`analysisApi.analyzeAsync()`、`analysisApi.getTasks()` | 首页报告列表、市场复盘历史、选择报告、删除报告、提交异步分析、任务轮询、股票报告聚合 |
| `agentChatStore.ts` | `agentApi.getChatSessions()`、`getChatSessionMessages()`、`chatStream()` | Agent 会话、消息历史、streaming 回复 |
| `analysisStore.ts` | 无直接 API | 仅保存 `currentAnalysis`、`isLoading`、`error` |

### 5.4 Component / utils 中的直接 API 调用

发现部分组件和工具并非只接收页面传入数据，而是直接调用 API：

- `components/report/ReportMarkdownPanel.tsx`：`historyApi.getMarkdown()`。
- `components/report/MarketReviewReportView.tsx`：`historyApi.getMarkdown()`。
- `components/report/ReportDiagnostics.tsx`：`historyApi.getDiagnostics()`。
- `components/report/ReportNews.tsx`：`historyApi.getNews()`。
- `components/alerts/AlertRuleForm.tsx`：`portfolioApi.getAccounts()`。
- `components/layout/SidebarNav.tsx`：`alphasiftApi.getStatus()`。
- `components/settings/AuthSettingsCard.tsx`：`authApi.updateSettings()`。
- `components/settings/IntelligentImport.tsx`：`stocksApi.extractFromImage()`、`stocksApi.parseImport()`、`systemConfigApi.update()`。
- `components/settings/LLMChannelEditor.tsx`：`systemConfigApi.update()`、`testLLMChannel()`、`discoverLLMChannelModels()`。
- `components/settings/NotificationTestPanel.tsx`：`systemConfigApi.testNotificationChannel()`。
- `utils/chatFollowUp.ts`：`historyApi.getDetail()`。
- `utils/stockIndexLoader.ts`：`fetch('/stocks.index.json?...')`，该请求是本地静态索引文件，不是 `/api/v1/**`，但 mock-only 网络策略仍应白名单化静态资产并阻断外网。

## 6. 关键词扫描结论

- `fetch(`：存在于 `agentApi.chatStream()`，会直接请求 `${API_BASE_URL}/api/v1/agent/chat/stream`；还存在于 `utils/stockIndexLoader.ts` 请求本地静态 `/stocks.index.json`。
- `axios`：集中在 `api/index.ts` 与 `api/error.ts`；业务 API 基本通过共享 `apiClient`。
- `/api/` 与 `/api/v1/`：大量存在于 `src/api/*.ts`；mock-only 不能只改页面层，必须覆盖 API 层或请求适配层。
- `VITE_API_URL`：存在于 `utils/constants.ts`，后续 mock-only 模式必须禁止它指向真实服务。
- `token` / `webhook` / `apiKey` / `secret`：配置和设置 UI 中存在字段名、mask token、LLM channel API key、通知 webhook 文案和模板默认 URL。这些字段说明 mock fixture 必须默认脱敏，且禁止把本机 `.env`、真实 token、真实 webhook、真实 API key 注入 fixture 或日志。

## 7. mock fixture 分类设计

后续建议在不接运行入口的前提下先建立 fixture 分类；所有 fixture 必须使用 `demo` / `mock` / `redacted` 值。

1. `auth fixture`
   - auth disabled / enabled；logged in / logged out；首次设置密码；401/403；安全空用户。
2. `dashboard fixture`
   - 首页报告列表、市场复盘摘要、任务状态、技能列表、自选股、安全空状态。
3. `analysis task fixture`
   - `accepted`、`pending`、`processing`、`completed`、`failed`、duplicate task、run-flow、SSE/stream 错误。
4. `history report fixture`
   - 报告列表、详情、Markdown、新闻、诊断、flow、stock bar、删除成功/失败、空列表。
5. `portfolio fixture`
   - 脱敏账户、脱敏持仓、脱敏金额、风险摘要、交易/现金/公司行动、CSV 导入预览、空账户。
6. `alerts fixture`
   - 告警规则、触发历史、通知历史、规则测试成功/失败、空状态。
7. `system config fixture`
   - schema、masked config、setup status、scheduler status、env export/import 的红线占位、LLM/通知测试结果、watchlist。
8. `agent chat fixture`
   - skills、session list、message history、stream chunk、send success/error、abort。
9. `alphasift / strategy fixture`
   - status、strategies、hotspots、hotspot detail、screen accepted、screen task、candidate list、disabled/install 状态。
10. `usage fixture`
    - period dashboard、model breakdown、call type breakdown、recent calls、zero usage。
11. `backtest fixture`
    - run accepted、results list、overall performance、stock performance、404-null、空结果。
12. `decision signals fixture`
    - list/detail/latest/status/outcomes/stats/feedback、空时间线、更新失败。
13. `stocks import fixture`
    - 图片识别、文本导入、低置信度、解析失败。
14. `error / loading / empty-state fixture`
    - HTTP 400/401/403/404/409/500、network blocked、timeout、validation conflict、loading skeleton、empty state。

## 8. mock-only 运行模式建议

本轮不实现。后续建议采用“模式开关 + API adapter + 网络断言”的最小安全方案：

1. 新增显式前端预览模式，例如 `VITE_DSA_WEB_PREVIEW_MODE=mock`。
2. 在 API 层建立单一 adapter 入口：
   - 正常模式继续导出真实 `apiClient` / API modules；
   - mock 模式导出 mock adapter 或 fixture service；
   - 所有 `src/api/*.ts` 和直接 `fetch` 路径必须被纳入适配，不能只 mock 页面层。
3. 对 `agentApi.chatStream()` 这类 `fetch` streaming 单独提供 mock `ReadableStream` 或事件序列 fixture。
4. 对 `utils/stockIndexLoader.ts` 这类静态资源请求设置白名单：只允许读取本地构建产物中的静态文件，不允许请求 `/api/v1/**` 或外网。
5. 引入测试证明 mock-only 模式中：
   - axios adapter 不发网络；
   - `globalThis.fetch` 被替换为阻断器或白名单 fetch；
   - 任意 `/api/v1/**`、`http://127.0.0.1:8000`、外网 URL 都会使测试失败。

可选技术路径：

- 优先：本地 fixture service + API module 级 adapter，改动可控、适合现有 `src/api/*.ts` 结构。
- 可选：MSW，用于浏览器级请求拦截；但仍需额外证明未穿透到真实后端。
- 可选：axios mock adapter；但必须额外覆盖 `fetch` streaming 和静态资源白名单。

## 9. 网络阻断要求

后续真正实现 mock-only 时必须保证：

- mock-only 模式下不请求 `/api/v1/**`。
- 不请求真实 provider。
- 不请求 `127.0.0.1:8000` 后端。
- 不请求外网。
- 不调用 `main.py`。
- 不调用 FastAPI / uvicorn。
- 不调用 OpenAI / LiteLLM / 本地模型。
- 不发送通知。
- 不生成正式日报。
- 不触发调度器、回测真实执行、真实分析任务或正式市场复盘。
- 不访问真实账户、真实交易、真实持仓或真实配置导出接口。

建议把这些要求固化为测试：在 mock-only 测试环境中 monkey patch `fetch`、axios adapter 和可能的 EventSource/SSE 入口，任何非白名单 URL 直接抛错并让测试失败。

## 10. 敏感信息边界

mock fixture、日志、错误消息、截图和 PR 描述均不得包含：

- 真实账户。
- 真实持仓。
- 真实金额。
- 真实收益率。
- 真实 token。
- 真实 webhook。
- 真实 API key。
- 真实手机号 / 邮箱 / 身份信息。
- 真实交易记录。
- 真实 `.env` 内容。
- 真实通知渠道、Bot token、Gotify token、Bark key、Telegram token。
- 真实 OpenAI / LiteLLM / provider base URL 与 key 的组合。

允许值仅限：

- `demo-*`、`mock-*`、`redacted-*`。
- `***`、`******`、`REDACTED`。
- 文档说明中的非可用示例域名，例如 `https://api.example.com/v1`。
- 不对应任何真实账户、真实资产和真实交易的虚构数据。

## 11. 推荐实施拆分

建议后续继续拆成最小安全步骤：

- L2E：新增前端 mock fixture 数据目录，但不接运行入口。
  - 只新增 fixture JSON/TS 数据与 README。
  - 不修改 Vite、不新增脚本、不让应用导入 fixture。
  - 加 secret scan / fixture 内容检查，确认只有 mock / redacted 值。
- L2F：新增 mock API adapter，并加测试证明不请求真实网络。
  - 覆盖 `apiClient`、`src/api/*.ts`、`agentApi.chatStream()` 和 `stockIndexLoader` 白名单。
  - 用 Vitest 验证 `/api/v1/**`、`127.0.0.1:8000`、外网 URL 被阻断。
- L2G：新增 localhost-only Web safe preview 脚本。
  - 仅在 mock adapter 与网络阻断测试通过后新增。
  - 显式绑定 `127.0.0.1`，不使用当前 `0.0.0.0` dev server 默认行为。
  - 强制 `VITE_DSA_WEB_PREVIEW_MODE=mock`，并拒绝同时设置真实 `VITE_API_URL`。
- L2H：Windows 本地运行验证。
  - 验证不启动后端、不调用 API、不联网、不读取 `.env`。
  - 验证页面可在 mock 数据下完成关键导航和空/error/loading 状态展示。

## 12. 风险与回滚

### 12.1 风险

- 只 mock 页面层会漏掉 store、context、component 和 `fetch` streaming 路径。
- `VITE_API_URL` 可能把请求导向真实后端或外网。
- 当前 Vite `/api` proxy 会把同源 `/api/v1/**` 转发到 `127.0.0.1:8000`。
- 设置页包含 API key、webhook、通知测试、LLM 测试、配置导入导出等敏感路径，mock fixture 如果设计不当可能泄露真实配置语义或误触发真实测试接口。
- Agent streaming、调度 run-now、市场复盘、持仓分析、回测运行等路径都可能触发后端工作流，必须在 mock-only 中硬阻断。

### 12.2 回滚

如果后续实现出问题，按影响面回滚：

1. 删除 mock fixture 目录。
2. 删除 mock-only mode / adapter。
3. 删除 Windows preview 脚本。
4. 删除对应测试和文档条目。
5. 保留 L2B 离线 HTML demo 作为安全退路；该退路不启动 Web、不连接真实后端、不调用 AI、不发送通知、不生成正式日报。

## 13. 本轮 Build / Judge 结论

本轮 Build 仅新增本文档并更新 `docs/CHANGELOG.md`。本轮没有：

- 新增 Web 启动脚本。
- 启动 `npm run dev` 或 `npm run preview`。
- 启动 FastAPI / uvicorn。
- 调用 `main.py`。
- 请求真实 API / provider / AI / 通知。
- 安装 npm 或 Python 依赖。
- 读取或打印 `.env`。
- 修改 `apps/dsa-web/src/**` 运行代码。
- 修改 `apps/dsa-web/package.json`。
- 修改 `apps/dsa-web/vite.config.ts`。
