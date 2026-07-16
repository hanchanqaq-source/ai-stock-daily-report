# 股票基金双中心 Build B 持仓分域与验收

## 1. 原因

Build A 已将股票中心和基金中心的入口、路由与页面展示分开，但快速持仓仍保存在同一个 `holdingsByUser` 混合对象中，增删接口还允许调用方传入任意用户 ID。该结构容易因错误参数把持仓写入其他用户或不存在的用户，也无法从类型层面阻止股票与基金状态混用。

Build B 只处理运行期持仓分域，不接真实基金数据、账户、Provider、AI、通知或自动交易。

## 2. 处理

- 将混合 `holdingsByUser` 拆为 `fundHoldingsByUser` 与 `stockHoldingsByUser` 两个独立状态仓库；
- 页面只读取 `activeFundHoldings` 或 `activeStockHoldings`，不再读取混合持仓对象；
- 快速持仓增删 API 不再接受调用方传入用户 ID，只能作用于当前用户；
- 股票持仓页和基金持仓页必须显式传入领域，不再保留可同时展示两种资产的 `all` 页面模式；
- 股票中心快速录入固定写入股票域，基金中心固定写入基金域；
- 删除非默认用户时同时清理该用户的股票与基金运行期状态；
- 非法用户 ID 切换保持当前用户，不创建孤立持仓。

## 3. 需求追踪矩阵

| 需求编号 | 用户要求 | 实现 | 自动测试 | Windows 证据 | 状态 |
|---|---|---|---|---|---|
| DUAL-B-001 | 股票持仓和基金持仓分成两个区域 | `PersonalPortfolioPage` 强制 `stock` / `fund` 领域，移除 `all` 模式 | `PersonalPortfolioPage.test.tsx`、`App.test.tsx` | Build B Portable Judge 待补 | 已实现 |
| DUAL-B-002 | 股票、基金状态分别保存 | 独立 `fundHoldingsByUser` / `stockHoldingsByUser` 状态仓库 | `PortfolioUserContext.test.tsx` | Build B Portable Judge 待补 | 已实现（运行期） |
| DUAL-B-003 | 切换用户后数据不能串用 | 增删 API 只作用于当前有效用户，非法切换不改变当前用户 | `PortfolioUserContext.test.tsx` | Build B Portable Judge 待补 | 已实现（运行期） |
| DUAL-B-004 | 保留快速录入 | `QuickHoldingEntryDrawer` 保留手工录入并由中心锁定资产类型 | `QuickHoldingEntryDrawer.test.tsx` | Build B Portable Judge 待补 | 已实现 |
| DUAL-B-005 | 删除用户不能残留或影响其他用户 | 删除用户时分别清理两个领域，默认用户禁止删除 | `PortfolioUserContext.test.tsx` | Build B Portable Judge 待补 | 已实现 |
| DUAL-B-006 | 基金页不能调用股票持仓接口 | 基金领域不加载证券账户、股票快照与股票风险 API | `PersonalPortfolioPage.test.tsx` | Build B Portable Judge 待补 | 已实现 |
| DUAL-B-007 | 刷新后数据仍存在 | schema 版本、数据库迁移、备份和回滚 | Build E 覆盖 | Build E 覆盖 | 延期至 Build E，未声称完成 |

## 4. 兼容边界

- 旧 `/portfolio` 仍由 Build A 兼容层跳转到上次使用的股票或基金持仓中心；
- 默认用户仍可读取现有正式股票账户快照，非默认用户不会复用默认用户的股票账户数据；
- 当前用户、用户档案和快速持仓仍是内存状态，刷新或重启会恢复；
- Build E 才实现数据库 `schema_version`、升级前备份、事务迁移、失败回滚和旧数据升级；
- 当前不读取或迁移 `.env`、token、webhook、API key，也不修改 safeStorage / Windows DPAPI。

## 5. 验证

```bash
cd apps/dsa-web
npm test
npm run lint
npm run build
```

Judge 必须检查：

- 用户 A 的股票、基金持仓不会显示给用户 B；
- 删除股票不影响基金，删除基金不影响股票；
- 基金路由不请求股票账户 API；
- Windows Portable 仍使用 packaged backend、仅绑定 `127.0.0.1` 并加载主页面；
- 没有把运行期隔离误标为重启持久化完成。

## 6. 回滚

只回滚 Build B 的独立状态仓库、当前用户限定增删 API、领域必填属性和对应测试；不回滚 Build A 双中心路由、Portable-M1、股票后端、安全凭证或其他功能。
