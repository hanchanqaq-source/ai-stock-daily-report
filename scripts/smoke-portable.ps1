param(
  [string]$ZipPath = '',
  [int]$TimeoutSeconds = 150
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if ([string]::IsNullOrWhiteSpace($ZipPath)) {
  $candidate = Get-ChildItem -Path (Join-Path $repoRoot 'dist\portable-assets') -Filter '股票基金质量分析系统-Portable-v*.zip' -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (-not $candidate) {
    throw 'No portable ZIP found under dist\portable-assets.'
  }
  $ZipPath = $candidate.FullName
}

$resolvedZip = (Resolve-Path $ZipPath).Path
$smokeRoot = Join-Path ([System.IO.Path]::GetTempPath()) "dsa-portable-smoke-$PID"
$appRoot = Join-Path $smokeRoot '股票基金质量分析系统'
$exePath = Join-Path $appRoot '股票基金质量分析系统.exe'
$logPath = Join-Path $appRoot 'logs\desktop.log'
$diagnosticsDir = Join-Path $repoRoot 'dist\portable-diagnostics'
$desktopDiagnosticsPath = Join-Path $diagnosticsDir 'desktop.log'
$process = $null

Write-Host "Portable smoke archive: $resolvedZip"

try {
  if (Test-Path $smokeRoot) {
    Remove-Item -Path $smokeRoot -Recurse -Force
  }
  New-Item -ItemType Directory -Path $smokeRoot -Force | Out-Null
  Expand-Archive -Path $resolvedZip -DestinationPath $smokeRoot -Force

  if (-not (Test-Path $exePath)) {
    throw "Portable executable is missing after extraction: $exePath"
  }

  foreach ($directoryName in @('data', 'logs', 'config', 'plugins')) {
    $directoryPath = Join-Path $appRoot $directoryName
    if (-not (Test-Path $directoryPath)) {
      throw "Portable directory is missing: $directoryPath"
    }
  }

  $process = Start-Process -FilePath $exePath -WorkingDirectory $appRoot -PassThru
  Write-Host "Portable process started: PID=$($process.Id)"

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $lastLog = ''
  $ready = $false

  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500

    if (Test-Path $logPath) {
      $lastLog = Get-Content -Path $logPath -Raw -ErrorAction SilentlyContinue
      $backendPackaged = $lastLog -match 'Backend launch mode=packaged'
      $localhostOnly = $lastLog -match '--host 127\.0\.0\.1'
      $uiLoaded = $lastLog -match 'Main UI loaded in'
      $startupFailed = $lastLog -match 'Startup failed|Backend launch failed'

      if ($startupFailed) {
        throw "Portable startup reported a failure.`n$lastLog"
      }

      if ($backendPackaged -and $localhostOnly -and $uiLoaded) {
        $ready = $true
        break
      }
    }

    if ($process.HasExited -and -not $ready) {
      throw "Portable process exited before readiness with code $($process.ExitCode).`n$lastLog"
    }
  }

  if (-not $ready) {
    throw "Portable startup did not become ready within $TimeoutSeconds seconds.`n$lastLog"
  }

  if ($lastLog -match 'Backend launch mode=development') {
    throw 'Portable package unexpectedly used the development Python launch path.'
  }

  Write-Host 'Portable smoke passed: packaged backend, 127.0.0.1 binding, and main UI were observed.'
} finally {
  New-Item -ItemType Directory -Path $diagnosticsDir -Force | Out-Null
  if (Test-Path $logPath) {
    Copy-Item -Path $logPath -Destination $desktopDiagnosticsPath -Force
    Write-Host '--- portable desktop log ---'
    Get-Content -Path $logPath -Tail 200 -ErrorAction SilentlyContinue
  } else {
    Write-Host "Portable desktop log was not created: $logPath"
  }

  if ($process) {
    try {
      $process.Refresh()
      Write-Host "Portable process state: exited=$($process.HasExited)"
      if ($process.HasExited) {
        Write-Host "Portable process exit code: $($process.ExitCode)"
      }
    } catch {
      Write-Host "Portable process state could not be read: $($_.Exception.Message)"
    }
  }

  if ($process -and -not $process.HasExited) {
    & taskkill.exe /PID $process.Id /T /F *> $null
  }
  Start-Sleep -Milliseconds 500
  if (Test-Path $smokeRoot) {
    Remove-Item -Path $smokeRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
}
