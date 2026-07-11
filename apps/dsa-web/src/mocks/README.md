# dsa-web mock fixtures

This directory is reserved for frontend mock-only preview data.

Current scope for L2E:

- Only static fixture JSON files and documentation are added.
- These fixtures are not imported by the real App, API client, pages, stores, components, or runtime entry points.
- The real Web application will not automatically use this directory.
- A later L2F task may add a mock API adapter that reads these fixtures behind an explicit mock-only mode.

Safety rules:

- Every fixture must be demo, mock, redacted, and local-preview-only.
- Do not add real accounts, real holdings, real asset amounts, real returns, real trading records, or personal information.
- Do not add real tokens, webhooks, API keys, provider URLs, OpenAI/LiteLLM settings, Feishu/DingTalk/Discord configuration, or model binding configuration.
- Use placeholders such as `REDACTED_TOKEN`, `REDACTED_WEBHOOK`, `REDACTED_API_KEY`, `DEMO_AMOUNT`, and `MOCK_API_PATH_ONLY`.
- Do not add JavaScript, TypeScript, external images, CDN references, or runnable startup scripts in this directory.
