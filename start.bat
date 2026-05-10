@echo off
title Inscriptio Launcher
echo   Initiating Inscriptio Launch Sequence (Windows)

echo.
echo [1/5] Checking Python compatibility...
python -c "import sys; major, minor = sys.version_info[:2]; sys.exit(0 if major == 3 and 9 <= minor <= 11 else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] ERROR: Incompatible or missing Python version.
    echo     TensorFlow requires Python 3.9, 3.10, or 3.11.
    echo     Python 3.12+ will cause the ML pipeline to crash.
    echo.
    echo     HOW TO FIX THIS:
    echo     1. Download Python 3.11 from python.org
    echo     2. Run the installer.
    echo     3. IMPORTANT: Check the box that says "Add python.exe to PATH"!
    echo.
    pause
    exit /b 1
)
echo [OK] Valid Python version found.

echo.
echo [2/5] Preparing Virtual Environment...
if not exist ".venv\" (
    echo [!] Creating new virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate

echo.
echo [3/5] Checking and Installing Dependencies...
pip install --prefer-binary -r inscriptio\python\requirements.txt

echo.
echo [4/5] Starting Servers...
:: Opens a new terminal window specifically for the Frontend
start "Inscriptio Frontend (Port 5500)" cmd /k "call .venv\Scripts\activate && python -m http.server 5500"

:: Opens a new terminal window specifically for the Backend
start "Inscriptio Backend API (Port 8000)" cmd /k "cd inscriptio\python && call ..\..\.venv\Scripts\activate && python -m uvicorn main:app --reload --port 8000"

echo.
echo [5/5] Launching Application...
echo Waiting 5 seconds for the ML model to load...
timeout /t 5 /nobreak >nul

start http://localhost:5500/inscriptio/html/01_authentication_portal.html

echo.
echo Launch Complete! 
echo You can now close this launcher window safely.
pause

REM run .\start.bat on terminal  