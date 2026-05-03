@echo off
chcp 65001 >nul
title AI TestCase Generator v4.0

echo.
echo ============================================
echo    AI TestCase Generator v4.0
echo    URL: http://localhost:8088
echo    API: http://localhost:8088/docs
echo    Shortcut: Ctrl+K Command Palette
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo [SETUP] Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo [SETUP] Installing dependencies...
    python -m pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

set PORT=8088
netstat -ano | findstr ":%PORT%" >nul 2>&1
if not errorlevel 1 (
    echo [WARN] Port %PORT% is in use, trying 8089...
    set PORT=8089
)

echo.
echo [START] http://localhost:%PORT%
echo [DOCS]  http://localhost:%PORT%/docs
echo.
echo Press Ctrl+C to stop
echo.

python run.py

pause

