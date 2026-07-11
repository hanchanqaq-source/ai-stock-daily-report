# 前端 mock-only 安全开关与网络阻断测试设计（L2G）

## 1. 本轮结论摘要

- 本轮只做 mock-only 安全开关与网络阻断测试设计。
- 本轮新增 non-runtime safety scaffold，仅供测试和后续接入设计复用。
- 本轮不接入真实 App，不修改 `main.tsx`、`App.tsx`、`src/api/**`、页面、store、组件、context 或 utils。
- 本轮不新增 Web 启动脚本，不新增 preview/dev 脚本。
- 本轮不启动 Web / 后端，不连接真实后端，不请求真实 `/api/v1/**`，不调用真实行情、AI、通知或正式日报链路。

## 2. 安全开关目标

mock-only 模式必须默认关闭，只有调用方显式传入约定的 mock 模式值时，才允许读取 mock fixture 或 mock module。

当前 L2G 代码遵循以下边界：

- 不读取 `import.meta.env`。
- 不读取 `.env`。
- 不访问 `window.location`。
- 不从运行时入口自动推断模式。
- 只通过纯函数参数接收 `mode`。

后续 L2H / L2I 可以设计 `VITE_DSA_WEB_PREVIEW_MODE=mock`，但必须在安全开关、网络阻断、真实 axios / fetch 入口穿透测试都存在并通过后，再决定是否接入真实 Web preview。

## 3. 网络阻断目标

mock-only 网络阻断函数只做字符串检查，不发起请求。以下目标必须被识别为禁止：

- `/api/v1/**` 运行时 API 路径。
- `http://` / `https://` 外部目标。
- `127.0.0.1`、`localhost`、`0.0.0.0`。
- provider-like target。
- 真实后端 target。
- AI、通知、正式日报相关路径或标记。

其中 `127.0.0.1`、`localhost`、`0.0.0.0`、`/api/v1` 只作为 blocklist / test marker 出现在 safety scaffold 与测试中，不是可请求地址，也不表示本轮允许绑定端口或启动服务。

## 4. 允许目标

mock-only 模式下仅允许以下本地、静态、不可联网的目标形态：

- 本地静态 fixture 名称，例如 `dashboard`。
- 本地 fixture 文件名，例如 `dashboard.json`。
- mock module name。
- `local_preview_only`。
- `mock://`、`mock:`、`fixture:` 这类纯标记字符串。

允许目标不代表自动接入页面或 API client；L2G 仍只提供 non-runtime scaffold。

## 5. 后续 L2H / L2I 前置条件

进入后续 mock-only Web preview 接入前，应至少满足：

1. adapter 与 safety scaffold 都有测试覆盖。
2. mock-only 模式默认关闭。
3. mock-only 读取必须依赖显式 mock 模式。
4. 明确 127.0.0.1-only 绑定策略，并继续禁止 `0.0.0.0`。
5. 真实 axios / fetch 入口必须有穿透测试，证明 mock-only preview 不会穿透到真实后端或外部目标。
6. 再决定是否新增 Windows Web safe preview 脚本。
7. 如新增脚本，必须继续禁止真实 provider URL、真实 token / webhook / API key、真实账户、真实持仓和真实金额进入 fixture 或日志。

## 6. 本轮不变更的运行行为

L2G 不修改真实 App 入口、不修改 API client、不修改页面 / store / 组件，因此当前 Web App 运行行为不变。新增 safety scaffold 只有测试导入，未来如要接入运行时代码，需要单独评审、补充测试，并更新相关文档与 changelog。
