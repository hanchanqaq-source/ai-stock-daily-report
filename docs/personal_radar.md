# 个人股票 / 基金影响雷达说明

> 项目级产品规则见 `docs/product_rules.md`。

个人股票 / 基金影响雷达当前处于 public 仓库安全 demo 阶段，只支持读取仓库内的 example 配置，用于验证后续本地网页工作台或 private 仓库复用的基础分析框架。

## 当前边界

- 仅读取 `config/examples/users.example.json`、`config/examples/task_groups.example.json`、`config/examples/watchlists.example.json`。
- 不读取真实 `data/user_config/*.json` 个人配置。
- 不保存真实持仓、金额、成本价、账户资产或任何账户级数据。
- 不输出直接交易建议，只输出“观察”类影响提示。
- 不接入正式日报、正式周报、Discord Webhook、GitHub Actions 定时任务、自动历史保存或归档清理。

## 分析方式

雷达根据 example 关注对象的 `tags` 匹配公共市场信号，公共信号来源包括历史趋势、板块 / 概念持续性、风险雷达和观察清单等现有模块。匹配规则保持简单、稳定、可测试：

- `positive_signal`：标签命中持续走强、市场升温或观察清单扩散方向。
- `risk_signal`：标签命中冲高回落、持续走弱或风险雷达方向。
- `neutral_signal`：标签命中短线爆发或轮动扩散方向。
- `insufficient_data`：历史样本不足、数据质量过低或无法匹配有效信号。

缺少历史数据或缺少 example 配置时，模块返回 `insufficient_data`，不会报错，也不会编造信号。

## 输出形式

`src/personal_radar.py` 提供结构化结果和 Markdown 示例报告渲染能力。结构化结果包含 radar 版本、状态、示例用户 / 任务组 / 关注列表标识、数据日期、关注对象影响、信号来源、原因、观察点和数据提示。每条 signal 都包含 `source` 与 `reason`。

Markdown 示例报告标题为“示例个人影响雷达”，明确标注示例报告，不包含真实金额、成本价、账户资产，也不包含买卖类建议。

## 公共数据与本地私人配置分层

后续 private 仓库或本地网页工作台可以在保持安全边界的前提下接入真实用户配置，但 GitHub 公共数据与本地私人配置需要继续分层：

- GitHub：公共行情、历史数据、归档摘要、公共日报 / 周报。
- 本地：真实用户配置、关注股票 / 基金 / 企业、任务组、个人分析结果。

public 仓库阶段不得把本地私人配置、个人分析结果、Webhook、Token、API Key、真实邮箱、手机号、身份证、金额、成本价或账户资产写入仓库。

后续所有资产识别、标签补全和个人雷达分析必须遵守 `docs/source_verification.md` 的信息来源可查证规则。

## 账户 / 分组模型衔接

后续个人雷达的主要输入将逐步从多用户示例配置收敛到账户 / 分组 / 投资组合模型。账户不代表实名用户，不需要邮箱、手机号或身份证；账户中的 `assets` 将用于表达基金、股票、企业、行业、主题和指数等观察对象。
