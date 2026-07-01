# 个人 AI 盯盘日报新手使用说明

> 适用场景：你已经 Fork 了 `daily_stock_analysis`，希望先不改核心代码，只通过 GitHub Secrets / Variables 配置成自己的 A 股、港股、美股、基金日报系统。
>
> 安全提醒：本文只写配置名称和示例格式，不包含任何真实 API Key、Token、密码或 Webhook。请不要把真实密钥提交到仓库。

## 1. 这个项目主要能做什么

这个项目是一个基于 AI 大模型的股票智能分析与推送系统，主要流程是：

1. 读取你的自选股列表 `STOCK_LIST`。
2. 拉取行情、K 线、技术指标、资金流、新闻、公告、基本面等信息。
3. 调用你配置的 AI 模型生成分析报告。
4. 生成自选股日报 / 大盘复盘。
5. 通过企业微信、飞书、Telegram、Discord、Slack、邮件等渠道推送。
6. 可通过 GitHub Actions 定时运行，也可以本地运行 `python main.py`。

适合个人使用的常见方式：

- **GitHub Actions 自动日报**：不用服务器，配置好 Secrets 后每天自动运行。
- **手动触发一次分析**：在 GitHub Actions 页面点 `Run workflow`。
- **本地调试**：复制 `.env.example` 为 `.env`，填写本地环境变量后运行。
- **后续扩展**：把 `STOCK_LIST` 改成你的 A 股、港股、美股、ETF / 基金代码组合。

## 2. 我需要配置哪些 GitHub Secrets

进入你的 Fork 仓库：

`Settings` → `Secrets and variables` → `Actions`

你会看到两个常用入口：

- **Secrets**：放 API Key、Token、Webhook、密码等敏感信息。
- **Variables**：放不敏感配置，例如股票列表、模型名、开关、超时时间等。

### 最小可用配置

建议先只配置下面三类：

| 类型 | 名称 | 建议位置 | 说明 |
| --- | --- | --- | --- |
| 自选股 | `STOCK_LIST` | Variables 或 Secrets | 你的股票代码列表，例如 `600519,hk00700,AAPL`。推荐放 Variables，若你不想公开自选股也可放 Secrets。 |
| AI 模型 Key | 任选一个：`ANSPIRE_API_KEYS` / `AIHUBMIX_KEY` / `GEMINI_API_KEY` / `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` | Secrets | 至少配置一个，否则无法调用 AI 生成报告。 |
| 推送渠道 | 任选一个：`WECHAT_WEBHOOK_URL` / `FEISHU_WEBHOOK_URL` / `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` / `DISCORD_WEBHOOK_URL` / `SLACK_BOT_TOKEN` + `SLACK_CHANNEL_ID` / `EMAIL_SENDER` + `EMAIL_PASSWORD` | Secrets | 至少配置一个，方便收到日报。 |

### 推荐增强配置

| 类型 | 名称 | 建议位置 | 说明 |
| --- | --- | --- | --- |
| 搜索新闻 | `ANSPIRE_API_KEYS` / `SERPAPI_API_KEYS` / `TAVILY_API_KEYS` / `BOCHA_API_KEYS` / `BRAVE_API_KEYS` / `MINIMAX_API_KEYS` | Secrets | 新闻、公告、催化因素和舆情分析会更完整。 |
| A 股数据 | `TUSHARE_TOKEN` | Secrets | 可选，增强 A 股数据。 |
| 港美股数据 | `LONGBRIDGE_APP_KEY`、`LONGBRIDGE_APP_SECRET`、`LONGBRIDGE_ACCESS_TOKEN` 或 OAuth 相关变量 | Secrets | 可选，增强港股 / 美股行情字段。 |
| 运行超时 | `ANALYSIS_TIMEOUT_MINUTES` | Variables | 默认工作流超时来自 workflow 配置，可按自选股数量调整。 |

> 新手建议：先配置 `STOCK_LIST` + 一个 AI Key + 一个推送渠道，确认能跑通后，再逐步增加搜索和数据源配置。

## 3. 如何配置 AI 模型 API Key

项目支持多种模型服务。新手不需要一次配置全部，任选一种即可。

### 方案 A：Anspire

适合想用一个 Key 同时覆盖模型和搜索的新手。

在 GitHub Actions Secrets 中新增：

```text
ANSPIRE_API_KEYS=你的 Anspire Key
```

可选：如果你需要指定 Anspire 网关或模型，可在 Variables 中配置：

```text
ANSPIRE_LLM_MODEL=模型名
ANSPIRE_LLM_BASE_URL=服务地址
ANSPIRE_LLM_ENABLED=true
```

### 方案 B：AIHubMix

在 GitHub Actions Secrets 中新增：

```text
AIHUBMIX_KEY=你的 AIHubMix Key
```

### 方案 C：Gemini

在 GitHub Actions Secrets 中新增：

```text
GEMINI_API_KEY=你的 Gemini Key
```

可选在 Variables 中指定模型：

```text
GEMINI_MODEL=模型名
```

