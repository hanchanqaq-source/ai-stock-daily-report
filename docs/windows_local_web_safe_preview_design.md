# Windows 本地 Web 安全预览设计（L2C）

## 1. 结论摘要

本轮仅新增设计文档，不新增 `scripts/windows_local_web_safe_preview.bat`。

原因是当前 `apps/dsa-web/` 已经是完整 Vite + React 前端应用，但默认开发服务配置为 `0.0.0.0`，并且通过 `/api` 代理到 `127.0.0.1:8000` 后端。前端运行时也会在认证、首页、聊天、组合、告警、设置、历史报告、策略筛选等页面直接调用 `/api/v1/**` 接口。仓库内存在测试 mock 与局部脱敏工具，但未发现可直接用于整站启动的 mock-only / demo-only / redacted-only 运行模式。

因此，在没有先补齐 Web mock 数据层和 localhost-only 启动约束前，不应新增一键 Web 启动脚本，避免用户误以为当前 Web 开发服务已经满足“默认 mock、不会请求真实 API、不会绑定公网地址”的安全预览要求。

## 2. 当前 `apps/dsa-web/` 结构观察

- `apps/dsa-web/package.json` 存在，项目名为 `dsa-web`，脚本包含 `dev`、`build`、`lint`、`test`、`test:smoke` 和 `preview`。
- `apps/dsa-web/src/` 存在，入口为 `src/main.tsx`，应用路由入口为 `src/App.tsx`。
- 技术栈为 Vite + React + TypeScript：`package.json` 使用 `vite`、`@vitejs/plugin-react`、`react`、`react-dom`、`typescript`、`vitest`、`playwright` 等依赖。
- API 封装集中在 `src/api/*.ts`，共用 `src/api/index.ts` 中的 axios client。
- `src/utils/constants.ts` 读取 `import.meta.env.VITE_API_URL`，未配置时默认使用同源 API base URL。
- `public/stocks.index.json` 是前端静态索引资源，不等同于整站 mock API 数据层。

## 3. 是否适合直接做本地 Web 安全预览

当前不适合直接做一键本地 Web 安全预览。

主要阻断点：

1. `vite.config.ts` 中开发服务默认 `host: '0.0.0.0'`，不满足“不得绑定公网地址、不得监听 `0.0.0.0`”的安全边界。
2. `vite.config.ts` 将 `/api` 代理到 `http://127.0.0.1:8000`，这意味着一旦本机后端存在，前端页面会连接真实后端 API。
3. `App.tsx` 默认挂载 `AuthProvider`，认证状态加载会触发 `/api/v1/auth/status`，不是纯静态离线页面。
4. 多个页面和 store 会调用 `analysisApi`、`historyApi`、`agentApi`、`portfolioApi`、`alertsApi`、`systemConfigApi`、`alphasiftApi` 等真实 API 封装。
5. 未发现整站级 mock-only 开关、mock service worker、静态 fixture 路由或可脱离 API 的演示入口。

## 4. mock / demo / redacted 数据机制观察

当前存在以下与 mock / demo / redacted 相关的内容，但它们不足以支撑整站安全预览：

- 单元测试中大量使用 `vi.mock(...)` 和 `mockResolvedValue(...)`，属于测试级 mock，不会在 `npm run dev` 的真实浏览器预览中自动生效。
- 设置页错误边界和相关测试包含敏感字段脱敏逻辑，例如 token、webhook、API key 的错误文案脱敏；这是 UI 安全能力，不是数据源 mock 层。
- `docs/demo/windows_local_demo_report_preview.html` 是 L2B 的离线 HTML demo，可直接用 `file://` 打开，适合作为当前阶段的安全展示入口。
- 未发现 `apps/dsa-web` 内有整站可用的 demo API fixture、redacted API fixture 或 mock-only runtime 配置。

## 5. 真实 API / 真实数据请求风险

当前 Web 前端存在明确的真实 API 请求路径：

- axios client 默认使用 `API_BASE_URL`，未设置 `VITE_API_URL` 时会请求同源 `/api/v1/**`。
- Vite dev server 将 `/api` 代理到 `http://127.0.0.1:8000`。
- API 模块覆盖认证、分析任务、历史报告、聊天 agent、组合账户、告警、系统配置、Token 用量、选股等接口。
- `agentApi` 中存在 `fetch` 流式聊天请求路径。
- `analysisApi` 中存在任务 stream URL 生成路径。
- `systemConfigApi` 中存在 LLM 测试、通知测试、模型发现、配置导入导出等接口调用封装。

这些请求是否进一步触发真实行情、真实账户、真实 token、AI 模型或通知，取决于后端配置和接口行为。仅从当前前端结构看，不能证明 `npm run dev` 是 mock-only，也不能证明它不会触达真实后端能力。

## 6. Node / npm / 本地服务需求

- 需要 Node.js 与 npm。`package.json` 声明 Node 版本范围为 `>=20.19.0 <27`，npm 版本为 `>=10`。
- 首次运行通常需要在 `apps/dsa-web` 下安装 npm 依赖；本轮不应自动执行 `npm install` 或 `npm ci`。
- 完整 Web 应用预览通常需要 `npm run dev` 或 `npm run build` 后配合静态服务 / `npm run preview`。
- 当前 `npm run dev` 是 Vite 开发服务，不是纯 `file://` 离线打开模式。
- 由于路由使用 BrowserRouter、页面依赖 API 状态，构建产物也不等同于完全离线可用的 mock demo。

