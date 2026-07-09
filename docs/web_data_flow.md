# Web 数据流说明

Web 工作台的数据流必须从最终安全闸门开始，而不是从真实 provider 或真实用户配置开始。

## Allowed flow

```text
provider / account processing upstream
  -> src/account_real_data_final_gate.py
  -> final_page_payload
  -> local Web workspace rendering
```

Web 只消费 `final_page_payload`。页面默认消费 redacted / safe payload，不直接请求真实行情，不直接请求真实基金净值，不直接读取真实 `user_config`，不保存 Token / API Key / Webhook，不保存真实金额 / 成本价 / 账户资产。

## Forbidden direct flow

```text
Web page -> cn_quote_real_provider raw result
Web page -> fund_nav_real_provider raw result
Web page -> cn_quote_result_audit unredacted result
Web page -> fund_nav_result_audit unredacted result
Web page -> real user_config
```

上述路径都不允许。Web 不直接抓数据，不直接连 provider，不直接写仓库，不直接保存真实行情，不直接保存真实基金净值。

## Blocked payload

当 `final_page_payload` 或上游结果被判定为 blocked 时，Web 只能显示安全错误提示，不显示真实值。

## Personal observation boundary

Web 可以展示买入观察、加仓观察、减仓观察、止盈观察、止损观察、清仓观察、低吸区、目标区、风险位、等待回调、继续持有、暂不操作等个人观察标签。展示时必须保留免责声明：本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。
