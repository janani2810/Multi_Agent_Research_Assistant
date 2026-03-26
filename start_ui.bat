@echo off
REM Multi-Agent Research Assistant - Complete Starter
REM This batch file starts backend and opens UI

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Multi-Agent Research Assistant
echo ========================================
echo.

REM Get the project directory (where this script is)
set PROJECT_DIR=%~dp0
set PROJECT_DIR=%PROJECT_DIR:~0,-1%

echo Project Directory: %PROJECT_DIR%

REM Check if venv exists
if not exist "%PROJECT_DIR%\venv" (
    echo.
    echo ❌ Virtual environment not found!
    echo Please create it first:
    echo   python -m venv venv
    echo   .\venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo ✅ Virtual environment found
echo.

REM Check if index.html exists
if not exist "%PROJECT_DIR%\index.html" (
    echo ❌ index.html not found in %PROJECT_DIR%
    pause
    exit /b 1
)

echo ✅ index.html found
echo.

REM Check if main.py exists
if not exist "%PROJECT_DIR%\main.py" (
    echo ❌ main.py not found
    pause
    exit /b 1
)

echo ✅ main.py found
echo.

REM Change to project directory
cd /d "%PROJECT_DIR%"

echo ========================================
echo Starting Backend...
echo ========================================
echo.

REM Start FastAPI backend in new window
start "FastAPI Backend - Multi-Agent Research" cmd /k "venv\Scripts\activate.bat && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

echo ✅ Backend started (wait 3 seconds for initialization)
echo.

REM Wait for backend to start
timeout /t 3 /nobreak

echo.
echo ========================================
echo Opening Web UI...
echo ========================================
echo.

REM Open index.html in default browser
REM Use file:// protocol with proper path conversion
for /f "tokens=*" %%A in ('cd /d %PROJECT_DIR% ^& cd') do set FULL_PATH=%%A
set HTML_PATH=%FULL_PATH:\=/%
set HTML_FILE=file:///%HTML_PATH%/index.html

echo Opening: %HTML_FILE%
start "" "%HTML_FILE%"

echo.
echo ========================================
echo ✅ SYSTEM READY!
echo ========================================
echo.
echo Backend URL:  http://127.0.0.1:8000
echo Health check: http://127.0.0.1:8000/health
echo API Docs:     http://127.0.0.1:8000/docs
echo UI:           index.html (opened in browser)
echo.
echo ========================================
echo INSTRUCTIONS:
echo ========================================
echo 1. Wait for browser to open (5-10 seconds)
echo 2. If browser doesn't open, manually visit:
echo    file:///C:/Users/Jananya/Desktop/MULTI-AGENT_RESEARCH_ASSISTANT/index.html
echo 3. Enter a research topic and click "Start Research"
echo 4. Watch real-time progress (takes 2-3 minutes)
echo 5. Download your report when complete
echo.
echo IMPORTANT: Keep the "FastAPI Backend" window open!
echo            Closing it will stop the system.
echo.
pause
