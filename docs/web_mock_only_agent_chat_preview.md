# Web-P25 Agent 对话预览 mock-only

Web-P25 在 `mock-only-preview` 独立入口中新增 **Agent 对话预览** 静态区域，将“Mock 模块预览范围”里的“Agent 对话预览”从“后续建设”升级为“可预览”，并提供同页锚点入口 `#mock-agent-chat-preview`。

## 目标

- 继续服务“股票基金质量分析系统”的本地 Web mock-only 预览链路。
- 固定日报/推送显示名称为“AI股票基金每日信息报告”。
- 只展示 Agent / AI / 对话 / 流式片段相关的静态脱敏 fixture。
- 不接入真实 API、真实 AI、真实 Agent、真实 provider、真实模型或真实账户。

## 页面结构

Agent 对话预览位于现有 mock-only 安全预览页面内，不引入 React Router，不引入新 npm 依赖。

1. 模块范围区域中的“Agent 对话预览”卡片：
   - 状态：`可预览`。
   - 入口：`进入预览`。
   - 锚点：`#mock-agent-chat-preview`。
2. Agent 对话预览内容区域：
   - 标题：`Agent 对话预览`。
   - 副标题说明该区域仅展示静态脱敏 fixture。
   - 展示安全标签、概览指标、会话列表、消息示例、流式片段示例、错误示例、风险提示和今日观察备注。

## fixture 数据说明

Agent 对话预览使用 TypeScript 内置静态脱敏 fixture，不读取真实会话、真实账户、数据库、云端配置、模型服务或通知渠道。

主要数据结构包括：

- `MockOnlyAgentChatPreview`
- `MockOnlyAgentSessionPreview`
- `MockOnlyAgentMessagePreview`
- `MockOnlyAgentStreamChunkPreview`
- `MockOnlyAgentErrorPreview`

当前 fixture 展示：

- 模拟会话数量：2
- 模拟消息数量：5
- 模拟流式片段：4
- 模拟 Agent 状态：mock-only
- 模拟模型来源：REDACTED FIXTURE DATA
- 真实调用状态：未调用

示例会话包括“日报摘要检查”和“风险提示解释”。示例消息、流式片段和错误状态均仅用于页面渲染检查，不代表正式 Agent 系统能力。

## 安全边界

本功能必须保持 mock-only：

- 仅本地静态预览，不启动后端。
- 不自动打开浏览器。
- 不接真实 API。
- 不接 provider。
- 不接 OpenAI、DeepSeek、智谱、本地大模型或任何真实模型服务。
- 不接真实 Agent。
- 不接通知。
- 不读取 API key、token、webhook 或 `.env`。
- 不读取真实账户、真实基金平台、真实历史日报文件或数据库。
- 不写入本地配置。
- 不写入 `localStorage` / `sessionStorage` / `indexedDB`。
- 不发送日报或提醒。
- 不进行交易。
- 不保存真实对话。

## 本地验证方法

在 `apps/dsa-web/` 下执行：

```bash
npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts
npm run test -- tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts
npm run build
```

如需验证文档与轻量 Python 静态检查，可在仓库根目录执行：

```bash
python -m py_compile scripts/check_ai_assets.py
```

## 非正式能力声明

- 本功能不是正式 Agent 系统。
- 本功能不会调用真实 AI。
- 本功能不会读取 API key、token 或 `.env`。
- 本功能不是投资建议。
- 本功能不接真实账户。
- 本功能不会发送通知。
- 本功能不会交易。
- 本功能不会保存真实对话。
