# Mock-only preview 独立 Web entry 设计

## 1. 本轮结论摘要

- 本轮新增 mock-only preview 独立 Web entry 设计 / 最小入口。
- 该入口不接入真实 App，仅作为后续 L2N / L2O 检查与启动脚本的独立目标。
- 本轮不修改 `main.tsx` / `App.tsx`。
- 本轮不修改真实 route。
- 本轮不修改真实 apiClient。
- 本轮不新增启动脚本。
- 本轮不启动 Web。
- 本轮不启动后端。
- 本轮不请求真实网络。

## 2. 为什么需要独立入口

- 后续 Windows localhost-only safe preview 脚本需要一个可检查、可启动的独立入口。
- 不能直接使用真实 `apps/dsa-web/index.html`，否则容易复用正式 App 启动链路。
- 不能直接使用真实 `main.tsx` / `App.tsx`，否则会引入真实路由、页面、store、上下文和 API 访问路径。
- 不能使用现有 Vite dev/proxy 默认行为作为安全边界，因为默认入口与正式 Web App 绑定。
- 独立入口可以降低误连真实后端、误读 `.env`、误用 `VITE_API_URL` 和误触发正式功能的风险。

## 3. 独立入口边界

- `index.html` 只放在 `apps/dsa-web/mock-only-preview/`。
- TS entry 只放在 `apps/dsa-web/src/mocks/preview-entry/`。
- 入口只消费 `mockOnlyPreviewModel`。
- `mockOnlyPreviewModel` 再消费 `mockService`。
- 不接 `src/api/**`。
- 不接 pages / stores / components / contexts / utils。
- 不接真实 route。
- 不读取 `.env`。
- 不读取 `import.meta.env`。
- 不使用 `VITE_API_URL`。
- 不连接 `/api/v1/**`。

## 4. 当前仍不能做什么

- 不能一键启动。
- 不能启动 Web。
- 不能启动后端。
- 不能开放局域网。
- 不能读取 `.env`。
- 不能使用 `VITE_API_URL`。
- 不能请求 `/api/v1/**`。
- 不能推送通知。
- 不能生成正式日报。

## 5. 后续拆分

- L2N：新增 Windows localhost-only safe preview dry-run 脚本，只检查，不真正启动。
- L2O：新增 Windows localhost-only safe preview 真启动脚本，但只绑定 `127.0.0.1`。
- L2P：Windows 本地实际验证。
- L2Q：用户侧故障处理文档。

## 6. 回滚方案

- 删除 `apps/dsa-web/mock-only-preview/`。
- 删除 `apps/dsa-web/src/mocks/preview-entry/`。
- 删除 `apps/dsa-web/tests/mocks/preview-entry/`。
- 删除本设计文档。
- 删除 `docs/CHANGELOG.md` 对应条目。
