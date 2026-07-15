# Windows Portable-M1 便携版计划

## 1. 目标

将“股票基金质量分析系统”交付为 Windows 便携版：用户只需下载 ZIP、解压并双击 EXE，不需要在工作电脑安装 Python、Node.js、npm、Git、Docker、数据库服务或编译器。

本阶段只解决便携打包、云端构建、启动与数据目录问题，不接入基金数据、OCR、AI、通知或插件业务。

## 2. 固定分工

- GPT-5.6：Plan 与 Judge，负责任务拆分、边界、验收和复核。
- Codex：Build，负责复杂多文件实现、Windows 打包、工作流和测试。
- 用户：人工验收下载、解压、双击启动体验。

所有实现遵循 Plan → Build → Judge。

## 3. 前置条件

- PR #182 保持独立，先完成 Windows 人工验收；未经明确许可不得自动合并。
- Portable-M1 使用独立分支和 Draft PR。
- 严格遵守根目录 `AGENTS.md`。

## 4. Build 范围

1. 在 GitHub Actions Windows Runner 上构建 Web、编译后端并打包 Electron。
2. 为 `apps/dsa-desktop` 增加 Windows `portable` 构建目标，同时保留现有 NSIS 能力。
3. 生成可下载 artifact：
   - `股票基金质量分析系统-Portable-<version>.zip`
   - ZIP 内提供可双击启动的 EXE。
4. 桌面端内置编译后的后端，不依赖用户电脑的 Python。
5. 产品显示名称统一为“股票基金质量分析系统”；日报名称“AI股票基金每日信息报告”保持不变。
6. 修正桌面更新仓库地址，不能继续指向旧的 `ZhuLinsen/daily_stock_analysis`。
7. 运行数据、日志、配置、插件预留目录与程序隔离；不得修改系统 PATH、注册系统服务或要求管理员权限。
8. 增加便携模式检测与最小启动日志，启动失败时给出可读错误，不静默闪退。
9. 更新专题文档和 `docs/CHANGELOG.md`。

## 5. 目录目标

```text
股票基金质量分析系统/
├─ 股票基金质量分析系统.exe
├─ data/
├─ logs/
├─ config/
└─ plugins/
```

允许 electron-builder 实际产物包含必要运行文件，但用户入口必须清晰，数据不得散落到系统目录。插件中心本身不在本阶段实现，只预留 `plugins/` 和契约边界。

## 6. 禁止事项

- 不在用户工作电脑执行 `pip install`、`npm install`、`npm ci`、创建虚拟环境或安装 Docker。
- 不新增真实密钥、`.env`、token、webhook、API key。
- 不接 AKShare、OCR、AI、通知、自动交易或真实账户。
- 不把 Qlib 等大型研究框架打入基础便携包。
- 不自动发布 GitHub Release。
- 不自动标记 PR Ready，不自动合并。
- 不修改与桌面打包无关的业务页面。
- 后端只能绑定 `127.0.0.1`，禁止 `0.0.0.0`。

## 7. 验收标准

- [ ] GitHub Actions Windows 构建成功并上传 Portable ZIP artifact。
- [ ] 在未安装 Python、Node.js、Git、Docker 的干净 Windows 环境中可启动。
- [ ] 双击 EXE 后 Web 页面和内置后端均正常启动。
- [ ] 后端仅绑定 `127.0.0.1`。
- [ ] 不要求管理员权限，不修改系统 PATH，不注册系统服务。
- [ ] `data/`、`logs/`、`config/`、`plugins/` 位于便携目录或明确的便携数据根目录。
- [ ] 复制整个目录到另一位置后仍可启动。
- [ ] 删除整个目录即可清理主要程序与数据。
- [ ] 启动失败有日志和用户可读提示，不出现窗口一闪而过且无信息。
- [ ] Desktop tests、Web lint/build、后端离线测试和便携构建 smoke 全部通过。

## 8. Judge 检查

重点检查：

- 是否仍暗中依赖全局 Python 或 Node.js；
- 是否把数据错误写入安装目录外或系统目录；
- 是否破坏现有安全凭据存储和 `127.0.0.1` 限制；
- 是否错误修改项目名、日报名或旧业务功能；
- artifact 是否真的可在干净 Windows 运行，而不只是“构建成功”；
- 更新地址、产品名和 artifact 名称是否全部指向当前仓库与当前项目。

## 9. 回滚

移除 portable target、Portable workflow/job 和便携模式路径逻辑，恢复现有 NSIS 构建与桌面运行路径。

## 10. 后续阶段

Portable-M1 通过后，依次进入：

1. Plugin-M1：插件清单、安装、启用、停用、版本兼容和卸载。
2. Fund-M1：基金代码或名称自动识别。
3. Fund-M2：AKShare 基金资料、公开持仓和行业配置。
4. Cycle-M1：轻量行业周期评分。
5. OCR-M1：本地截图识别与人工确认。
6. Ask-M1：股票问题集、基金问题集、当前持仓问题集。
