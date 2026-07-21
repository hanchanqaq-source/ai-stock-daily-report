# 股票基金双中心 Build E1：本地数据库持久化

## 结果

Build E1 已经把工作台用户、股票快速持仓和基金快速持仓接入项目原有 SQLAlchemy SQLite 数据库。Build E2 审计后确认这条生产链路继续作为唯一正式数据源，不再增加平行 sqlite3 数据库。

正式调用链固定为：

`PortfolioUserContext → workspacePortfolioApi → /api/v1/workspace-portfolio → FastAPI get_db → SQLAlchemy Session → src.storage workspace 模型 → DATABASE_PATH 指向的 SQLite 数据库`

前端不直接打开 SQLite。刷新 Web 页面或重启便携程序后，状态重新从本机 API 和数据库读取。

## 正式数据模型

| 数据 | 表 | 隔离方式 |
| --- | --- | --- |
| 工作台用户 | `workspace_users` | `self` 是不可删除的默认用户 |
| 当前用户偏好 | `workspace_portfolio_preferences` | 保存有效的 `active_user_id` |
| 股票快速持仓 | `workspace_stock_holdings` | 通过 `user_id` 归属用户 |
| 基金快速持仓 | `workspace_fund_holdings` | 通过 `user_id` 归属用户 |
| 基金自选 | `workspace_fund_watchlist_items` | 通过 `user_id` 归属用户；与基金持仓独立 |
| 导入/恢复点 | `workspace_portfolio_backups` | 只保存工作台白名单数据 |
| 删除回收站 | `workspace_holding_recycle_entries` | 按用户及股票/基金领域隔离 |
| 修改历史 | `workspace_holding_history_entries` | 按用户及股票/基金领域隔离 |

这些表只保存用户手动录入的工作台数据，不代表登录账户，不读取券商或基金平台账户，也不与高级股票账户、交易流水或自动交易模型合并。

## 数据库位置

- 后端通过 `DATABASE_PATH` / `Config.database_path` 使用一个 SQLite 文件，默认值为 `./data/stock_analysis.db`。
- 桌面端只向后端传入一个 `DATABASE_PATH`。
- Windows 便携更新保留 `data/stock_analysis.db`、`data/stock_analysis.db-wal`、`data/stock_analysis.db-shm`，不得用程序更新覆盖它们。
- 不创建 `stock_fund_quality.db`，也不创建第二套 `users` / `stock_holdings` / `fund_holdings` 表。

## 本机接口

`/api/v1/workspace-portfolio` 提供状态读取，以及用户、当前用户、股票持仓、基金持仓、基金自选、备份、回收站和历史记录操作。接口只接受 `127.0.0.1`、`::1` 和测试客户端请求。

## 迁移与回滚

- 首次访问时自动创建默认“本人”档案；SQLAlchemy `create_all` 幂等创建缺失表。
- 数据库迁移记录继续统一使用既有 `schema_migrations`。
- 测试只使用临时 `DATABASE_PATH`，并通过重建应用和数据库会话验证重启持久化。
- 回滚代码不得主动删除 workspace 表或用户数据；重新升级后应可继续读取。
