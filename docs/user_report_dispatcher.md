# 多用户报告分发框架说明

`src/user_report_dispatcher.py` 是 P5-C 的公开仓库安全版 / dry-run 版多用户报告分发框架。当前阶段只基于 `config/examples/` 下的 example 配置生成结构化 delivery plan 和 Markdown demo，不接入正式日报、周报、Discord Webhook、GitHub Actions 定时任务、历史保存或归档清理。

## 当前 public 阶段边界

1. 当前 public 阶段只支持 example dry-run。
2. 当前不会发送真实 Discord。
3. 当前不会读取真实 webhook。
4. 当前不会保存真实用户数据、金额、成本价或账户资产。
5. 当前不会读取真实 `data/user_config/*.json`。
6. 当前不会输出直接交易建议。
7. 后续本地网页工作台可复用该框架管理用户报告，但真实配置必须保持在本地或 private 仓库。

## 配置安全规则

- Discord webhook 只能放在 GitHub Secrets 或本地环境变量中。
- JSON 配置里只能写 secret name，例如 `DISCORD_WEBHOOK_DEMO_USER`，不能写 URL。
- `private_discord_channel` 在当前 public 阶段只记录所需 secret name，不读取 secret 值，也不会发送消息。
- 真实用户配置、关注股票 / 基金 / 企业、任务组和个人分析结果只能放本地或 private 仓库。

## output_mode 说明

- `public_summary_only`：只生成公开摘要分发目标；当前只输出 dry-run 计划，`will_send=false`。
- `local_private_report`：后续用于本地网页工作台生成本地私人报告；当前 public 阶段不写真实私人报告，只输出 dry-run 计划。
- `private_discord_channel`：后续用于 private 仓库或本地环境的 Discord 私密频道推送；当前只输出 `secret_name`，不读取 webhook URL，不执行发送。

## 数据分层

GitHub 公共数据和本地私人配置继续分层：

- **GitHub**：公共行情、历史数据、归档摘要、公共日报 / 周报。
- **本地 / private 仓库**：真实用户配置、关注股票 / 基金 / 企业、任务组、个人分析结果、Discord webhook Secret 配置。

## 模块入口

`src/user_report_dispatcher.py` 提供以下能力：

- `build_delivery_plan(config_dir=None, dry_run=True)`：读取 example 配置并生成结构化分发计划。
- `build_delivery_plan_for_user(user_id, config_dir=None, dry_run=True)`：生成单个 example 用户的分发计划。
- `build_delivery_target(user, task_group, dry_run=True)`：根据 `output_mode` 生成 dry-run 分发目标。
- `validate_delivery_plan(plan)`：校验计划不包含 webhook URL、token、API key、邮箱、手机号、金额、成本价、账户资产等敏感内容，并确保 `will_send=false`。
- `render_delivery_plan_markdown(plan)`：渲染 demo Markdown 摘要，不写入真实私人报告。
- `load_demo_delivery_plan()`：加载公开安全 example 配置并生成 demo plan。

可选脚本：

```bash
python scripts/run_delivery_plan_demo.py
```

该脚本只加载 example 配置，只生成 dry-run delivery plan，并打印 Markdown demo；不会读取真实 `data/user_config`，不会读取 webhook，也不会发送 Discord。

后续所有资产识别、标签补全和个人雷达分析必须遵守 `docs/source_verification.md` 的信息来源可查证规则。
