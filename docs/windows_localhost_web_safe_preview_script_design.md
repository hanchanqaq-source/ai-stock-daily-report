# Windows localhost-only Web safe preview script design

## 1. 本轮结论摘要

本轮只新增 Windows 本地 Web safe preview 脚本设计，用于描述后续一键预览脚本应如何在 Windows 上执行安全检查、保持 localhost-only、保持 mock-only，并在失败时停止。

本轮明确不做以下事情：

- 不新增真实 Web 启动脚本。
- 不新增 `.bat`、`.cmd`、`.ps1` 或 npm script。
- 不启动 Web。
- 不启动后端。
- 不接入真实 App、真实 route、真实 store、真实组件或真实 `apiClient`。
- 不读取真实 `.env`。
- 不使用真实 `VITE_API_URL`。
- 不请求真实网络。
- 不调用真实 `/api/v1/**`。
- 不触发 provider、AI、通知或正式日报生成。

结论：L2L 只沉淀脚本设计与安全边界，不提供可执行启动入口。真实 Windows 一键 safe preview 必须等后续 preview entry、localhost-only 启动命令和 mock-only 环境契约复核后再实现。

## 2. 当前状态

当前 mock-only 预览链路已有以下基础：

- L2I `mockService` 已存在，用于消费 fixture、adapter 和 safety scaffold。
- L2J preview scaffold 已存在，用于演示后续 mock-only preview model 如何消费 `mockService`。
- L2K 网络穿透测试已存在，用于静态验证 preview/service/adapter/safety 不引入真实网络调用、真实 URL 或运行时 App 导入。
- `apps/dsa-web/src/mocks/fixtures/` 已存在，用于保存 redacted fixture 数据。
- `apps/dsa-web/src/mocks/adapter/` 已存在，用于 mock API adapter scaffold。
- `apps/dsa-web/src/mocks/safety/` 已存在，用于 mock-only safety scaffold。
- `apps/dsa-web/src/mocks/service/` 已存在，用于 mock service scaffold。
- `apps/dsa-web/src/mocks/preview/` 已存在，用于 mock-only preview scaffold。

但当前仍然不能直接新增真实 Windows Web safe preview 启动脚本，原因是：

- mock-only preview 仍未接入独立 Web entry。
- 当前没有经过复核的 preview route。
- 当前没有经过复核的 localhost-only 启动命令。
- 当前 Vite dev/proxy 行为还不能直接用于用户一键启动。
- 当前 mock-only 环境变量命名和读取方式尚未在 L2M / L2N 实现前复核。

因此，本轮只做脚本设计。

## 3. 未来脚本目标

未来 Windows localhost-only Web safe preview 脚本应做到：

- Windows 一键检查，适合不了解 Node、Vite、npm 细节的用户。
- 默认 mock-only。
- 只能绑定 `127.0.0.1`。
- 禁止绑定 `0.0.0.0`、局域网 IP、公网 IP 或任何外网可访问 host。
- 先测试，后启动。
- 失败即停止，不继续执行后续步骤。
- 不连接真实后端。
- 不读取真实 `.env`。
- 不使用真实 `VITE_API_URL`。
- 不调用真实 `/api/v1/**`。
- 不触发 provider、AI、通知或正式日报生成。
- 不自动安装 Node、Python 或 npm 依赖。
- 不自动修改系统 PATH、Git 配置或系统环境。
- 不自动打开公网地址。
- 启动前必须显示清晰的安全横幅。

未来脚本可以设计使用类似以下变量表达 mock-only 意图，但在 L2M / L2N 实现前必须再次复核命名、注入方式和读取边界：

- `DSA_WEB_PREVIEW_MODE=mock`
- `DSA_WEB_PREVIEW_SOURCE=local_preview_only`

注意：本轮不实现 `VITE_DSA_WEB_PREVIEW_MODE`，不读取 `import.meta.env`，也不改变 Vite 或 Web runtime 行为。

## 4. Windows 友好原则

未来脚本应遵循以下 Windows 友好原则：

