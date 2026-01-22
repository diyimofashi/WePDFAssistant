#!/bin/bash
# Nuitka 编译脚本 - Linux/macOS
# 用于将 PDFAssistant 编译为独立的目录模式程序

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "         PyPDF - Nuitka 目录模式编译脚本                  "
echo "═══════════════════════════════════════════════════════════"
echo "  编译模式: 目录模式（推荐）"
echo "  优点:"
echo "    - 启动更快（无需解压临时文件）"
echo "    - 资源文件可见（方便修改配置）"
echo "    - 体积更小"
echo "    - 代码已编译为 C，难以反编译"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 检测操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
else
    echo "[错误] 不支持的操作系统: $OSTYPE"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "pypdf/bin" ] && [ ! -d "pypdf/Scripts" ]; then
    echo "[错误] 未找到虚拟环境，请先创建虚拟环境"
    echo ""
    echo "运行以下命令创建虚拟环境:"
    echo "  python3 -m venv pypdf"
    echo ""
    exit 1
fi

# 激活虚拟环境
echo "[1/5] 激活虚拟环境..."
if [ -f "pypdf/bin/activate" ]; then
    source pypdf/bin/activate
else
    source pypdf/Scripts/activate
fi

# 检查 Nuitka 是否安装
echo "[2/5] 检查 Nuitka..."
if ! pip show nuitka > /dev/null 2>&1; then
    echo "[信息] Nuitka 未安装，正在安装..."
    pip install nuitka
fi

# 清理旧的编译输出
echo "[3/5] 清理旧的编译输出..."
rm -rf dist build

# 开始编译
echo "[4/5] 开始 Nuitka 编译（这可能需要 10-30 分钟）..."
echo ""

# 使用 build_config.py 执行编译
python -c "from build_config import execute_command, command_to_string, get_linux_command, get_macos_command; import sys; cmd = get_linux_command() if sys.platform.startswith('linux') else get_macos_command(); print('[Info] Executing:', command_to_string(cmd)); exit(execute_command(cmd))"

echo ""
if [ $? -eq 0 ]; then
    echo "[5/5] 编译成功！"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "                    编译成功！                              "
    echo "═══════════════════════════════════════════════════════════"
    echo "  输出目录: dist/PyPDF"
    echo "  可执行文件: dist/PyPDF/start.bin"
    echo ""
    echo "  接下来的步骤:"
    echo "    1. 测试程序运行: cd dist/PyPDF && ./start.bin"
    echo "    2. 打包发布: 将 dist/PyPDF 目录打包发布"
    echo "═══════════════════════════════════════════════════════════"
else
    echo "[错误] 编译失败，请检查错误信息"
fi

echo ""
