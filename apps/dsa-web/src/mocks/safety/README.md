# Mock-only safety scaffold

This directory contains non-runtime safety helpers for the future mock-only Web preview path.

Current boundaries:

- Pure functions only.
- No Web App entry integration.
- No API client integration.
- No page, store, component, context, or utility imports.
- No network calls.
- No environment reads.
- No real provider endpoints, tokens, webhooks, or API keys.

The helpers are intended to be imported by tests and by a future reviewed mock-only preview integration only after the safety switch and network blocking tests remain in place.
