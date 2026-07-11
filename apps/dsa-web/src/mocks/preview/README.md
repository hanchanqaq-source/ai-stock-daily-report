# Mock-only preview scaffold

This directory contains the L2J non-runtime mock-only preview scaffold.

Boundaries:

- Uses the L2I mock service with `{ mode: "mock", source: "local_preview_only" }`.
- Stays outside the real Web App entry, App shell, routes, API client, pages, stores, components, contexts, and utils.
- Does not add or require any Web startup script.
- Does not call backend, provider, outbound delivery, AI service, or formal report generation paths.
- Uses only redacted fixture-backed mock data.

Future visual drafts should stay outside the real App and route tree until a separately reviewed preview entry is approved.
