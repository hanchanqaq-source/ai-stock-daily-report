# Web 页面路由规划

Web-P0 只规划页面路由，不实现真实页面，不请求真实行情，不请求真实基金净值，不读取真实 `user_config`，不保存 secrets 或真实账户数值。

## Planned routes

| Route | 页面 | 用途 | Web-P0 状态 |
| --- | --- | --- | --- |
| `/dashboard` | 首页 | 账户总览、股票 ETF 区域、基金净值区域、风险雷达 | 仅规划 |
| `/indices` | 指数模块 | A股、港股、美股、韩股等指数通过 tab 切换 | 仅规划 |
| `/holdings` | 持仓页面 | 显示 holding 资产 | 仅规划 |
| `/watchlist` | 观察页面 | 显示 watching 资产 | 仅规划 |
| `/cleared` | 已清仓 | 显示 cleared 资产，不参与默认实时汇总 | 仅规划 |
| `/observation-points` | 个人观察点位 | 显示买入观察、加仓观察、减仓观察、止盈观察、止损观察、清仓观察等个人标签 | 仅规划 |
| `/cleanup` | 清理中心 | 只扫描，不默认删除；危险操作必须预览和确认 | 仅规划 |
| `/settings` | 设置页面 | 本地设置、导入导出、备份恢复；不得保存 secrets 到 public repo | 仅规划 |

## Route safety rules

All routes only consume `final_page_payload`. Routes must not directly connect to quote providers, fund NAV providers, Discord, daily reports, weekly reports, or real `user_config`. Pages must keep: 本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。

## Web-P1 static skeleton

Web-P1 先以 `web/static/index.html` 承载本地静态首页骨架，包含左侧导航、顶部栏、账户概览、股票 ETF、场外基金净值、个人观察点位、风险提醒和数据说明。各规划 route 仍不接真实 provider。


## Web-P15 行情与基金净值安全看板

Web-P15 在 `web/static/index.html` 中增强股票 / ETF 行情和场外基金净值卡片展示，只读取 `web/static/demo_final_page_payload.json` 或未来 P5-T `final_page_payload`，不请求真实行情，不请求真实基金净值，并保留“不自动下单 / 不构成强制交易指令”的安全文案。

## Web-P16 个人观察点位卡片

当前本地静态页面已支持个人观察点位卡片展示，为 Web-P17 账户首页综合看板预留 `observation_points` 页面区域。该区域只消费 demo `final_page_payload` / 未来 P5-T `final_page_payload`，不请求真实行情、真实基金净值或真实 provider。
