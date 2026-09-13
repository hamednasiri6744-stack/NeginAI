@echo off
setlocal EnableExtensions
title NeginAI v0.17 - Live Backend Bridge

set "FRONTEND=%~dp0"
set "BACKEND=D:\Projects\NeginAI"

echo.
echo ===============================================
echo       NeginAI v0.17 - Live Backend Bridge
echo ===============================================
echo.

if not exist "%FRONTEND%package.json" (
  echo [ERROR] package.json not found beside this launcher.
  pause
  exit /b 1
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm.cmd not found. Install Node.js or repair PATH.
  pause
  exit /b 1
)

if not exist "%BACKEND%\start.bat" (
  echo [ERROR] NeginAI backend was not found at:
  echo %BACKEND%
  echo.
  echo The frontend will not be started without the real backend.
  pause
  exit /b 1
)

echo [1/4] Starting existing NeginAI FastAPI backend...
start "NeginAI Backend" cmd /k "cd /d ""%BACKEND%"" && call start.bat"

echo [2/4] Waiting for backend health...
set "BACKEND_OK="
for /L %%I in (1,1,20) do (
  curl.exe -fsS http://127.0.0.1:8000/health >nul 2>&1
  if not errorlevel 1 (
    set "BACKEND_OK=1"
    goto :backend_ready
  )
  timeout /t 1 /nobreak >nul
)

:backend_ready
if not defined BACKEND_OK (
  echo [ERROR] Backend did not become healthy on 127.0.0.1:8000.
  echo Check the NeginAI Backend window for the exact error.
  pause
  exit /b 1
)

echo [OK] Backend is healthy.
cd /d "%FRONTEND%"

if not exist "node_modules" (
  echo [3/4] Installing frontend dependencies...
  call npm.cmd install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
) else (
  echo [3/4] Frontend dependencies already installed.
)

echo [4/4] Starting Visitor frontend on port 4183...
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://localhost:4183'"
call npm.cmd run dev

echo.
echo Frontend stopped.
pause
