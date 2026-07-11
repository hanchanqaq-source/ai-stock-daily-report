# Mock-only preview TypeScript entry

This directory contains the independent TypeScript entry for the mock-only preview.

The entry is intentionally limited to the mock-only preview model and DOM-safe rendering. It must not import the real App, main entry, router, API modules, pages, stores, components, contexts, or utilities.

Allowed rendering primitives are limited to `createElement`, `textContent`, and `appendChild`.
