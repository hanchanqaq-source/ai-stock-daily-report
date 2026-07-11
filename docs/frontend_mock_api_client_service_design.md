# 前端 mockApiClient / mockService non-runtime 设计说明

## 1. 本轮结论摘要

- 本轮新增 `mockApiClient` / `mockService` non-runtime scaffold，用于后续 mock-only preview entry 的本地预览数据层准备。
- 本轮不接入真实 App，不修改 `src/main.tsx`、`src/App.tsx`、页面、store、组件、contexts、utils 或真实 API 调用链。
- 本轮不修改真实 `apiClient`，避免改变现有 Web 运行时请求契约。
- 本轮不新增 Web 启动脚本，也不新增 preview/dev/backend 启动入口。
- 本轮不启动 Web 或后端服务，不连接真实后端，不请求真实网络。

## 2. mockService 目标

- 统一消费 L2E 已建立的 `apps/dsa-web/src/mocks/fixtures/` 静态 fixture。
- 复用 L2F 已建立的 `apps/dsa-web/src/mocks/adapter/` fixture adapter。
- 复用 L2G 已建立的 `apps/dsa-web/src/mocks/safety/` mock-only safety scaffold。
- 为后续 L2J 独立 mock-only preview entry 做准备。
- 在进入任何真实运行入口前，用单元测试固定 mock-only 默认关闭、显式启用和网络阻断边界。

## 3. mockService 不做什么

- 不请求真实 API。
- 不调用后端。
- 不调用 AI。
- 不发通知。
- 不生成正式日报。
- 不读取 `.env`。
- 不读取 `import.meta.env`。
- 不接真实 provider。
- 不保存数据到浏览器存储。
- 不创建轮询、定时器、WebSocket 或 EventSource。

## 4. 推荐模块

后续 mock-only preview entry 可优先围绕以下模块组织页面数据：

- `auth`
- `dashboard`
- `analysis`
- `history`
- `portfolio`
- `alerts`
- `systemConfig`
- `agent`
- `alphasift`
- `usage`
- `backtest`
- `decisionSignals`
- `stocksImport`
- `errors`
- `emptyStates`

## 5. 后续 L2J 前置条件

- `mockService` 必须保持单元测试覆盖，尤其是显式 mock mode、未知模块和网络阻断边界。
- mock-only 默认关闭；调用方必须显式传入 `mode: 'mock'` 和 `source: 'local_preview_only'`。
- `mockService` 不能被真实 App 导入，不能进入当前 `main.tsx` / `App.tsx` / runtime API / 页面 / store / 组件链路。
- preview entry 必须独立，不复用真实 Web 启动入口作为隐式 mock 开关。
- 后续可以在设计中使用 `VITE_DSA_WEB_PREVIEW_MODE=mock` 作为独立 preview entry 的外部开关，但本轮代码不读取环境变量。
- 继续禁止真实网络穿透；任何目标地址、后端路径、provider 或通知目标都必须被 safety 层阻断或在测试中证明不存在。

## 6. 回滚方式

如需回滚本轮改动，可删除 `apps/dsa-web/src/mocks/service/`、`apps/dsa-web/tests/mocks/service/`、本文档，并移除 `docs/CHANGELOG.md` 中对应 `[Unreleased]` 条目。由于本轮不接入真实运行代码，回滚不需要迁移用户数据或调整后端配置。
