@echo off
setlocal
cd /d "%~dp0"
if not exist "tools\cloudflared.exe" (
  echo cloudflared.exe not found in tools folder.
  pause
  exit /b 1
)
echo Starting temporary HTTPS tunnel...
echo Keep this window open while testing the Custom GPT.
"tools\cloudflared.exe" tunnel --url http://127.0.0.1:8000 --no-autoupdate
pause
