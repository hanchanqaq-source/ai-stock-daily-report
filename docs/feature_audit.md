# AI 股票基金日报系统功能盘点报告

> 审计范围：基于当前工作区 `work` 分支（本容器未配置远端 `origin/main` ref，已执行 `git fetch --all --prune`，没有可拉取的远端 main）对 README、docs、main.py、指定 `src/*` 文件、`.github/workflows/`、Web/应用目录与 tests 做静态盘点。本报告只总结现状，不修改业务逻辑、不新增功能、不删除旧代码。

## 0. 结论摘要

- **已真实可用**：公共日报生成、Markdown 报告落盘与 artifact 上传、Discord Webhook 推送、Discord 报告摘要压缩、A 股与多市场大盘复盘、数据质量检查、非交易日/未开盘兜底、repository_dispatch 触发日任务、Web 管理台/历史报告预览、历史分析记录/API/Web 查询、周报基础生成。
- **部分可用**：周报增强、近几日变化、历史快照长期仓库、Discord 操作面板、command executor、Discord Bot listener、图片通知路径、个人持仓/组合页面。
- **仅有入口或预留**：Discord Bot listener 需要手动部署；重推日报指令已识别但未真正重发；网页“工作台入口索引与目录规范”尚未形成独立规范；公共日报/周报图片卡片没有完整端到端产物；多用户个人雷达还不是独立成型能力。
- **重复风险最高**：A 股数据抓取、多市场指数映射、日报 Markdown 渲染、Discord 摘要/报告生成、历史快照/历史记录、配置读取与数据质量判断。

## 1. 当前已真实可用功能

