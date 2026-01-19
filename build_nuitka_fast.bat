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

nuitka --standalone ^
       --output-dir=dist ^
       --show-progress ^
       --show-memory ^
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
    echo [Info] Incremental build successful!
    echo.
    echo  Output directory: dist\PDFAssistant
    echo  Executable: dist\PDFAssistant\start.exe
) else (
    echo [Error] Build failed
)

echo.
pause
