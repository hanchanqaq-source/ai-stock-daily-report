# 公开仓库安全检查报告

> 项目级产品规则见 `docs/product_rules.md`。

## 1. 检查目标

P6-A 阶段的目标是在仓库仍可能为 public 的前提下，新增只读安全检查能力，确认仓库只保存公开市场数据、公开报告和 example 配置，不误提交真实用户配置、Webhook、Token、API Key、真实金额、成本价、账户资产或个人身份信息。

本检查脚本只负责扫描、分级和生成报告，不删除文件、不清理文件、不修改业务逻辑。

## 2. 允许公开保存的内容

- 公共行情数据。
- 历史市场数据。
- 归档摘要。
- 公共日报 / 周报。
- example 用户配置。
- example 任务组。
- example 关注列表。
- Secret 名称占位符，例如 `DISCORD_WEBHOOK_DEMO_USER` 或 `OPENAI_API_KEY_SECRET_NAME`。

## 3. 禁止提交的内容

- Discord Webhook URL。
- GitHub Token。
- OpenAI / DeepSeek / 其他 API Key。
- 真实用户配置。
- 真实持仓金额。
- 成本价。
- 账户资产。
- 手机号。
- 身份证。
- 私人邮箱。
- `.env`、`.env.local`、`.env.production` 等包含真实环境变量的文件。

## 4. 当前扫描规则

`scripts/security_scan.py` 默认扫描仓库文本文件，并跳过 `.git/`、缓存目录、虚拟环境、`node_modules/`、构建产物、图片、二进制文件和大型 artifact。当前规则包括：

- Discord Webhook URL：识别 `discord.com/api/webhooks/` 与 `discordapp.com/api/webhooks/`。
- GitHub Token：识别 `ghp_`、`github_pat_`、`gho_`、`ghu_`、`ghs_`、`ghr_` 前缀。
- API Key：识别 `sk-`、`sk-proj-` 以及常见 `OPENAI_API_KEY`、`DEEPSEEK_API_KEY`、`ZHIPU_API_KEY`、`API_KEY` 真实值。
- 私有配置路径：识别 `data/user_config/*.json`、`local_config/*.json`、`private_config/*.json`、`*.local.json`、`*.secret.json` 等非 example 路径。
- 金额与资产字段：在 JSON / YAML / ENV 中识别 `amount`、`asset`、`assets`、`balance`、`cost`、`cost_price`、`holding_amount`、`position_amount`、`profit`、`real_amount`、`account_value`、`账户资产`、`成本价`、`持仓金额`、`收益金额` 且带数值的内容。
- 个人信息：识别私人邮箱、中国手机号样式、身份证样式；允许 GitHub Actions bot 邮箱。
- 误报控制：文档安全说明、example/demo/sample 占位符、Secret 名称和 `.gitignore` 忽略规则不作为高风险泄露。

## 5. 发现结果

脚本输出包含 `scan_version`、`status`、`checked_files`、`findings` 和 `summary`，并对敏感值做脱敏处理。

- BLOCKER：几乎确定是真实密钥或真实 Webhook URL；默认导致命令失败。
- HIGH：疑似真实私人配置、真实密钥或真实个人敏感信息；默认导致命令失败。
- MEDIUM：可能敏感，需要人工确认；进入报告但不阻断命令。
- INFO：安全说明、占位符、example 或 ignore 规则；仅用于提示。

本次新增了扫描能力和测试。完整仓库扫描可通过以下命令执行：

```bash
python scripts/security_scan.py --json
```

如果发现 BLOCKER / HIGH，应先撤销或迁移敏感内容，再继续进入 private、真实用户配置或本地网页工作台阶段。

## 6. 后续建议

- P6-A：公开仓库安全检查。
- P6-B：仓库 private 迁移准备。
- P6-C：真实配置接入前安全确认。
- P6-D：本地网页工作台私人配置隔离。

建议在 P6-B 前将 `python scripts/security_scan.py --json` 纳入人工发布检查；在接入真实配置前，仍以 GitHub Secrets、本地 `.env` 和 private-only 配置目录作为唯一真实敏感信息入口。

后续所有资产识别、标签补全和个人雷达分析必须遵守 `docs/source_verification.md` 的信息来源可查证规则。
