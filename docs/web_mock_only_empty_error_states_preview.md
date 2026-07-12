# Web-P26 空状态与错误示例 mock-only

Web-P26 在 `mock-only-preview` 独立入口中新增 **空状态与错误示例** 静态区域，将“Mock 模块预览范围”里的“空状态与错误示例”升级为“可预览”，并提供同页锚点入口 `#mock-empty-error-states-preview`。

本功能服务 **股票基金质量分析系统** 的本地 Web mock-only 预览链路，日报 / 推送显示名称保持为 **AI股票基金每日信息报告**。

## 目标

- 展示未来真实产品可能出现的空状态、错误状态和降级状态 UI。
- 仅用于本地页面渲染检查和静态文案验收。
- 不接入 React Router，不新增 npm 依赖，不连接真实 API。

## 页面结构

空状态与错误示例位于现有 mock-only 安全预览页面内：

1. 模块范围区域中的“空状态与错误示例”卡片：
   - 状态：`可预览`。
   - 提供 `进入预览` 链接。
   - 链接指向 `#mock-empty-error-states-preview`。
2. 内容区域：
   - 标题：`空状态与错误示例`。
   - 副标题说明该区域只展示静态脱敏 fixture。
   - 安全标签：模拟数据、REDACTED FIXTURE DATA、非真实错误、非真实账户、非投资建议、不读取真实文件、不读取数据库、不读取 webhook、不读取 token、不读取 API key、不会调用模型、不会发送通知、不会交易。
   - 概览指标：模拟空状态数量、模拟错误示例数量、模拟降级状态数量、模拟数据来源、真实处理状态。
   - 空状态示例列表。
   - 错误示例列表。
   - 降级状态示例列表。
   - 风险提示区域。
   - 观察备注区域。

## fixture 数据说明

Web-P26 使用 TypeScript 内置静态脱敏 fixture，不读取真实文件、真实账户、数据库、云端配置、provider、通知渠道或模型服务。

fixture 分为：

- `summary`：展示模拟数量、模拟数据来源和真实处理状态。
- `emptyStates`：展示暂无持仓数据、暂无历史报告、暂无提醒规则、暂无 Agent 会话等空状态。
- `errorStates`：展示 mock-only provider 未连接、导入文件格式无效、通知目标未配置、报告生成失败等非真实错误示例。
- `degradedStates`：展示行情 provider 未启用、通知通道禁用、Agent 流式输出不可用等降级状态。
- `riskNotes`：说明安全边界和非正式监控定位。
- `actionNotes`：说明当前不会读取状态、保存日志或上传诊断信息。

## 安全边界

本功能必须保持 mock-only：

- 仅用于 127.0.0.1 本地安全预览链路。
- 不启动后端。
- 不自动打开浏览器。
- 不接真实 API。
- 不接 provider。
- 不接 OpenAI、DeepSeek、智谱或本地大模型。
- 不接真实 Agent。
- 不接通知。
- 不读取 `.env`。
- 不读取 token、webhook 或 API key。
- 不读取真实账户。
- 不读取真实基金平台。
- 不读取真实历史日报文件。
- 不读取数据库。
- 不读取用户本地文件。
- 不写入本地配置。
- 不写入 localStorage 或 sessionStorage。
- 不上传日志。
- 不发送日报。
- 不发送提醒。
- 不进行交易。
- 不保存真实错误日志。

## 非正式错误监控声明

本功能不是正式错误监控系统。页面中的空状态、错误状态和降级状态只用于 mock-only 页面演示和渲染测试，不代表真实运行状态，也不会采集、保存或上报任何真实错误日志。

## 投资与账户边界

本功能不是投资建议，不接真实账户，不读取真实持仓、真实基金平台、真实金额或真实交易信息，也不会执行任何交易。

## 本地验证方法

建议执行以下轻量验证：

```bash
cd apps/dsa-web
npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
npm run build
```

如需检查 Python 文档 / 脚本静态语法，可在仓库根目录执行：

```bash
python -m py_compile scripts/check_ai_assets.py
```

## 回滚方式

如需回滚 Web-P26：

1. 移除 `mockOnlyPreviewModel.ts` 中的空状态与错误示例 fixture 与模块可预览配置。
2. 移除 `mockOnlyPreviewTypes.ts` 中新增的空状态、错误状态和降级状态类型。
3. 移除 `mockOnlyPreviewEntry.ts` 中 `#mock-empty-error-states-preview` 渲染区块。
4. 移除对应 Vitest 断言。
5. 删除本文档并移除 `docs/CHANGELOG.md` 的 Web-P26 记录。
