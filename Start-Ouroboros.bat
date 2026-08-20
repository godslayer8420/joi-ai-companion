@echo off
REM Start-Ouroboros.bat  --  Launch Ouroboros sidecar with full Ollama backend
REM No API key required -- routes all models to local Ollama at port 11434
REM Port 8765 (AGENT_SERVER_PORT from ouroboros/config.py)

setlocal

set "REPO_ROOT=%~dp0"
set "OUROBOROS_DIR=%REPO_ROOT%ai_core\ouroboros\ouroboros-main"
set "SETTINGS_FILE=%REPO_ROOT%ai_core\ouroboros\ouroboros_ollama_settings.json"

REM Point Ouroboros data/app root to local AppData so it doesn't scatter files
set "OUROBOROS_APP_ROOT=%APPDATA%\Aurion\Ouroboros"
set "OUROBOROS_DATA_DIR=%APPDATA%\Aurion\Ouroboros\data"
set "OUROBOROS_SETTINGS_PATH=%APPDATA%\Aurion\Ouroboros\data\settings.json"

REM Route all LLM calls to local Ollama (OpenAI-compatible API)
set "OPENAI_COMPATIBLE_BASE_URL=http://localhost:11434/v1"
set "OPENAI_COMPATIBLE_API_KEY=ollama"
set "OUROBOROS_MODEL=ouroboros-next"
set "OUROBOROS_MODEL_HEAVY=ouroboros-next"
set "OUROBOROS_MODEL_LIGHT=gemma3-voice"
set "OUROBOROS_MODEL_CONSCIOUSNESS=ouroboros-next"
set "OUROBOROS_MODEL_FALLBACKS="
set "OUROBOROS_MODEL_DEEP_SELF_REVIEW=eva-7b"
set "ANTHROPIC_API_KEY="
set "OPENAI_API_KEY="
set "TOTAL_BUDGET=0"
set "OUROBOROS_PER_TASK_COST_USD=0"
set "OUROBOROS_MAX_ROUNDS=99"
set "OUROBOROS_MAX_WORKERS=3"

REM Copy our settings into the expected location
if not exist "%APPDATA%\Aurion\Ouroboros\data" mkdir "%APPDATA%\Aurion\Ouroboros\data"
copy /Y "%SETTINGS_FILE%" "%APPDATA%\Aurion\Ouroboros\data\settings.json" >nul

echo [Ouroboros] Starting Ouroboros soul sidecar on port 8765...
echo [Ouroboros] Backend: Ollama (http://localhost:11434/v1)
echo [Ouroboros] Primary model: ouroboros-next
echo.

cd /d "%OUROBOROS_DIR%"
python server.py --port 8765 --host 127.0.0.1

endlocal