@echo off
title MNP Payroll Subsystem - Test Suite
echo ============================================================
echo  Running MNP Payroll Subsystem Automated Verification
echo ============================================================
echo.

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py test_prototype.py
    echo.
    pause
    goto end
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python test_prototype.py
    echo.
    pause
    goto end
)

where python3 >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python3 test_prototype.py
    echo.
    pause
    goto end
)

echo [ERROR] Python was not found on your system PATH.
echo Please install Python from https://www.python.org/ or check "Add Python to PATH".
echo.
pause

:end