## 7. 是否会读取 `.env`

前端代码通过 Vite 的 `import.meta.env.VITE_API_URL` 读取构建 / 开发环境变量。Vite 默认会加载项目环境文件（如 `.env`、`.env.local`、模式相关 env 文件）中的 `VITE_*` 变量。

本轮没有读取、打印或要求填写 `.env`。但正因为 Vite 运行时可能加载 env，当前不应提供“安全预览”脚本来直接启动 Web，除非后续先建立明确的 mock-only mode，并保证脚本不会读取或暴露真实配置。

## 8. 是否需要后端服务

当前完整 Web 应用默认需要后端 API 才能正常完成认证状态、首页数据、历史报告、设置、告警、组合账户等页面的数据加载。Playwright 配置也会启动 `main.py --webui-only --host 127.0.0.1 --port 8000` 作为测试后端，并用 `npm run dev -- --host 127.0.0.1 --port 4173` 启动前端测试服务。

这说明现有 Web 的常规联调路径依赖本地后端服务，不满足“本轮不要做真实 Web 服务”的目标。

## 9. 推荐方案

### A. 暂不做 Web 启动，只保留 L2B 离线 HTML demo

推荐作为当前 L2C 结论。

优点：

- 已有 `docs/demo/windows_local_demo_report_preview.html` 可通过 `file://` 打开。
- 不需要 Node/npm。
- 不启动 Vite、FastAPI、uvicorn 或 `main.py`。
- 不读取 `.env`。
- 不请求真实行情、账户、token、AI 模型或通知渠道。
- 不绑定端口，不存在 `0.0.0.0` 暴露风险。

缺点：

- 只能展示离线报告 demo，不能预览完整 Web 应用路由和交互。

### B. 做 Web mock-only preview

暂不推荐立即实施，适合作为后续 L2D。

前置条件：

- 新增显式 mock-only mode，例如 `VITE_DSA_WEB_PREVIEW_MODE=mock`。
- mock mode 下禁止创建真实 axios client 请求，或使用 mock adapter / MSW / fixture service 截获所有 `/api/v1/**`。
- mock mode 下默认展示 redacted fixture，不包含真实账户、真实价格、真实 token、真实 webhook 或真实 API key。
- Vite 启动必须显式绑定 `127.0.0.1`，不能沿用默认 `0.0.0.0`。
- Windows 脚本只能检查 Node/npm 和依赖状态，不自动安装依赖，不读取 `.env`，不调用后端。

### C. 后续单独做 Web mock 数据层

推荐作为 L2D 或 L3 前置工程。

建议范围：

- 在 `apps/dsa-web/src/mocks/` 或等价目录建立前端 mock 数据层。
- 为认证状态、首页、历史报告、组合账户、告警、设置、聊天、筛选等关键 API 提供 redacted fixture。
- 增加测试证明 mock-only mode 下不会发出真实网络请求。
- 增加文档说明 mock 数据字段边界和禁止项。
- 在 mock 数据层完成后，再新增 `scripts/windows_local_web_safe_preview.bat`。

## 10. 推荐选择

本轮推荐选择 **方案 A：暂不做 Web 启动，只保留 L2B 离线 HTML demo**。

理由：

1. 用户明确要求本轮优先“设计文档 + 安全边界确认”。
2. 当前 Web 开发服务默认绑定 `0.0.0.0`，与本地安全预览原则冲突。
3. 当前 Web 存在大量真实 API 调用封装，未确认整站 mock-only。
4. Vite 可能加载 `VITE_*` env，当前不能宣称“不读取 `.env`”。
5. L2B 离线 HTML 已能满足“安全展示”的保守目标。

## 11. 安全边界

当前 L2C 设计结论要求：

- 不新增 Web 启动脚本。
- 不启动 `npm run dev`、`npm run preview`、FastAPI、uvicorn 或 `main.py`。
- 不调用真实后端。
- 不请求真实行情、真实账户、真实 token、AI 模型或通知渠道。
- 不读取、打印或要求填写 `.env`。
- 不绑定任何端口，更不会绑定 `0.0.0.0`。
- 不生成正式日报。
- 不删除文件，不修改 Git 配置，不推送远端。

## 12. 后续 L2D / L3 前置条件

进入 Web mock-only preview 前，建议先完成：

1. 定义 mock-only mode 的环境变量或构建模式，且默认不触发真实 API。
2. 建立前端 redacted fixture 数据层，覆盖认证、首页、历史、组合、告警、设置、聊天、筛选等关键页面。
3. 增加网络阻断测试，证明 mock-only preview 不会访问 `/api/v1/**` 之外的真实服务，也不会把 `/api` 代理到后端。
4. 调整或覆盖本地预览启动参数，确保只绑定 `127.0.0.1`。
5. 明确 Windows 脚本只做检查和 mock-only 启动提示，不自动安装依赖、不读取 `.env`、不调用后端。
6. 文档中列出所有仍未覆盖的页面和 mock 数据缺口。
