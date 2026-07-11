# Mock API Adapter Scaffold

本目录仅用于 L2F mock API adapter 设计与后续 mock-only preview 的 non-runtime 准备。

## 边界

- 只读取 `apps/dsa-web/src/mocks/fixtures/*.json` 中的静态 fixture。
- 不接入 `main.tsx`、`App.tsx`、`src/api/**`、页面、store、组件或 context。
- 不改变当前 Web App 运行行为。
- 不请求真实 API、不调用后端、不读取环境变量、不包含真实 token / webhook / API key。

## 当前导出

- `loadMockFixture(name)`：按模块名读取本地 fixture。
- `getMockFixtureCatalog()`：返回模块到 fixture 文件的静态映射。
- `getMockResponse(moduleName, scenarioName)`：返回带模块名、场景名和 fixture 的 mock response 包装。

后续 L2G/L2H 如需接入 mock-only 模式，必须显式新增安全开关、网络阻断测试和本地绑定策略后再接入运行入口。

## 测试位置

Adapter 测试位于 `apps/dsa-web/tests/mocks/adapter/`，避免被正式 App build 的 `tsconfig.app.json` 作为 `src` 源码扫描。
