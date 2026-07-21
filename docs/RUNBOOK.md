# Runbook

## SQLite 持久化地基

- 初始化：调用 `LocalPersistenceService(...).initialize()`，空库会自动执行 `0001_initial_schema`。
- 查看版本：调用 `LocalPersistenceService.schema_version()`，当前应返回 `0001_initial_schema`。
- 测试数据库：使用 pytest 的 `tmp_path` 和 `LocalPersistenceService.for_test_dir(tmp_path)`；不要复用正式数据库。
- 排障：如果目录不可创建或 SQLite 无法打开，会抛出明确异常；不要在 API 层静默吞掉数据库错误。
- Git 安全：确认 `git status --short` 中没有 `*.db`、`*.sqlite`、`*.sqlite3`。
