# Web Workspace AGENTS.md

Scope: this file applies to all files under `web/`.

1. The `web/` directory is only for the local personal Web workspace.
2. Web code and docs must not directly request real market quotes.
3. Web code and docs must not directly request real fund NAV values.
4. Web can only consume `final_page_payload` from `src/account_real_data_final_gate.py`.
5. Web must not save Token / API Key / Webhook values.
6. Web must not save real amount values, cost basis, or account asset values to the public repository.
7. Pages may use personal observation labels such as 买入观察、加仓观察、减仓观察、止盈观察、止损观察、清仓观察、低吸区、目标区、风险位、等待回调、继续持有、暂不操作.
8. Pages must not present forced trading instructions, guaranteed returns, or automatic order execution.
9. Dangerous operations must be previewed, confirmed, and then executed; never delete or overwrite by default.
10. Complex tasks continue to follow Plan → Build → Judge.
11. Every user-facing personal observation page must keep: 本页面仅作为个人观察和记录，不自动下单，不构成强制交易指令。
