# Web-P21 仪表盘摘要 mock-only 预览

## 目标

Web-P21 将“股票基金质量分析系统”的 mock-only 首页模块范围从静态清单升级为可进入的模块入口，并先实现第一个同页模块：**仪表盘摘要预览**。

页面固定显示名称为 **AI股票基金每日信息报告**。本功能只用于本地静态预览，不是正式日报、不接真实账户，也不是投资建议。

## 页面模块

当前 mock-only 页面包含：

- 安全边界：继续展示本地预览、脱敏 fixture、无真实网络与无通知发送等边界。
- Web-P20 设置与导入导出（模拟）：继续展示不读取配置、不导入文件、不导出备份的模拟说明。
- 模拟模块预览范围：展示模块入口和建设状态。
  - 仪表盘摘要：标记为“可预览”，提供“进入预览”锚点入口。
  - 持仓预览、历史报告预览、提醒预览、Agent 对话预览等未实现模块：标记为“后续建设”，不伪装为已完成。
- 仪表盘摘要预览：同页静态区域，展示一句话摘要、市场状态、模拟持仓总额、模拟当日涨跌、模拟仓位比例、风险等级、持仓结构、风险提示和今日动作建议示例。

## Fixture 数据来源

仪表盘摘要区域使用前端 mock-only scaffold 内的静态脱敏 fixture 模型：

- `apps/dsa-web/src/mocks/preview/mockOnlyPreviewModel.ts`
- `apps/dsa-web/src/mocks/fixtures/dashboard.json`

展示数据固定为演示用途，例如“震荡观察”“¥59,167.78”“+0.68%”“32.9%”等模拟值。页面显式标注：

- 模拟数据
- REDACTED FIXTURE DATA
- 非真实账户
- 非投资建议
- 不会发送通知

这些内容不得被解释为用户真实资产、真实行情、正式日报结论或交易建议。

## 安全边界

Web-P21 继续保持 mock-only 本地安全边界：

- 只渲染静态脱敏 fixture。
- 仅用于 `127.0.0.1` 本地安全预览脚本路径。
- 不启动后端。
- 不自动打开浏览器。
- 不接真实 API。
- 不接 provider。
- 不接通知。
- 不读取环境配置文件。
- 不读取 token、webhook 或 API key。
- 不发送日报。
- 不进行交易。
- 不新增 npm 依赖。
- 不使用 fetch、axios、XMLHttpRequest、WebSocket 或 EventSource。

## 本地验证方法

推荐执行与 mock-only preview 直接相关的轻量静态测试：

```bash
cd apps/dsa-web
npm run test -- tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts tests/mocks/preview/mockOnlyPreview.test.ts tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
```

如需确认 Windows safe preview 脚本边界未被破坏，可在仓库根目录执行：

```bash
python -m pytest tests/test_windows_localhost_preview_dry_run_script.py tests/test_windows_localhost_preview_one_click_script.py tests/test_windows_localhost_preview_start_script.py
```

## 非正式能力声明

- 本功能不是正式日报生成流程。
- 本功能不是投资建议。
- 本功能不接真实账户。
- 本功能不读取用户真实持仓。
- 本功能不接真实行情或 provider。
- 本功能不会发送通知、日报或 webhook。
