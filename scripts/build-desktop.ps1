param(
  [ValidateSet('nsis', 'portable')]
  [string]$Target = 'nsis'
)

$ErrorActionPreference = 'Stop'

$devModeKey = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock'
$allowDev = 0
$allowTrusted = 0
if (Test-Path $devModeKey) {
  $props = Get-ItemProperty -Path $devModeKey -ErrorAction SilentlyContinue
  if ($null -ne $props) {
    $allowDev = $props.AllowDevelopmentWithoutDevLicense
    $allowTrusted = $props.AllowAllTrustedApps
  }
}

$skipDevModeCheck = ($env:DSA_SKIP_DEVMODE_CHECK -eq 'true') -or ($env:CI -eq 'true')
if (-not $skipDevModeCheck -and ($allowDev -ne 1) -and ($allowTrusted -ne 1)) {
  Write-Host 'Developer Mode is disabled. Enable it to allow symlink creation for electron-builder.'
  Write-Host 'Windows Settings -> Privacy & security -> For developers -> Developer Mode'
  throw 'Developer Mode required for electron-builder cache extraction.'
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:CSC_IDENTITY_AUTO_DISCOVERY = 'false'
$env:ELECTRON_BUILDER_ALLOW_UNRESOLVED_SYMLINKS = 'true'
$env:ELECTRON_BUILDER_CACHE = Join-Path $repoRoot '.electron-builder-cache'
$env:ELECTRON_CACHE = Join-Path $repoRoot '.electron-cache'
$env:NPM_CONFIG_FETCH_RETRIES = '5'
$env:NPM_CONFIG_FETCH_RETRY_MINTIMEOUT = '10000'
$env:NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT = '60000'

$backendArtifact = Join-Path $repoRoot 'dist\backend\stock_analysis'

if (!(Test-Path $backendArtifact)) {
  throw "Backend artifact not found: $backendArtifact. Run scripts\build-backend.ps1 first."
}

function Get-PackageLockHash {
  return (Get-FileHash -Path 'package-lock.json' -Algorithm SHA256).Hash
}

function Remove-DesktopNodeModules {
  if (-not (Test-Path 'node_modules')) {
    return
  }

  for ($attempt = 1; $attempt -le 5; $attempt += 1) {
    try {
      Remove-Item -Recurse -Force 'node_modules' -ErrorAction Stop
      return
    } catch {
      if ($attempt -eq 5) {
        throw
      }
      Write-Warning "Could not remove node_modules on attempt $attempt; retrying..."
      Start-Sleep -Seconds (2 * $attempt)
    }
  }
}

function Install-DesktopDependencies {
  param(
    [string]$Reason,
    [switch]$Clean
  )

  $installCommand = if ($env:CI -eq 'true') { 'ci' } else { 'install' }
  Write-Host "Installing desktop dependencies ($Reason) with npm $installCommand..."

  for ($attempt = 1; $attempt -le 3; $attempt += 1) {
    if ($Clean -or $attempt -gt 1) {
      Remove-DesktopNodeModules
    }

    Write-Host "Desktop dependency install attempt $attempt of 3..."
    & npm $installCommand
    $installExitCode = $LASTEXITCODE

    if ($installExitCode -eq 0) {
      New-Item -ItemType Directory -Force -Path 'node_modules' | Out-Null
      Set-Content -Path 'node_modules\.dsa-package-lock.sha256' -Value (Get-PackageLockHash) -Encoding ascii
      return
    }

    if ($attempt -eq 3) {
      throw "Desktop dependency installation failed after 3 attempts (last exit code $installExitCode)."
    }

    Write-Warning "Desktop dependency installation failed with exit code $installExitCode; retrying after a bounded delay."
    Start-Sleep -Seconds (10 * $attempt)
  }
}

function Ensure-DesktopDependencies {
  $lockHashMarker = 'node_modules\.dsa-package-lock.sha256'
  $installReason = $null

  if (!(Test-Path 'node_modules')) {
    $installReason = 'node_modules missing'
  } elseif (!(Test-Path $lockHashMarker)) {
    $installReason = 'package-lock marker missing'
  } elseif ((Get-Content -Path $lockHashMarker -Raw).Trim() -ne (Get-PackageLockHash)) {
    $installReason = 'package-lock.json changed'
  } elseif (!(Test-Path 'node_modules\electron-updater')) {
    $installReason = 'electron-updater missing'
  }

  if ($null -ne $installReason) {
    Install-DesktopDependencies -Reason $installReason
  } else {
    Write-Host 'Desktop dependencies are up to date.'
  }
}

Write-Host "Building Electron desktop app (target=$Target)..."
Push-Location (Join-Path $repoRoot 'apps\dsa-desktop')
try {
  Ensure-DesktopDependencies

  Write-Host 'Stopping running app (if any)...'
  Get-Process -Name 'Daily Stock Analysis' -ErrorAction SilentlyContinue | Stop-Process -Force
  Get-Process -Name '股票基金质量分析系统' -ErrorAction SilentlyContinue | Stop-Process -Force
  Get-Process -Name 'stock_analysis' -ErrorAction SilentlyContinue | Stop-Process -Force

  if (Test-Path 'dist\win-unpacked') {
    Write-Host 'Cleaning dist\win-unpacked...'
    Remove-Item -Recurse -Force 'dist\win-unpacked'
  }

  $appBuilderPath = 'node_modules\app-builder-bin\win\x64\app-builder.exe'
  if (!(Test-Path $appBuilderPath)) {
    Write-Host 'app-builder.exe missing, reinstalling dependencies...'
    Install-DesktopDependencies -Reason 'app-builder.exe missing' -Clean
  }

  if ($Target -eq 'portable') {
    npx electron-builder --config electron-builder.portable.cjs --win --x64 --dir --publish never
  } else {
    npx electron-builder --win nsis --publish never
  }
  if ($LASTEXITCODE -ne 0) {
    throw "Electron $Target build failed."
  }
} finally {
  Pop-Location
}

Write-Host "Desktop build completed (target=$Target)."
