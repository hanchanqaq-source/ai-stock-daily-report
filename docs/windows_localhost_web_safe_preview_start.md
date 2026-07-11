# Windows localhost-only safe preview 真启动脚本

## 1. 本轮结论摘要

本轮新增 Windows localhost-only safe preview 真启动脚本，用于启动 mock-only preview 的本地 Web 预览服务。

该脚本的边界是：

- 只绑定 `127.0.0.1`。
- 不启动后端。
- 不打开浏览器。
- 不读取 `.env`。
- 不请求真实 API。
- 不使用真实 App。
- 使用 mock-only preview 专用 Vite 配置，不修改正式 Web 配置。

## 2. 用户如何运行

在仓库根目录运行：

```bat
scripts\windows_localhost_web_safe_preview_start.bat
```

## 3. 用户如何打开

脚本不会自动打开浏览器。dry-run 通过并启动服务后，用户需要手动打开：

```text
http://127.0.0.1:5174/mock-only-preview/
```

## 4. 用户如何停止

在运行脚本的终端中按 `Ctrl+C` 停止服务。

## 5. 启动前会做什么

真启动脚本会先运行 L2N dry-run：

- 检查无 `.env`。
- 检查 Node/npm/node_modules。
- 运行 mock-only tests。
- 运行 build。
- 只有 dry-run 通过后才启动 mock-only preview Web 服务。

如果 dry-run 失败，脚本会立即停止，不会启动 Web。

## 6. 安全边界

- 仅绑定 `127.0.0.1`。
- 不开放局域网。
- 不开放公网。
- 不打开浏览器。
- 不启动后端。
- 不接真实 API。
- 不用 `VITE_API_URL`。
- 不用 `/api/v1`。
- 专用 Vite config 不使用 proxy。
- guard 会阻止真实 App、api、pages、stores、components、contexts、utils 等路径。
- 误打开根路径时，guard 返回 `MOCK_ONLY_PREVIEW_BLOCKED`。

## 7. 失败处理

- dry-run 失败：不启动 Web，先按 dry-run 输出修复问题。
- 端口被占用：启动停止，需要关闭占用 `5174` 的程序后重试。
- node_modules 不存在：先在本地手动安装依赖，再重新运行脚本；脚本不会自动安装。
- 发现 `.env`：先移除或隔离，不能带真实环境运行。
- 误打开根路径：会被 guard 阻止，不会进入真实 App。

## 8. 后续步骤

- L2P：Windows 本地实际运行验证。
- L2Q：用户故障处理文档。
- L2R：再考虑是否增加更友好的本地入口，但仍不接生产。
