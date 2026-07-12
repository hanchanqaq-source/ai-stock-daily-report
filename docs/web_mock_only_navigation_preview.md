# Web-P27 页面导航与返回顶部优化 mock-only

Web-P27 为 `mock-only-preview` 独立入口补充页面内导航和长页面返回入口，用于优化“股票基金质量分析系统”的本地预览体验。页面显示名称继续固定为 `AI股票基金每日信息报告`。

## 目标

- 在 mock-only 本地预览页面增加 `页面快速导航` / `本地预览导航` 区域。
- 为已经可预览的模块提供同页锚点跳转。
- 在主要区域底部提供 `返回顶部` 和 `返回模块列表`。
- 保持 mock-only、127.0.0.1 only 和不连接真实服务的安全边界。

## 页面导航结构

导航区域位于页面顶部信息之后、具体模块内容之前，包含：

- 安全边界确认
- 设置与导入导出
- 仪表盘摘要
- 持仓预览
- 历史报告预览
- 提醒预览
- Agent 对话预览
- 空状态与错误示例

所有导航项均为同页锚点，不使用 React Router，不引入新 npm 依赖，不引入浏览器滚动库，不打开新窗口，也不跳转外部 URL。

## 锚点列表

| 锚点 | 用途 |
| --- | --- |
| `#mock-preview-top` | 页面顶部稳定锚点 |
| `#mock-preview-modules` | 模块列表稳定锚点 |
| `#mock-safety-boundary` | 安全边界确认 |
| `#mock-settings-import-export` | 设置与导入导出 |
| `#mock-dashboard-summary-preview` | 仪表盘摘要 |
| `#mock-portfolio-preview` | 持仓预览 |
| `#mock-history-reports-preview` | 历史报告预览 |
| `#mock-alerts-preview` | 提醒预览 |
| `#mock-agent-chat-preview` | Agent 对话预览 |
| `#mock-empty-error-states-preview` | 空状态与错误示例 |

## 返回入口行为

每个主要预览区域底部都提供轻量返回入口：

- `返回顶部`：跳转到 `#mock-preview-top`。
- `返回模块列表`：跳转到 `#mock-preview-modules`。

这些入口只修改页面内锚点位置，不触发网络请求，不打开外部链接，不写入浏览器存储。

## 安全边界

Web-P27 仍然只用于 mock-only 本地静态预览：

- 不接真实 API。
- 不接后端。
- 不接 provider。
- 不接 OpenAI、DeepSeek、智谱、本地大模型或真实 Agent。
- 不读取账户、真实基金平台、真实历史日报文件、数据库或 `.env`。
- 不读取 token、webhook、API key 或任何密钥。
- 不读取用户本地文件。
- 不写入本地配置。
- 不写入 `localStorage` / `sessionStorage` / `indexedDB`。
- 不上传日志。
- 不发送日报或提醒。
- 不进行交易。

## 本地验证方法

在 `apps/dsa-web` 目录执行：

```bash
npm run test -- tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts
npm run test -- tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
npm run build
```

如需通过 Windows 安全预览脚本验证，仍使用既有 localhost-only safe preview 流程，并访问：

```text
http://127.0.0.1:5174/mock-only-preview/
```

该地址仅作为本地访问说明；本功能不会自动打开浏览器，也不会启动后端。
