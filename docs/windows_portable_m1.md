# Windows Portable-M1 便携版

## 目标

Windows Portable-M1 让用户只下载一个 ZIP，解压后双击 `股票基金质量分析系统.exe` 使用，不需要在目标电脑安装 Python、Node.js、npm、Git、Docker 或数据库服务。

本阶段由 GitHub Actions 的 Windows Runner 完成 Web、Python 后端和 Electron 桌面端构建，用户电脑只运行构建产物。

## 下载产物

GitHub Actions 工作流：`Windows Portable Preview`

产物结构：

```text
股票基金质量分析系统-Portable-v<version>.zip
└─ 股票基金质量分析系统/
   ├─ 股票基金质量分析系统.exe
   ├─ resources/
   │  └─ backend/stock_analysis/stock_analysis.exe
   ├─ data/
   ├─ logs/
   ├─ config/
   ├─ plugins/
   ├─ 使用说明.txt
   └─ VERSION.txt
```

ZIP 同时生成 SHA-256 校验文件：

```text
股票基金质量分析系统-Portable-v<version>.zip.sha256
```

## 使用方法

1. 下载 GitHub Actions 生成的 Windows Portable artifact。
2. 解压 ZIP，保持目录结构不变。
3. 双击 `股票基金质量分析系统.exe`。
4. 首次启动等待内置后端完成初始化。

程序不会修改系统 PATH，不注册 Windows 服务，不要求管理员权限。

## 数据目录

便携版把普通运行数据放在 EXE 同级目录：

- `data/`：数据库和运行数据；
- `logs/`：桌面端和后端日志；
- `config/`：后续非敏感插件配置；
- `plugins/`：后续插件目录。

迁移到其他电脑时，应复制整个 `股票基金质量分析系统` 文件夹。删除整个文件夹即可清理普通运行数据。

安全凭证仍沿用 Electron `safeStorage` / Windows DPAPI 的安全边界，不降级为便携目录明文文件。复制程序文件夹不会自动复制 Windows 用户的安全凭证。

## 网络边界

桌面端启动内置后端时固定使用：

```text
--host 127.0.0.1
```

不允许绑定 `0.0.0.0`。Portable-M1 不新增远程访问、账户读取、通知、交易、OCR、基金行业周期或 AI 能力。

## 云端构建流程

```text
GitHub Windows Runner
  → 构建 Web 静态资源
  → PyInstaller 编译 stock_analysis.exe
  → Electron Builder 生成 win-unpacked
  → 封装中文便携目录
  → 压缩 Portable ZIP
  → 解压 ZIP 并真实启动
  → 验证 packaged backend + 127.0.0.1 + 主页面完成加载
  → 上传 Actions artifact
```

便携版构建使用独立 `electron-builder.portable.cjs`，不会改变现有 NSIS 安装包构建目标。

构建期间会在 GitHub Runner 的临时工作区把桌面端更新地址切换到当前仓库；构建结束后立即恢复源码，不影响现有安装版构建。

## 验收标准

- ZIP 中存在 `股票基金质量分析系统.exe`；
- 内置后端 `stock_analysis.exe` 随包存在；
- 启动日志显示 `Backend launch mode=packaged`；
- 启动命令只绑定 `127.0.0.1`；
- 主页面完成加载；
- 启动链路不进入 development Python 模式；
- `data`、`logs`、`config`、`plugins` 目录存在；
- 桌面端 Node 测试通过；
- 构建产物只上传为 GitHub Actions artifact，不自动发布 Release。

## 已知限制

- 当前产物未进行商业代码签名，Windows 可能显示未知发布者或 SmartScreen 提示；
- Portable-M1 是便携运行基础，不包含插件中心；
- 插件安装、启停、权限声明、校验与回滚归入 Plugin-M1；
- 正式 Release 发布仍需独立人工批准。

## 回滚

删除以下新增文件并将 `scripts/build-desktop.ps1`、`apps/dsa-desktop/package.json` 恢复到原状态即可回滚：

- `.github/workflows/desktop-portable-preview.yml`
- `apps/dsa-desktop/electron-builder.portable.cjs`
- `apps/dsa-desktop/tests/portableBuildConfig.test.js`
- `scripts/build-portable.ps1`
- `scripts/smoke-portable.ps1`
- `docs/windows_portable_m1.md`
