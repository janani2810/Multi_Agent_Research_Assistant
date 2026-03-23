@echo off
REM Start AI Research Assistant - UI + Backend
REM This batch file starts both the FastAPI backend and opens the web UI

echo.
echo ========================================
echo  🚀 AI Research Assistant Starter
echo ========================================
echo.

REM Get the project directory
set PROJECT_DIR=C:\Users\Jananya\Desktop\MULTI-AGENT_RESEARCH_ASSISTANT

REM Check if project exists
if not exist "%PROJECT_DIR%" (
    echo ❌ Project directory not found: %PROJECT_DIR%
    pause
    exit /b 1
)

echo ✅ Project found: %PROJECT_DIR%
echo.

REM Change to project directory
cd /d "%PROJECT_DIR%"

echo Starting FastAPI backend...
echo.

REM Start FastAPI in a new window
start "FastAPI Backend" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo ✅ Backend starting on port 8000...
echo Waiting 3 seconds for backend to initialize...

timeout /t 3 /nobreak

echo.
echo Opening Web UI...
echo.

REM Open HTML file in default browser
start "" "file:///%PROJECT_DIR:C:\=/%\index.html"

echo.
echo ========================================
echo ✅ Backend: http://localhost:8000
echo ✅ UI: index.html (should open automatically)
echo ========================================
echo.
echo Keep the backend window open!
echo.
pause