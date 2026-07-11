# 前端 mock-only preview entry 设计（L2J）

## 1. 本轮结论摘要

本轮新增 mock-only preview entry 设计与 non-runtime preview scaffold，用于说明后续 mock-only Web preview 如何消费 L2I `mockService`。

本轮明确保持以下边界：

- 不接入真实 App。
- 不修改 `apps/dsa-web/src/main.tsx`。
- 不修改 `apps/dsa-web/src/App.tsx`。
- 不修改真实路由。
- 不修改真实 `apiClient` 或 `src/api/**`。
- 不新增 Web 启动脚本。
- 不启动 Web。
- 不启动后端。

因此，本轮完成后不会改变现有 Web App 的运行行为，也不会形成可直接交付给用户的一键 Web 预览入口。

## 2. preview 目标

本轮 preview scaffold 的目标是：

1. 使用 L2I `mockService`，并显式传入 `{ mode: "mock", source: "local_preview_only" }`。
2. 展示未来 mock-only 页面建议包含的区域和数据消费方式。
3. 证明 preview 数据只来自 redacted fixture，不来自真实 API、真实后端或真实 provider。
4. 为后续 L2K / L2L 的安全验证和本地预览入口设计做准备。

当前 scaffold 只允许由测试 import，或由后续经过 review 的 mock-only preview 入口 import；它不被真实 `main.tsx`、`App.tsx`、路由、页面、store、组件、context、utils 或 `src/api/**` 导入。

## 3. preview 不做什么

本轮 preview 不做以下事情：

- 不请求真实 API。
- 不调用后端。
- 不调用 AI。
- 不发通知。
- 不生成正式日报。
- 不读取 `.env`。
- 不读取 `import.meta.env`。
- 不接真实 provider。
- 不接真实账户。
- 不读取或保存真实 Token、Webhook、API Key、账户、持仓、金额或成本数据。
- 不新增 Web 启动脚本。
- 不启动 Web dev server 或 preview server。

## 4. 推荐最小 preview 区域

后续 mock-only Web preview 页面建议至少包含以下区域：

1. 安全横幅：明确展示 `MOCK ONLY`、`LOCAL PREVIEW ONLY`、`REDACTED FIXTURE DATA`、`NO REAL NETWORK`、`NO REAL ACCOUNT`、`NO NOTIFICATION`。
2. Dashboard 摘要：展示 dashboard fixture 中的摘要卡片、市场状态和 watchlist 示例。
3. Portfolio 摘要：展示 portfolio fixture 中的账户、持仓、风险和交易形态示例。
4. History reports 摘要：展示 history fixture 中的报告列表、报告详情和空状态示例。
5. Alerts 摘要：展示 alerts fixture 中的规则、触发记录和通知形态示例，但不触发真实通知。
6. Agent chat 摘要：展示 agent fixture 中的会话、消息、stream chunk 和错误形态示例，但不调用真实 AI。
7. Empty/error 示例：展示 empty states fixture 和各模块内置错误形态，便于后续页面验证空态、错误态和降级展示。

## 5. 后续拆分

- L2K：新增 mock-only preview 网络穿透测试，继续证明 preview scaffold 无真实网络路径、无真实 API import、无运行时代码接入。
- L2L：新增 localhost-only Windows Web safe preview 脚本设计，但仍需保持显式安全开关、mock-only 数据源和网络阻断约束。
- L2M：Windows 本地 mock-only Web 实际验证，在 L2K / L2L 安全设计通过后再执行，不在本轮启动 Web 或后端。

## 6. 风险与回滚

主要风险是后续误将 preview scaffold 接入真实 App、真实路由或真实 API client，导致 mock-only preview 与生产运行路径混淆。当前通过目录隔离、文档边界和测试扫描降低该风险。

回滚方式：删除 `apps/dsa-web/src/mocks/preview/`、`apps/dsa-web/tests/mocks/preview/`、本文档，并移除 `docs/CHANGELOG.md` 中对应的 `[Unreleased]` 条目即可。
