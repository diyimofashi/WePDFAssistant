@echo off
echo 启动极光PDF应用...

REM 激活虚拟环境
call pypdf\Scripts\activate

REM 运行主程序
python app\main.py

pause