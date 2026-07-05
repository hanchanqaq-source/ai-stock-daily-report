# 资产实时行情能力标记说明
场外基金净值 / 估算涨跌抓取框架见 `docs/fund_nav_provider.md`。场外 fund 不进入股票 / ETF 实时行情框架；场外 fund 只能展示净值 / 估算净值，不能称为实时涨跌。
A股指数矩阵与体感指标见 `docs/cn_market_indicators.md`。A股中位数涨跌幅、上涨家数占比等属于系统计算指标，非官方指数。
全球市场指数矩阵与页面切换模型见 `docs/market_index_matrix.md`。官方指数和系统计算指标必须分开展示，系统计算指标必须标注“非官方指数”。韩股指数矩阵与体感指标见 `docs/kr_market_indicators.md`；韩股中位数涨跌幅、上涨家数占比等属于系统计算指标，非官方指数；韩股体感指标不照搬 A 股涨跌停差逻辑。美股指数矩阵与广度指标见 `docs/us_market_indicators.md`；美股中位数涨跌幅、NYSE上涨家数占比、Nasdaq上涨家数占比等属于系统计算指标，非官方指数；美股体感指标不照搬 A 股涨跌停差逻辑。

## 1. 设计目标

资产实时行情能力标记用于判断统一资产模型中的资产理论上适合展示哪类行情模式，并输出结构化 `quote_capability`。本模块只做能力标记，不负责真实行情抓取，不联网，不接入 AKShare、yfinance、东方财富、天天基金、支付宝或其他数据源，也不保存真实价格、涨跌幅、净值、金额、成本价或账户资产。

该能力用于后续账户页、行情抓取框架和汇总视图复用：当前只回答“这个资产应该展示哪种行情模式”，不回答“当前价格是多少”。

## 2. 股票 / ETF 规则

股票（`stock`）适合展示实时 / 接近实时涨跌，`price_mode` 为 `realtime_quote`。适用市场包括 `CN`、`HK`、`US`、`JP`、`KR`。具体延迟、字段和可查证来源以后由数据源接入阶段决定。

ETF / 场内基金（`etf`）适合展示交易所实时或接近实时行情，`price_mode` 为 `exchange_realtime_quote`。可展示语义包括交易所行情、最新价、涨跌幅等，但当前阶段只输出能力标记，不输出真实行情。

指数（`index`）适合展示指数行情，`price_mode` 为 `index_quote`。指数行情同样需要后续接入可查证数据源。

## 3. 场外基金规则

普通场外基金（`fund`）不支持真正实时涨跌，不能写成实时涨跌、实时价格、交易所最新价或实时净值。

场外基金只能展示：

- 净值
- 估算净值
- 估算涨跌
- 最终以基金公司公布净值为准

因此 `fund` 的能力标记为：

- `realtime_supported = false`
- `exchange_quote_supported = false`
- `daily_nav_supported = true`
- `intraday_estimate_supported = true`
- `price_mode = estimated_nav_or_daily_nav`

## 4. price_mode 定义

- `realtime_quote`：股票实时 / 接近实时行情能力。
- `exchange_realtime_quote`：ETF / 场内基金 / 交易所品种实时或接近实时行情能力。
- `index_quote`：指数行情能力。
- `daily_nav`：场外基金每日净值能力。
- `estimated_nav`：场外基金盘中估算净值能力。
- `estimated_nav_or_daily_nav`：优先展示估算净值，无法获取估算时展示每日净值。
- `unsupported`：当前资产类型不支持直接展示行情。
- `unknown`：资产类型或市场未知，暂不展示行情。

## 5. 后续路线

- P5-L：股票 / ETF 实时涨跌抓取框架。
- P5-M：场外基金净值 / 估算涨跌抓取框架。
- P5-N：账户资产实时涨跌汇总。
- Web-P14：实时行情看板。
港股指数矩阵与体感指标见 docs/hk_market_indicators.md。港股中位数涨跌幅、上涨家数占比等属于系统计算指标，非官方指数；港股体感指标不照搬 A 股涨跌停差逻辑。
