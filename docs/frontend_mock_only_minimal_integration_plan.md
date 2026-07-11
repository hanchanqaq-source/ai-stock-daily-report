# 前端 mock-only 最小接入方案设计（L2H）

## 1. 当前状态

L2H 的结论是：本轮只做设计，不接入真实 App，不启动 Web，不读取真实 `.env`，不请求真实网络。

当前前端 mock-only 相关资产已经分三层存在，但仍然是 non-runtime：

- L2E fixture：`apps/dsa-web/src/mocks/fixtures/` 已提供脱敏 JSON 样例和 fixture 目录说明，作为后续 mock-only 的唯一数据来源。
- L2F adapter：`apps/dsa-web/src/mocks/adapter/` 已提供 mock API adapter 设计与 scaffold，当前未被真实页面、store、组件或 `apiClient` 引用。
- L2G safety scaffold：`apps/dsa-web/src/mocks/safety/` 与 `apps/dsa-web/tests/mocks/safety/` 已提供安全开关和网络阻断测试 scaffold，当前未接入 Vite、React 入口或真实请求链路。

因此，当前仓库状态仍满足：

- mock fixture、adapter、safety 已存在。
- mock-only 尚未接入真实 App、`apiClient`、页面、store、组件或 context。
- 本轮继续保持不接入真实 App。
- 后续必须分阶段接入，不允许一步到位启动 Web 或直接替换真实运行路径。

## 2. 推荐接入原则

后续所有 mock-only 接入都应遵循以下原则：

- mock-only 默认关闭。
- 只有显式 mock-only 模式才启用。
- mock-only 不读取真实 `.env`。
- mock-only 不调用真实后端。
- mock-only 不请求 `/api/v1/**`。
- mock-only 不调用 provider、AI、通知、正式日报生成链路。
- mock-only 不保存真实账户、真实持仓、真实金额、真实 token、真实 webhook 或真实 API key。
- 所有 mock 数据必须来自 `apps/dsa-web/src/mocks/fixtures/`。
- mock-only 网络阻断必须覆盖 axios、fetch 和 agent streaming，不得只覆盖单一请求库。
- mock-only 接入点应尽量与真实 App 解耦，优先通过显式 preview entry 或 mock-only route 使用。

## 3. 接入点分析

| 接入点 | 可能做法 | 主要风险 | L2H 结论 |
| --- | --- | --- | --- |
| `src/api/index.ts` 的 `apiClient` | 在真实 axios client 内根据开关切换 mock adapter | `apiClient` 是真实运行核心，任何条件分支都可能影响正式请求、认证、错误处理、拦截器和 base URL 语义 | 不推荐直接修改 |
| `src/api/*.ts` | 在每个 API 模块内改为按模式选择真实请求或 mock 返回 | 改动面大，容易遗漏模块；同一语义可能在 axios、fetch、streaming 间表现不一致 | 不作为第一步 |
| `AuthContext` | 在认证上下文内注入 mock 用户或 mock session | 认证状态是全局高风险入口，可能污染正式登录、Cookie、session 和权限判断 | 不推荐直接修改 |
| `App.tsx` | 在根组件内根据开关切换 mock 页面或 provider | 根组件影响全部路由和 provider，容易让 mock-only 分支进入正式 build/runtime | 不推荐直接修改 |
| `main.tsx` | 在 React 入口内根据开关切换真实 App 或 mock App | 入口层风险最高，可能改变正式启动、StrictMode、全局样式、provider 装配和错误边界 | 不推荐直接修改 |
| pages | 在页面级逐步替换数据来源 | 可控但容易形成页面级散落分支，初期覆盖不完整 | 后续可在独立 preview route 中显式使用 |
| stores | 在 store 层切换 mock 数据 | store 状态通常跨页面共享，可能污染真实缓存、轮询状态和用户状态 | 不作为第一步 |
| agent streaming fetch | 为 agent 流式接口提供 mock stream | streaming 通常绕过 axios，仅改 `apiClient` 无法覆盖；若遗漏会穿透真实后端 | 必须单独设计和测试 |
| Vite dev / preview | 通过独立 entry、route 或脚本启动安全预览 | 会涉及端口、host、env、proxy 和浏览器真实网络行为 | 先设计，不在 L2H 新增脚本或启动 Web |

