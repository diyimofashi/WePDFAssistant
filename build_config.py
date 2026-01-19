# -*- mode: python ; coding: utf-8 -*-
"""
Nuitka 编译配置文件
用于将 PDFAssistant 编译为独立的目录模式程序
"""

import os
import sys

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(ROOT_DIR, 'app')
PLUGINS_DIR = os.path.join(APP_DIR, 'plugins')
PLUGINS_UPLOAD_DIR = os.path.join(APP_DIR, 'plugins-upload')
PLUGINS_DOWNLOAD_DIR = os.path.join(APP_DIR, 'plugins-download')
PLUGINS_BARCODE_DIR = os.path.join(APP_DIR, 'plugins-barcode')

# Nuitka 编译选项
NUITKA_OPTIONS = [
    # ==================== 基础选项 ====================
    '--standalone',               # 独立运行，包含所有依赖
    '--onefile',                  # 单文件模式（后续会改为目录模式）
    '--output-dir=dist',          # 输出目录
    '--output-filename=PDFAssistant.exe',  # 输出文件名

    # ==================== 显示选项 ====================
    '--show-progress',            # 显示编译进度
    '--show-memory',              # 显示内存使用
    '--show-scons',               # 显示构建详情

    # ==================== Python 插件 ====================
    '--enable-plugin=pyqt5',      # 启用 PyQt5 插件
    '--enable-plugin=pyside2',    # 启用 PySide2 插件（备用）
    '--include-package-data=PyQt5',  # 包含 PyQt5 数据文件

    # ==================== 导入控制 ====================
    '--follow-imports',           # 跟踪所有导入
    '--include-package=app',      # 包含 app 包
    '--include-module=fitz',      # PyMuPDF
    '--include-module=PIL',       # Pillow
    '--include-module=cv2',       # OpenCV
    '--include-module=pyzbar',    # PyZBar
    '--include-module=picologging', # picologging

    # ==================== 性能优化 ====================
    '--jobs=4',                   # 使用 4 个并行任务
    '--lto=yes',                  # 链接时优化

    # ==================== Qt 特定 ====================
    '--qt-plugins=sensible,platforms,imageformats',  # 包含必要插件
]

# 目录模式打包命令
DIRECTORY_MODE_CMD = [
    'nuitka',

    # ==================== 基础选项 ====================
    '--standalone',
    '--output-dir=dist/PyPDF',

    # ==================== 显示选项 ====================
    '--show-progress',
    '--show-memory',
    '--show-scons',

    # ==================== Python 插件 ====================
    '--enable-plugin=pyqt5',
    '--plugin-disable=anti-bloat',
    '--plugin-disable=implicit-imports',
    '--include-package-data=PyQt5',

    # ==================== 导入控制 ====================
    '--follow-imports',
    '--include-package=app',
    '--include-module=fitz',
    '--include-module=PIL',
    '--include-module=cv2',
    '--include-module=pyzbar',
    '--include-module=picologging',

    # ==================== 数据文件 ====================
    f'--include-data-dir={APP_DIR}/assets=assets',
    f'--include-data-dir={APP_DIR}/config=config',
    f'--include-data-dir={PLUGINS_DIR}=plugins',
    f'--include-data-dir={PLUGINS_UPLOAD_DIR}=plugins-upload',
    f'--include-data-dir={PLUGINS_DOWNLOAD_DIR}=plugins-download',
    f'--include-data-dir={PLUGINS_BARCODE_DIR}=plugins-barcode',

    # ==================== 性能优化 ====================
    '--jobs=4',
    '--lto=no',

    # ==================== 输入文件 ====================
    'start.py'
]

# 单文件模式打包命令（不推荐，仅作参考）
ONEFILE_MODE_CMD = [
    'nuitka',
    '--standalone',
    '--onefile',
    '--output-dir=dist',
    '--output-filename=PDFAssistant.exe',
    '--show-progress',
    '--show-memory',
    '--enable-plugin=pyqt5',
    '--include-package-data=PyQt5',
    '--follow-imports',
    '--include-package=app',
    '--include-module=fitz',
    '--include-module=PIL',
    '--include-module=cv2',
    '--include-module=pyzbar',
    '--include-module=picologging',
    f'--include-data-dir={APP_DIR}/assets=assets',
    f'--include-data-dir={APP_DIR}/config=config',
    f'--include-data-dir={PLUGINS_DIR}=plugins',
    f'--include-data-dir={PLUGINS_UPLOAD_DIR}=plugins-upload',
    f'--include-data-dir={PLUGINS_DOWNLOAD_DIR}=plugins-download',
    f'--include-data-dir={PLUGINS_BARCODE_DIR}=plugins-barcode',
    '--jobs=4',
    '--lto=no',
    'start.py'
]

# Windows 特定选项
if sys.platform == 'win32':
    DIRECTORY_MODE_CMD.extend([
        '--windows-console-mode=disable',  # 禁用控制台窗口
        '--windows-icon-from-ico=app/assets/app_icon.ico',  # 应用图标
    ])

# Linux 特定选项
elif sys.platform.startswith('linux'):
    DIRECTORY_MODE_CMD.extend([
        '--linux-icon=app/assets/app_icon.png',
    ])

# macOS 特定选项
elif sys.platform == 'darwin':
    DIRECTORY_MODE_CMD.extend([
        '--macos-create-app-bundle',
        '--macos-app-icon=app/assets/app_icon.png',
    ])

def get_directory_command():
    """获取目录模式编译命令"""
    return ' '.join(DIRECTORY_MODE_CMD)

def get_onefile_command():
    """获取单文件模式编译命令"""
    return ' '.join(ONEFILE_MODE_CMD)

if __name__ == '__main__':
    print("=" * 60)
    print("Nuitka 编译配置 - PyPDF")
    print("=" * 60)
    print()
    print("目录模式编译命令:")
    print(get_directory_command())
    print()
    print("单文件模式编译命令:")
    print(get_onefile_command())
    print()
    print("推荐使用目录模式，以获得更好的性能和可维护性")
