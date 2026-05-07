@echo off
title BusBook TN - Bus Booking System
color 0A

echo ============================================
echo    BusBook TN - Bus Booking System
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b
)

echo [1/3] Python found. Checking pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not found.
    pause
    exit /b
)

echo [2/3] Installing required packages...
pip install -r requirements.txt --quiet

if errorlevel 1 (
    echo [ERROR] Failed to install packages. Check your internet connection.
    pause
    exit /b
)

echo [3/3] Starting BusBook TN server...
echo.
echo ============================================
echo  Server running at: http://127.0.0.1:5000
echo  Admin Login: admin@busbook.com / admin123
echo  Press Ctrl+C to stop the server
echo ============================================
echo.

start "" http://127.0.0.1:5000
python app.py

pause