| 功能名称 | 相关文件 | 是否有测试 | 是否被 GitHub Actions / 主流程调用 | 当前状态 |
| --- | --- | --- | --- | --- |
| 公共日报生成 | `main.py`、`src/core/pipeline.py`、`src/notification.py` | 有，覆盖主流程、通知、报告渲染等多组测试 | `main.py` 默认入口；`.github/workflows/00-daily-analysis.yml` 定时/手动/repository_dispatch 调用 | 可用 |
| Discord Webhook 推送 | `src/notification.py`、`.env.example`、`.github/workflows/00-daily-analysis.yml`、`docs/notifications.md` | 有，`tests/test_notification.py` 覆盖通道、失败隔离、Discord 摘要等 | 日报 workflow 注入 `DISCORD_WEBHOOK_URL` 并调用通知服务 | 可用 |
| Discord 精简摘要 | `src/notification.py` 中 `format_discord_report_summary()` 与 report route 摘要逻辑 | 有，`tests/test_notification.py` 覆盖摘要裁剪与运行信息 | 通知服务在 Discord report route 中启用 | 可用 |
| 完整 Markdown artifact | `src/notification.py` 的 `save_report_to_file()`、`.github/workflows/00-daily-analysis.yml` 的 `actions/upload-artifact` | 有，通知/报告相关测试覆盖文件名和报告内容片段；workflow 本身未本地执行 | 日报 workflow 上传 `reports/` | 可用 |
| A 股核心数据 | `data_provider/akshare_fetcher.py`、`tencent_fetcher.py`、`efinance_fetcher.py`、`tushare_fetcher.py`、`src/market_analyzer.py`、`src/core/pipeline.py` | 有，多数据源、行情、fallback 与市场分析测试 | 主流程和大盘复盘通过 `DataFetcherManager`/pipeline 调用 | 可用，但依赖三方数据稳定性 |
| 全球指数数据 | `src/market_analyzer.py`、`src/core/market_profile.py`、`data_provider/us_index_mapping.py`、多市场 fetcher | 有，`tests/test_market_analyzer_generate_text.py` 覆盖多区域 market light；部分指数映射有单测 | `--market-review` 与日任务大盘复盘调用 | 可用/部分可用：A 股更完整，HK/US/JP/KR 宽度与涨跌停维度较弱 |
| 数据质量检查 | `src/data_quality.py`、`src/data_fallback.py`、`src/notification.py` | 有，数据质量与通知摘要相关测试 | 报告/通知链路可消费 | 可用 |
| 非交易日 / 未开盘兜底 | `main.py` 的交易日过滤与跳过通知、`src/data_fallback.py`、`src/market_analyzer.py` 的最近交易日/暂缺状态 | 有，主流程/market analyzer/fallback 测试覆盖 | workflow 可通过 force run 或交易日判断控制 | 可用，但节假日/海外市场仍需持续验证 |
| 周报功能 | `main.py --report-type weekly`、`src/weekly_report.py`、`src/market_history.py`、`.github/workflows/weekly-analysis.yml`、`.github/workflows/00-daily-analysis.yml` | 有，`tests/test_weekly_report.py` 覆盖样本不足、5 日指标、文件名 | `main.py` 与 workflow 都有入口 | 部分可用：基础周报可生成，指数表现仍有占位缺口 |
| 近几日变化 | `src/weekly_report.py`、`src/market_history.py`、`data/history` 约定、Web 历史趋势组件 | 有，周报和历史趋势相关测试 | 周报读取历史快照；Web 历史页读取 API | 部分可用：以周报/历史记录消费为主，还不是统一的 5 日/20 日趋势策略模块 |
| repository_dispatch | `src/github_dispatcher.py`、`src/command_executor.py`、`.github/workflows/00-daily-analysis.yml` | 有，`tests/test_command_executor.py` 覆盖 payload、token 缺失、dry-run | workflow 监听 `run-stock-report` | 可用 |
| Discord 操作面板 | `src/notification.py` 的 `DISCORD_OPERATION_PANEL` 与指令解析、`src/command_executor.py` | 有，command executor 与解析测试覆盖 | 主流程会在报告中展示/输出操作面板相关文案，但实际交互依赖 bot listener | 部分可用 |
| command executor | `src/command_executor.py`、`src/github_dispatcher.py` | 有，`tests/test_command_executor.py` | 不由日报主流程直接执行；由 Discord Bot listener 或人工调用 | 部分可用：重跑 dispatch 可用，重推日报仍是 planned |
| Discord Bot listener | `src/discord_command_bot.py` | 有，`tests/test_discord_command_bot.py` 覆盖消息过滤与执行器边界 | 明确不被 `main.py` 或计划任务导入，需要手动 `python -m src.discord_command_bot` | 预留/部分可用：代码可运行但未部署即不可交互 |
| 历史快照 / 历史数据 | `src/repositories/*history*`、`src/services/history_service.py`、`api/v1/endpoints/history.py`、`apps/dsa-web/src/api/history.ts`、`src/weekly_report.py` | 有，API/Web/run-flow/周报多组测试 | API/Web 主流程写入与读取；周报读取 `data/history` 快照 | 部分可用：已有分析历史与快照读取，但长期统一存储策略未收敛 |
| 网页预览 / 网页工作台 | `main.py --serve/--serve-only`、`server.py`、`api/`、`apps/dsa-web/`、`apps/dsa-desktop/` | 有，Web unit/e2e/API 测试较多 | 可由本地 serve 或桌面端调用；非日报 workflow 主产物 | 可用/部分可用：Web 管理台已存在，未来“本地网页工作台入口索引”需规范边界 |
| 图片卡片 | `src/notification.py` 图片通道判断、`docs/assets/*` 示例图、Web 卡片组件样式 | 有少量通知路径测试 | 通知服务有图像发送判断，但日报/周报图片卡片未形成主流程产物 | 预留/部分可用 |
| 多用户个人雷达 | `api/v1/endpoints/portfolio.py`、`src/services/portfolio_*`、`apps/dsa-web/src/pages/PortfolioPage.tsx`、alerts/portfolio API | 有，portfolio API/Web/alerts 测试 | Web/API 可用；日报主流程不按多用户生成个人雷达 | 部分可用/预留：组合管理存在，个人雷达未独立成型 |

