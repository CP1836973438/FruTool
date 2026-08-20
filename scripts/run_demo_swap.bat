@echo off
REM Double-click to test skipping swap step 1 with a fake BMC.
setlocal
cd /d "%~dp0"
set FRUTOOL_DEMO_SWAP=1
set FRUTOOL_SKIP_ADMIN=1
if not exist "fru_backup" mkdir "fru_backup"
if not exist "fru_backup\12345678.bin" (
  echo FRUTOOL_DEMO_FRU_BIN> "fru_backup\12345678.bin"
)
start "" "FRUTool.exe"
endlocal
