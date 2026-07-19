const fs = require('fs');
const path = require('path');

function assertAbsolutePath(value, label) {
  if (typeof value !== 'string' || (!path.isAbsolute(value) && !path.win32.isAbsolute(value))) {
    throw new Error(`${label}必须是绝对路径`);
  }
  return value;
}

function buildWindowsPortableUpdateHelper({ appDir, zipPath, expectedHash, stageRoot, backupRoot, exePath, parentPid }) {
  [
    [appDir, '程序目录'], [zipPath, '更新包路径'], [stageRoot, '临时解压目录'],
    [backupRoot, '恢复点目录'], [exePath, '启动文件'],
  ].forEach(([value, label]) => assertAbsolutePath(value, label));
  if (typeof expectedHash !== 'string' || !/^[a-f0-9]{64}$/i.test(expectedHash)) throw new Error('更新包 SHA-256 无效');
  if (!Number.isInteger(parentPid) || parentPid <= 0) throw new Error('父进程 PID 无效');
  const quote = (value) => `'${value.replaceAll("'", "''")}'`;
  return `$ErrorActionPreference = 'Stop'
$pidToWait = ${parentPid}
$appDir = ${quote(appDir)}
$zipPath = ${quote(zipPath)}
$expectedHash = ${quote(expectedHash.toLowerCase())}
$stageRoot = ${quote(stageRoot)}
$backupRoot = ${quote(backupRoot)}
$exePath = ${quote(exePath)}
$preserved = @('data','config','logs','plugins','.portable-update-backups')
while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) { Start-Sleep -Milliseconds 300 }
try {
  if ((Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) { throw 'archive checksum changed after confirmation' }
  Expand-Archive -LiteralPath $zipPath -DestinationPath $stageRoot -Force
  $stagedAppDir = Join-Path $stageRoot '股票基金质量分析系统'
  $requiredPaths = @('股票基金质量分析系统.exe','resources\\backend\\stock_analysis\\stock_analysis.exe','data','config','logs','plugins')
  if ($requiredPaths | Where-Object { -not (Test-Path -LiteralPath (Join-Path $stagedAppDir $_)) }) { throw 'archive layout is invalid after extraction' }
  Get-ChildItem -LiteralPath $appDir -Force | Where-Object { $preserved -notcontains $_.Name } | Remove-Item -Recurse -Force
  Get-ChildItem -LiteralPath $stagedAppDir -Force | Where-Object { $preserved -notcontains $_.Name } | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $appDir -Recurse -Force }
  $process = Start-Process -FilePath $exePath -WorkingDirectory $appDir -PassThru
  Start-Sleep -Seconds 8
  if ($process.HasExited) { throw 'updated process exited during startup validation' }
} catch {
  Get-ChildItem -LiteralPath $appDir -Force | Where-Object { $preserved -notcontains $_.Name } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  Get-ChildItem -LiteralPath $backupRoot -Force | Where-Object { $_.Name -ne 'portable-update-recovery.json' } | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $appDir -Recurse -Force }
  Start-Process -FilePath $exePath -WorkingDirectory $appDir
  exit 1
}
`;
}

function writeWindowsPortableUpdateHelper({ helperPath, ...options }, fsModule = fs) {
  assertAbsolutePath(helperPath, 'Helper 脚本路径');
  fsModule.mkdirSync(path.dirname(helperPath), { recursive: true });
  fsModule.writeFileSync(helperPath, buildWindowsPortableUpdateHelper(options), 'utf8');
  return helperPath;
}

module.exports = { buildWindowsPortableUpdateHelper, writeWindowsPortableUpdateHelper };
