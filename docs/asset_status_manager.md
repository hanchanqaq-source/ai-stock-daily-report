# 资产状态管理说明

## 1. 设计目标

资产状态管理用于在账户 / 分组内表达资产从持有、收藏、清仓、归档到删除标记的状态变化。当前阶段只提供后端逻辑、预览结果、确认保护、结构化执行结果、文档和测试，不做真实网页页面，不读取真实用户配置，不接入日报 / 周报 / Discord，也不保存真实金额、成本价或账户资产。

## 2. 状态定义

- `holding`：持有中，显示在当前持有列表。
- `watching`：收藏 / 观察，显示在收藏或观察列表，不代表真实持有。
- `cleared`：已清仓，不再显示为当前持有，但保留历史记录。
- `archived`：已归档，默认不显示在主页面，但保留记录。
- `deleted`：删除标记，属于危险状态；本阶段不物理删除文件或资产记录。

## 3. 状态流转规则

允许的流转包括：

- `watching -> holding`
- `holding -> watching`
- `holding -> cleared`
- `watching -> archived`
- `cleared -> watching`
- `cleared -> archived`
- `archived -> watching`
- `watching -> deleted`
- `cleared -> deleted`
- `archived -> deleted`

`holding -> deleted` 属于高风险谨慎流转。本阶段没有二次确认机制时，默认只返回阻断或需要二次确认结果，不直接执行。

风险等级约定：

- `low`：`watching -> holding`、`holding -> watching`、`cleared -> watching`。
- `medium`：`holding -> cleared`、`watching -> archived`、`cleared -> archived`、`archived -> watching`。
- `high`：所有进入 `deleted` 的删除标记流转，其中 `holding -> deleted` 需要二次确认。

## 4. 预览确认规则

所有清仓、归档、删除等危险操作必须遵守“先预览 → 说明影响 → 用户确认 → 再执行”。默认 `confirm=false`，只返回 `preview` 或 `blocked`，不得修改输入分组。只有调用方显式传入 `confirm=true`，且状态流转安全可执行时，才返回 `applied`、`updated_asset` 和 `updated_group`。

预览结果必须包含 `from_status`、`to_status`、`risk_level`、`impact`、`requires_confirm`、`safe_to_apply` 和 `warnings`，方便后续网页工作台展示确认文案。

## 5. 删除规则

本阶段 `deleted` 只是状态标记，不物理删除文件，也不从 `assets` 列表移除记录。真正删除属于高风险操作，后续网页工作台必须二次确认，并应明确说明影响范围、恢复方式和不可逆风险。

## 6. 清仓规则

资产设为 `cleared` 后不再显示为当前持有，但仍保留在已清仓记录中。清仓是状态变化，不代表删除历史记录，也不保存真实金额、成本价或账户资产。

## 7. 收藏规则

`watching` 表示收藏 / 观察，不代表真实持有。收藏资产可以后续设为持有，也可以归档或标记删除；所有危险操作仍需先预览再确认。

## 8. 后续路线

- P5-I：持有 vs 收藏对比分析。
- P5-J：动态基金 / 股票页面逻辑。
- Web-P11：资产删除 / 清仓 / 归档管理。
