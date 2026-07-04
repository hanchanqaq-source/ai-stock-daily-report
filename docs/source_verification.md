# 信息来源可查证规则

> 项目级产品规则见 `docs/product_rules.md`。

统一资产模型见 `docs/asset_model.md`，后续账户分组、个人雷达、网页工作台均应复用该模型。

## 1. 为什么需要这个规则

后续项目会继续建设股票 / 基金代码识别、标签补全、企业观察、个人影响雷达和网页工作台自动补全能力。这些能力会把输入代码、名称、市场、行业、概念、基金主题和用户标签转换为分析依据；如果系统凭感觉补全或编造，会直接污染日报、周报、个人雷达和企业观察结论。

因此，GLOBAL-R1 要求：所有股票、基金、企业、行业、概念、标签、市场归属和名称补全都必须可查证。能查到，才写成确定信息；查不到标记 `unknown`；不确定标记 `pending_confirmation`；多个来源冲突标记 `conflict`。本规则只建立结构、校验和测试约束，不要求本阶段联网查询。

## 2. 适用范围

本规则适用于所有后续资产识别、标签补全和个人化分析入口，包括：

- 股票代码识别
- 基金代码识别
- ETF 识别
- 港股 / 美股识别
- 企业名称识别
- 市场归属识别
- 行业标签
- 概念标签
- 基金主题
- 个人影响雷达
- 企业观察模块
- 网页工作台自动补全

## 3. 状态定义

- `verified`：已经通过至少一个可记录来源确认，且来源证据结构有效，可作为确定信息使用。
- `unknown`：未能从允许来源确认，不能填入猜测值，必须保留原因。
- `pending_confirmation`：存在候选值但置信度不足、来源不足或需要用户确认，不能进入正式分析结论。
- `conflict`：多个来源之间存在冲突，必须保留冲突来源或冲突说明，不能进入正式分析结论。

## 4. 置信度定义

- `high`：来源权威或多来源一致，字段可作为已确认事实使用。
- `medium`：来源可查但仍可能需要后续交叉验证，字段可作为候选信息，但使用场景应保持谨慎。
- `low`：来源不足、无法确认或需要用户确认，不得被写成确定事实。

置信度只能取 `high` / `medium` / `low`，不得使用其他自由文本。

## 5. 来源类型定义

来源证据结构统一包含：

```json
{
  "source_name": "公开数据来源名称",
  "source_type": "official / public_web / market_data / fund_data / manual_user_input / internal_history",
  "source_url": null,
  "checked_at": "YYYY-MM-DDTHH:MM:SS",
  "evidence_text": "可选的简短证据说明",
  "confidence": "high / medium / low"
}
```

允许的 `source_type`：

- `official`：交易所、基金公司、上市公司公告或其他官方来源。
- `public_web`：公开网页信息。
- `market_data`：公开市场行情或证券基础资料数据源。
- `fund_data`：公开基金资料或基金持仓资料数据源。
- `manual_user_input`：用户手动输入、确认或修改的内容。
- `internal_history`：系统历史中已经带来源与置信度的可追溯记录。

来源要求：`source_name` 不能为空；`source_type` 必须是允许值；`checked_at` 必须存在且格式稳定；`confidence` 必须是 `high` / `medium` / `low`；`source_url` 可以为空。不允许伪造“已查官方来源”，如果是手动输入必须使用 `manual_user_input`。

## 6. 不能做的事

- 不能编造股票名称。
- 不能编造基金名称。
- 不能编造企业名称。
- 不能编造行业标签。
- 不能编造概念标签。
- 不能编造基金持仓。
- 不能编造基金主题。
- 不能编造股票所属行业。
- 不能编造数据来源。
- 不能编造 `checked_at`。
- 不能把待确认信息当成事实。
- 不能把用户猜测当成公开事实。
- 不能把 `unknown` 当成 `verified`。
- 不能把 `pending_confirmation` 写入正式分析结论。
- 不能保存 webhook URL、Token、API Key、真实金额、成本价或账户资产作为来源证据。

## 7. 后续代码识别必须遵守的规则

后续实现代码识别或自动补全时，应先查基金，再查股票，再查其他资产类型；不得在没有来源证据时直接猜测代码含义、名称、市场、行业或标签。

自动补全字段统一使用以下结构：

```json
{
  "value": "沪电股份",
  "status": "verified / unknown / pending_confirmation / conflict",
  "confidence": "high / medium / low",
  "sources": [],
  "reason": "为什么这样判断"
}
```

正式分析可用性规则：

1. 资产识别结果整体 `status` 为 `verified`，才可以进入正式分析。
2. `asset_type` / `name` / `market` 至少都必须是 `verified`，才可以正式分析。
3. `tags` 中只有 `verified` 且带有效来源的标签可以参与正式分析。
4. 用户手动标签可以参与用户维度分析，但必须标明 `source_type=manual_user_input`。
5. `unknown`、`pending_confirmation`、`conflict` 标签不能参与正式分析。
6. 来源冲突必须标记 `conflict`。
7. 无法确认必须标记 `unknown`。
8. 置信度低或需要人工判断时必须要求用户确认。
9. 报告中必须避免把待确认信息写成确定事实。

## 8. 用户可编辑原则

自动识别和自动标签只是系统建议，不是不可变事实。用户必须可以确认、修改、删除系统建议标签；用户手动输入或确认的标签必须保留 `manual_user_input` 来源、置信度和确认原因，不能伪装成公开来源。

## 账户 / 分组模型衔接

账户 / 分组模型中的资产可以来自手工输入或后续自动识别。账户不代表实名用户，不需要邮箱、手机号或身份证；后续对 `assets` 进行代码识别、名称补全或标签建议时，必须继续遵守本文件的信息来源可查证规则：查不到为 `unknown`，不确定为 `pending_confirmation`，冲突为 `conflict`。
