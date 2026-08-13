# Verify PyInstaller onedir output exists and bundled resources are present.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DistDir = Join-Path (Join-Path $Root "dist") "FRUTool"
$Exe = Join-Path $DistDir "FRUTool.exe"
$Internal = Join-Path $DistDir "_internal"

if (-not (Test-Path $Exe)) {
    Write-Error "Missing packaged executable: $Exe"
}
$size = (Get-Item $Exe).Length
$minBytes = 1MB
if ($size -lt $minBytes) {
    Write-Error "FRUTool.exe too small ($size bytes); expected at least $minBytes"
}
Write-Host "OK: FRUTool.exe ($([math]::Round($size / 1MB, 2)) MB)"

if (-not (Test-Path $Internal)) {
    Write-Error "Missing _internal directory: $Internal"
}
Write-Host "OK: _internal/"

$BundledIpmitool = Join-Path (Join-Path $Internal "ipmitool") "ipmitool.exe"
if (Test-Path $BundledIpmitool) {
    Write-Host "OK: bundled ipmitool.exe"
} else {
    Write-Warning "bundled ipmitool.exe not found (build without ipmitool/ source?)"
}

$BundledTopo = Join-Path (Join-Path $Internal "ipmitool") "PcieEEpromTool.py"
if (Test-Path $BundledTopo) {
    Write-Host "OK: bundled ipmitool/PcieEEpromTool.py"
} else {
    Write-Warning "bundled ipmitool/PcieEEpromTool.py not found"
}

$LegacyTopo = Join-Path $Internal "PcieEEpromTool.py"
if (Test-Path $LegacyTopo) {
    Write-Warning "legacy _internal/PcieEEpromTool.py should be removed; use ipmitool/PcieEEpromTool.py only"
}

$BundledPcle = Join-Path $Internal "PCLE"
if (Test-Path $BundledPcle) {
    Write-Host "OK: bundled PCLE/"
} else {
    Write-Warning "bundled PCLE/ not found (build without PCLE/ source?)"
}

Write-Host "Distribution folder: $DistDir"
