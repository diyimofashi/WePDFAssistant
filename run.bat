@echo off
chcp 65001 >nul
title PDFAssistant - 集成优化版

echo.
echo ============================================================
echo              PDFAssistant - Performance Optimized
echo ============================================================
echo  Auto-detecting and enabling all performance features
echo   - Async loading • Virtual scrolling • Smart cache • Lazy thumbnails
echo   - Real-time performance monitoring • Auto memory optimization
echo ============================================================
echo.

REM Check virtual environment
if not exist "PDFAssistant\Scripts\activate.bat" (
    echo [Error] Virtual environment not found: PDFAssistant
    echo.
    echo Creating virtual environment...
    python -m venv PDFAssistant

    REM Install dependencies
    call PDFAssistant\Scripts\activate
    pip install -r requirements.txt
    echo.
)

REM Activate virtual environment
call PDFAssistant\Scripts\activate.bat

REM Try to run the program
python start.py

REM If error occurs, show error message
if %errorlevel% neq 0 (
    echo.
    echo ============================================================
    echo Program exited with error code: %errorlevel%
    echo.
    echo Possible causes:
    echo   1. Missing Python module in requirements.txt
    echo   2. Run: pip install <missing_module>
    echo   3. Or run: scan_imports.py to detect all imports
    echo ============================================================
    pause
)