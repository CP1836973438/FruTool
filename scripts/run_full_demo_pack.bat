@echo off
chcp 65001 >nul
cd /d "%~dp0"
set FRUTOOL_DEMO_ALL=1
set FRUTOOL_DEMO_SWAP=1
set FRUTOOL_DEMO_TOPO=1
set FRUTOOL_SKIP_ADMIN=1
set FRUTOOL_DISABLE_GPU_EFFECTS=1
echo Starting FRUTool full demo...
echo  SN sample: 21D111761  ^|  FRU / Swap manual+auto / Topo / DHCP simulated
start "" "%~dp0FRUTool.exe"