## 4. 三种接入方案比较

### 方案 A：`apiClient` 层切换

优点：

- 集中。
- 所有 axios API 容易统一拦截。
- 对已有 `src/api/*.ts` 调用方侵入较小。

风险：

- `apiClient` 是真实运行核心，改动风险较高。
- 真实拦截器、认证 header、错误处理、超时、base URL 和 retry 语义都可能被 mock 分支污染。
- `agentApi` 等模块可能包含 fetch 或 streaming，不能只靠 axios 覆盖。
- 如果开关判断失误，mock-only 可能影响正式 App，或正式请求可能穿透 mock-only。

结论：不推荐作为最小安全接入第一步。

### 方案 B：新增 `mockApiClient` / `mockService`，不替换真实 `apiClient`

优点：

- 不动真实 `apiClient`。
- 后续可按页面、模块或 preview route 显式接入。
- mock-only 数据来源、错误形态和延迟策略可以独立收敛。
- 回滚简单，删除新增 mock service 即可恢复。

风险：

- 需要逐步替换调用点。
- 初期不能覆盖全部页面。
- 如果没有统一测试清单，可能出现页面接入顺序不一致。

结论：推荐作为 L2I 的最小实现方向，但 L2H 不实现。

### 方案 C：mock-only preview entry / 独立入口

优点：

- 与真实 App 隔离。
- 适合后续安全预览。
- 不影响正式 App、真实路由、认证状态和正式 API client。
- 可以强制只消费 `mockApiClient` / `mockService` 和 fixture。

风险：

- 需要额外入口、route 或最小 preview 页面设计。
- 后续仍需测试 build、preview、localhost-only、host 绑定和网络阻断。
- 如果直接新增启动脚本，可能过早引入端口、host、`.env` 和代理风险。

结论：推荐作为 L2J 的方向，但 L2H 不实现。

## 5. 最小安全接入推荐

推荐采用方案 B + C 的组合，并按阶段拆分：

1. L2I：新增 `mockApiClient` / `mockService`，只消费 `apps/dsa-web/src/mocks/fixtures/`，但不接真实 App。
2. L2J：新增 mock-only preview entry 设计或最小 preview 页面，并显式使用 `mockApiClient` / `mockService`，但仍不启动 Web。
3. L2K：增加 axios、fetch、streaming 的网络穿透测试，证明 mock-only 不会请求真实后端。
4. L2L：新增 localhost-only Windows Web safe preview 脚本，且默认不读取真实 `.env`、不接真实后端。
5. L2M：在 Windows 本地执行实际安全验证。

L2H 明确不做以下事情：

- 不直接改真实 `apiClient`。
- 不直接改 `main.tsx` / `App.tsx`。
- 不修改 `src/api/**`、pages、stores、components、contexts 或 utils。
- 不新增 Web 启动脚本。
- 不启动 Web。
- 不启动后端。
- 不读取 `.env`。
- 不发起真实网络请求。

## 6. 优先 mock 的 API 模块

后续进入 L2I / L2J 时，优先 mock 的模块应按页面预览价值和安全风险排序：

1. 认证与当前用户状态：只提供脱敏 mock user/session，不能复用真实 token、Cookie 或持久化登录态。
2. Dashboard / portfolio / history reports：优先覆盖安全预览首页、资产卡片和历史报告列表。
3. Analysis tasks / stocks import：提供任务状态、空状态、错误状态和导入反馈的 mock 数据。
4. Alerts / decision signals / usage / system config：覆盖通知、信号、用量、配置展示，但不得接真实通知或真实配置。
5. Agent chat / streaming：必须提供独立 mock stream，不能依赖 axios adapter，也不能请求真实 agent 后端。
6. Backtest / AlphaSift 等较重模块：可在核心安全链路稳定后逐步补齐。

