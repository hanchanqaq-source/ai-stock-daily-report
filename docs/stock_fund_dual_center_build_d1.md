# 股票基金双中心 Build D1：AKShare 基金公开数据只读接入

## 1. 原因

Build A/B/C 已完成双中心、用户持仓分域和基金数据契约，但基金页面此前只有安全空状态。Build D1 将 AKShare 官方文档公开的基金概况、正式净值和季度披露持仓适配到 Build C 契约，形成用户可见的最小真实数据闭环。

本阶段不做基金比较、行业判断、Qlib 模型、AI 建议或持久化。行业映射没有可核验来源时保持 `unknown`，不得按证券名称猜行业。

## 2. 用户操作与安全门禁

- 只在基金首页提供“手动读取”入口，不自动请求；
- 用户必须输入六位基金代码并逐次勾选只读确认；
- API 仅接受 `127.0.0.1`、`::1` 或测试客户端；
- 请求固定声明 `readOnly=true`；
- 账户读取、交易、通知、AI 和持久化必须全部为 `false`；
- 返回结果只保存在当前页面内存，刷新后清空；
- CI 只使用注入式固定数据，不请求 AKShare 或其他真实网络；
- Provider 异常和超时只返回固定低敏错误，不向页面透传第三方异常。

## 3. AKShare 接口与字段映射

| Build C 区块 | AKShare 接口 | 读取字段 | 缺失策略 |
|---|---|---|---|
| 基金资料 | `fund_overview_em` | 基金全称、类型、经理、资产规模、成立日期 | 缺失字段逐项记录原因 |
| 正式净值 | `fund_open_fund_info_em` | 单位净值、累计净值、日增长率、净值日期 | 只合并同一净值日期；盘中估算保持缺失 |
| 披露持仓 | `fund_portfolio_hold_em` | 最新季度前十大股票代码、名称、净值权重 | 当前年无数据时回退上一年；无有效记录则区块缺失 |
| 行业映射 | Build D2 | 暂无 | `unknown`，不得强行归为“其他” |

## 4. 需求追踪矩阵

| 需求编号 | 用户要求 | 实现 | 自动测试 | Windows 证据 | 状态 |
|---|---|---|---|---|---|
| DUAL-D1-001 | AKShare 真正用于基金公开数据 | `AkshareFundDataProvider` | `test_fund_data_akshare_provider.py` | Build D1 Portable Judge 待补 | 已实现适配器 |
| DUAL-D1-002 | 用户可在基金区域找到功能 | 基金首页“读取公开基金数据” | `FundCenterPage.test.tsx` | Build D1 Portable Judge 待补 | 已实现 |
| DUAL-D1-003 | 只允许本机手动只读请求 | `/provider-readonly/akshare/fund` | `test_api_fund_public_readonly.py` | Build D1 Portable Judge 待补 | 已实现 |
| DUAL-D1-004 | 数据必须带来源和日期 | Build C `FundDataSource` | Provider 契约测试 | Build D1 Portable Judge 待补 | 已实现 |
| DUAL-D1-005 | 不能伪造行业 | 持仓行业为 `unknown` 并记录 D2 缺失原因 | Provider 契约测试、页面测试 | Build D1 Portable Judge 待补 | 已实现 |
| DUAL-D1-006 | 失败不能泄漏第三方异常 | 分区降级、固定超时与低敏错误 | Provider/endpoint 测试 | Build D1 Portable Judge 待补 | 已实现 |
| DUAL-D1-007 | Qlib 周期思路进入基金分析 | Build D3 | Build D3 覆盖 | Build D3 覆盖 | 未开始，不声称完成 |
| DUAL-D1-008 | 基金数据刷新后仍存在 | Build E | Build E 覆盖 | Build E 覆盖 | 未开始，不声称完成 |

## 5. 验证

```bash
python -m py_compile src/fund_data_akshare_provider.py api/v1/endpoints/provider_readonly.py
python -m pytest tests/test_fund_data_akshare_provider.py tests/test_api_fund_public_readonly.py

cd apps/dsa-web
npm test -- --run src/api/fundData.test.ts src/pages/__tests__/FundCenterPage.test.tsx
npm run lint
npm run build
```

Judge 必须确认：

- 页面首次加载不会请求 AKShare；
- 六位代码和逐次确认缺一不可；
- 非 localhost 请求在 Provider 调用前被阻断；
- CI 日志没有真实 AKShare 网络请求；
- ZIP 中包含基金页面资源；
- Windows Smoke 仍为 packaged backend、`127.0.0.1`、健康检查 200 和主页面加载成功；
- Build D1 没有被误报为行业穿透、Qlib 周期、建议或持久化完成。

## 6. 回滚

回滚 Build D1 适配器、只读 endpoint、基金首页查询卡片、测试和文档即可。Build A/B/C、股票功能、Windows Portable、安全凭证和其他 Provider 不回滚。
