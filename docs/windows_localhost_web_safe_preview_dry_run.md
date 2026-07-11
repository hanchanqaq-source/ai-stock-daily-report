# Windows localhost-only safe preview dry-run

## 本轮结论摘要

本轮新增 `scripts\windows_localhost_web_safe_preview_dry_run.bat`，用于在 Windows 本地检查 mock-only preview 的安全启动前置条件。

该脚本只做 dry-run 检查；任意检查、测试或 build 失败时会立即进入统一失败出口并返回 exit code 1，只有完整成功路径才会打印 `DRY RUN PASSED`：

- 不真正启动 Web。
- 不启动后端。
- 不打开浏览器。
- 不读取 `.env` 内容。
- 不连接真实网络。
- 不触发 provider、AI、通知或正式日报流程。

## 用户如何运行

在仓库根目录双击运行：

```bat
scripts\windows_localhost_web_safe_preview_dry_run.bat
```

也可以在命令提示符中运行同一命令。脚本会从自身所在的 `scripts\` 目录自动定位仓库根目录。

## 脚本会检查什么

脚本按顺序检查：

1. 仓库根目录标记是否存在：`docs\CHANGELOG.md` 与 `apps\dsa-web\package.json`。
2. mock-only preview entry 是否存在：
   - `apps\dsa-web\mock-only-preview\index.html`
   - `apps\dsa-web\src\mocks\preview-entry\mockOnlyPreviewEntry.ts`
3. 仓库根目录与 `apps\dsa-web\` 下是否存在 `.env` 或 `.env.*` 文件。
4. dry-run host policy 是否固定为 `127.0.0.1`。
5. Node 是否可用。
6. npm 是否可用。
7. `apps\dsa-web\node_modules` 是否存在。
8. mock-only preview entry 测试是否通过。
9. mock-only preview network-boundary 测试是否通过。
10. mock-only preview model 测试是否通过。
11. `npm run build` 是否通过。

## 如果失败怎么办

脚本失败时会打印 `FAIL ...`、提示 dry-run 已在启动任何 Web / 后端 / 浏览器前停止，并以 exit code 1 退出；CI 环境不会 pause，普通双击环境下会 pause 便于查看错误。常见失败与处理方式：

- 不在正确仓库：确认脚本路径仍为 `scripts\windows_localhost_web_safe_preview_dry_run.bat`，且仓库内存在 `docs\CHANGELOG.md` 与 `apps\dsa-web\package.json`。
- 没装 Node：手动安装 Node 后重新运行脚本。
- 没装 npm：手动安装 npm 后重新运行脚本。
- `node_modules` 不存在：在确认本地环境安全后，手动安装前端依赖，再重新运行脚本；dry-run 脚本不会自动安装依赖。
- 存在 `.env` 或 `.env.*`：先移除或临时移走这些文件；脚本只检查文件是否存在，不读取、不打印内容。
- 测试失败：先查看对应 mock-only preview 测试输出，修复后重新运行。
- build 失败：先查看 `npm run build` 输出，修复后重新运行。

## 安全边界

该 dry-run 脚本的安全边界为：

- 只执行 dry-run 检查。
- 不启动 Web。
- 不启动后端。
- 不打开浏览器。
- 不请求真实 API。
- 不读取 `.env` 内容。
- 不使用 `VITE_API_URL`。
- 不连接 `/api/v1/**`。
- 不触发 provider、AI、通知或正式日报。
- 不自动执行依赖安装。
- 任意失败立即停止后续测试与 build，不打印 `DRY RUN PASSED`。
- CI 环境失败时不 pause；普通双击环境失败时可以 pause。

## 后续步骤

建议后续继续按阶段推进：

- L2O：Windows localhost-only safe preview 真启动脚本。
- L2P：Windows 本地实际验证。
- L2Q：用户故障处理文档。
