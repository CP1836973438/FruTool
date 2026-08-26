param(
    [switch]$NoGpuEffects
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv not found: $VenvPython"
}

$env:FRUTOOL_DEMO_ALL = "1"
$env:FRUTOOL_DEMO_SWAP = "1"
$env:FRUTOOL_DEMO_TOPO = "1"
$env:FRUTOOL_SKIP_ADMIN = "1"
$env:FRUTOOL_DEMO_SCENARIO = "multi"
if ($NoGpuEffects) { $env:FRUTOOL_DISABLE_GPU_EFFECTS = "1" }

Write-Host "Starting full demo (FRU/Swap manual+auto/Topo/DHCP) ..."
Write-Host "  Sample SN: 21D111761  ·  auto swap simulates offline → new board → clone"
Write-Host ""

& $VenvPython (Join-Path $Root "fru_tool.py") --no-gpu-effects
