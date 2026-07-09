# Web 数据流说明

Web 工作台的数据流必须从最终安全闸门开始，而不是从真实 provider 或真实用户配置开始。

## Allowed flow

```text
provider / account processing upstream
  -> src/account_real_data_final_gate.py
  -> final_page_payload
  -> local Web workspace rendering
```

Web 只消费 `final_page_payload`。页面默认消费 redacted / safe payload，不直接请求真实行情，不直接请求真实基金净值，不直接请求原始行情字段，不直接请求原始基金净值字段，不直接读取真实 `user_config`，不保存 Token / API Key / Webhook，不保存个人敏感字段 / 成本字段 / 账户字段。

## Web 页面渲染流程

Web-P2 页面渲染流程为：

```text
P5-T final_page_payload
  -> web/static/demo_final_page_payload.json 或后续本地安全 payload
  -> web/static/app.js 渲染
```

当前静态页面只消费 demo final_page_payload 或 fallback payload，不请求真实行情，不直接请求原始行情字段，不请求真实基金净值，不直接请求原始基金净值字段，不读取真实 `user_config`。

## Forbidden direct flow

```text
Web page -> cn_quote_real_provider raw result
Web page -> fund_nav_real_provider raw result
Web page -> cn_quote_result_audit unredacted result
Web page -> fund_nav_result_audit unredacted result
Web page -> real user_config
```

上述路径都不允许。Web 不直接抓数据，不直接连 provider，不直接写仓库，不直接保存原始行情字段，不直接保存原始基金净值字段。

## Blocked payload

当 `final_page_payload` 或上游结果被判定为 blocked 时，Web 只能显示安全错误提示，不显示真实值。

## Personal observation boundary

Web 可以展示买入观察、加仓观察、减仓观察、止盈观察、止损观察、清仓观察、低吸区、目标区、风险位、等待回调、继续持有、暂不操作等个人观察标签。展示时必须保留免责声明：本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。

## Web-P1 demo payload

Web-P1 静态页面只读取 `web/static/demo_final_page_payload.json` 或本地 fallback demo。该 demo 用于验证页面骨架；未来正式页面必须继续只消费 P5-T `final_page_payload`，不得直接请求真实行情、真实基金净值或 provider 原始字段或真实 `user_config`。
