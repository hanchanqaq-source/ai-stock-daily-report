# SQLite 持久化地基（Build E0/E1）

本文记录“股票基金质量分析系统”后续用户、股票持仓、基金持仓、自选、分析记录和聊天记录的本机 SQLite 地基。当前只完成持久化基础，不开始 E2 用户和持仓界面接入。

## 数据目录原则

`src.repositories.sqlite_foundation.resolve_app_data_dirs()` 统一抽象以下目录：

| 目录 | 用途 |
| --- | --- |
| 程序目录 | 当前仓库或打包后的程序文件位置，只放代码和只读资源 |
| 用户数据目录 | SQLite 正式数据库位置，不能放在每次程序更新会覆盖的目录 |
| 缓存目录 | 可再生成的缓存 |
| 日志目录 | 运行日志，不能写入密钥或真实持仓明细 |
| 备份目录 | 后续 E2 备份记录和导出文件 |
| 测试数据目录 | 自动测试或手工验收的临时数据 |

云端和 CI 测试必须使用临时目录，不能和正式数据库共用。Windows 路径只做跨平台设计，代码不得访问开发者本机盘符（例如 `D:\AI_Workspace`）。

## 数据库文件

默认数据库文件名为 `stock_fund_quality.db`，位于用户数据目录。`.gitignore` 已忽略 `*.db`、`*.sqlite`、`*.sqlite3`，真实数据库和测试数据库都不得提交到 GitHub。

## 首版 schema 与迁移

首个迁移编号为 `0001_initial_schema`，由 `SQLiteConnectionManager.initialize()` 在事务内执行。已执行迁移记录在 `data_migrations`，当前版本记录在 `schema_version`。

首版表包括：

- `schema_version`
- `users`
- `app_state`
- `stock_holdings`
- `fund_holdings`
- `stock_watchlist`
- `fund_watchlist`
- `user_preferences`
- `stock_analysis_records`
- `fund_analysis_records`
- `stock_chat_sessions`
- `fund_chat_sessions`
- `data_migrations`
- `backup_records`

迁移要求：空库首次启动自动建表；重复启动不重复插入迁移；迁移失败回滚；数据库目录缺失时安全创建；不可写或异常路径返回明确 `SQLiteFoundationError`，不静默吞错。

## Repository / Service 边界

推荐链路：

前端 → 本地 API → Service → Repository → SQLite

- 前端不得直接操作 SQLite。
- API 只负责参数校验、调用服务和返回结果。
- Service 负责业务规则，例如用户存在性、数量/金额非负。
- Repository 负责 SQL 读写。
- SQLite 连接创建和关闭集中在 `SQLiteConnectionManager`。
- 当前不引入大型 ORM；本地地基使用 Python 标准库 `sqlite3`。

## 测试数据库使用方式

自动测试通过 `LocalPersistenceService.for_test_dir(tmp_path)` 创建临时数据库。测试数据只能是虚构用户、虚构股票和虚构基金，不得读取 `.env`、Token、Cookie、Webhook 或真实持仓。

## 后续 E2 接入说明

E2 如果接入用户和持仓界面，应只新增 localhost API 与前端调用，继续复用 `LocalPersistenceService` 和 Repository。E2 不应让 React 页面直接读写 SQLite，也不应将测试数据库路径或 Windows 真实路径写死到前端。
