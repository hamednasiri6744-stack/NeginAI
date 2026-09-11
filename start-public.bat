@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment not found.
  pause
  exit /b 1
)
if not exist "tools\caddy.exe" (
  echo Caddy was not found in the tools folder.
  pause
  exit /b 1
)

start "NeginAI API" /min cmd /c "".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8006"
timeout /t 3 /nobreak >nul
"tools\caddy.exe" run --config Caddyfile --adapter caddyfile
