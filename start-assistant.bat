@echo off
cd /d "%~dp0"
if exist "NeginAI-Assistant.exe" (
  start "" "NeginAI-Assistant.exe"
) else (
  call ".venv\Scripts\activate.bat"
  start "" http://127.0.0.1:8000/assistant
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
)
