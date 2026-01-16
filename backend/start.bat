@echo off
REM EURABAY Living System - Backend Startup Script for Windows

echo ========================================
echo EURABAY Living System - Backend Startup
echo ========================================
echo.

REM Check Python version
echo Checking Python version...
python --version
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found. Creating...
    python -m venv venv
    echo Virtual environment created.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
echo Dependencies installed.
echo.

REM Create necessary directories
echo Creating directories...
if not exist "data\" mkdir data
if not exist "logs\" mkdir logs
echo Directories created.
echo.

REM Check if .env exists
if not exist ".env" (
    echo .env file not found. Copying from .env.example...
    copy .env.example .env
    echo Please update .env with your configuration.
    echo.
)

REM Start the server
echo Starting EURABAY Living System backend...
echo API Documentation: http://127.0.0.1:8000/api/docs
echo Health Check: http://127.0.0.1:8000/health
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run the application
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
