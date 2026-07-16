# 股票基金双中心 Build C 基金数据契约与验收

## 1. 原因

Build A/B 已完成双中心入口和运行期持仓分域，但基金中心仍缺少统一的数据事实边界。若直接进入基金对比、行业周期或建议，页面容易混用不同日期的数据、把旧持仓当成实时持仓、强行归类未知行业，或者把测试 fixture 当作正式结论。

Build C 只建立可审计的数据契约和 Provider 边界，不连接真实 Provider，不请求网络，不读取账户、密钥或真实配置，也不生成基金分析和买卖建议。

## 2. 处理

- 新增统一 `FundDataSource`，每个事实区块必须携带来源、抓取时间、生效日或报告期、过期状态、置信度、缺失字段和字段级缺失原因；
- 新增基金资料契约：代码、名称、类型、基金经理、规模、规模币种/单位、成立日期；
- 新增净值快照契约，并与既有基金净值框架保持 `unit_nav`、`accumulated_nav`、`daily_change_pct`、`nav_date` 等字段语义一致；
- 新增披露持仓契约：报告期、证券、权重、已披露合计及行业映射；
- 行业映射明确区分 `mapped`、`unknown`、`ambiguous`、`unmapped`，未知项不得强行写成“其他”；
- 新增 Provider Protocol，正式默认实现只返回“真实基金数据尚未接入”的可审计缺失状态；
- 测试 fixture 必须带 `test_fixture` 双重标记，并且调用方显式开启测试门禁才可通过契约验证；
- Provider 异常、返回其他基金代码、改变请求区块或违反契约时 fail closed，不向正式页面暴露错误载荷；
- 基金中心显示 Build C 契约状态，但仍明确不接真实数据、不生成分析结论。

## 3. 需求追踪矩阵

| 需求编号 | 用户要求 | 页面 / 数据 / 实现 | 自动测试 | Windows 证据 | 状态 |
|---|---|---|---|---|---|
| DUAL-C-001 | 基金事实必须标明来源和日期 | `/funds/*`、`FundDataSource` | `test_fund_data_contract.py`、`FundCenterPage.test.tsx` | Build C Portable Judge 待补 | 已实现 |
| DUAL-C-002 | 基金资料字段统一 | `FundProfile` | `test_fund_data_contract.py` | Build C Portable Judge 待补 | 已实现契约，真实数据未接入 |
| DUAL-C-003 | 净值和净值日期不能混淆 | `FundNavSnapshot`，复用既有 NAV 字段语义 | `test_fund_data_contract.py` | Build C Portable Judge 待补 | 已实现契约，真实数据未接入 |
| DUAL-C-004 | 披露持仓、权重和报告期可核对 | `FundHoldingsSnapshot` / `FundHoldingPosition` | `test_fund_data_contract.py` | Build C Portable Judge 待补 | 已实现契约，真实数据未接入 |
| DUAL-C-005 | 未知行业不能强行归类 | `FundIndustryMapping` unresolved 状态保持空值并说明缺失原因 | `test_fund_data_contract.py` | Build C Portable Judge 待补 | 已实现 |
| DUAL-C-006 | Provider 接口和实现分离 | `FundDataProvider` Protocol / `UnavailableFundDataProvider` | `test_fund_data_contract.py` | Build C Portable Judge 待补 | 已实现，未提供真实实现 |
| DUAL-C-007 | Mock/fixture 只能用于测试 | `allow_test_fixture` 显式门禁，正式默认返回缺失 | `test_fund_data_contract.py` | Build C Portable Judge 待补 | 已实现 |
| DUAL-C-008 | 基金对比、周期、生产力和建议 | Build D 页面与分析模块 | Build D 覆盖 | Build D 覆盖 | 延期至 Build D，未声称完成 |
| DUAL-C-009 | 用户与基金数据重启后仍存在 | Build E 数据库、迁移、备份和回滚 | Build E 覆盖 | Build E 覆盖 | 延期至 Build E，未声称完成 |

## 4. Provider 与 fixture 边界

- `FundDataProvider` 是 Build C 的基金资料/净值/披露持仓统一入口；
- 当前没有真实 Provider 实现，也没有对外 API endpoint；
- 不传 Provider 时使用 `UnavailableFundDataProvider`，返回 `not_connected` 和全部请求区块的缺失原因；
- Provider 返回的数据必须先通过 `validate_fund_data_bundle`；
- 测试 fixture 只存在于测试代码，正式模块不包含示例基金事实；
- 仓库既有基金净值实验模块继续保持默认关闭/测试性质，本阶段不把它接到基金中心页面或新的统一入口。

## 5. 验证

最低验证：

```bash
python -m py_compile src/fund_data_contract.py src/fund_data_provider.py
python -m pytest tests/test_fund_data_contract.py

cd apps/dsa-web
npm test -- --run src/pages/__tests__/FundCenterPage.test.tsx
npm run lint
npm run build
```

Judge 必须核对：

- 正式默认结果没有测试净值、测试持仓或测试行业；
- 测试 fixture 未显式授权时被阻断；
- 未知行业保持未知并有缺失原因；
- 净值日期与披露报告期分别存在，不能互相替代；
- Provider 异常或错误基金代码 fail closed；
- Windows Portable 仍使用 packaged backend、仅绑定 `127.0.0.1` 并加载基金中心资源；
- 未把 Build C 契约误标为 Build D 分析能力或 Build E 持久化完成。

## 6. 明确未包含

- 真实基金 Provider、网络请求或公开数据抓取；
- 基金对比、行业穿透计算、行业周期、景气度、生产力证据或仓位建议；
- 数据库、刷新/重启持久化、schema 迁移、备份和回滚；
- 真实账户、AI、通知、自动交易或 Release。

## 7. 回滚

只回滚 Build C 新增的基金数据契约、Provider 门禁、基金中心状态说明、测试和文档；不回滚 Build A/B 双中心、用户持仓隔离、现有股票功能或 Windows Portable-M1。
