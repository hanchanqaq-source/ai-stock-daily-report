# 股票基金双中心 Build A 实现与验收

## 1. 本阶段目标

Build A 在同一个“股票基金质量分析系统”中建立两个清晰的一级工作区：股票中心与基金中心。当前用户和系统设置保持共用，股票与基金的页面入口、问答语义和持仓展示分开。

本阶段不接真实基金 Provider、净值、披露持仓、行业周期计算或 AI 基金建议。

## 2. 需求追踪矩阵

| 需求编号 | 用户要求 | 页面 / 路由 | 实现 | 自动测试 | Windows 证据 | 状态 |
|---|---|---|---|---|---|---|
| DUAL-A-001 | 一个程序内分为股票、基金两个大板块 | `/`、`/stocks`、`/funds` | `WorkspaceLandingPage`、`WorkspaceSwitcher` | `App.test.tsx`、`SidebarNav.test.tsx` | Build A Portable Judge 待补 | 已实现，待 Windows Judge |
| DUAL-A-002 | 用户切换后查看对应用户数据 | 全局侧栏、`/users` | `WorkspaceSwitcher` 复用 `PortfolioUserContext` | 既有用户与持仓隔离测试 | Build A Portable Judge 待补 | 已实现，持久化属于 Build E |
| DUAL-A-003 | 股票功能集中在股票区域 | `/stocks/*` | 股票首页、问股票、持仓、选股、建议、回测、告警迁移 | `App.test.tsx`、`SidebarNav.test.tsx` | Build A Portable Judge 待补 | 已实现 |
| DUAL-A-004 | 基金功能集中在基金区域 | `/funds/*` | 基金首页、问基金、持仓、对比、行业穿透、行业周期、建议入口 | `FundCenterPage.test.tsx`、`SidebarNav.test.tsx` | Build A Portable Judge 待补 | 骨架已实现 |
| DUAL-A-005 | 问股票与问基金必须分开 | `/stocks/ask`、`/funds/ask` | 股票继续使用现有 Chat；基金为独立安全空状态，不加载股票 Chat | `App.test.tsx`、`workspaceCenter.test.ts` | Build A Portable Judge 待补 | 已实现 |
| DUAL-A-006 | 股票持仓与基金持仓区域分开 | `/stocks/portfolio`、`/funds/portfolio` | 同一持仓组件按 domain 隔离展示和快速录入类型 | `PersonalPortfolioPage.test.tsx`、`QuickHoldingEntryDrawer.test.tsx` | Build A Portable Judge 待补 | 已实现展示隔离，正式持久化属于 Build B/E |
| DUAL-A-007 | 旧功能和链接不能因迁移丢失 | `/chat`、`/portfolio`、`/screening` 等 | 旧路由保留兼容跳转并保留查询参数 | `App.test.tsx` | Build A Portable Judge 待补 | 已实现 |
| DUAL-A-008 | 没有真实基金数据时不得伪造 | 全部 `/funds/*` | 明确“未接入”提示与安全空状态，不调用真实 Provider | `FundCenterPage.test.tsx` | Build A Portable Judge 待补 | 已实现 |

## 3. 路由结果

### 股票中心

- `/stocks`：现有股票分析首页；
- `/stocks/ask`：现有股票问答；
- `/stocks/portfolio`：只显示股票持仓；
- `/stocks/portfolio/manage`：股票高级管理；
- `/stocks/screening`：选股策略；
- `/stocks/advice`：股票 AI 建议；
- `/stocks/backtest`：股票回测；
- `/stocks/alerts`：股票告警。

### 基金中心

- `/funds`：基金中心首页；
- `/funds/ask`：基金问答独立入口；
- `/funds/portfolio`：只显示基金持仓；
- `/funds/compare`：基金筛选与对比骨架；
- `/funds/industry-exposure`：行业穿透骨架；
- `/funds/industry-cycle`：行业周期与景气度骨架；
- `/funds/advice`：基金仓位与风险建议骨架。

### 共用区域

- `/users`：用户管理；
- `/settings`：系统设置；
- `/usage`：模型用量。

## 4. 兼容与边界

- 旧 `/chat` 自动跳到 `/stocks/ask`，股票参数和查询字符串继续保留；
- 旧 `/portfolio` 按上次中心跳到股票或基金持仓；
- 旧选股、建议、回测、告警和股票高级管理路径跳到对应 `/stocks/*`；
- 股票后台任务完成提示只把 `/stocks/ask` 和兼容 `/chat` 视为股票问答页；
- 基金页面不复用股票 Chat，不请求真实基金数据，不生成买卖结论；
- 当前用户仍为内存状态，刷新后新增用户恢复，这是 Build E 持久化范围；
- Web 和桌面后端绑定、安全凭证及 Portable 目录结构均未修改。

## 5. 验证与回滚

最低验证：

```bash
cd apps/dsa-web
npm ci
npm test
npm run lint
npm run build
```

回滚时只撤销 Build A 新增页面、中心切换器、路由映射和持仓 domain 展示；现有股票 API、后端、Portable-M1、安全凭证和用户持仓状态模型不回退。
