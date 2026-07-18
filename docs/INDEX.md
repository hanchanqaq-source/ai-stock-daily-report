# 文档中心

这里是项目文档入口。README 负责项目概览和快速开始；更完整的配置、部署、功能说明和排障内容从这里进入。

## 按场景选择

| 我想要 | 先看 | 继续看 |
| --- | --- | --- |
| 快速了解项目能做什么 | [README](../README.md) | [完整配置与部署指南](full-guide.md) |
| 第一次把项目跑起来 | [小白客户端安装与配置](beginner-client-setup.md) | [完整配置与部署指南](full-guide.md) |
| 配置大模型渠道 | [LLM 配置指南](LLM_CONFIG_GUIDE.md) | [LLM 服务商配置指南](llm-providers.md) |
| 配置推送通知 | [通知能力基线](notifications.md) | [完整配置与部署指南](full-guide.md) |
| 部署到服务器或云平台 | [部署指南](DEPLOY.md) | [云端 WebUI 部署](deploy-webui-cloud.md)、[Zeabur 部署](docker/zeabur-deployment.md) |
| 使用 Bot / IM 接入 | [Bot 命令与接入](bot-command.md) | [Bot 平台配置](bot/) |
| 排查运行问题 | [FAQ](FAQ.md) | [更新日志](CHANGELOG.md) |
| 处理数据源失败或降级 | [数据源稳定性与故障处理图示](data-source-stability.md) | [FAQ](FAQ.md) |
| 参与开发或提交 PR | [贡献指南](CONTRIBUTING.md) | [API 规格](architecture/api_spec.json) |

## 快速开始

| 文档 | 内容 |
| --- | --- |
| [README](../README.md) | 项目定位、核心能力、快速开始、推送效果 |
| [小白客户端安装与配置](beginner-client-setup.md) | 面向不会代码用户的客户端下载、Anspire Open / AIHubMix 模型配置、新闻源配置和常见问题 |
| [完整配置与部署指南](full-guide.md) | 环境准备、运行方式、配置说明、部署路径和常见问题 |
| [FAQ](FAQ.md) | 常见配置、模型、通知、部署和运行问题 |
| [数据源稳定性与故障处理图示](data-source-stability.md) | Tushare、TickFlow、AkShare、Efinance、YFinance、Longbridge 等已接入源的使用场景、fallback 链路和推荐配置 |
| [更新日志](CHANGELOG.md) | 版本变化、能力调整和迁移说明 |
| [历史数据归档与清理规则](history-archive.md) | 月度归档摘要、机器摘要和清理候选清单 |

## 配置

| 文档 | 内容 |
| --- | --- |
| [LLM 配置指南](LLM_CONFIG_GUIDE.md) | 大模型渠道、三层配置、Web 设置页和常见模型配置 |
| [LLM 服务商配置指南](llm-providers.md) | Provider 预设、Actions 映射、错误分类和诊断建议 |
| [LiteLLM YAML 示例](examples/litellm_config.example.yaml) | LiteLLM 多渠道配置示例 |
| [通知能力基线](notifications.md) | 企业微信、飞书、Telegram、Discord、Slack、邮件等通知渠道配置 |
| [Tushare 股票列表指南](TUSHARE_STOCK_LIST_GUIDE.md) | Tushare 股票列表相关配置和使用说明 |

## 使用专题

| 文档 | 内容 |
| --- | --- |
| [Bot 命令与接入](bot-command.md) | Bot 命令、Webhook、平台接入和回调说明 |
| [Bot 平台配置](bot/) | 飞书、钉钉、Discord 等 Bot 配置截图和补充说明 |
| [实时告警中心](alerts.md) | EventMonitor 基线、Web 规则管理、通知结果、冷却状态和 Phase 边界 |
| [DecisionSignal 决策信号专题](decision-signals.md) | AI 建议池字段语义、API、Web 展示、告警/通知/组合风险联动、后验评估、脱敏、迁移与回滚 |
| [资讯 / 情报源](intelligence-sources.md) | RSS/Atom 合规资讯源配置、测试、拉取、去重、存储、查询与安全边界 |
| [分析上下文包契约、运行态消费与可见性](analysis-context-pack.md) | AnalysisContextPack 首版范围、字段质量状态、P1/P2 内部契约、P3 Prompt 摘要消费、P4 历史/API/Web 低敏可见性、P5 数据质量评分、P6 迁移回滚与源码锚点；完整指南补充 #1386 阶段感知分析、迁移与回滚入口 |
| [图片识别 Prompt](image-extract-prompt.md) | 图片识别股票信息的 Prompt 与使用边界 |
| [OpenClaw Skill 集成](openclaw-skill-integration.md) | OpenClaw / Skill 外部集成说明 |

