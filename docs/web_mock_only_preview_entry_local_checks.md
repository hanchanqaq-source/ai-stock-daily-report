# Web-P37 mock-only 页面预览入口与本地验收说明

## 1. 文档定位

本文档用于 Web-P37 阶段说明 mock-only 页面预览入口的安全识别方式、Windows 本地验收命令和人工本地预览边界。

当前页面只允许作为 mock-only 本地安全预览入口使用；本文档不授权真实日报接入，不改变页面视觉设计，不改变 TypeScript 运行逻辑，不新增真实 API、provider、AI / Agent、通知、账户、数据库或交易能力。

固定页面名称必须保持为“AI股票基金每日信息报告”。

固定项目名称必须保持为“股票基金质量分析系统”。

## 2. mock-only 页面入口识别

人工或 reviewer 识别 mock-only 页面入口时，只以以下路径为准：

| 类型 | 固定路径 | 说明 |
| --- | --- | --- |
| 页面入口 HTML | `apps/dsa-web/mock-only-preview/index.html` | 独立 mock-only 本地预览 HTML 入口。 |
| 入口脚本 | `apps/dsa-web/src/mocks/preview-entry/mockOnlyPreviewEntry.ts` | mock-only 页面入口脚本。 |

识别入口时必须确认它仍然只服务本地 mock-only 预览，不得把真实 Web App 入口、真实路由、真实 `apiClient`、真实后端服务或生产部署路径混入该页面。

## 3. 页面安全边界

当前页面只允许 mock-only 本地安全预览，并必须继续满足以下边界：

- 不读取环境配置文件。
- 不读取 `.env`、token、webhook、API 凭据。
- 不连接真实 API。
- 不启动后端。
- 不发送通知。
- 不接 provider。
- 不接 AI / Agent。
- 不接账户。
- 不接数据库。
- 不交易。
- 不新增真实日报 JSON 示例。
- 不自动启动 dev server。
- 不自动打开浏览器。

如果后续需求需要接入任一真实链路，不能作为 Web-P37 的延续处理，必须进入独立阶段重新设计 schema、授权、凭证管理、脱敏、日志、回滚和验收方案。

## 4. Windows 本地验收命令

在 Windows 本地验收 Web-P37 mock-only 页面预览入口说明时，允许执行以下命令。

### 4.1 必跑文档检查

```bash
git diff --check
```

### 4.2 mock-only preview 测试

```bash
cd apps/dsa-web && npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
```

### 4.3 Web 构建

```bash
cd apps/dsa-web && npm run build
```

### 4.4 Web lint

```bash
cd apps/dsa-web && npm run lint
```

如果只修改文档，可以不跑 `npm run test`、`npm run build` 和 `npm run lint`，但 PR 描述必须明确说明原因，并至少保留 `git diff --check` 作为本地检查证据。

如果改到 TypeScript、测试、`package.json`、入口 HTML 或入口脚本，则必须运行上述 mock-only preview 测试、Web build 和 Web lint。

## 5. 人工打开 mock-only 预览的唯一允许方式

如需人工打开前端 mock-only 预览，只允许绑定 `127.0.0.1`：

```bash
cd apps/dsa-web
npm run dev -- --host 127.0.0.1
```

该命令只用于人工本地预览说明。Codex / PR 自动验证不应自动启动 dev server。

人工预览仍必须遵守以下限制：

- 不允许使用 `0.0.0.0`。
- 不允许自动打开浏览器。
- 不允许启动后端。
- 不允许读取 `.env`、token、webhook、API 凭据。
- 不允许连接真实 API。
- 不允许接 provider、AI / Agent、通知、账户、数据库或交易链路。

## 6. PR 复核清单

提交或审查 Web-P37 相关 PR 时，至少确认：

- [ ] 页面入口仍为 `apps/dsa-web/mock-only-preview/index.html`。
- [ ] 入口脚本仍为 `apps/dsa-web/src/mocks/preview-entry/mockOnlyPreviewEntry.ts`。
- [ ] 页面固定名称仍为“AI股票基金每日信息报告”。
- [ ] 项目固定名称仍为“股票基金质量分析系统”。
- [ ] 当前页面仍只允许 mock-only 本地安全预览。
- [ ] 自动验证没有启动 dev server。
- [ ] 自动验证没有打开浏览器。
- [ ] 没有使用 `0.0.0.0` 作为人工预览绑定地址。
- [ ] 没有启动后端。
- [ ] 没有读取或打印 `.env`、token、webhook、API 凭据。
- [ ] 没有新增真实 API、provider、AI / Agent、通知、账户、数据库或交易接入。
- [ ] 如果只改文档，PR 描述说明未跑 npm test / build / lint 的原因。
