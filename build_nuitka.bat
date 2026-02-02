@echo off
chcp 65001 >nul
REM Nuitka compilation script for Windows
REM Compile PDFAssistant to standalone directory mode

title PDFAssistant - Nuitka Build

echo.
echo ============================================================
echo      PDFAssistant - Nuitka Directory Build Script
echo ============================================================
echo  Mode: Directory Mode (Recommended)
echo  Advantages:
echo    - Faster startup (no temp file extraction)
echo    - Resource files visible (easy to modify config)
echo    - Smaller size
echo    - Code compiled to C, hard to decompile
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

REM Activate virtual environment
echo [1/5] Activating virtual environment...

REM Ensure virtual environment is properly initialized
if not exist "PDFAssistant\Scripts\python.exe" (
    echo [Error] Virtual environment not properly set up
    echo.
    echo Please run: python -m venv PDFAssistant
    echo.
    pause
    exit /b 1
)

call PDFAssistant\Scripts\activate.bat

REM Check and create pyvenv.cfg if needed
if not exist "PDFAssistant\pyvenv.cfg" (
    echo [Info] Creating virtual environment configuration...
    python -c "import venv; import os; os.makedirs('PDFAssistant', exist_ok=True); f=open('PDFAssistant\\pyvenv.cfg','w'); f.write('home = '+os.path.dirname(os.path.dirname(venv.__file__))); f.close()" 2>nul || echo [Warning] Could not create pyvenv.cfg
)

REM Check Nuitka installation
echo [2/5] Checking Nuitka...
pip show nuitka >nul 2>&1
if %errorlevel% neq 0 (
    echo [Info] Nuitka not installed, installing...
    pip install nuitka
)

REM 清理旧的编译输出
echo [3/5] Cleaning old build output...
if exist "dist" (
    echo [Info] Deleting dist directory...
    rmdir /s /q dist
)

REM Start compilation
echo [4/5] Starting Nuitka compilation (this may take 10-30 minutes)...
echo.

REM Execute Nuitka compilation using build_config.py
PDFAssistant\Scripts\python.exe -c "from build_config import execute_command, command_to_string, get_windows_command; cmd = get_windows_command(); print('[Info] Executing:', command_to_string(cmd)); exit(execute_command(cmd))"

if %errorlevel% equ 0 (
    echo [Info] Renaming PDFAssistant.exe if needed...

    echo [Info] Copying all plugin directories...
    if exist "dist\start.dist\app" (
        for /d %%d in ("app\plugins*") do (
            echo [Info] Copying %%~nxd to dist\start.dist\app\...
            if exist "%%d" xcopy /e /y "%%d" "dist\start.dist\app\%%~nxd\"
        )
    )

    echo [Info] Copying all plugin directories...
    if exist "dist\start.dist\app" (
        for /d %%d in ("app\plugins*") do (
            echo [Info] Copying %%~nxd to dist\start.dist\app\...
            if exist "%%d" xcopy /e /y "%%d" "dist\start.dist\app\%%~nxd\"
        )
    )
)
REM 复制插件到dist/start.dist目录
if exist "app\plugins" (
    for /d %%d in ("app\plugins*") do (
        echo [Info] Copying %%~nxd to dist\start.dist\app\...
        if exist "%%d" xcopy /e /y "%%d" "dist\start.dist\%%~nxd\"
    )
)

echo.
if %errorlevel% equ 0 (
    echo [5/5] Compilation successful!
    echo.
    echo ============================================================
    echo                  Compilation successful!
    echo ============================================================
    echo  Output directory: dist\start.dist
    echo  Executable: dist\start.dist\PDFAssistant.exe
    echo
    echo  Next steps:
    echo    1. Test the program: dist\start.dist\PDFAssistant.exe
    echo    2. Create installer: create_installer.bat
    echo ============================================================
) else (
    echo [Error] Compilation failed, please check the error messages
)

echo.
pause