### 方案 D：OpenAI 兼容接口

如果你使用 OpenAI、DeepSeek、通义千问、Kimi、硅基流动、OpenRouter 等兼容 OpenAI 协议的服务，常见配置是：

```text
OPENAI_API_KEY=你的 API Key
OPENAI_BASE_URL=服务商的兼容 API 地址
OPENAI_MODEL=模型名
```

其中：

- `OPENAI_API_KEY` 建议放 Secrets。
- `OPENAI_BASE_URL` 和 `OPENAI_MODEL` 可放 Variables；如果你认为它们敏感，也可以放 Secrets。

### 本地运行时怎么配

本地运行不要改代码，复制模板即可：

```bash
cp .env.example .env
```

然后只在本机 `.env` 中填写真实 Key。不要把 `.env` 提交到仓库。

## 4. 如何配置自选股 `STOCK_LIST`

`STOCK_LIST` 是最重要的业务配置，决定每天分析哪些标的。

### GitHub Actions 推荐配置

进入：

`Settings` → `Secrets and variables` → `Actions` → `Variables` → `New repository variable`

新增：

```text
Name: STOCK_LIST
Value: 600519,hk00700,AAPL
```

如果你不想让自选股显示在 Variables 中，也可以放到 Secrets，同名为 `STOCK_LIST`。

### 代码格式示例

| 市场 | 示例 | 说明 |
| --- | --- | --- |
| A 股 | `600519`、`000001`、`300750` | 直接写 6 位代码。 |
| 港股 | `hk00700`、`hk09988` | 建议使用 `hk` + 5 位代码。 |
| 美股 | `AAPL`、`MSFT`、`NVDA` | 直接写美股 ticker。 |
| 日本 / 韩国股票 | `7203.T`、`005930.KS` | README 中提到支持 `.T`、`.KS`、`.KQ` 后缀。 |

多个标的用英文逗号分隔，不要用中文逗号：

```text
600519,300750,hk00700,AAPL,MSFT
```

### 手动运行时临时指定股票

本地命令行可以临时覆盖：

```bash
python main.py --stocks 600519,hk00700,AAPL
```

这适合调试，不建议为了个人日报去修改核心代码。

## 5. 如何配置推送渠道

项目支持多个推送渠道，可同时配置多个。新手建议先选一个最容易接收的渠道。

### 企业微信机器人

Secrets：

```text
WECHAT_WEBHOOK_URL=企业微信机器人 Webhook
```

适合企业微信群或个人测试群。

### 飞书机器人

简单群机器人方式：

```text
FEISHU_WEBHOOK_URL=飞书自定义机器人 Webhook
```

如果飞书机器人开启了签名校验，还需要：

```text
FEISHU_WEBHOOK_SECRET=飞书签名密钥
```

如果开启了关键词校验，可配置：

```text
FEISHU_WEBHOOK_KEYWORD=股票日报
```

### Telegram

Secrets：

```text
TELEGRAM_BOT_TOKEN=机器人 Token
TELEGRAM_CHAT_ID=聊天 ID
```

如果是论坛话题，可选：

```text
TELEGRAM_MESSAGE_THREAD_ID=话题 ID
```

### 邮件

Secrets / Variables：

```text
EMAIL_SENDER=发件邮箱
EMAIL_PASSWORD=邮箱授权码或密码
EMAIL_RECEIVERS=收件邮箱，多个可按项目支持格式填写
```

建议：

- `EMAIL_PASSWORD` 必须放 Secrets。
- `EMAIL_SENDER`、`EMAIL_RECEIVERS` 如果不敏感可放 Variables，保守起见也可放 Secrets。

### Discord / Slack / PushPlus / ntfy / Gotify / AstrBot

常见配置名：

```text
DISCORD_WEBHOOK_URL=Discord Webhook
SLACK_WEBHOOK_URL=Slack Webhook
SLACK_BOT_TOKEN=Slack Bot Token
SLACK_CHANNEL_ID=Slack Channel ID
PUSHPLUS_TOKEN=PushPlus Token
NTFY_URL=ntfy topic URL
NTFY_TOKEN=ntfy Token（可选）
GOTIFY_URL=Gotify 服务地址
GOTIFY_TOKEN=Gotify Token
ASTRBOT_URL=AstrBot Webhook 地址
ASTRBOT_TOKEN=AstrBot Token（可选）
```

## 6. 如何手动运行一次 GitHub Actions 测试

1. 打开你的 Fork 仓库页面。
2. 点击顶部 `Actions`。
3. 如果第一次使用 Actions，点击启用工作流。
4. 在左侧选择 **每日股票分析**。
5. 点击右侧 `Run workflow`。
6. 选择运行参数：
   - `mode=full`：股票分析 + 大盘复盘。
   - `mode=market-only`：只跑大盘复盘。
   - `mode=stocks-only`：只跑自选股分析。
   - `force_run=true`：强制运行，跳过交易日检查；周末或节假日测试时建议打开。