- 输出使用 ASCII 或稳定 UTF-8，避免中文乱码。
- 每一步都打印明确的 `PASS` / `FAIL`。
- 失败时暂停，避免终端窗口一闪而过。
- 错误消息用普通用户能理解的文字说明下一步应该做什么。
- 不要求用户理解 Node、Vite、npm 内部细节。
- 不自动修改系统 `PATH`。
- 不自动安装 Node。
- 不自动安装 Python。
- 不自动安装 npm package。
- 不自动修改 Git 配置。
- 不打印 `.env`、token、webhook、API key、账户、持仓或金额。

## 5. localhost-only 原则

未来脚本如需启动 Web，只能绑定：

- `127.0.0.1`

未来脚本必须拒绝以下 host：

- `0.0.0.0`
- 局域网 IP，例如 `192.168.*.*`、`10.*.*.*`、`172.16.*.*` 到 `172.31.*.*`
- 公网 IP
- 域名形式的外网可访问 host
- 任何由用户输入覆盖为非 `127.0.0.1` 的 host

建议未来启动前执行显式断言：

```text
IF requested_host != "127.0.0.1":
  PRINT "FAIL host must be 127.0.0.1"
  PAUSE
  EXIT 1
```

该断言必须在真实启动命令之前执行，并且启动命令本身也必须显式携带 `127.0.0.1`，不能依赖工具默认值。

## 6. mock-only 默认原则

未来脚本必须显式设置 mock-only 模式，并把 mock-only 状态打印到启动前横幅。建议横幅包含：

```text
MOCK ONLY
LOCAL PREVIEW ONLY
REDACTED FIXTURE DATA
NO REAL NETWORK
NO REAL ACCOUNT
NO OUTBOUND DELIVERY
```

mock-only 模式必须满足：

- 数据只来自 redacted fixture 或经过复核的本地 mock service。
- 不读取真实 `.env`。
- 不使用真实 `VITE_API_URL`。
- 不调用真实 `/api/v1/**`。
- 不连接 FastAPI、provider、AI、通知、正式日报或交易相关路径。
- 不允许 token、webhook、API key、真实账户、真实持仓或真实金额进入 preview。

未来如果需要将 mock-only 模式传递给 Web 层，必须先在 L2M / L2N 复核：

- 变量名是否不会与正式环境变量混淆。
- 是否不会读取或覆盖真实 `.env`。
- 是否不会影响正常 Web build、production build 或 CI。
- 是否有网络穿透测试覆盖。

## 7. 未来脚本伪流程

以下仅为伪流程，不是可执行脚本：

```text
Start

Print safety banner:
  MOCK ONLY
  LOCAL PREVIEW ONLY
  REDACTED FIXTURE DATA
  NO REAL NETWORK
  NO REAL ACCOUNT
  NO OUTBOUND DELIVERY

Step A: Check repo root
  Require marker files such as docs/CHANGELOG.md and apps/dsa-web/package.json
  If missing: FAIL, pause, exit
  Else: PASS

Step B: Check apps/dsa-web exists
  If missing: FAIL, pause, exit
  Else: PASS

Step C: Check apps/dsa-web/package.json exists
  If missing: FAIL, pause, exit
  Else: PASS

Step D: Check Node and npm are available
  Run version checks only
  If unavailable: FAIL with user-friendly install guidance, pause, exit
  Else: PASS

Step E: Check node_modules exists
  If missing: FAIL and ask user to run the existing install flow manually
  Do not run npm install automatically
  Else: PASS

Step F: Run mock-only network boundary tests
  If tests fail: FAIL, pause, exit
  Else: PASS

Step G: Run mock-only preview tests
  If tests fail: FAIL, pause, exit
  Else: PASS

Step H: Run npm run build
  If build fails: FAIL, pause, exit
  Else: PASS

Step I: Check whether real .env files exist
  If present: print that they will not be read, printed, or used
  Never print file contents
  Continue only if preview mode does not depend on real .env

Step J: Check mock-only preview entry exists
  If missing: FAIL with message:
    "Current stage is design-only. Preview entry is not implemented yet."
  Else: PASS

Step K: Validate host
  requested_host = "127.0.0.1"
  If requested_host is not exactly "127.0.0.1": FAIL, pause, exit
  Else: PASS

Step L: Start localhost-only preview only after all previous checks pass
  Start with explicit host 127.0.0.1
  Print local URL only, for example http://127.0.0.1:<port>/...
  Never print LAN or public URL

Stop on any failure
```

