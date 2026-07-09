# Web-P2 final_page_payload 页面渲染适配说明

## 1. 设计目标

Web-P2 让 `web/static/` 下的静态 HTML / CSS / JS 页面能够消费 `final_page_payload` 结构，并在本地预览账户信息、safety_badges、股票 / ETF、场外基金净值、个人观察点位、warnings 和 disclaimer。

本阶段只做页面渲染适配，不引入 React / Vue / Next.js，不接真实 provider，不扩大为复杂前端工程。

## 2. 数据来源

当前页面读取 `web/static/demo_final_page_payload.json`，用于本地 demo 预览。浏览器无法读取 demo JSON 时，`app.js` 使用本地 fallback payload。

未来正式数据必须来自 P5-T `src/account_real_data_final_gate.py` 输出的 `final_page_payload`。Web 页面只消费 `final_page_payload`，不得绕过最终安全闸门读取 provider 原始结果、未脱敏中间结果或真实 `user_config`。

## 3. 渲染区域

当前静态页面渲染以下区域：

- 账户信息：账户名称、`payload_status`、`display_mode`。
- `safety_badges`：展示安全审计、默认脱敏和禁止写入真实数据等标记。
- 股票 ETF：消费 `sections.stock_etf`，只展示 payload 中已经脱敏的 display model。
- 场外基金净值：消费 `sections.fund_nav`，只展示 payload 中已经脱敏的净值 / 估算展示字段，并保留“盘中估算仅供观察，最终以基金公司公布净值为准。”
- 个人观察点位：消费 `sections.observation_points`。
- `warnings`：展示页面风险提醒；为空时显示暂无额外风险提示。
- `disclaimer`：展示页面免责声明。

## 4. blocked payload

当 `payload_status=blocked` 时，页面显示安全拦截提示，说明该 payload 已被阻断，并且不显示真实值。blocked 状态下也不得展示上游 raw value、真实价格、真实基金净值、真实金额、成本价、账户资产或 secrets。

## 5. 安全边界

Web-P2 保持以下边界：

- 不请求真实行情。
- 不请求真实基金净值。
- 不读取真实 `user_config`。
- 不保存真实金额 / 成本价 / 账户资产。
- 不保存 Token / API Key / Webhook。
- 不连接 Discord、日报、周报或真实 provider。
- 不自动下单，不构成强制交易指令。

## 6. 个人观察标签

页面允许展示买入观察、加仓观察、减仓观察、止盈观察、止损观察、清仓观察、低吸区、目标区、风险位、等待回调、继续持有、暂不操作等个人观察标签。

这些标签只能表达个人观察记录。页面禁止展示必须买入、必须卖出、立即满仓、稳赚、保证收益、无风险、自动下单、系统替你操作等强制交易、收益承诺或自动执行表达。

页面必须保留：本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。

## 7. 后续路线

- Web-P15：实时行情与基金净值看板。
- Web-P16：个人观察点位卡片页面。
- Web-P17：账户首页综合看板。
