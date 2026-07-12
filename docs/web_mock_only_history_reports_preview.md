# Web-P23 历史报告预览 mock-only

## 目标

Web-P23 在 `mock-only-preview` 独立入口中新增“历史报告预览”静态区域，将模块范围列表里的“历史报告预览”从“后续建设”升级为“可预览”，并提供同页锚点入口 `#mock-history-reports-preview`。

固定显示名称保持为：

- 项目名称：股票基金质量分析系统
- 日报 / 页面显示名称：AI股票基金每日信息报告

## 页面结构

历史报告预览位于现有 mock-only 安全预览页面内，不引入 React Router，不引入新依赖，也不接入正式 Web App 路由。

页面结构包括：

1. 模块范围区域中的“历史报告预览”卡片：
   - 状态显示为“可预览”。
   - 提供“进入预览”链接。
   - 链接跳转到同页 `#mock-history-reports-preview`。
2. 历史报告预览内容区域：
   - 标题：`历史报告预览`。
   - 副标题说明该区域只展示静态脱敏 fixture。
   - 标签包含 `模拟数据`、`REDACTED FIXTURE DATA`、`非真实日报`、`非真实账户`、`非投资建议`、`不会发送通知`、`不会交易`。
   - 展示历史报告概览、历史报告列表、报告详情示例、风险提示和今日观察备注。

## fixture 数据说明

历史报告预览使用 TypeScript 内置静态脱敏 fixture，不读取真实日报文件、数据库、账户、行情或通知记录。

fixture 模型包括：

- `MockOnlyHistoryReportsPreview`
- `MockOnlyHistoryReportItemPreview`
- `MockOnlyHistoryReportDetailPreview`

概览字段示例：

- 模拟报告数量：`3`
- 最新模拟报告：`2026-07-12`
- 模拟发送状态：`未发送`
- 模拟数据来源：`REDACTED FIXTURE DATA`

列表包含三条静态示例：

- `2026-07-12｜AI股票基金每日信息报告｜状态：本地预览｜市场：震荡观察｜动作：不调仓｜风险：中等｜发送：未发送`
- `2026-07-11｜AI股票基金每日信息报告｜状态：本地预览｜市场：分化观察｜动作：仅观察｜风险：中等｜发送：未发送`
- `2026-07-10｜AI股票基金每日信息报告｜状态：本地预览｜市场：偏强观察｜动作：不交易｜风险：中高｜发送：未发送`

详情示例固定为 `AI股票基金每日信息报告 mock-only 历史详情`，并展示市场概览、持仓观察、风险提示、动作建议四个静态区块。

## 安全边界

本功能必须保持 mock-only 和 localhost-only 安全预览语义：

- 不启动后端。
- 不自动打开浏览器。
- 不接真实 API。
- 不接 provider。
- 不接通知。
- 不读取环境配置文件。
- 不读取任何凭据、通知地址或接口密钥。
- 不发送日报。
- 不进行交易。
- 不读取真实账户。
- 不读取真实基金平台。
- 不读取真实历史日报文件。
- 不读取数据库。
- 不写入本地配置。
- 不写入浏览器持久化存储。

本功能不是正式日报，不是历史归档系统，不是投资建议，不接真实账户，不会发送通知，也不会交易。

## 本地验证方法

在 `apps/dsa-web/` 下执行相关轻量验证：

```bash
npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts
npm run build
```

如需补充 Windows safe preview 脚本静态回归，可在仓库根目录执行：

```bash
python -m pytest tests/test_windows_localhost_preview_one_click_script.py tests/test_windows_localhost_preview_dry_run_script.py tests/test_windows_localhost_preview_start_script.py
```

当前任务不新增 Python 运行时代码。

## 回滚说明

如需回滚 Web-P23，可移除历史报告预览 fixture、页面渲染区、相关测试断言和本说明文档，并将模块范围中的“历史报告预览”状态恢复为“后续建设”。
