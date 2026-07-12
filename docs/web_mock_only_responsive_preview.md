# Web-P29 mock-only 移动端 / 窄屏预览优化

## 目标

Web-P29 面向“股票基金质量分析系统”的 mock-only 本地预览页，优化 `AI股票基金每日信息报告` 在移动端、窄屏和平板尺寸下的布局可读性。本功能仅调整 mock-only 页面展示，不接入真实业务链路。

## 支持的视口范围

- 桌面宽屏：`>= 1024px`，保持多列卡片与宽屏信息密度。
- 平板 / 窄屏：约 `768px`，通过 `max-width: 900px` 断点收窄容器 padding，并让概览、导航与指标卡片按可用宽度自动换行。
- 手机窄屏：约 `390px - 430px`，通过 `max-width: 640px` 与 `max-width: 420px` 断点将主要 grid 调整为单列，提升按钮点击高度并减少卡片 padding。

## 响应式布局策略

- 主容器在窄屏下使用更小的左右 padding，避免内容贴边或产生横向滚动。
- 多列 grid 在手机宽度下统一变为单列，避免卡片被压缩。
- 文本、标签 chips、卡片、列表项和按钮加入 `min-width: 0`、`overflow-wrap`、`word-break` 等防溢出规则。
- 安全标签、导航说明、仪表盘标签继续使用可换行 flex 布局，不强制单行展示。
- 返回顶部 / 返回模块列表在手机宽度下变为全宽按钮，并保留适合触控的高度。

## 页面总览区域窄屏行为

“页面总览 / mock-only 模块完成度”在窄屏下会自动调整指标卡片列数：

- 平板宽度下按可用空间换行。
- 手机宽度下变为单列。
- 安全状态摘要与完成度信息不强制横向排列，长文本可换行显示。

## 页面快速导航窄屏行为

“页面快速导航”保持同页锚点，不打开新窗口，不跳转外部地址：

- 平板宽度下导航项按卡片自动换行。
- 手机宽度下导航项变为单列。
- 导航链接在手机宽度下使用全宽触控按钮，避免文字重叠和点击区域过小。

## 模块卡片窄屏行为

以下 mock-only 模块在窄屏下均保持卡片式单列阅读：

- 安全边界确认
- 设置与导入导出
- 仪表盘摘要
- 持仓预览
- 历史报告预览
- 提醒预览
- Agent 对话预览
- 空状态与错误示例

列表型内容继续使用可换行卡片展示，不使用表格撑开页面。

## 本地验证方法

建议在 `apps/dsa-web` 下执行：

```bash
npm run test -- tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
npm run lint
npm run build
```

如需要人工查看，可使用已有 Windows localhost-only safe preview 流程在本机访问 `http://127.0.0.1:5174/mock-only-preview/`，并分别检查桌面、平板与手机宽度。

## 安全边界

Web-P29 保持 mock-only 与 `127.0.0.1 only` 边界：

- 不接真实 API。
- 不接后端。
- 不读取账户、文件、数据库或 `.env`。
- 不读取 token、webhook 或 API key。
- 不发送通知。
- 不进行交易。
- 不调用 OpenAI、DeepSeek、智谱、本地大模型或任何模型 provider。
- 不连接真实 Agent。
- 不写入 localStorage / sessionStorage。

## Playwright 移动端截图说明

本轮不要求 Playwright 截图测试。若当前环境缺少 Playwright 浏览器二进制，可不安装浏览器依赖，改用静态测试、Vitest、lint 与 build 覆盖响应式 CSS 和 mock-only 安全边界。
