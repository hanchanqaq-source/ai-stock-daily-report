# Windows 本地 Demo 报告预览

`scripts\windows_local_demo_report_preview.bat` 是一个面向 Windows 本地用户的安全预览入口，用于打开一份离线 demo HTML 报告，帮助用户直观看到报告页面的大致展示效果并保留命令行窗口截图。

## 适用场景

适合在完成 L1 Windows 本地基础验证和 L2A Windows 本地安全预览后使用：

- 想先查看 demo 报告排版效果。
- 想确认本地浏览器能打开仓库内的离线 HTML 示例。
- 想为后续反馈或 PR 验收提供安全截图。

## 运行前提

建议先完成：

1. L1 Windows 本地基础验证。
2. L2A Windows 本地安全预览：`scripts\windows_local_safe_preview.bat`。

本脚本不要求 `.env`，不会安装依赖，也不会运行 pytest。

## 运行方式

请在项目根目录打开 Windows cmd，然后运行：

```bat
scripts\windows_local_demo_report_preview.bat
```

脚本会检查当前目录是否像项目根目录，并打开：

```text
docs\demo\windows_local_demo_report_preview.html
```

## 重要安全边界

这个入口打开的是离线 demo HTML，不是真实报告。

它不会：

- 连接真实数据源。
- 调用 AI 模型。
- 发送钉钉、飞书、Discord、邮件或其他通知。
- 写入正式日报。
- 修改 Git。
- 读取、打印或要求填写 `.env`。
- 安装 requirements。
- 运行 pytest。
- 启动 FastAPI、uvicorn 或本地 Web 服务。

页面中的股票、基金、金额、涨跌幅、风险提示和结论均为 demo/mock/redacted 示例，不代表真实账户、真实持仓或真实市场行情。

## 如果页面打不开

可以按顺序检查：

1. 是否在项目根目录运行脚本。
2. `docs\demo\windows_local_demo_report_preview.html` 是否存在。
3. 浏览器是否拦截了本地文件打开动作。
4. 是否可以手动双击或用浏览器打开该 HTML 文件。

命令行窗口会在最后 `pause`，方便保留错误信息或成功截图。

## 关于本地 Web 安全预览

本轮 L2B 不新增 Web 静态预览入口。

当前 `apps/dsa-web/` 是 Vite/React 前端，直接静态打开源码入口不能可靠代表完整 Web 预览，并且更完整的 Web 预览可能涉及构建产物、路由、API mock 或本地服务边界。本轮为了保持最小安全改动，只提供离线 demo 报告预览。

更完整的本地 Web 安全预览需要后续 L2C 单独设计。