## 8. 建议启动前检查顺序

未来脚本建议按以下失败即停止顺序执行：

1. 检查是否在仓库根目录。
2. 检查 `apps/dsa-web` 是否存在。
3. 检查 `apps/dsa-web/package.json` 是否存在。
4. 检查 Node / npm 是否可用。
5. 检查 `apps/dsa-web/node_modules` 是否存在；如果不存在，只提示用户先执行已有安装流程，不自动安装。
6. 运行 mock-only 网络边界测试。
7. 运行 mock-only preview 测试。
8. 运行 `npm run build`。
9. 检查是否存在真实 `.env`，并明确不读取、不打印、不使用。
10. 检查 preview 入口是否已经存在；如果不存在，应停止并提示“当前只完成设计，尚未实现 preview entry”。
11. 只有所有检查通过，未来版本才允许启动 localhost-only preview。
12. 启动时必须明确显示：
    - `MOCK ONLY`
    - `LOCAL PREVIEW ONLY`
    - `REDACTED FIXTURE DATA`
    - `NO REAL NETWORK`
    - `NO REAL ACCOUNT`
    - `NO OUTBOUND DELIVERY`

## 9. 安全检查清单

未来脚本和配套测试必须覆盖以下安全检查：

- 禁止绑定 `0.0.0.0`。
- 禁止绑定局域网 IP。
- 禁止绑定公网 IP。
- 禁止打开公网地址。
- 禁止真实 API URL。
- 禁止真实 `/api/v1/**` 请求。
- 禁止 `VITE_API_URL` 穿透。
- 禁止读取真实 `.env`。
- 禁止打印 `.env` 内容。
- 禁止 provider 调用。
- 禁止 AI 调用。
- 禁止 notification / webhook / outbound delivery 调用。
- 禁止正式日报生成。
- 禁止 token、webhook、API key 出现在输出或 fixture 中。
- 禁止真实账户、真实持仓、真实金额进入 preview。
- 禁止自动安装依赖。
- 禁止自动安装 Node。
- 禁止自动安装 Python。
- 禁止自动修改系统环境。
- 禁止自动修改系统 PATH。
- 禁止自动修改 Git 配置。
- 禁止把 preview 接入真实 App、真实 route、真实 store、真实组件或真实 `apiClient`，除非后续阶段完成单独复核。

## 10. 当前阻塞点

当前不能直接做真实 Web safe preview 脚本，阻塞点如下：

- mock-only preview 仍未接入独立 Web entry。
- 当前没有经过复核的 preview route。
- 当前没有经过复核的 localhost-only 启动命令。
- 当前 Vite dev/proxy 行为还不能直接用于用户一键启动。
- 当前 mock-only 环境变量契约尚未复核。
- 当前还没有证明真实 Web 启动路径不会读取 `.env` 或使用 `VITE_API_URL`。

因此，L2L 只能输出设计文档，不应新增可执行脚本。

## 11. 后续拆分建议

建议后续继续拆分为：

- L2M：新增 mock-only preview entry 设计或最小独立入口，但仍不启动 Web。
- L2N：新增 Windows localhost-only safe preview 脚本，但默认只做 dry-run 检查，不真正启动。
- L2O：Windows 本地实际启动验证，验证 host 只绑定 `127.0.0.1` 且不发生真实网络穿透。
- L2P：补充用户侧操作文档和故障处理，面向 Windows 小白说明如何检查 Node/npm、依赖安装、失败信息和回滚方式。

每个阶段都应保持最小 diff，并在进入下一阶段前复核安全边界。

## 12. 回滚方案

如果 L2L 设计或后续脚本方向需要回滚：

- 删除 `docs/windows_localhost_web_safe_preview_script_design.md`。
- 删除后续新增的 Windows safe preview 脚本。
- 删除后续新增的 preview entry 或 route，如果它们尚未进入稳定路径。
- 保留 L2B 离线 HTML demo 作为安全退路。
- 保留既有 mock fixture、adapter、safety、service、preview scaffold，除非确认它们也需要一并回滚。

L2B 离线 HTML demo 仍是当前最安全的本地可视化退路，因为它不启动 Web、不连接后端、不请求真实网络、不读取真实 `.env`。