所有模块都必须从 fixture catalog 或 fixture 文件读取数据，不能临时写死真实响应、真实 URL、真实账户或真实 provider 结果。

## 7. mock-only 默认关闭设计

后续实现必须让 mock-only 默认关闭：

- 没有显式 mock-only 入口时，真实 App 完全不加载 mock service。
- 没有显式 mock-only 开关时，mock adapter 不应拦截任何请求。
- 不使用真实 `.env` 中的 API URL、token、webhook 或 provider 配置来决定 mock-only 行为。
- 不把 mock-only 开关混入正式业务配置、真实 API base URL 或认证状态。
- preview entry 或 preview route 应在命名、文档和测试中明确标注 `mock-only`。

## 8. 网络阻断设计

后续实现必须证明以下目标不会穿透真实网络：

- axios 不请求真实 `/api/v1/**`。
- fetch 不请求真实 `/api/v1/**`。
- agent streaming 不请求真实后端。
- `VITE_API_URL` 不影响 mock-only 数据来源。
- `127.0.0.1`、`localhost`、`0.0.0.0` 不被 mock-only 误用为真实后端。
- `http` / `https` 外部目标在 mock-only 中被阻断。
- mock-only 不访问 provider、AI、通知、正式日报或自动交易相关链路。

建议测试分层：

1. 单元测试：对 mock safety helper 输入 `/api/v1/**`、localhost、内网地址、外部 URL，断言阻断。
2. adapter 测试：对 axios 风格请求断言只返回 fixture，不触发真实 adapter。
3. fetch 测试：在 mock-only 环境中替换或监控 `globalThis.fetch`，断言任何真实 URL 都失败。
4. streaming 测试：为 agent streaming 提供 mock stream，并断言不会打开真实 EventSource、fetch stream 或 WebSocket。
5. 配置污染测试：设置 `VITE_API_URL` 后仍断言 mock-only 数据只来自 fixtures。

## 9. 回滚方案

若后续接入出现问题，应按改动层级回滚：

- 删除本设计文档或后续 mock integration 文档。
- 删除未来新增的 `mockApiClient` / `mockService`。
- 删除未来新增的 mock-only preview entry 或 preview route。
- 删除未来新增的 Web safe preview 脚本。
- 保留 L2B 离线 HTML demo 作为安全退路，继续用于不启动 Web、不接真实后端的展示验证。

只要真实 `apiClient`、`main.tsx`、`App.tsx` 和正式页面/store 未被修改，回滚成本就保持最低。

## 10. L2I / L2J / L2K / L2L / L2M 拆分建议

- L2I：新增 `mockApiClient` / `mockService`，定义 fixture 到 API 响应的最小映射；不接真实 App，不新增启动脚本。
- L2J：新增 mock-only preview entry 设计或最小 preview 页面；只显式消费 mock service，不启动 Web。
- L2K：补充网络穿透测试，覆盖 axios、fetch、agent streaming、`VITE_API_URL`、localhost 和外部 URL。
- L2L：新增 localhost-only Windows Web safe preview 脚本；必须默认 mock-only、默认不读真实 `.env`、默认不连接真实后端。
- L2M：执行 Windows 本地实际验证，记录启动方式、浏览器访问范围、网络阻断证据、未验证项和回滚方式。

## 11. Judge 清单

L2H 完成后应满足：

- 没有新增 Web 启动脚本。
- 没有修改 `apiClient`。
- 没有修改 `apps/dsa-web/src/api/**`。
- 没有修改 `apps/dsa-web/src/main.tsx` 或 `apps/dsa-web/src/App.tsx`。
- 没有修改 pages / stores / components / contexts / utils。
- 没有修改 `apps/dsa-web/package.json`。
- 没有修改 `apps/dsa-web/vite.config.ts`。
- 没有启动 Web。
- 没有启动后端。
- 没有读取 `.env`。
- 没有真实网络请求。
- 只新增文档或说明 README，并更新 `docs/CHANGELOG.md`。
- `docs/CHANGELOG.md` 的 `[Unreleased]` 继续保持扁平条目格式。
