@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "LAUNCHER_EXE=%SCRIPT_DIR%MyFinModelLauncher.exe"

if not exist "%LAUNCHER_EXE%" (
  echo Could not find MyFinModelLauncher.exe in:
  echo %SCRIPT_DIR%
  echo.
  echo Re-extract the full portable folder and try again.
  pause
  exit /b 1
)

echo Starting MyFinModel...
echo The first launch can take up to about a minute on some systems.
echo Your browser will open automatically when the app is ready.
echo.

start "" "%LAUNCHER_EXE%"
timeout /t 20 /nobreak >nul
exit /b 0
