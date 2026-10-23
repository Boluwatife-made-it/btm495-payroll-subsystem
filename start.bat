@echo off
title MNP Payroll Subsystem - Server
echo ============================================================
echo  Starting MNP Payroll Subsystem (BTM 495 Working Prototype)
echo ============================================================
echo.

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo Detected Python launcher (py). Starting server...
    py app.py
    goto end
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo Detected Python. Starting server...
    python app.py
    goto end
)

where python3 >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo Detected Python 3. Starting server...
    python3 app.py
    goto end
)

echo [ERROR] Python was not found on your system PATH.
echo Please install Python from https://www.python.org/ or check "Add Python to PATH".
echo.
pause

:end
