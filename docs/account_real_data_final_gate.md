# 真实数据进入账户页面模型前最终安全闸门说明

## 1. 设计目标

`src/account_real_data_final_gate.py` 用于在真实数据进入账户页面模型前做最后安全检查。它只消费已经完成统一安全适配的汇总结果，不请求真实行情、不请求真实基金净值、不读取真实 `user_config`，也不写文件或保存真实数据。

## 2. 输入来源

输入来自 `account_real_data_unified_summary` 生成的统一汇总。该汇总应已经把股票 / ETF 与场外基金分成 `stock_etf`、`fund_nav` 两个 section，并提供 `safety_summary` 中的审计、展示适配、默认脱敏和仓库写入状态。

## 3. 检查规则

最终安全闸门会检查：

- audit：`safety_summary.all_results_audited` 必须为 `true`。
- display adapter：`safety_summary.all_display_models_checked` 必须为 `true`。
- redacted：默认展示必须为 `redacted`；若存在真实数据且未脱敏，则阻断。
- repository safety：真实数据不得写入 public repo，`real_data_written_to_repo` 必须为 `false`。
- secret：任何位置出现 token、api_key、webhook、cookie、authorization 等敏感字段都会阻断。
- 真实金额：任何位置出现 amount、cost_price、cost、position_value、account_value、balance、real_amount、real_cost 等真实金额 / 成本价 / 账户资产字段都会阻断。
- 场外基金措辞：场外基金不能写成“实时涨跌”“实时价格”“实时行情”或“盘中实时净值”，估算必须提示“盘中估算仅供观察，最终以基金公司公布净值为准。”。
- 字段边界：股票 / ETF 与场外基金字段必须分区，不得把基金净值字段混入股票行情 section，也不得把股票行情字段混入基金净值 section。
- 个人观察标签：最终安全闸门应区分“个人观察标签”和“强制交易指令”。买入观察、加仓观察、减仓观察、止盈观察、止损观察、清仓观察等可作为个人观察标签进入页面 payload；必须买入、保证收益、自动下单等强制交易、收益承诺或自动执行表达必须阻断。

## 4. 输出结果

`run_account_real_data_final_gate(summary)` 输出 `allowed`、`allowed_with_warnings` 或 `blocked`：

- `allowed`：所有阻断项通过，仅输出默认脱敏页面 payload。
- `allowed_with_warnings`：没有阻断项，但存在需要页面或后续接入方注意的警告。
- `blocked`：发现未审计、未展示适配、真实数据可能写仓库、secret、真实金额、字段混用等阻断风险，页面不得消费真实值。

## 5. 页面 Payload

`final_page_payload` 只用于后续页面消费，默认 `display_mode=redacted`。即使闸门通过，也只输出脱敏后的 `stock_etf` 与 `fund_nav` 展示模型；页面 payload 可以包含 `personal_observation_label`，但必须附带“本页面标签仅作为个人观察和记录，不自动下单，不构成强制交易指令。”；阻断时只输出 `payload_status=blocked`、空 sections、issues 和 warnings，不输出真实价格、真实基金净值、真实金额或 secrets。

## 6. 安全边界

本模块不请求真实数据、不保存真实数据、不写 public repo、不输出 secrets，不接日报 / 周报 / Discord，也不做真实网页 UI。它只是页面模型前的最终安全闸门，为后续页面接入提供可验证的安全结果。

## 7. 后续路线

- Web-P0：本地网页工作台入口规范。
- Web-P15：实时行情与基金净值看板。
- Web-P17：账户首页综合看板。
