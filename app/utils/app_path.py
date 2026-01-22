"""
应用路径工具
提供统一的应用根目录获取方法
"""

import os
import sys


def get_app_root():
    """
    获取应用根目录
    """
    is_frozen = getattr(sys, 'frozen', False)
    has_meipass = hasattr(sys, '_MEIPASS')
    app_path_env = os.environ.get('APPLICATION_PATH')
    
    if is_frozen or has_meipass or app_path_env:
        if app_path_env:
            exe_dir = app_path_env
        else:
            exe_dir = os.path.dirname(sys.executable)
        app_dir = os.path.join(exe_dir, 'app')
        if os.path.exists(app_dir):
            print(f"使用应用目录: {app_dir}")
            return app_dir
        print(f"使用执行目录: {exe_dir}")
        return exe_dir
    else:
        print(f"使用当前目录: {os.path.dirname(os.path.abspath(__file__))}")
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_plugin_dir(plugin_type='plugins'):
    return os.path.join(get_app_root(), plugin_type)


def get_config_dir():
    return os.path.join(get_app_root(), 'config')


def get_assets_dir():
    return os.path.join(get_app_root(), 'assets')