## 2. 只有入口但尚未完整接通的功能

- **Discord 重推日报**：`execute_command_text()` 能识别 `resend_latest`，但返回状态为 `planned`，说明“实际重发将在 Discord Bot 接入后启用”。这是入口存在、执行未接通。
- **Discord Bot listener**：`src/discord_command_bot.py` 注释说明不被 `main.py` 或 scheduled workflow 导入，只能手动运行。当前更像可部署组件，不是默认线上能力。
- **Discord 操作面板完整闭环**：操作面板文案、命令解析、GitHub dispatch payload 均存在；但用户在 Discord 里发命令后能否被监听，取决于单独 bot 进程、token、频道白名单和权限。
- **周报增强**：周报能根据历史快照生成核心指标和板块统计，但指数表现 `_index_judgement()` / `_index_lines()` 仍返回 `数据暂缺`，因此不是完整周报增强。
- **近 5 日 / 20 日趋势分析**：已有周报 5 日样本、Web 历史趋势和历史 API，但尚未看到独立、统一、可复用的 5 日/20 日趋势分析模块与主流程稳定输出契约。
- **历史数据仓库**：已有 DB 历史、context snapshot、`data/history` 快照和周报读取；但日报大盘快照、分析历史、Web 历史、周报历史之间还不是同一套长期仓库契约。
- **网页预览 vs 本地网页工作台**：当前 `apps/dsa-web/` 是完整 Web 管理台，支持历史、报告 Markdown、设置、聊天、组合、告警、回测等页面；“工作台入口索引与目录规范”尚未单独文档化，未来不应再新建平行 web/app/dashboard 入口。
- **图片卡片**：仓库中有 `docs/assets` 示例图和通知图片路径判断，但没有公共日报/周报图片卡片的端到端生成、上传、推送和回归测试链路。
- **多用户个人雷达**：portfolio/alerts/analysis context 已具备基础，但 public 日报与个人持仓影响雷达没有明确多用户隔离、配置存储、安全边界和通知路由契约。
- **README 展示性能力**：README 和 docs 中提及 WebUI、桌面端、Bot、告警、组合、AlphaSift 等多个能力；部分属于已有后台能力，部分需配置三方服务或单独部署，不能默认等同于日任务已启用。

## 3. 可能重复的功能

