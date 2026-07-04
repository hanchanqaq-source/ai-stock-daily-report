# 多用户配置系统说明

本页说明 P5-A 多用户配置系统的公开仓库安全边界。当前阶段只提供 example 配置、读取、校验与基础敏感信息扫描，不接入日报、周报、Discord 推送或任何个人雷达分析。

## Public / Private 分层

- **GitHub public 仓库**：只提交公共行情、历史数据、归档摘要、公共日报 / 周报，以及 `config/examples/*.example.json` 示例配置。
- **本地或 private 仓库**：保存真实用户关注股票、基金、企业、任务组和后续个人分析结果。
- **后续本地网页工作台**：将读取本地 `data/user_config/` 或其他 private 配置目录，而不是 public 仓库中的真实个人配置。
- **后续个人雷达**：会在该配置系统基础上扩展，但不会要求把私人配置提交到 public 仓库。

## 示例配置

公开仓库只允许提交以下 example 文件：

- `config/examples/users.example.json`
- `config/examples/task_groups.example.json`
- `config/examples/watchlists.example.json`

这些文件只能使用示例用户、示例股票、示例基金和示例企业，不应包含真实姓名、邮箱、手机号、持仓、金额、成本价、账户资产、webhook URL、Token 或 API Key。

## 真实配置存放建议

真实配置可以在本地或 private 仓库中使用类似目录：

```text
data/user_config/
local_config/
private_config/
```

这些路径中的 JSON 文件会被 `.gitignore` 忽略。需要分享真实配置时，请使用 private 仓库、加密密钥库或团队内部安全配置系统。

## Secrets 与隐私规则

- Discord webhook 只能保存到 GitHub Secrets，JSON 中只能写 Secret 名称，例如 `DISCORD_WEBHOOK_DEMO_USER`，不允许写入 webhook URL。
- Token、API Key、OpenAI / DeepSeek 等模型服务密钥只能放在 GitHub Secrets 或本地 `.env`，不允许写进 JSON 配置。
- 不建议保存真实金额、成本价、账户资产、收益率或其他可反推出个人投资情况的字段。
- 配置读取和校验函数不会打印 secrets、webhook 或 token 值；发现疑似敏感信息时只返回脱敏位置说明。

## 当前可用函数

`src/user_config.py` 提供以下基础能力：

- `load_user_config(config_dir=None)`：默认读取 example 配置；传入本地目录时读取本地配置，目录不存在则返回空配置。
- `load_example_user_config()`：读取公开安全的 example 配置。
- `validate_user_config(config)`：校验用户配置结构、风险偏好和 webhook secret 名称。
- `validate_task_groups(config)`：校验任务组类型、报告类型和输出模式。
- `validate_watchlists(config)`：校验关注列表条目类型、代码和标签结构。
- `get_enabled_users(config)`：返回启用用户。
- `get_task_group_by_id(config, task_group_id)`：按 ID 查找任务组。
- `get_watchlist_by_id(config, watchlist_id)`：按 ID 查找关注列表。
- `scan_config_for_sensitive_values(config)`：扫描 webhook URL、GitHub token、API Key、邮箱、手机号、身份证样式和金额 / 成本 / 账户类字段。

## 当前不做的事情

P5-A 不会执行以下行为：

- 不生成个人日报或个人周报。
- 不把用户配置接入正式日报 / 周报主流程。
- 不做多 webhook 或 Discord 私人频道推送。
- 不接入数据库、SQLite、DeepSeek 或新数据源。
- 不保存真实个人数据、真实金额、成本价、账户资产、webhook URL、Token 或 API Key。
