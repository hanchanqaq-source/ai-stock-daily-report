# Web-P28 页面总览 / 模块完成度状态栏 mock-only

## 1. 目标

Web-P28 为 `mock-only-preview` 独立页面新增顶部“页面总览 / mock-only 模块完成度”状态栏，用于在进入长页面前快速确认：

- 当前模式为 `mock-only 本地预览`。
- 项目名称固定为 **股票基金质量分析系统**。
- 页面显示名称固定为 **AI股票基金每日信息报告**。
- 模块完成度由现有 mock preview model 的 `sections` 状态派生。
- 页面仍只展示静态脱敏 fixture，不连接真实服务。

## 2. 页面总览区域结构

页面总览区域位于页面标题之后、Web-P27 “页面快速导航”之前，保持如下顺序：

1. 顶部锚点 `#mock-preview-top`。
2. 页面标题与本地安全预览副标题。
3. 页面总览 / mock-only 模块完成度。
4. Web-P27 页面快速导航。
5. 安全边界确认。
6. 模块列表 `#mock-preview-modules`。
7. 各 mock-only 预览区域。

总览区域展示：

- 当前模式。
- 项目名称。
- 页面显示名称。
- 总模块数量。
- 可预览模块数量。
- 后续建设模块数量。
- 完成度。
- 数据来源。
- 网络、通知、交易、Agent 与安全边界状态。
- 当前页面用途说明。

## 3. 模块完成度统计规则

模块完成度不维护第二份静态模块清单，而是从 mock preview model 的 `sections` 统计：

- `可预览模块数量` = `sections` 中 `status === '可预览'` 的数量。
- `后续建设模块数量` = `sections` 中 `status === '后续建设'` 的数量。
- `总模块数量` = 可预览模块数量 + 后续建设模块数量。
- `完成度` = `Math.round(可预览模块数量 / 总模块数量 * 100)`；总模块为 0 时显示 0。

因此，当后续模块从“后续建设”升级为“可预览”时，只需要更新 `sections` 中对应状态，总览统计会同步变化。

## 4. 安全状态字段

总览区域显式展示以下安全状态：

| 字段 | 值 |
| --- | --- |
| 运行范围 | `127.0.0.1 only` |
| 数据来源 | 静态脱敏 fixture / `REDACTED FIXTURE DATA` |
| 真实网络 | 未连接 |
| 真实账户 | 未读取 |
| 真实通知 | 未发送 |
| 真实交易 | 禁用 |
| 模型调用 | 未调用 |

页面说明文案强调：本页面仅用于 Windows 本地 mock-only 渲染检查，帮助验证页面结构、模块入口、空状态和错误状态，不代表正式日报、真实账户分析或投资建议。

## 5. 与 Web-P27 页面导航的关系

Web-P28 不替换 Web-P27 的导航能力：

- `页面快速导航` 继续保留。
- `返回顶部` 继续指向 `#mock-preview-top`。
- `返回模块列表` 继续指向 `#mock-preview-modules`。
- 页面内跳转仍全部使用同页锚点，不打开新窗口，不跳转外部地址。

## 6. 本地验证方法

在 `apps/dsa-web` 下执行 mock-only 相关轻量验证：

```bash
npm run test -- tests/mocks/preview/mockOnlyPreview.test.ts tests/mocks/preview-entry/mockOnlyPreviewEntry.test.ts tests/mocks/preview/mockOnlyPreviewNetworkBoundary.test.ts
npm run build
```

如需检查 Windows safe preview / one-click 脚本边界，可在仓库根目录补充运行相关 Python 静态测试：

```bash
python -m pytest tests/test_windows_localhost_preview_one_click_script.py
```

## 7. 非接入边界

Web-P28 只优化 mock-only 页面顶部总览展示，不改变真实运行链路：

- 不接真实 API。
- 不接后端。
- 不接 provider。
- 不读取账户、文件、数据库或 `.env`。
- 不读取 Token、Webhook 或 API Key。
- 不发送通知。
- 不进行交易。
- 不调用模型。
- 不写入本地配置、浏览器存储或用户本地文件。
