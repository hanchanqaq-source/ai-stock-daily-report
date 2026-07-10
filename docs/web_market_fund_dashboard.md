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
- `redacted`：展示脱敏占位值，不显示原始价格字段、原始基金净值字段或个人敏感字段。
- `blocked`：数据已被安全闸门拦截，不显示真实值。
- `unavailable`：当前数据不可用，页面展示不可用提示并继续保持安全说明。

## 6. 安全边界

- 不请求真实行情，不直接请求原始行情字段。
- 不请求真实基金净值，不直接请求原始基金净值字段。
- 不请求原始行情字段。
- 不请求原始基金净值字段。
- 不读取真实 `user_config`。
- 不保存个人敏感字段 / 成本字段 / 账户字段。
- 不保存 Token / API Key / Webhook。
- 不连接 Discord、日报、周报或真实 provider。
- `blocked` 状态不显示真实值。
- 页面必须保留：本页面仅作为个人观察和记录，需用户自行判断。

## 7. 后续路线

- Web-P16：个人观察点位卡片页面。
- Web-P17：账户首页综合看板。
- Web-P18：指数模块页面切换。

## Web-P16 衔接

Web-P16 已增强 `sections.observation_points` 卡片展示，页面在同一个 demo `final_page_payload` 中渲染个人观察标签、状态 badge、风险等级 badge、脱敏观察点位、数据状态和“需用户自行判断”免责声明。该增强不请求原始行情字段、不请求真实基金净值，不直接请求原始基金净值字段，也不直接消费 provider 原始数据。

## Web-P17 衔接

Web-P17 已在首页综合看板中复用 Web-P15 的股票 / ETF 与场外基金净值卡片渲染逻辑，展示前 2～3 个 display model 作为快览。场外基金快览继续使用净值 / 估算净值语义，避免使用交易所实时价格类表述，并保留“盘中估算仅供观察，最终以基金公司公布净值为准。”

本页遵循 `docs/personal_wording_policy.md`：股票 / ETF / 指数可以写实时涨跌；场外基金不能写场外基金实时涨跌、基金实时价格或实时净值，只能写估算涨跌 / 净值涨跌 / 估算净值，并保留最终以基金公司公布净值为准。
