@echo off
REM Create installer script using Inno Setup

title PyPDF - Create Installer

echo.
echo ============================================================
echo         PyPDF - Inno Setup Installer Creator
echo ============================================================
echo  Using Inno Setup to create Windows installer
echo
echo  Features:
echo    - Install to Program Files
echo    - Register as default PDF reader
echo    - Create desktop shortcut
echo    - Add to Start Menu
echo    - Full uninstall support
echo ============================================================
echo.

REM Check if dist/PDFAssistant directory exists
if exist "dist\PDFAssistant\start.exe" (
    goto :check_inno
) else (
    echo [Error] Compiled program not found
    echo.
    echo Please run build_nuitka.bat first to compile
    echo.
    pause
    exit /b 1
)

:check_inno
REM Check if Inno Setup is installed
echo [1/3] Checking Inno Setup...
iscc >nul 2>&1
if errorlevel 1 goto :no_inno
goto :clean_installer

:no_inno
echo.
echo [Error] Inno Setup compiler ^(iscc.exe^) is missing
echo.
echo Please install Inno Setup first:
echo   Download: https://jrsoftware.org/isdl.php
echo   Or visit: https://innosetup.com/
echo.
pause
exit /b 1

:clean_installer

REM Clean old installer
echo [2/3] Cleaning old installer...
if exist "installer" (
    echo [Info] Deleting old installer directory...
    rmdir /s /q installer
)

REM Compile installer
echo [3/3] Compiling installer...
echo.

iscc create_installer.iss

echo.
if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo              Installer created successfully!
    echo ============================================================
    echo  Output file: installer\PDFAssistant-Setup.exe
    echo
    echo  You can now:
    echo    1. Distribute the installer to users
    echo    2. Users double-click to install
    echo    3. Choose to set as default PDF reader during install
    echo ============================================================
    echo.
) else (
    echo [Error] Installer creation failed, please check error messages
)

pause
