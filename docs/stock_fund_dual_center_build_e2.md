# Build E2：用户、股票持仓和基金持仓持久化收敛与重启验收

## 架构结论

Build E2 不再从零建立持久化。审计确认生产前端、API、备份、回收站和历史记录已经使用既有 SQLAlchemy workspace 链路，因此最终只保留这一套正式数据源：

`PortfolioUserContext → workspacePortfolioApi → /api/v1/workspace-portfolio → FastAPI get_db → SQLAlchemy Session → src.storage → DATABASE_PATH 指向的 SQLite 数据库`

## 审计结果

- `src.storage` 中的 `workspace_*` 模型已被生产 API 实际调用。
- `src/repositories/sqlite_foundation.py` 与 `src/services/sqlite_foundation_service.py` 只有其新增测试和文档引用，没有生产 API、前端或桌面启动调用方。
- 保留两套实现会形成两个数据库、两套用户/持仓表和两个 schema 版本来源，无法可靠确定哪一份数据是真相。
- 收敛前已全仓搜索 `sqlite_foundation`、`LocalPersistenceService` 与 `LocalFoundationRepository` 调用方；移除后不得存在剩余引用。

## 唯一正式数据库

- 配置入口：`DATABASE_PATH` / `Config.database_path`。
- 默认文件：`./data/stock_analysis.db`。
- 正式表：`workspace_users`、`workspace_portfolio_preferences`、`workspace_stock_holdings`、`workspace_fund_holdings`、`workspace_portfolio_backups`、`workspace_holding_recycle_entries`、`workspace_holding_history_entries`。
- 迁移记录：既有 `schema_migrations`。
- Windows 便携运行：`data/stock_analysis.db` 及其 WAL/SHM 文件属于用户数据，更新时保留。

以下内容不是正式数据源，且不得重新引入：

- `stock_fund_quality.db`；
- 独立 `users` / `stock_holdings` / `fund_holdings` 表；
- 独立 `schema_version` / `data_migrations`；
- 两套数据库之间的静默双写或双向同步。

## 前端一致性

`PortfolioUserContext` 可在请求发出时进行即时界面更新，但必须遵守以下规则：

1. API 成功后使用返回的完整服务端状态，或重新读取 `/api/v1/workspace-portfolio`。
2. API 失败后重新读取完整服务端状态，撤销未写入数据库的乐观结果，并显示持久化错误。
3. mutation 按发起顺序写入服务端；初次加载和 mutation 同时使用递增请求序号，旧响应不得覆盖更新的用户或持仓状态。
4. 多个快速操作全部落库后，由最后一个请求重新读取完整状态，避免较早操作晚完成后只存在于数据库、不存在于界面。
5. 外部导入/恢复应用完整状态时，使此前尚未完成的旧请求失效。
6. 不引入大型状态管理框架，前端仍不得直接连接 SQLite。

## 重启验收

后端回归测试使用临时 `DATABASE_PATH` 和虚构数据，并通过重置 `DatabaseManager` / `Config`、重新创建 FastAPI 应用与数据库会话验证：

- 首次启动创建“本人”，主用户不可删除；
- 新增、改名、切换和删除普通用户，当前用户在重启后恢复；
- 删除当前普通用户后回退到“本人”；
- 股票数量、成本、证券账户、备注在重启后保留；
- 基金金额、持有收益、目标仓位、备注在重启后保留；
- 用户之间、股票与基金之间保持隔离；
- 删除后回收站与修改历史仍正常；
- 临时库存在 `workspace_*` 与 `schema_migrations`，不存在第二套持仓表和 schema 版本表；
- 测试目录不生成 `stock_fund_quality.db`。

前端定向测试验证：

- 用户、股票和基金状态隔离；
- API 失败后重新读取服务端状态；
- 旧请求响应不能覆盖较新的当前用户状态。

桌面端既有回归测试继续验证更新和回退保留 `data/stock_analysis.db`、WAL、SHM 与其他用户目录。

## 既有备份与恢复能力

原有版本化 JSON 导出、导入预览、明确确认覆盖和恢复点能力继续保留。它只处理工作台用户与快速持仓，不导出 `.env`、密钥、DPAPI 凭证、日志、数据库文件、真实账户或交易记录。

## 安全与回滚

- 不读取用户真实数据库、`.env`、Token、API Key、Cookie 或 Webhook。
- 不连接真实证券/基金账户，不使用真实持仓测试，不自动交易。
- 回滚本次代码时不得删除或改写现有 `stock_analysis.db`；只恢复代码，workspace 数据表原样保留。