7. 点击绿色 `Run workflow` 按钮。
8. 运行完成后查看：
   - 日志中的配置检查结果。
   - `reports/` 和 `logs/` artifact。
   - 你配置的推送渠道是否收到消息。

如果第一次测试失败，优先检查：

- `STOCK_LIST` 是否为空或格式错误。
- 是否至少配置了一个 AI API Key。
- 推送渠道 Token / Webhook 是否正确。
- 免费模型、搜索或数据源是否额度耗尽。

## 7. 如何以后改成我自己的 A 股、港股、美股、基金日报

不要改核心分析逻辑，优先通过配置完成。

### 第一步：整理自己的标的池

示例：

```text
# A 股 + 港股 + 美股
600519,300750,000001,hk00700,hk09988,AAPL,NVDA,MSFT
```

如果你关注 ETF / 基金，可先按项目和数据源支持的代码格式尝试加入 `STOCK_LIST`。不同数据源对基金、ETF、跨市场代码的支持可能不一致，建议一次少量增加并手动运行验证。

### 第二步：按市场补充数据源

- A 股：可选配 `TUSHARE_TOKEN`、TickFlow 等增强源。
- 港股 / 美股：可选配 Longbridge、YFinance 相关增强源。
- 新闻和舆情：建议配置至少一个搜索服务，例如 `ANSPIRE_API_KEYS`、`SERPAPI_API_KEYS`、`TAVILY_API_KEYS`。

### 第三步：控制自选股数量

自选股越多：

- 运行时间越长。
- AI 调用成本越高。
- 搜索和行情接口更容易触发限流。

建议新手先从 3～5 个标的测试，稳定后再扩展到 10～30 个。

### 第四步：保留 GitHub Actions 自动运行

当前每日分析工作流默认在工作日北京时间 18:00 附近运行，并支持手动触发。你通常只需要改配置，不需要改 workflow。

## 8. 哪些内容不能直接写进代码

以下内容不要写进 Python、Markdown、YAML、README、截图、Issue、PR 描述或提交记录中：

- AI 模型 API Key，例如 `OPENAI_API_KEY`、`GEMINI_API_KEY`、`DEEPSEEK_API_KEY`。
- 搜索服务 Key，例如 `SERPAPI_API_KEYS`、`TAVILY_API_KEYS`。
- 数据源 Token，例如 `TUSHARE_TOKEN`、Longbridge 相关密钥。
- 推送 Webhook，例如企业微信、飞书、Discord、Slack Webhook。
- Telegram Bot Token、Slack Bot Token、Gotify Token、PushPlus Token。
- 邮箱密码、邮箱授权码、Cookie、账号密码。
- 私有代理地址、内网服务地址、个人身份信息。

正确做法：

- GitHub Actions 用 **Secrets** 保存敏感值。
- 不敏感的开关、模型名、自选股可放 **Variables**。
- 本地调试用 `.env`，但不要提交 `.env`。
- 文档里只写占位符，例如 `sk-xxx`、`your_token_here`，不要写真实值。

## 9. 不要上传任何真实密钥

提交前建议检查：

```bash
git status
git diff -- . ':!.env'
```

确认：

- 没有新增 `.env`。
- 没有真实 Key、Token、Webhook、密码。
- 没有把 GitHub Secrets 页面截图提交到仓库。
- 没有把个人报告中包含的敏感持仓信息提交到仓库。

如果不小心提交过真实密钥：

1. 立即去对应平台作废 / 轮换密钥。
2. 删除代码中的密钥。
3. 视情况清理 Git 历史。
4. 重新配置 GitHub Secrets。

## 10. 不要修改核心分析逻辑

个人 Fork 初期建议只改：

- GitHub Secrets / Variables。
- 本地 `.env`。
- 个人说明文档，例如本文件。
- 自己的部署说明或运行记录。

暂时不要改：

- `src/` 下的核心分析流程。
- `data_provider/` 下的数据源 fallback 逻辑。
- `api/`、`bot/` 的接口和推送实现。
- `.github/workflows/00-daily-analysis.yml` 的核心执行步骤。
- 报告 prompt、评分规则、交易纪律等分析语义。

等你确认系统能稳定生成个人日报后，再考虑小范围修改，并且每次修改都要先看 README、`.env.example`、workflow、入口文件和相关文档，避免配置和实际执行逻辑不一致。

## 快速配置清单

新手可以按这个顺序配置：

1. `STOCK_LIST`：先填 3 个以内标的，例如 `600519,hk00700,AAPL`。
2. AI Key：任选一个，例如 `ANSPIRE_API_KEYS`、`AIHUBMIX_KEY`、`GEMINI_API_KEY`、`DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`。
3. 推送渠道：任选一个，例如 `WECHAT_WEBHOOK_URL` 或 `FEISHU_WEBHOOK_URL`。
4. 手动运行 GitHub Actions：选择 `mode=stocks-only`，周末测试时打开 `force_run=true`。
5. 看日志和 artifact，确认生成报告。
6. 再逐步增加搜索源、数据源和更多股票。
