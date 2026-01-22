@echo off
chcp 65001 >nul
REM 快速编译脚本 - 仅更新修改过的部分

title PDFAssistant - Fast Build (Incremental)

echo.
echo ============================================================
echo      PDFAssistant - Fast Incremental Build
echo ============================================================
echo  This script uses Nuitka's incremental compilation
echo  Only modified files are recompiled
echo ============================================================
echo.

REM Check virtual environment
if not exist "PDFAssistant\Scripts\activate.bat" (
    echo [Error] Virtual environment not found
    echo.
    echo Create virtual environment:
    echo   python -m venv PDFAssistant
    echo.
    pause
    exit /b 1
)

call PDFAssistant\Scripts\activate.bat

REM Check Nuitka installation
echo [1/3] Checking Nuitka...
pip show nuitka >nul 2>&1
if %errorlevel% neq 0 (
    echo [Info] Nuitka not installed, installing...
    pip install nuitka
)

REM 只删除 dist 目录，保留 build
echo [2/3] Cleaning output directory...
if exist "dist" (
    echo [Info] Deleting dist directory...
    rmdir /s /q dist
)

REM 开始快速编译
echo [3/3] Starting incremental compilation...
echo.

REM 使用 build_config.py 执行增量编译
PDFAssistant\Scripts\python.exe -c "from build_config import execute_command, command_to_string, get_windows_command; cmd = get_windows_command(incremental=True); print('[Info] Executing:', command_to_string(cmd)); exit(execute_command(cmd))"

if %errorlevel% equ 0 (
    echo [Info] Finalizing output directory...
    if exist "dist\PDFAssistant.dist" (
        if exist "dist\PDFAssistant" rmdir /s /q "dist\PDFAssistant"
        move "dist\PDFAssistant.dist" "dist\PDFAssistant"
    )

    echo [Info] Renaming start.exe to PDFAssistant.exe...
    if exist "dist\PDFAssistant\start.exe" (
        move "dist\PDFAssistant\start.exe" "dist\PDFAssistant\PDFAssistant.exe"
    )

    echo [Info] Copying all plugin directories...
    if exist "dist\PDFAssistant\app" (
        for /d %%d in ("app\plugins*") do (
            echo [Info] Copying %%~nxd to dist\PDFAssistant\app\...
            if exist "%%d" xcopy /e /y "%%d" "dist\PDFAssistant\app\%%~nxd\"
        )
    )
)

echo.
if %errorlevel% equ 0 (
    echo [Info] Incremental build successful!
    echo.
    echo  Output directory: dist\PDFAssistant
    echo  Executable: dist\PDFAssistant\PDFAssistant.exe
) else (
    echo [Error] Build failed
)

echo.
pause
