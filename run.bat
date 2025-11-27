@echo off
title 极灵PDF - 集成优化版

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║                🚀 极灵PDF 集成优化版                      ║
echo ╠════════════════════════════════════════════════════════╣
echo ║  自动检测并启用所有性能优化特性                              ║
echo ║  ⚡ 异步加载 • 虚拟滚动 • 智能缓存 • 延迟缩略图         ║
echo ║  📊 实时性能监控 • 自动内存优化                             ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM 激活虚拟环境
call pypdf\Scripts\activate

REM 运行主程序
python start.py

REM 如果出错则暂停
if %errorlevel% neq 0 (
    echo.
    echo ❌ 程序运行出错，错误代码: %errorlevel%
    pause
)