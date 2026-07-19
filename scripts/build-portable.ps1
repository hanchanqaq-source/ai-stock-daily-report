param(
  [switch]$SkipBackendBuild
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$desktopRoot = Join-Path $repoRoot 'apps\dsa-desktop'
$mainPath = Join-Path $desktopRoot 'main.js'
$portableOutputRoot = Join-Path $repoRoot 'dist\portable-package'
$portableAppRoot = Join-Path $portableOutputRoot '股票基金质量分析系统'
$portableAssetsRoot = Join-Path $repoRoot 'dist\portable-assets'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

Write-Host '=== 股票基金质量分析系统 Windows Portable Build ==='
Write-Host 'All dependencies are installed only inside the GitHub Actions runner or the current development workspace.'

if (-not $SkipBackendBuild) {
  & (Join-Path $PSScriptRoot 'build-backend.ps1')
  if ($LASTEXITCODE -ne 0) {
    throw "Backend build failed with exit code $LASTEXITCODE."
  }
}

$backendEntry = Join-Path $repoRoot 'dist\backend\stock_analysis\stock_analysis.exe'
if (-not (Test-Path $backendEntry)) {
  throw "Packaged backend entrypoint not found: $backendEntry"
}

& (Join-Path $PSScriptRoot 'build-desktop.ps1') -Target portable
if ($LASTEXITCODE -ne 0) {
  throw "Portable desktop build failed with exit code $LASTEXITCODE."
}

Push-Location $desktopRoot
try {
  npm test
  if ($LASTEXITCODE -ne 0) {
    throw "Desktop tests failed with exit code $LASTEXITCODE."
  }
} finally {
  Pop-Location
}

$winUnpacked = Join-Path $desktopRoot 'dist\win-unpacked'
if (-not (Test-Path $winUnpacked)) {
  throw "Portable desktop directory not found: $winUnpacked"
}

if (Test-Path $portableOutputRoot) {
  Remove-Item -Path $portableOutputRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $portableAppRoot -Force | Out-Null
Copy-Item -Path (Join-Path $winUnpacked '*') -Destination $portableAppRoot -Recurse -Force

$portableExe = Join-Path $portableAppRoot '股票基金质量分析系统.exe'
if (-not (Test-Path $portableExe)) {
  $availableExecutables = @(Get-ChildItem -Path $portableAppRoot -Filter '*.exe' -File | Select-Object -ExpandProperty Name)
  throw "Expected portable executable was not generated: $portableExe. Available executables: $($availableExecutables -join ', ')"
}

$directoryNotes = @{
  'data' = '程序数据库和运行数据目录。复制整个便携版文件夹时请一并保留。'
  'logs' = '程序日志目录。启动异常时可查看 desktop.log。'
  'config' = '插件和程序的非敏感配置目录。真实密钥不会以明文插件配置保存。'
  'plugins' = '插件目录。Portable-M1 仅预留目录，插件中心将在后续阶段接入。'
}

foreach ($directoryName in $directoryNotes.Keys) {
  $directoryPath = Join-Path $portableAppRoot $directoryName
  New-Item -ItemType Directory -Path $directoryPath -Force | Out-Null
  [System.IO.File]::WriteAllText(
    (Join-Path $directoryPath 'README.txt'),
    $directoryNotes[$directoryName] + [Environment]::NewLine,
    $utf8NoBom
  )
}

$packageJson = Get-Content -Path (Join-Path $desktopRoot 'package.json') -Raw | ConvertFrom-Json
$version = [string]$packageJson.version
if ([string]::IsNullOrWhiteSpace($version)) {
  throw 'Desktop package version is missing.'
}

$rootReadme = @"
股票基金质量分析系统 Windows 便携版 v$version

使用方法：
1. 保持本文件夹结构不变。
2. 双击“股票基金质量分析系统.exe”。
3. 不需要安装 Python、Node.js、Git 或 Docker。

数据位置：
- data：数据库和运行数据
- logs：启动与运行日志
- config：非敏感配置
- plugins：后续插件目录

安全说明：
- 后端只监听 127.0.0.1。
- 不注册 Windows 服务，不修改系统 PATH，不要求管理员权限。
- 当前构建未进行商业代码签名，Windows 可能显示未知发布者提示。
- Portable-M1 不包含插件中心、OCR、基金行业周期或新增 AI 能力。
"@
[System.IO.File]::WriteAllText((Join-Path $portableAppRoot '使用说明.txt'), $rootReadme, $utf8NoBom)
[System.IO.File]::WriteAllText((Join-Path $portableAppRoot 'VERSION.txt'), "$version`n", $utf8NoBom)

if (Test-Path $portableAssetsRoot) {
  Remove-Item -Path $portableAssetsRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $portableAssetsRoot -Force | Out-Null

$zipName = "股票基金质量分析系统-Portable-v$version.zip"
$zipPath = Join-Path $portableAssetsRoot $zipName
Push-Location $portableOutputRoot
try {
  Compress-Archive -Path '股票基金质量分析系统' -DestinationPath $zipPath -CompressionLevel Optimal -Force
} finally {
  Pop-Location
}

if (-not (Test-Path $zipPath)) {
  throw "Portable ZIP was not generated: $zipPath"
}

$zipHash = Get-FileHash -Path $zipPath -Algorithm SHA256
$hashLine = "$($zipHash.Hash.ToLowerInvariant())  $zipName`n"
[System.IO.File]::WriteAllText("$zipPath.sha256", $hashLine, $utf8NoBom)

Write-Host 'Portable package created:'
Get-Item $zipPath, "$zipPath.sha256" | Format-Table Name, Length, LastWriteTime
