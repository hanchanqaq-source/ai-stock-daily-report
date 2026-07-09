# Web-P15 行情与基金净值看板说明

## 1. 设计目标

Web-P15 将 `final_page_payload` 中的 `sections.stock_etf` 和 `sections.fund_nav` 渲染为本地 Web 看板卡片。页面只做展示增强，保留轻量静态 HTML / CSS / JS 实现，不引入 React、Vue、Next.js 或外部样式库。

## 2. 数据来源

当前本地预览只读取 `web/static/demo_final_page_payload.json`。未来正式数据必须来自 P5-T `final_page_payload`，也就是 `src/account_real_data_final_gate.py` 输出的最终安全 payload。

Web 页面不能绕过最终安全闸门，不能直接消费 provider 原始数据，不能读取真实 `user_config`。

## 3. 股票 / ETF 行情区

股票 / ETF 行情区展示 `sections.stock_etf.display_models` 中已经过安全闸门处理的 display model。可展示字段包括：名称、代码、类型、市场、最新价、涨跌幅、成交额、provider、checked_at、source_status、display_mode 和 badges。

当 `display_mode=redacted` 时，最新价、涨跌幅、成交额显示为 `<redacted>`。

## 4. 场外基金净值区

场外基金净值区展示 `sections.fund_nav.display_models` 中已经过安全闸门处理的 display model。可展示字段包括：名称、代码、类型、市场、单位净值、累计净值、净值日期、日涨跌幅、估算净值、估算涨跌、估算更新时间、provider、checked_at、source_status、display_mode 和 badges。

场外基金不支持真正实时价格。盘中估算仅供观察，最终以基金公司公布净值为准。

## 5. 展示状态

- `displayable`：可以展示安全 payload 中允许展示的字段。
- `redacted`：展示脱敏占位值，不显示真实价格、真实基金净值或真实账户数值。
- `blocked`：数据已被安全闸门拦截，不显示真实值。
- `unavailable`：当前数据不可用，页面展示不可用提示并继续保持安全说明。

## 6. 安全边界

- 不请求真实行情。
- 不请求真实基金净值。
- 不读取真实 `user_config`。
- 不保存真实金额 / 成本价 / 账户资产。
- 不保存 Token / API Key / Webhook。
- 不连接 Discord、日报、周报或真实 provider。
- `blocked` 状态不显示真实值。
- 页面必须保留：本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。

## 7. 后续路线

- Web-P16：个人观察点位卡片页面。
- Web-P17：账户首页综合看板。
- Web-P18：指数模块页面切换。
