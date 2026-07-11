# Mock-only preview scaffold

This directory contains the L2J non-runtime mock-only preview scaffold.

Boundaries:

- Uses the L2I mock service with `{ mode: "mock", source: "local_preview_only" }`.
- Stays outside the real Web App entry, App shell, routes, API client, pages, stores, components, contexts, and utils.
- Does not add or require any Web startup script.
- Does not call a backend, provider, notification channel, AI service, or formal report generator.
- Uses only redacted fixture-backed mock data.

`MockOnlyPreviewPage.tsx` is a draft component for future review only. It is intentionally not imported by the real App or route tree.
