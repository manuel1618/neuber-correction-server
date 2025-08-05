@echo off
REM Neuber Correction Server Start Script (Windows Batch)
REM Usage: start_server.bat [PORT]

setlocal enabledelayedexpansion

REM Default port
set PORT=%1
if "%PORT%"=="" set PORT=8000

REM Check if uv is available
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: uv is not installed or not in PATH. Please install uv first.
    exit /b 1
)

REM Check if dependencies are installed
if not exist "uv.lock" (
    echo Installing dependencies...
    uv sync >nul 2>&1
)

REM Set environment variables for silent operation
set PYTHONUNBUFFERED=1
set UV_SILENT=1

REM Start the server silently
echo Starting Neuber Correction Server on port %PORT%...
echo Server URL: http://localhost:%PORT%
echo Press Ctrl+C to stop the server

REM Start uvicorn with minimal output
uv run uvicorn app.main:app --host 0.0.0.0 --port %PORT% --no-access-log --log-level error 