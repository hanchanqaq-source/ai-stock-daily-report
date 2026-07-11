# 前端 mock-only preview 网络穿透测试（L2K）

## 结论摘要

L2K 新增 mock-only preview 网络穿透测试，用于证明当前 `apps/dsa-web/src/mocks/preview/`、`service`、`adapter` 与 `safety` scaffold 仍然保持 non-runtime 边界。

本轮仅新增测试与文档，并更新 `docs/CHANGELOG.md`：

- 不接入真实 App。
- 不修改 `main.tsx` / `App.tsx`。
- 不修改真实路由。
- 不新增 Web 启动脚本。
- 不启动 Web dev / preview 服务。
- 不启动后端。
- 不连接真实后端或真实 provider。

## 测试目标

新增测试 `apps/dsa-web/tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts` 覆盖以下边界：

- 证明 preview 不使用 `fetch`。
- 证明 preview 不使用 `axios`。
- 证明 preview 不使用 `XMLHttpRequest`。
- 证明 preview 不使用 `EventSource` / `WebSocket`。
- 证明 preview 不读取 `import.meta.env`。
- 证明 preview 不读取 `window.location`。
- 证明 preview 不使用真实 API 路径或真实可请求 URL。
- 证明 preview / service / adapter 不导入真实 `src/api/**`、页面、store、组件、context 或 utils。
- 证明真实运行入口与运行目录没有导入 mock preview / service。
- 证明创建 `createMockOnlyPreviewModel({ mode: "mock", source: "local_preview_only" })` 时，即使全局网络函数或构造器被替换为抛错 sentinel，也不会触发网络调用。
- 证明 `production`、`preview` 或未显式 `mock` 的模式仍然会被拒绝，不会读取 fixture-backed preview 数据。
- 证明 preview model 的 metadata 来自 fixture metadata，且保持 `containsRealData=false`、`containsSecrets=false`、`safeForWindowsPreview=true`。

## safety blocklist marker 说明

`safety` 文件允许出现 `/api/v1`、`http://`、`https://`、`127.0.0.1`、`localhost`、`0.0.0.0` 等 blocklist marker。

这些 marker 只用于阻断测试与字符串判断，不是可请求地址，也不代表 preview/service/adapter 可以连接这些目标。L2K 测试会区分：

- `src/mocks/safety/mockOnlySafety.ts` 可以保存 blocklist marker。
- `src/mocks/preview/**`、`src/mocks/service/**`、`src/mocks/adapter/**` 不能出现这些真实可请求目标。
- `safety` 只做纯字符串归一化、marker 匹配和本地 fixture/module name 判断，不执行网络请求。

## 后续 L2L 前置条件

进入 L2L 前需满足：

1. L2K 网络穿透测试通过。
2. preview scaffold 仍然保持 non-runtime，不被真实入口导入。
3. 再设计 localhost-only Windows Web safe preview 脚本。
4. 后续脚本必须默认 mock-only，默认不连接真实后端。
5. 后续如需接入运行入口，必须先复核网络阻断、安全开关、fixture metadata、启动参数和文档说明。

## 验证建议

在 `apps/dsa-web/` 下执行：

```bash
npm run test -- tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
npm run lint -- tests/mocks/preview
npm run build
```

本轮不要求、也不应执行 `npm run dev`、`npm run preview` 或后端启动命令。
