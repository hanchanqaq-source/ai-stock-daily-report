# Web-P24 提醒预览 mock-only

Web-P24 在 `mock-only-preview` 独立入口中新增“提醒预览”静态区域，将模块范围列表里的“提醒预览”从“后续建设”升级为“可预览”，并提供同页锚点入口 `#mock-alerts-preview`。

本功能属于“股票基金质量分析系统”的 Web 静态预览能力；日报 / 推送显示名称保持为“AI股票基金每日信息报告”。

## 目标

- 提供提醒 / 通知概念的本地页面渲染检查样例。
- 只展示静态脱敏 fixture，不接真实通知能力。
- 明确展示“模拟数据”“非真实通知”“不会发送通知”“不会交易”等安全标签。
- 保持 Web-P20、Web-P21、Web-P22、Web-P23 的 mock-only 边界不变。

## 页面结构

提醒预览位于现有 mock-only 安全预览页面内，不引入 React Router，不引入新 npm 依赖，也不接入正式 Web App 路由。

1. 模块范围区域中的“提醒预览”卡片：
   - 状态：`可预览`。
   - 入口：`进入预览`。
   - 锚点：`#mock-alerts-preview`。
2. 提醒预览内容区域：
   - 标题：`提醒预览`。
   - 副标题说明本区域仅展示静态脱敏 fixture，不读取真实通知配置，不连接真实 provider，不发送任何通知。
   - 展示提醒概览、提醒规则列表、触发记录、发送状态、风险提示和今日观察备注。

## fixture 数据说明

提醒预览使用 TypeScript 内置静态脱敏 fixture，不读取真实提醒规则、真实通知配置、数据库、云端配置或通知渠道。

fixture 结构包含：

- `summary`：模拟提醒规则数量、模拟触发记录、模拟发送状态、模拟通知通道和模拟数据来源。
- `rules`：提醒规则名称、范围、条件、级别、状态和说明。
- `triggers`：模拟触发时间、规则名称、状态、观测值、展示结果和说明。
- `deliveries`：模拟通道、状态、脱敏目标、发送时间和展示说明。
- `riskNotes`：mock-only 风险提示。
- `actionNotes`：今日观察备注。

示例数据全部为 `REDACTED FIXTURE DATA` 或脱敏标签，不包含真实账号、通知目标、webhook、token、API key、邮箱、手机号、企业微信、Telegram、PushPlus 或其他真实推送配置。

## 安全边界

Web-P24 必须保持以下边界：

- mock-only。
- 127.0.0.1 only。
- 不启动后端。
- 不自动打开浏览器。
- 不接真实 API。
- 不接 provider。
- 不接通知。
- 不读取 `.env`。
- 不读取 token、webhook、API key。
- 不读取邮箱、手机号、企业微信、Telegram、PushPlus 等真实通知目标。
- 不发送日报。
- 不发送提醒。
- 不进行交易。
- 不读取真实账户。
- 不读取真实基金平台。
- 不读取真实历史日报文件。
- 不读取数据库。
- 不写入本地配置。
- 不写入 localStorage/sessionStorage。

本功能不是正式通知系统，不会调用 webhook、邮件、短信、企业微信、Telegram、PushPlus 或其他推送服务。

本功能不是投资建议，不接真实账户，不会交易。

## 本地验证方法

建议执行以下轻量验证：

```bash
cd apps/dsa-web
npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts
npm run test -- tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts
npm run build
cd ../..
python -m py_compile scripts/check_ai_assets.py
```

如需额外核对安全边界，可搜索 mock-only 入口和模型源码，确认没有 `fetch`、`axios`、`XMLHttpRequest`、`WebSocket`、`EventSource`、`localStorage`、`sessionStorage`、`indexedDB`、Notification API、Service Worker 或 `navigator.sendBeacon`。

## 回滚方式

如需回滚 Web-P24，可移除提醒预览 fixture、页面渲染区、相关测试断言和本说明文档，并将模块范围中的“提醒预览”状态恢复为“后续建设”。
