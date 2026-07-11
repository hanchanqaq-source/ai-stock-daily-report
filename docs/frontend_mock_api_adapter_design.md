# 前端 mock API adapter 设计（L2F）

## 1. 本轮结论摘要

- 本轮只做 mock API adapter 设计与最小 non-runtime scaffold。
- 本轮不接入真实 App，不修改 `main.tsx`、`App.tsx`、`src/api/**`、页面、store、组件、context 或 utils。
- 本轮不新增 Web 启动脚本，不启动 Web，不连接真实后端。
- 新增 scaffold 仅位于 `apps/dsa-web/src/mocks/adapter/`，用于后续 L2G/L2H 显式 mock-only 模式的准备。

## 2. Adapter 目标

- 统一读取 L2E 已沉淀的 `apps/dsa-web/src/mocks/fixtures/*.json` fixture。
- 为后续 mock-only Web preview 提供稳定的模块映射与读取入口。
- 默认阻断真实网络：adapter 不包含网络客户端、不拼接真实 API 地址、不读取环境变量。
- 保持 non-runtime：当前真实 Web App 不导入该 adapter，因此不会改变现有运行行为。

## 3. Adapter 不做什么

- 不请求真实 API。
- 不调用后端。
- 不调用 AI、OpenAI、LiteLLM 或本地模型。
- 不发送 Discord、Webhook 或其他通知。
- 不生成正式日报。
- 不读取 `.env` 或 `import.meta.env`。
- 不读取真实账户、真实持仓、真实金额、真实 token、真实 webhook 或 API key。
- 不新增 Windows Web 启动脚本、mock-only Web 启动脚本、dev/preview 脚本或后端启动脚本。

## 4. 建议模块映射

| 模块名 | Fixture 文件 |
| --- | --- |
| `auth` | `auth.json` |
| `dashboard` | `dashboard.json` |
| `analysis` | `analysis_tasks.json` |
| `history` | `history_reports.json` |
| `portfolio` | `portfolio.json` |
| `alerts` | `alerts.json` |
| `systemConfig` | `system_config.json` |
| `agent` | `agent_chat.json` |
| `alphasift` | `alphasift.json` |
| `usage` | `usage.json` |
| `backtest` | `backtest.json` |
| `decisionSignals` | `decision_signals.json` |
| `stocksImport` | `stocks_import.json` |
| `errors` | `errors.json` |
| `emptyStates` | `empty_states.json` |

## 5. 最小 scaffold 形态

`apps/dsa-web/src/mocks/adapter/mockApiAdapter.ts` 暂只建议暴露以下 mock-only 函数：

- `loadMockFixture(name)`：按模块名返回本地 fixture。
- `getMockFixtureCatalog()`：返回模块名、fixture 文件名和支持场景列表。
- `getMockResponse(moduleName, scenarioName)`：返回 `{ moduleName, scenarioName, fixture }` 包装，供后续 mock-only 模式统一消费。

当前 scaffold 的约束：

- 只通过静态 JSON import 读取 `apps/dsa-web/src/mocks/fixtures/*.json`。
- 不使用 `fetch`、`axios` 或 `XMLHttpRequest`。
- 不访问 `window.location` 拼接真实 API。
- 不读取 `import.meta.env.VITE_API_URL`、`.env` 或任何环境变量。
- 不包含真实 URL、本地端口绑定、真实 provider URL、token、webhook 或 API key。
- 不导入 `src/api/**`，也不被 `src/api/**` 导入。
- 不被 App、页面、store、组件、context 或 utils 导入。

## 6. 后续 L2G 前置条件

进入 L2G 前需要先完成并验证：

- 明确 mock-only env 开关，且默认关闭。
- 明确 127.0.0.1-only 绑定策略，避免暴露到公网网卡。
- 增加网络阻断测试，证明 mock-only 模式不会穿透真实后端。
- 证明 `axios` / `fetch` 不会在 mock-only 模式下请求真实后端。
- 再决定是否新增 Windows Web safe preview 脚本。
- 明确 mock-only 模式的用户提示、风险提示和退出方式。

## 7. 验证建议

L2F 的验证重点是静态边界，而不是启动 Web：

- 检查新增文件仅位于 `docs/`、`docs/CHANGELOG.md` 和 `apps/dsa-web/src/mocks/adapter/`。
- 检查 adapter 源码不包含网络、环境变量和 secret 访问关键字。
- 检查 `src/api/**`、`main.tsx`、`App.tsx`、页面、store、组件、context、utils 没有导入 mock adapter。
- 运行 mock adapter 单元测试或等价静态检查。

## 8. 回滚方式

如需回滚 L2F，可删除：

- `docs/frontend_mock_api_adapter_design.md`
- `apps/dsa-web/src/mocks/adapter/`

并移除 `docs/CHANGELOG.md` 中对应 `[Unreleased]` 条目。该回滚不会影响真实 App 运行入口，因为本轮没有接入真实运行代码。
