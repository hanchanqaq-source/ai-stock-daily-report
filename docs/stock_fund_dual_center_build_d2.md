# 股票基金双中心 Build D2：基金对比与披露行业穿透

## 1. 原因

Build D1 已能按用户逐次确认读取单只基金的公开资料、正式净值和最新披露前十大持仓，但“基金投什么、主要行业是什么、集中度多高、两只基金是否重复”仍缺少可核验的计算入口。

Build D2 只完成基金对比与行业穿透的事实层。行业周期、景气度和生产力证据属于 Build D3，用户组合风险与配置建议属于 Build D4；本阶段不得用对比结果替代后续结论。

## 2. 数据来源与口径

| 数据区块 | AKShare 官方接口 | Build D2 用途 | 口径 |
| --- | --- | --- | --- |
| 基金资料 | `fund_overview_em` | 名称、类型、经理、规模 | 复用 Build D1 契约 |
| 正式净值 | `fund_open_fund_info_em` | 单位净值、累计净值、日期 | 不使用盘中估值 |
| 披露持仓 | `fund_portfolio_hold_em` | 最新披露前十大、前十大集中度、持仓重合下限 | 按最新可用季度；不是完整组合 |
| 行业配置 | `fund_portfolio_industry_allocation_em` | 主要行业、已披露行业合计、前三行业集中度、行业重合 | 直接使用基金披露行业类别，不从证券名称猜测 |

每条结果携带 Provider、抓取时间、净值日期、持仓报告期或行业配置截止日期。当前年无披露时可回退上一年；单一区块失败只降级该区块，不泄露上游异常。

## 3. 计算定义

### 3.1 集中度

- 前十大持仓集中度：最新披露前十大持仓的 `占净值比例` 之和；
- 前三行业集中度：同一行业配置截止日期内，权重最大的三个披露行业之和；
- 已披露行业合计：当前展示行业权重之和；超过 `100.5%` 的异常响应被拒绝，不自动缩放为 100%。

### 3.2 两基金重合

- 披露持仓重合下限：共同证券逐项取两只基金披露权重的较小值，再求和；
- 披露行业重合：共同披露行业逐项取较小权重，再求和；
- 持仓报告期、行业截止日期或净值日期不同，结果必须显示警告；
- 前十大持仓重合只代表披露下限，不得显示为完整持仓重合度。

## 4. 页面行为

- `/funds/compare`：输入 2–4 个不重复六位基金代码，展示基金资料、净值、集中度、主要行业、前十大持仓和两两重合；
- `/funds/industry-exposure`：输入 1–4 个不重复六位基金代码，展示基金披露行业配置与集中度；
- 两个页面都不自动请求；每次读取都需要用户重新勾选只读确认；
- 结果只保存在当前页面内存，刷新后清空；
- 单只证券行业不通过名称推测，基金首页的前十大持仓指向独立行业穿透页查看基金级披露配置。

## 5. 需求追踪矩阵

| 编号 | 用户要求 | 实现 | 自动测试 | 状态 |
| --- | --- | --- | --- | --- |
| DUAL-D2-001 | 股票/基金功能分区 | 仅 `/funds/compare` 与 `/funds/industry-exposure` | `FundCenterPage.test.tsx` | 已实现 |
| DUAL-D2-002 | 看基金主要投什么 | 披露行业配置 + 最新前十大持仓 | `test_fund_comparison.py` | 已实现 |
| DUAL-D2-003 | 看行业集中度 | 已披露行业合计、前三行业集中度 | `test_fund_comparison.py` | 已实现 |
| DUAL-D2-004 | 看持仓是否重复 | 共同证券与披露重合下限 | `test_fund_comparison.py` | 已实现，明确非完整组合 |
| DUAL-D2-005 | 比较主要行业重复 | 共同披露行业与较小权重求和 | `test_fund_comparison.py` | 已实现 |
| DUAL-D2-006 | 日期和来源可核对 | 净值日期、持仓报告期、行业截止日、抓取时间 | 后端契约测试 + 页面测试 | 已实现 |
| DUAL-D2-007 | 未知行业不能强行归类 | 直接采用披露行业；缺失时保持缺失 | 失败降级与异常总权重测试 | 已实现 |
| DUAL-D2-008 | 行业周期/生产力 | Build D3 的轻量、可解释证据模块 | Build D3 | 未包含 |
| DUAL-D2-009 | 组合配置建议 | Build D4 当前用户组合风险模块 | Build D4 | 未包含 |

## 6. 安全边界

- 后端只接受 `127.0.0.1`、`::1` 或测试客户端；
- 请求严格限制 1–4 个六位基金代码和固定数据区块；
- `allowAccountRead`、`allowTrading`、`allowNotificationSend`、`allowAiCall`、`allowPersistence` 必须全部为 `false`；
- 不读取 `.env`、密钥、账户或真实用户配置；
- CI 只使用注入的假 AKShare 模块，不访问真实网络；
- 不接 Microsoft Qlib 依赖；Build D3 只借鉴其市场状态/周期识别思想；
- 不生成行业周期、生产力、仓位、买卖或自动执行建议。

## 7. 验证

```bash
python -m py_compile src/fund_comparison.py src/fund_data_akshare_provider.py api/v1/endpoints/provider_readonly.py
python -m pytest tests/test_fund_comparison.py tests/test_api_fund_comparison_readonly.py

cd apps/dsa-web
npm test -- --run src/api/fundData.test.ts src/pages/__tests__/FundCenterPage.test.tsx
npm run lint
npm run build
```

Judge 还必须核对 Windows Portable ZIP、SHA-256、中文桌面 EXE、打包后端 EXE、`127.0.0.1`、packaged backend、主页面加载，以及产物内存在 Build D2 基金页面资源。

## 8. 回滚

只回滚 Build D2 新增的基金比较服务、只读比较 API、比较/行业穿透页面、测试和本文档；Build D1 单基金公开数据读取、Build A/B/C 双中心和数据契约、股票功能及 Windows Portable-M1 保持不变。
