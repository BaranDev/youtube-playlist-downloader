@echo off
REM YouTube Playlist Downloader - Auto Setup and Run Script
REM This script creates a virtual environment, installs dependencies, and runs the app

echo ============================================
echo YouTube Playlist Downloader - Setup and Run
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.7 or higher from https://www.python.org/
    echo.
    pause
    exit /b 1
)

echo [1/4] Checking Python installation...
python --version
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [2/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        echo.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
    echo.
) else (
    echo [2/4] Virtual environment already exists.
    echo.
)

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    echo.
    pause
    exit /b 1
)
echo.

REM Install/update dependencies
echo [4/4] Installing/updating dependencies...
echo This may take a few minutes on first run...
echo.
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    echo.
    pause
    exit /b 1
)
echo.

REM Run the application
echo ============================================
echo Starting YouTube Playlist Downloader...
echo ============================================
echo.
python main.py

REM Deactivate virtual environment when app closes
deactivate

echo.
echo Application closed.
pause
