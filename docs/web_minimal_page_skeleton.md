# Web-P1 本地 Web 最小页面骨架说明

## 1. 设计目标

Web-P1 只做本地 Web 最小静态页面骨架，用原生 HTML / CSS / JS 提供可打开的预览页面。当前阶段不引入 React、Vue、Next.js、Vite、外部 CDN、外部字体或真实 provider 接入。

页面目标是验证左侧导航、顶部栏、主内容卡片、账户概览、股票 ETF、场外基金净值、个人观察点位、风险提醒和数据说明等基础布局是否成立。

## 2. 启动方式

可以直接在本地打开：

```text
web/static/index.html
```

由于部分浏览器在 `file://` 下会限制 `fetch` 读取本地 JSON，推荐使用简单本地静态服务器预览：

```bash
python -m http.server 8000 -d web/static
```

然后访问本地页面。当前测试不要求真正启动服务器。

## 3. 数据来源

当前页面只读取 `web/static/demo_final_page_payload.json`。该文件是 demo 数据，只用于本地静态页面预览。

未来正式数据必须来自 P5-T 最终安全闸门输出的 `final_page_payload`。Web 页面只消费 `final_page_payload`，不得绕过最终安全闸门直接读取上游 provider、真实账户配置或未脱敏中间结果。

## 4. 安全边界

Web-P1 保持以下安全边界：

- 不请求真实行情，不直接请求原始行情字段。
- 不请求真实基金净值，不直接请求原始基金净值字段。
- 不读取真实 `user_config`。
- 不保存个人敏感字段 / 成本字段 / 账户字段。
- 不保存 Token / API Key / Webhook。
- 不连接 Discord、日报、周报或真实 provider。
- 不自动下单，不构成强制交易指令，不替用户操作。

## 5. 页面结构

当前静态页面包含：

- 左侧导航：首页、指数、持仓、观察、个人点位、清理中心、设置。
- 顶部栏：页面标题、搜索框占位、数据状态。
- 账户概览：展示 demo 账户名称和 safety badges。
- 股票 ETF：占位卡片，不请求真实行情，不直接请求原始行情字段。
- 场外基金：占位卡片，不请求真实基金净值，不直接请求原始基金净值字段。
- 个人观察点位：展示 demo 个人观察标签。
- 风险提醒：展示不自动下单和非强制交易指令说明。
- 数据说明：说明当前只消费 demo payload，未来只消费 `final_page_payload`。

## 6. 个人观察标签

页面允许展示个人观察标签，例如：买入观察、加仓观察、减仓观察、止盈观察、止损观察、清仓观察、低吸区、目标区、风险位。

这些标签只能作为个人观察和记录。页面禁止表达或暗示：必须买入、保证收益、自动下单、替用户操作。

## 7. 后续路线

- Web-P15：实时行情与基金净值看板。
- Web-P16：个人观察点位卡片页面。
- Web-P17：账户首页综合看板。

## 8. Web-P2 渲染适配

Web-P2 在最小静态页面骨架上继续增强 `final_page_payload` 渲染能力。页面读取 `web/static/demo_final_page_payload.json`，并渲染账户名称、`payload_status`、`display_mode`、`safety_badges`、股票 / ETF section、场外基金净值 section、个人观察点位、warnings、disclaimer 和 blocked payload 安全提示。

该适配仍然只消费 `final_page_payload`，不请求真实行情，不直接请求原始行情字段，不请求真实基金净值，不直接请求原始基金净值字段，不读取真实 `user_config`，不保存个人敏感字段 / 成本字段 / 账户字段，也不保存 Token / API Key / Webhook。