## 部署与打包

| 文档 | 内容 |
| --- | --- |
| [部署指南](DEPLOY.md) | 服务器部署、Docker、systemd、Supervisor 等部署方式 |
| [云端 WebUI 部署](deploy-webui-cloud.md) | 云服务器访问 WebUI 的部署说明 |
| [Zeabur 部署](docker/zeabur-deployment.md) | Zeabur 平台部署说明 |
| [桌面端打包说明](desktop-package.md) | Electron 桌面端和 Web 构建产物打包说明 |

## 参考与开发

| 文档 | 内容 |
| --- | --- |
| [API 规格](architecture/api_spec.json) | FastAPI OpenAPI 规格产物 |
| [贡献指南](CONTRIBUTING.md) | Issue、PR、测试、文档同步和协作要求 |
| [Web mock-only 页面阶段收口说明](web_mock_only_phase_closeout.md) | Web-P21 到 Web-P29 mock-only 页面阶段完成内容、Windows 本地验证流程、安全边界总表和 Web-P31 前复核要求 |
| [Web-P32 mock 报告 schema 说明](web_mock_only_report_schema.md) | AI股票基金每日信息报告 mock-only schema、字段契约、字段映射、脱敏规则和未来真实日报接入前置条件 |
| [Web-P36 mock-only 日报链路阶段收口与验收清单](web_mock_only_daily_report_acceptance.md) | Web-P31 到 Web-P35 mock-only 日报链路、核心文件、安全边界、Windows 本地验证命令和 PR 复核清单 |
| [Web-P37 mock-only 页面预览入口与本地验收说明](web_mock_only_preview_entry_local_checks.md) | mock-only 页面入口、入口脚本、Windows 本地验收命令、127.0.0.1 人工预览方式和安全边界 |
| [Web-P38 真实日报接入前 schema 高规格复核](web_real_daily_report_schema_review.md) | 真实日报接入前的 schema 高规格复核清单、provider 前置条件、凭证与密钥管理、通知 dry-run、真实账户边界和回滚方案；当前仍保持 mock-only |
| [Web-P39～Web-P42.1 真实日报 dry-run 输入契约与链路复核](web_real_daily_report_dry_run_input_contract.md) | 真实日报 dry-run 输入 payload 字段结构、TypeScript 类型草案、validator、adapter、P39～P42 链路小总复核、providerName 脱敏、敏感字段边界和 mock-only 回退规则；当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易 |
| [Web-P43 provider 只读设计文档](web_provider_readonly_design.md) | provider 只读候选输入来源、安全边界、最小字段、输出脱敏、schema normalization、validator、adapter、mock-only fallback、凭证日志缓存超时重试降级和真实接入前置条件；当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易 |
| [Web-P44 provider 只读接口契约文档](web_provider_readonly_interface_contract.md) | provider 只读请求、响应、候选 payload、错误、超时重试缓存策略和日志字段的文档级契约；provider 输出仍必须经过脱敏、schema normalization、validator、adapter 和 mock-only fallback；当前仍不接真实 API / provider / AI / 通知 / 账户 / 数据库 / 交易 |
| [Web-P48 真实 provider 接入前安全复核](web_provider_pre_integration_safety_review.md) | 复核 P45～P47.1 mock-only 链路，记录 Go / No-Go 条件；当前真实 provider 状态为 NO-GO，下一步仅允许默认关闭 feature flag |
| [Core-M2 首个真实只读 Provider 本地 Dry-Run 基础框架](web_provider_readonly_local_dry_run_framework.md) | 统一只读 Provider Port、默认禁用 Provider、凭证状态边界、本地 Dry-Run Pipeline、mock-only fallback 与真实 Provider NO-GO 结论 |
| [Core-M2.1 Provider 结果脱敏与输入契约收口](web_provider_readonly_local_dry_run_framework.md#core-m21-provider-result-脱敏与输入契约收口) | Provider Result runtime sanitizer、固定低敏错误映射、非法 Provider Result blocked 与 Pipeline 顶层未知字段优先阻断 |
| [Web-M1B Provider Dry-Run 安全门禁闭环](web_provider_dry_run_gate_closure.md) | Provider Dry-Run feature flag、candidate normalizer、dry-run validator 的 mock-only 安全门禁闭环；当前未接页面、runtime 或真实 provider，真实 provider 状态仍为 NO-GO |
| [App-M4.1 设置工作台骨架](app_m4_1_settings_workspace_shell.md) | 既有 Web 设置页内嵌的三个静态页签；既有设置功能继续保留，无真实密钥保存、无 App-M4.1 配置持久化、无网络请求，App-M4.2 尚未开始 |
| [App-M4.2.1 服务端敏感字段契约和统一脱敏](app_m4_2_1_sensitive_contract_and_masking.md) | schema 驱动的服务端敏感字段脱敏、keep/set/clear 更新语义、掩码占位保护和本阶段未启用真实 Provider / DPAPI / 本地迁移边界 |
| [App-M4.2.2 前端敏感字段安全交互](app_m4_2_2_frontend_sensitive_interaction.md) | Web 设置页敏感字段 keep/set/clear 交互、明确修改/取消/清除、掩码占位保护、非敏感字段兼容和未启用真实 Provider / DPAPI / 本地迁移边界 |
| [App-M4.2.3A Windows 桌面端安全凭证存储基础](app_m4_2_3a_windows_secure_credential_store.md) | Electron 主进程 safeStorage 加密、LOCALAPPDATA 凭证文件、IPC/preload 最小边界和本阶段未接 SettingsPage / 后端 / Provider 的安全说明 |
| [App-M4.2.3A.1 Windows DPAPI / safeStorage 本地实机 Smoke 验收工具](app_m4_2_3a_1_windows_dpapi_smoke.md) | Windows 本机两阶段 write / restart-read-clear Smoke、临时 LOCALAPPDATA 隔离、磁盘无明文检查、低敏输出、BAT 入口和 mock 测试不等于 DPAPI 实机通过的说明 |
| [股票基金双中心 Build D1：AKShare 基金公开数据只读接入](stock_fund_dual_center_build_d1.md) | 基金首页本机手动只读查询、基金概况/正式净值/披露持仓到 Build C 契约的映射、逐次确认、localhost 门禁、离线测试与 Build D2/D3 边界 |
| [股票基金双中心 Build D2：基金对比与披露行业穿透](stock_fund_dual_center_build_d2.md) | 1–4 只基金手动只读比较、基金披露行业配置、集中度、前十大持仓重合下限、日期警告、安全门禁与 Build D3/D4 边界 |
| [股票基金双中心 Build D3：行业周期与经营生产力代理证据](stock_fund_dual_center_build_d3.md) | 1–4 只基金手动只读周期证据、固定阈值阶段、经营生产力代理、证据日期/置信度/缺失项、安全门禁与 Build D4 边界 |
| [股票基金双中心 Build D4：组合风险与配置建议](stock_fund_dual_center_build_d4.md) | 当前用户基金组合集中度、重合、周期风险、目标偏离、证据覆盖与人工复核建议 |
| [股票基金双中心 Build E1：本地数据库持久化](stock_fund_dual_center_build_e1.md) | 用户、股票快速持仓、基金快速持仓的本机 SQLite 持久化、隔离、恢复与侧栏完整显示 |
| [股票基金双中心 Build E2：本机数据备份与恢复](stock_fund_dual_center_build_e2.md) | 工作台用户与股票/基金快速持仓的 JSON 导出、预览校验、确认覆盖导入和本机恢复点；不含密钥或设置 |
| [App-M4.2.4A 桌面 Setup Status 安全凭证状态接入](app_m4_2_4a_desktop_setup_status_credentials.md) | Electron 设置页基于 DPAPI configured 状态向后端提交低敏 overlay，由后端复用既有 Setup Status 规则计算首次设置状态；不回显明文、不注入 Provider。 |

## 多语言

| 文档 | 内容 |
| --- | --- |
| [英文文档索引](INDEX_EN.md) | English documentation index |
| [英文 README](README_EN.md) | English project overview and quick start |
| [繁中 README](README_CHT.md) | 繁體中文項目概覽與快速開始 |

| [Core-M3 AkShare 公开 A 股真实只读 Dry-Run](core_m3_akshare_public_market_readonly_dry_run.md) | 默认关闭、本地人工批准、单标的 A 股公开行情 Dry-Run 链路；Core-M3.2 显式禁用东财补丁并绕过通用 Config |
