# Web Workspace Entry Contract

Web-P0 defines the local Web workspace entry contract only. No real UI, real quote request, real fund NAV request, real account persistence, or heavy frontend framework is introduced in this phase.

## Single safe data input

The Web workspace can only read the final safe page payload:

- Source module: `src/account_real_data_final_gate.py`
- Allowed object: `final_page_payload`
- Expected mode: redacted or otherwise explicitly safe payload that passed the final page gate

## Forbidden inputs

The Web workspace must not directly consume or request:

1. Raw `cn_quote_real_provider` results.
2. Raw `fund_nav_real_provider` results.
3. Raw unredacted `cn_quote_result_audit` results.
4. Raw unredacted `fund_nav_result_audit` results.
5. Real `user_config` content.
6. Secrets, credentials, API keys, or webhook addresses.
7. Real amount values, cost basis, or account asset values.

## Blocked payload behavior

If the final gate returns a blocked payload, Web pages may show only a safe error or blocked-state message. They must not display the blocked raw values.

## Execution boundary

- Web does not fetch data directly.
- Web does not connect to providers directly.
- Web does not write real market or account values into the repository.
- Web does not place orders or execute trades.

## Web-P1 local preview

The minimal static page can be opened at `web/static/index.html`. For browsers that block local JSON loading under `file://`, use:

```bash
python -m http.server 8000 -d web/static
```

This preview only reads `demo_final_page_payload.json` or the local fallback demo payload. It does not request real market quotes, real fund NAV values, or real `user_config`.
