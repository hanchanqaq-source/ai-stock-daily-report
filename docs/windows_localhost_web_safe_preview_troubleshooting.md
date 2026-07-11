# Windows localhost-only safe preview 故障处理

本文记录 L2P Windows 本地真实运行 `localhost-only safe preview` 时遇到的常见问题、原因、处理方式和验证标准。目标是帮助 Windows 新手按“原因—处理—验证”的顺序排查，同时保持安全边界：不启动后端、不打开浏览器、不读取 `.env`、不接真实 API/provider/AI/通知/正式日报。

## 0. 安全边界先确认

在排查任何问题前，请先确认本预览只用于 mock-only 本地安全预览：

- 正确预览入口固定为 `http://127.0.0.1:5174/mock-only-preview/`。
- 服务只能绑定 `127.0.0.1:5174`，禁止 0.0.0.0。
- 禁止真实 API/provider/AI/通知/正式日报。
- 禁止读取或依赖 `.env`。
- 禁止为了修复依赖问题执行 `npm audit fix`。
- 禁止为了修复脚本问题执行 `npm approve-scripts`。
- 禁止为了修复 npm 版本问题执行 `npm install -g npm`。
- 快速禁令：禁止 npm audit fix；禁止 npm approve-scripts；禁止 npm install -g npm。

## 1. Node is not available

### 现象

运行 dry-run 或 start 脚本时出现 `Node is not available`，或者 `node` 不是内部或外部命令。

### 原因

未安装 Node，或 Node 已安装但当前 CMD / PowerShell 的 PATH 还没有生效。

### 处理

1. 安装 Node LTS。
2. 关闭当前 CMD / PowerShell。
3. 重新打开一个新的 CMD。
4. 在新 CMD 中验证 Node 和 npm：

```bat
node -v
npm -v
```

### 验证标准

- `node -v` 能打印版本号。
- `npm -v` 能打印版本号。
- 重新运行 safe preview dry-run 后，应能看到 `PASS Node version`，并继续进入后续 npm、node_modules、tests、build 检查。

## 2. node_modules is missing

### 现象

运行 dry-run 或 start 脚本时出现 `node_modules is missing`。

### 原因

新 clone 的仓库还没有安装前端依赖；`apps\dsa-web\node_modules` 不存在。

### 处理

在仓库根目录打开 CMD，执行：

```bat
cd apps\dsa-web
npm install
```

安装完成后回到仓库根目录，重新运行 safe preview dry-run 或 start 脚本。

### 注意事项

- 禁止 `npm audit fix`。
- 禁止 `npm approve-scripts`。
- 禁止 `npm install -g npm`。

### 验证标准

- `apps\dsa-web\node_modules` 存在。
- dry-run 不再停在 `node_modules is missing`。
- dry-run 能继续执行 mock-only tests 和 build。

## 3. dry-run 到 PASS Node version 后提前退出

### 现象

dry-run 打印 `PASS Node version` 后直接退出，没有继续打印 npm version、node_modules、tests、build，也没有打印 `DRY RUN PASSED` 或 `FAIL`。

### 原因

Windows bat 中如果裸调用 `npm`、`npm run` 或 `vite.cmd`，对应 `.cmd` 可能接管父 bat，导致父脚本提前退出。这是 L2P 真实运行中发现的问题。

### 处理

该问题已由 L2N-fix-2 修复：脚本中需要通过 `call npm ...` 方式调用 npm 相关命令，避免父 bat 被接管。

请先同步最新 main：

```bat
git pull --ff-only
```

如果你在本地维护分支，请先确认没有未提交改动或冲突，再按项目协作流程同步最新代码。

### 验证标准

修复后的 dry-run 不能只停在 `PASS Node version`。它必须继续打印：

- npm version 检查结果。
- node_modules 检查结果。
- mock-only tests 运行结果。
- build 运行结果。
- 最终 `DRY RUN PASSED` 或 `FAIL`。

## 4. 访问 / 或 /index.html 显示 MOCK_ONLY_PREVIEW_BLOCKED

### 现象

safe preview 服务启动后，访问以下地址看到 `MOCK_ONLY_PREVIEW_BLOCKED`：

```text
http://127.0.0.1:5174/
http://127.0.0.1:5174/index.html
```

### 原因

这是安全 guard 正常拦截。mock-only preview 不允许通过根路径或正式 App 入口进入，避免误触真实 Web App 路径。

### 处理

请改用正确入口：

```text
http://127.0.0.1:5174/mock-only-preview/
```

### 验证标准

- `/` 或 `/index.html` 显示 `MOCK_ONLY_PREVIEW_BLOCKED` 是正常行为。
- `http://127.0.0.1:5174/mock-only-preview/` 才是预期入口。

## 5. 访问 /api/v1/test 显示 MOCK_ONLY_PREVIEW_BLOCKED

### 现象

访问以下地址显示 `MOCK_ONLY_PREVIEW_BLOCKED`：

```text
http://127.0.0.1:5174/api/v1/test
```

### 原因

API 路径必须被阻断。safe preview 不启动后端，也不允许前端通过 `/api/v1/**` 连接真实 API。

### 处理

不需要修复。这是安全 guard 正常生效。

### 验证标准

访问 `/api/v1/test` 显示 `MOCK_ONLY_PREVIEW_BLOCKED` 是通过，不是错误。

## 6. 端口 5174 被占用

### 现象

start 脚本启动失败，提示端口 `5174` 被占用，或 Vite 无法绑定 `127.0.0.1:5174`。

### 原因

本机已有其他程序占用了 `127.0.0.1:5174`。

### 处理

1. 关闭占用 `5174` 的程序。
2. 回到运行脚本的 CMD。
3. 重新运行 start 脚本。

### 禁止事项

- 禁止 0.0.0.0。
- 禁止随意换端口绕过问题。
- 禁止启动后端来“补齐”API。

### 验证标准

- 服务成功绑定 `127.0.0.1:5174`。
- 正确入口仍然是 `http://127.0.0.1:5174/mock-only-preview/`。
- 不开放局域网或公网访问。

## 7. 如何停止服务

### 现象

safe preview 已经启动，需要停止本地服务。

### 处理

在运行 start 脚本的 CMD 窗口中按：

```text
Ctrl+C
```

如果 Windows 提示：

```text
Terminate batch job (Y/N)?
```

请输入：

```text
Y
```

### 验证标准

- CMD 返回命令输入状态，或窗口可安全关闭。
- 再访问 `http://127.0.0.1:5174/mock-only-preview/` 时不应继续由该脚本提供服务。

## 8. 排查顺序建议

1. 先确认 Node：`node -v` / `npm -v`。
2. 再确认依赖：`apps\dsa-web\node_modules`。
3. 再运行 dry-run，确认它不会停在 `PASS Node version`。
4. dry-run 通过后再运行 start。
5. 只打开 `http://127.0.0.1:5174/mock-only-preview/`。
6. 看到 `MOCK_ONLY_PREVIEW_BLOCKED` 时先确认自己访问的是不是 `/`、`/index.html` 或 `/api/v1/**`。
7. 使用完毕后按 `Ctrl+C`，必要时输入 `Y`。
