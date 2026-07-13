# Core-M3：AkShare 公开 A 股真实只读 Dry-Run

Core-M3 为“股票基金质量分析系统”增加首个范围受限的真实只读数据链路，日报显示名称固定为“AI股票基金每日信息报告”。首个真实数据源为 AkShare 公开 A 股行情，仅覆盖单个 A 股公开日线 / 最新可用交易日快照。

## 授权范围

仅允许用户本地手动触发、单个六位 A 股代码、AkShare 公开市场数据、无 Token/API Key/Cookie/账户凭证、结果只进入 Dry-Run。失败时只可回退 mock-only。不得读取账户、持仓、券商接口，不得交易、通知、AI 调用、数据库写入、定时运行、云端自动请求或 GitHub Actions 真实联网测试。

## 为什么选择 AkShare

仓库既有 `data_provider` 已包含 AkShare fetcher 和 `DataFetcherManager` 统一日线获取入口。Core-M3 复用该路径，不在 Web 端直接调用 AkShare，不硬编码东方财富 URL，也不复制新的行情抓取实现。

## 链路

显式开启 `REAL_READONLY_PROVIDER_ENABLED=true` 后，本地 Web Port 只能请求 `http://127.0.0.1:8000/api/v1/provider-readonly/akshare/dry-run`，FastAPI endpoint 校验 localhost、人工批准和请求契约，再调用 Python `DataFetcherManager.get_daily_data()`，生成最小公开行情快照，经过后端 sanitizer 和 Web sanitizer 后转换为 `sourceType=real-readonly` 的 `RealDailyReportDryRunInput`。

## 默认关闭与人工批准

`.env.example` 中 `REAL_READONLY_PROVIDER_ENABLED=false`。请求必须同时满足 `humanApproved=true`、`mode=real-readonly-dry-run`、`provider=akshare-public-market`，并固定禁止账户读取、交易、通知、AI 和持久化。

## 数据字段与脱敏

快照只保留：代码、名称、交易日、开高低收、上一收盘或涨跌幅、成交量、成交额、延迟/只读/脱敏标记。响应固定 `providerLabel=REDACTED_PROVIDER_LABEL`，不得返回 DataFrame 原对象、原始字典、URL、endpoint、headers、cookies、traceback、本机路径、账户、持仓或交易数据。

## 状态

- `completed-real-readonly`：真实公开只读数据通过双重 sanitizer。
- `completed-mock-only-fallback`：Provider unavailable/timeout 时 Web 可使用既有 mock-only fallback。
- `blocked`：未批准、非法代码、非法响应、字段漂移或 validator 阻断。
- `disabled`：Web 真实只读入口未显式启用。

## 不生成投资建议

Dry-Run 只展示事实型公开行情：名称/代码、最新可用交易日、开高低收、成交量/成交额，以及可合法计算的涨跌幅。固定不生成买入、卖出、加仓、减仓、清仓、目标价、收益预测、AI 结论、自动风险评级或个人持仓操作。

## 本地 smoke

1. 以 `127.0.0.1` 启动后端并显式设置 `REAL_READONLY_PROVIDER_ENABLED=true`。
2. 手动传入一个公开 A 股六位代码。
3. POST 到 `/api/v1/provider-readonly/akshare/dry-run`。
4. 只检查状态、公开代码、公开名称、交易日期、是否使用真实公开数据、是否 fallback、固定错误码。

本次 Codex 未执行真实网络 smoke，原因：真实第三方请求仅允许用户本地手动批准后运行。

## 回滚方式

删除 Core-M3 新增 endpoint、service、Web Port、真实只读 sanitizer/normalizer/tests/docs，并保持 `REAL_READONLY_PROVIDER_ENABLED=false` 即可回到 Core-M2 mock-only 行为。

## Core-M4 前置条件

扩展到基金和组合前，需要先定义基金公开字段契约、组合输入去个人化规则、跨标的速率限制、更多 provider unavailable/timeout 观测，以及正式页面接入前的单独安全评审。