| 重复方向 | 重复位置 | 当前推荐保留 | 暂时不要删除 | 后续合并建议 |
| --- | --- | --- | --- | --- |
| 多套 A 股数据抓取 | `data_provider/akshare_fetcher.py`、`efinance_fetcher.py`、`tencent_fetcher.py`、`tushare_fetcher.py`、`baostock_fetcher.py`、`pytdx_fetcher.py`、pipeline 中上下文预取 | 保留 `DataFetcherManager` 统一调度与现有 fetcher fallback | 不删除任何 fetcher；三方数据源稳定性互补 | 明确每个 fetcher 的首选场景、字段标准化表、fallback 优先级和失败诊断 |
| 多套全球指数映射 | `src/core/market_profile.py`、`src/market_analyzer.py`、`data_provider/us_index_mapping.py`、各 fetcher 内置 symbol | 保留 `market_profile` 作为区域/指数口径入口 | 不删除 `us_index_mapping.py`，可能仍被 fetcher 依赖 | 建议把区域指数清单、显示名、数据源 symbol 映射集中成单一契约 |
| 多套历史快照读取 | DB `analysis_history`、`context_snapshot`、`data/history` JSON、`src/market_history.py` 对 `weekly_report` 的兼容导出、Web history API | 保留 API/DB 历史作为 Web 与分析详情主入口；保留 `data/history` 供周报快照短期使用 | 不删除 `src/market_history.py`，它是兼容 import path | P2-A 应统一“日报快照/市场快照/分析历史”的长期存储与导出策略 |
| 多套日报 Markdown 渲染 | `src/notification.py` 直接拼 Markdown、`src/services/report_renderer.py`、`src/report_renderer.py` 兼容导出、Web `ReportMarkdown*` | 保留 `src/services/report_renderer.py` 作为新 renderer 入口，保留通知 fallback | 不删除 notification 内 fallback 渲染，避免破坏旧配置 | 渐进把 dashboard/brief/WeChat/Discord 公共块收敛到 renderer 模板，先补快照测试 |
| 多套 Discord 摘要生成 | `format_discord_report_summary()`、`NotificationService.generate_brief_report()`、`weekly_report._render_discord_summary()`、操作面板文案 | 保留 Discord report route 摘要函数与 weekly summary | 不删除 brief report，它服务非 Discord 或其他路由 | 建议定义“Discord 日报摘要”和“通用 brief report”的边界，避免互相复刻格式 |
| 多套周报逻辑 | `src/weekly_report.py`、`src/market_history.py` 兼容层、workflow 中 `report_type=weekly`、README/docs 说明 | 保留 `src/weekly_report.py` | 不删除 `src/market_history.py` | 周报增强应在 `weekly_report.py` 内完成，避免新建平行 weekly renderer |
| 多套网页入口 | `apps/dsa-web/`、`apps/dsa-desktop/`、`server.py`/`main.py --serve`、docs/assets 演示图、未来 Web-P0 | 保留 `apps/dsa-web/` 作为唯一 Web 前端，`apps/dsa-desktop/` 只包装 Web | 不删除桌面端；不新建 `web/`、`frontend/`、`dashboard/` 平行目录 | Web-P0 先写入口索引和目录规范，再做新页面 |
| 多套配置读取 | `.env`/`src/config.py`、`main.py` runtime reload、workflow inputs/client_payload、Web system config | 保留 `src/config.py` 为配置真源 | 不删除 workflow 参数解析，Actions 仍需要 | 新增配置必须同步 `.env.example`、docs 和 Web settings 帮助，避免三处漂移 |
| 多套数据质量判断 | `src/data_quality.py`、`src/data_fallback.py`、market light `data_quality`、analysis context pack quality、通知摘要质量说明 | 保留 `src/data_quality.py` 作为报告级覆盖率诊断，保留 context pack quality 作为单股上下文质量 | 不删除 market light quality，它服务大盘状态 | 后续应明确报告级、数据源级、上下文 pack 级质量分的层级关系和字段名 |

## 4. 当前风险

- **数据字段命名不统一**：市场快照、历史快照、context snapshot、analysis result、Web camelCase 类型之间存在 `date/data_date/latest_data_date`、`amount/turnover`、`signal/market_score` 等多套字段，需要靠兼容映射兜底。
- **报告格式变动容易导致测试失败**：通知、Web Markdown、Discord 摘要、周报、renderer fallback 都消费 Markdown；任意标题或运行信息变化都可能影响快照/断言。
- **数据源不稳定**：AkShare、腾讯、eFinance、Tushare、Yahoo 等都可能受网络、限流、字段变更影响；需要继续保持 fail-open 和 fallback 诊断。
- **GitHub Actions 测试容易受环境影响**：workflow 依赖 secrets、网络、npm/pip 缓存、三方 API；本次未跑慢测试，不能证明全链路在线能力。
- **非交易日 / 未开盘数据容易为空**：当前已有跳过通知和最近交易日兜底，但多市场时区、节假日和盘前/盘中 partial bar 仍是高风险路径。
- **public 仓库不适合保存个人配置**：个人持仓、Discord channel id、Bot token、GITHUB_DISPATCH_TOKEN、模型 key、组合交易流水都不应入库。
- **Discord Bot 代码存在但未部署**：listener 是手动运行组件；没有部署进程就无法完成 Discord 操作面板交互。
- **网页预览和未来本地网页工作台边界不清**：现有 Web 管理台已经很完整，未来不应另建展示页或 dashboard 平行实现。
- **历史数据还没有统一长期存储策略**：DB 历史、context snapshot、`data/history`、artifact reports 都在承担“历史”职责，P2-A 需要先统一契约。
- **图片卡片容易扩散实现**：Web 卡片样式、通知图片路径、docs 示例图容易被误认为已有日报卡片生成；应先确定卡片 renderer 和产物生命周期。
- **多用户能力安全边界不足**：组合/告警存在，但个人雷达若进入 public workflow 或公共通知，必须先解决用户隔离、配置密钥、输出脱敏。

