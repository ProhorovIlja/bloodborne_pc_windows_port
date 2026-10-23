@echo off
setlocal
set "POC=%LOCALAPPDATA%\SeamlessHunt-Yharnam-POC"
if not exist "%POC%\BLauncher.exe" (
  echo First run INSTALL.cmd.
  pause
  exit /b 1
)
start "Yharnam Together - Seamless Hunt PoC" "%POC%\BLauncher.exe"
