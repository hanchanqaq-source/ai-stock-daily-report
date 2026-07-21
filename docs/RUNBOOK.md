# Runbook

## Workspace 持久化唯一数据源

- 正式数据源：`DatabaseManager` 与 `src.storage` 中的 SQLAlchemy workspace 模型。
- 正式调用链：`PortfolioUserContext → workspacePortfolioApi → /api/v1/workspace-portfolio → FastAPI get_db → SQLAlchemy Session → src.storage → SQLite`。
- 数据库配置：后端只读取 `DATABASE_PATH` / `Config.database_path`；默认值为 `./data/stock_analysis.db`，`Config.get_db_url()` 会创建其父目录。
- 桌面运行时：Electron 只向后端传入一个 `DATABASE_PATH`。便携更新保留 `data/stock_analysis.db`、`data/stock_analysis.db-wal` 和 `data/stock_analysis.db-shm`。
- 禁止平行实现：不得再创建 `stock_fund_quality.db`、第二套 `users` / `stock_holdings` / `fund_holdings` 表或独立 schema 版本体系。

## 迁移与测试

- 迁移记录统一使用既有 `schema_migrations`，不得新增第二套 `schema_version` / `data_migrations`。
- 自动测试必须设置临时 `DATABASE_PATH`，并在测试后重置 `DatabaseManager` 与 `Config`；禁止读取用户真实数据库。
- 持久化验收必须重新创建应用和数据库会话，不能只验证 React 内存状态。
- 检查唯一数据库：临时库中应存在 `workspace_*` 业务表和 `schema_migrations`，且不应出现 `users`、`stock_holdings`、`fund_holdings`、`schema_version` 或 `data_migrations`。
- Git 安全：确认 `git status --short` 中没有 `*.db`、`*.sqlite`、`*.sqlite3`。

## 故障处理

- 本机 API 写入失败时，前端会重新读取完整服务端状态并显示错误；不要让乐观更新长期停留在界面中。
- 若重新读取也失败，保留明确错误状态，让用户核对后重试；不得静默假定保存成功。
- 更新或迁移前不得覆盖数据库文件。后续迁移必须先建立备份，并验证主文件及 WAL/SHM 的处理方式。
