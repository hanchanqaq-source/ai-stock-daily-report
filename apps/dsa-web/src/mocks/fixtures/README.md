# Fixture catalog

These JSON files are static mock-only data for future frontend preview work. They are not automatically requested, imported, or executed by the current Web app.

| File | Purpose | Related API module / page |
| --- | --- | --- |
| `auth.json` | Authentication enabled/disabled, logged-out/logged-in, 401/403 examples | `authApi`, Login, AuthProvider |
| `dashboard.json` | Home dashboard cards, market status, watchlist, skills, loading/empty/error | Home dashboard, `analysisApi`, `historyApi`, `agentApi` |
| `analysis_tasks.json` | Accepted/running/completed/failed/duplicate tasks and market review | `analysisApi`, task panels, run flow |
| `history_reports.json` | Report list/detail, markdown, news, diagnostics, stock bar, empty states | `historyApi`, report components |
| `portfolio.json` | Redacted account, holdings, risk, cash flow, trades | `portfolioApi`, Portfolio page |
| `alerts.json` | Alert rules, triggers, notification history, test success/failure | `alertsApi`, Alerts page |
| `system_config.json` | Masked config, setup/scheduler status, watchlist, LLM/notification tests | `systemConfigApi`, Settings, Chat |
| `agent_chat.json` | Skills, sessions, messages, stream chunks, abort/error examples | `agentApi`, Chat page, agent store |
| `alphasift.json` | Enabled/disabled status, strategies, hotspots, screen task, candidates | `alphasiftApi`, Stock screening |
| `usage.json` | Mock token usage dashboard, model/call type breakdown, recent calls, empty usage | `usageApi`, Token usage page |
| `backtest.json` | Run result, result list, performance, failed/empty examples | `backtestApi`, Backtest page |
| `decision_signals.json` | Signal list/latest, outcomes, timeline, feedback | `decisionSignalsApi`, Decision signals page |
| `stocks_import.json` | Text import and image extraction mock results, low confidence and errors | `stocksApi`, intelligent import |
| `errors.json` | Network, validation, unauthorized, forbidden, conflict, rate limit, server errors | API error handling |
| `empty_states.json` | Empty dashboard, portfolio, history, alerts, chat, usage | Empty-state UI previews |

Sensitive information boundary:

- All files must keep `metadata.contains_real_data` and `metadata.contains_secrets` set to `false`.
- Amounts, returns, account identifiers, token usage, provider details, webhooks, and keys must stay as obvious mock/redacted placeholders.
- Do not add external URLs, CDN URLs, image URLs, real API endpoints, or provider base URLs. Use `MOCK_API_PATH_ONLY` if a route label is needed.

Future adapter usage:

- L2F may read these fixtures through an explicit mock API adapter.
- The adapter must block real network calls and must not use these JSON files unless mock-only mode is explicitly enabled.
- These fixtures do not start dev servers, bind ports, call the backend, or request real network resources.
