# dsa-web mock service

This directory contains the non-runtime mock API client and mock service scaffold for a future mock-only preview entry.

## Boundary

- It is not imported by `src/main.tsx`, `src/App.tsx`, runtime API modules, pages, stores, components, contexts, or utilities.
- It does not change the real API client.
- It only reads the existing mock adapter, fixture catalog, and mock-only safety helpers.
- Callers must pass `{ mode: 'mock', source: 'local_preview_only' }` explicitly.
- It has no browser storage, timers, streaming channels, notification calls, report generation, or backend connection behavior.

## Public scaffold

- `createMockApiClient(options)` returns a frozen service-shaped client.
- `createMockApiService(options)` returns a frozen service object.
- `assertMockServiceReady(options)` verifies explicit mock mode and the local preview source.
- `listMockModules(options)` lists fixture-backed modules.
- `getMockModule(options, moduleName)` returns fixture data for a known module.
- `getMockScenario(options, moduleName, scenarioName)` returns a response wrapper with module, scenario, and fixture data.
