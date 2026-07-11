# Mock-only preview scaffold

This directory contains the L2J non-runtime mock-only preview scaffold.

Boundaries:

- Uses the L2I mock service with `{ mode: "mock", source: "local_preview_only" }`.
- Stays outside the real Web App entry, App shell, routes, API client, pages, stores, components, contexts, and utils.
- Does not add or require any Web startup script.
- Does not call backend, provider, outbound delivery, AI service, or formal report generation paths.
- Uses only redacted fixture-backed mock data.

Future visual drafts should stay outside the real App and route tree until a separately reviewed preview entry is approved.

## Future Windows localhost-only safe preview script design

L2L only documents how a future Windows one-click safe preview script should behave. It does not add a startup script, npm script, Vite entry, route, or runtime App integration.

Future script work must keep this preview mock-only and localhost-only:

- Bind only to `127.0.0.1`.
- Reject `0.0.0.0`, LAN IPs, public IPs, and externally reachable hosts.
- Run mock-only network boundary and preview tests before any startup attempt.
- Do not read real `.env` files or real `VITE_API_URL` values.
- Do not call real `/api/v1/**`, providers, AI services, notifications, or formal report generation paths.

Until a separately reviewed mock-only preview entry exists, a future script should stop with a design-only message instead of trying to start Web preview.
