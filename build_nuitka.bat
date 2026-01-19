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
REM 保留 build 目录以支持增量编译
REM if exist "build" (
REM     echo [Info] Deleting build directory...
REM     rmdir /s /q build
REM )

REM Start compilation
echo [4/5] Starting Nuitka compilation (this may take 10-30 minutes)...
echo.

REM Execute Nuitka compilation
nuitka --standalone ^
       --output-dir=dist ^
       --show-progress ^
       --show-memory ^
       --show-scons ^
       --enable-plugin=pyqt5 ^
       --plugin-disable=anti-bloat ^
       --plugin-disable=implicit-imports ^
       --include-package-data=PyQt5 ^
       --follow-imports ^
       --include-package=app ^
       --include-module=fitz ^
       --include-module=PIL ^
       --include-module=cv2 ^
       --include-module=pyzbar ^
       --include-module=picologging ^
       --include-data-dir=app\assets=assets ^
       --include-data-dir=app\config=config ^
       --include-data-dir=app\plugins=plugins ^
       --include-data-dir=app\plugins-upload=plugins-upload ^
       --include-data-dir=app\plugins-download=plugins-download ^
       --include-data-dir=app\plugins-barcode=plugins-barcode ^
       --jobs=2 ^
       --lto=no ^
       --windows-console-mode=disable ^
       --windows-icon-from-ico=app\assets\app_icon.ico ^
       start.py

if %errorlevel% equ 0 (
    echo [Info] Finalizing output directory...
    if exist "dist\start.dist" (
        if exist "dist\PDFAssistant" rmdir /s /q "dist\PDFAssistant"
        move "dist\start.dist" "dist\PDFAssistant"
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
    echo [5/5] Compilation successful!
    echo.
    echo ============================================================
    echo                  Compilation successful!
    echo ============================================================
    echo  Output directory: dist\PDFAssistant
    echo  Executable: dist\PDFAssistant\start.exe
    echo
    echo  Next steps:
    echo    1. Test the program: dist\PDFAssistant\start.exe
    echo    2. Create installer: create_installer.bat
    echo ============================================================
) else (
    echo [Error] Compilation failed, please check the error messages
)

echo.
pause