## 5. 后续推荐路线

### 5.1 调整后的优先级

1. **P0-R：现有功能盘点与重复功能确认** — 本文档已完成首轮盘点；后续只需随 PR 持续更新。
2. **Web-P0：本地网页工作台入口索引与目录规范** — 无需重复开发 Web，只需接入 / 修复 / 文档化现有 `apps/dsa-web/`、`server.py`、`main.py --serve` 与桌面端关系。
3. **P2-A：历史数据仓库** — 必须先统一 DB 历史、`data/history` 快照、reports artifact、context snapshot 的职责。
4. **P2-B：GitHub Actions 持久化保存历史数据** — 在 P2-A 契约确定后做；否则会固化重复历史格式。
5. **P3-A：近 5 日 / 20 日趋势分析** — 现有周报/历史只覆盖部分，建议复用 P2 历史仓库，不新建数据读取链路。
6. **P3-B：板块持续性分析** — 可复用 market analyzer 的板块榜和周报 sector counts；无需重复抓取，只需增强统计口径。
7. **P4-A：周报增强** — 周报已有基础，属于“无需重复开发，只需接入 / 修复 / 文档化”；重点补指数表现、样本质量和通知摘要。
8. **P6-A：公开仓库安全检查** — 在多用户/个人配置前必须做，避免 secrets 或个人持仓进入 public 仓库。
9. **P5-A：多用户配置系统** — 应在安全检查与历史仓库后推进，避免先做 UI 后补隔离。
10. **P5-B：个人股票 / 基金影响雷达** — 当前仅有 portfolio/alerts 基础，建议暂缓到多用户配置、安全和历史契约明确后。
11. **P7-A：公共日报 / 周报图片卡片** — 仅有入口，尚未真实接通；建议暂缓，等报告结构稳定后再做单一 renderer。
12. **P6-B：仓库改 private** — 这是治理/运营决策，不是功能前置；若要保存个人配置，可优先 private 或改为外部 secrets/DB。

### 5.2 对原路线的标注

- **无需重复开发，只需接入 / 修复 / 文档化**：公共日报、Discord Webhook、完整 Markdown artifact、repository_dispatch、基础周报、Web 管理台、历史报告预览。
- **已有部分基础，继续优化**：历史数据仓库、近几日变化、板块持续性、周报增强、Discord 操作面板、command executor。
- **仅有入口，尚未真实接通**：Discord 重推日报、Discord Bot 默认部署、公共日报/周报图片卡片、多用户个人雷达、本地网页工作台入口索引规范。
- **建议暂缓**：图片卡片、多用户个人雷达、仓库 private 决策绑定开发，直到 P2 历史和 Web-P0 目录边界完成。

## 6. 本次审计范围缺失说明

- 指定文件中均已发现：`README.md`、`docs/`、`main.py`、`src/market_analyzer.py`、`src/market_history.py`、`src/data_quality.py`、`src/report_renderer.py`、`src/report_language.py`、`src/notification.py`、`src/weekly_report.py`、`src/command_executor.py`、`src/discord_command_bot.py`、`.github/workflows/`、`apps/dsa-web/`、`apps/dsa-desktop/`、`tests/`。
- 未发现独立顶层目录：`web/`、`app/`、`frontend/`、`dashboard/`。当前 Web 前端集中在 `apps/dsa-web/`；静态/文档图片集中在 `docs/assets/`，Web 运行资产在 `apps/dsa-web/src/assets/`。
- 本次未验证在线数据源、Discord 实际投递、GitHub Actions 远端运行、Web 构建、桌面端构建；因为任务限定为文档审计且要求不要跑全量慢测试。
