# Local Web Workspace

This directory is the skeleton for the local personal Web workspace. Web-P0 only defines the entry contract, directory boundary, route plan, and safe data flow; it does not implement real pages or a frontend framework.

## Positioning

- The workspace is a local personal dashboard for account review, holdings, watching assets, funds, ETFs, observation points, and risk notes.
- It does not place orders, does not trade for the user, and does not connect to Discord, daily reports, or weekly reports.
- It does not store secrets, credentials, webhook addresses, real prices, real fund NAV values, real amount values, cost basis, or account assets in the public repository.
- It only consumes `final_page_payload` produced by `src/account_real_data_final_gate.py` after the final safety gate.
- It must not directly request real market quotes or real fund NAV values.
- It must not directly read real `user_config` files.

## Required disclaimer

Every future page that renders personal observation labels must keep this disclaimer:

> 本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。

## Allowed personal observation labels

Future pages may display personal observation wording such as 买入观察、加仓观察、减仓观察、止盈观察、止损观察、清仓观察、低吸区、目标区、风险位、等待回调、继续持有、暂不操作.

These labels are personal notes only. They must not be rendered as forced trading instructions, guaranteed returns, or automatic execution actions.

## Web-P1 static preview

Web-P1 adds the minimal local static page skeleton at:

```text
web/static/index.html
```

The page only consumes the demo `final_page_payload` shape from `web/static/demo_final_page_payload.json` or its in-page fallback. It does not request real quotes, real fund NAV values, real `user_config`, or save real account values.

## Web-P2 final_page_payload rendering

Web-P2 extends the static preview so `web/static/app.js` reads `web/static/demo_final_page_payload.json` and renders the current safe payload areas:

- account name, `payload_status`, and `display_mode`
- `safety_badges`
- `sections.stock_etf`
- `sections.fund_nav` with the note that intraday estimates are for observation only and final values depend on the fund company published NAV
- `sections.observation_points`
- `warnings` and `disclaimer`
- blocked payload safety banner

The page still does not request real quotes, real fund NAV values, real `user_config`, Discord, daily reports, weekly reports, or real providers.


## Web-P15 market and fund NAV dashboard

Web-P15 extends the static preview with safe demo cards for `sections.stock_etf` and `sections.fund_nav`. The page renders redacted, blocked, unavailable, and displayable states from `web/static/demo_final_page_payload.json`, keeps provider/source status metadata, and keeps the notice that intraday fund estimates are for observation only and final values depend on the fund company published NAV. It still does not request real quotes, real fund NAV values, real `user_config`, Discord, daily reports, weekly reports, or real providers.
