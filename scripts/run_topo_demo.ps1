param(
    [ValidateSet("multi", "foxconn", "single", "missing")]
    [string]$Scenario = "multi",
    [switch]$NoGpuEffects,
    [switch]$ListScenarios
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$DemoScript = Join-Path $Root "scripts\demo_topo.py"

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv not found: $VenvPython`nRun: python -m venv .venv ; .\.venv\Scripts\pip install -r requirements.txt"
}

$argsList = @()
if ($ListScenarios) { $argsList += "--list-scenarios" }
else { $argsList += @("--scenario", $Scenario) }
if ($NoGpuEffects) { $argsList += "--no-gpu-effects" }

Write-Host "Starting topo demo (scenario: $Scenario) ..."
Write-Host "  Uses local PCLE/ folder; no BMC required."
Write-Host "  App will open the Topo page with mock FRU hints."
Write-Host ""

& $VenvPython $DemoScript @argsList
