# -*- mode: python ; coding: utf-8 -*-
"""
Nuitka 编译配置文件
统一管理 Nuitka 编译参数，支持多平台构建
"""

import os
import sys

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(ROOT_DIR, 'app')



def get_base_command(output_dir: str = 'dist', incremental: bool = False):
    """获取基础 Nuitka 编译命令（跨平台通用）"""
    cmd = [
        'nuitka',
        '--standalone',
        f'--output-dir={output_dir}',
        '--show-progress',
        '--show-memory',
        '--show-scons',
        '--enable-plugin=pyqt5',
        '--follow-imports',
        '--include-package=app',
        '--include-module=fitz',
        '--include-module=PIL',
        '--include-module=cv2',
        '--include-module=pyzbar',
        '--include-module=picologging',
        '--include-package=qcloud_cos',
        '--include-package=oss2',
        '--include-package=paramiko',
        '--include-data-dir=app/assets=assets',
        '--include-data-dir=app/config=config',
    ]

    if incremental:
        cmd.extend(['--jobs=2', '--lto=no'])
    else:
        cmd.extend(['--jobs=4', '--lto=no'])

    cmd.append('start.py')
    return cmd


def get_windows_command(output_dir='dist', incremental=False):
    """获取 Windows 平台编译命令"""
    cmd = get_base_command(output_dir, incremental)
    # Windows 特定选项
    windows_options = [
        '--plugin-disable=anti-bloat',
        '--plugin-disable=implicit-imports',
        '--include-package-data=PyQt5',
        '--windows-console-mode=disable',
        '--windows-icon-from-ico=app/assets/app_icon.ico',
        '--output-filename=PDFAssistant.exe',
    ]
    # 在 start.py 之前插入 Windows 选项
    cmd = cmd[:-1] + windows_options + [cmd[-1]]
    return cmd


def get_linux_command(output_dir: str = 'dist/PyPDF'):
    """获取 Linux 平台编译命令"""
    cmd = get_base_command(output_dir)
    cmd.extend([
        '--include-package-data=PyQt5',
        '--linux-icon=app/assets/app_icon.png',
    ])
    return cmd


def get_macos_command(output_dir: str = 'dist/PyPDF'):
    """获取 macOS 平台编译命令"""
    cmd = get_base_command(output_dir)
    cmd.extend([
        '--include-package-data=PyQt5',
        '--macos-create-app-bundle',
        '--macos-app-icon=app/assets/app_icon.png',
    ])
    return cmd


def get_command():
    """根据当前平台返回编译命令"""
    if sys.platform == 'win32':
        return get_windows_command()
    elif sys.platform.startswith('linux'):
        return get_linux_command()
    elif sys.platform == 'darwin':
        return get_macos_command()
    else:
        raise ValueError(f'Unsupported platform: {sys.platform}')


def execute_command(cmd: list[str]) -> int:
    """执行命令并返回退出码"""
    import subprocess
    import shutil
    try:
        nuitka_path = shutil.which('nuitka')
        if not nuitka_path:
            print(f"[Error] 未找到 nuitka 命令")
            print(f"[Info] 请确保已在虚拟环境中安装: pip install nuitka")
            return 1
        print(f"[Info] 使用 nuitka: {nuitka_path}")
        cmd[0] = nuitka_path
        result = subprocess.run(cmd, shell=False)
        return result.returncode
    except FileNotFoundError as e:
        print(f"[Error] 命令未找到: {cmd[0]}")
        return 1
    except Exception as e:
        print(f"[Error] 执行命令失败: {e}")
        return 1


def command_to_string(cmd: list[str]) -> str:
    """将命令列表转换为字符串（仅用于显示）"""
    return ' '.join(f'"{c}"' if ' ' in c else c for c in cmd)


if __name__ == '__main__':
    print("=" * 60)
    print("Nuitka 编译配置 - PyPDF")
    print("=" * 60)
    print()
    print(f"当前平台: {sys.platform}")
    print()
    print("编译命令:")
    print(command_to_string(get_command()))
    print()
    print("=" * 60)
