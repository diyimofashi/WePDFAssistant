"""
应用路径工具
提供统一的应用根目录获取方法
"""

import os
import sys


def get_app_root() -> str:
    """
    获取应用根目录
    开发环境：返回 app 目录（因为插件、配置、资源都在 app 目录下）
    编译后环境：返回可执行文件所在目录
    """
    is_frozen = getattr(sys, 'frozen', False)
    has_meipass = hasattr(sys, '_MEIPASS')

    # 只有在真正的编译后环境(frozen或_MEIPASS存在)才使用APPLICATION_PATH
    # 开发环境即使设置了APPLICATION_PATH也不应该使用
    if is_frozen or has_meipass:
        # 编译后环境
        app_path_env = os.environ.get('APPLICATION_PATH')
        if app_path_env:
            exe_dir = app_path_env
        else:
            exe_dir = os.path.dirname(sys.executable)
        print(f"使用编译后目录: {exe_dir}")
        return exe_dir
    else:
        # 开发环境：返回 app 目录
        # __file__ = app/utils/app_path.py
        # os.path.dirname(__file__) = app/utils
        # os.path.dirname(os.path.dirname(__file__)) = app
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(f"使用开发环境目录: {app_dir}")
        return app_dir


def get_plugin_dir(plugin_type: str = 'plugins') -> str:
    """
    获取插件目录
    开发环境：app 目录/plugins-type
    编译后：执行目录/plugins-type
    """
    return os.path.join(get_app_root(), plugin_type)


def get_config_dir() -> str:
    """
    获取配置目录
    开发环境：app 目录/config
    编译后：执行目录/config
    """
    return os.path.join(get_app_root(), 'config')


def get_assets_dir() -> str:
    """
    获取资源目录
    开发环境：app 目录/assets
    编译后：执行目录/assets (因为 --include-data-dir=app/assets=assets 会将 assets 放到根目录)
    """
    # 检查是否编译后环境
    is_frozen = getattr(sys, 'frozen', False)
    has_meipass = hasattr(sys, '_MEIPASS')

    if is_frozen or has_meipass:
        # 编译后环境：assets 在可执行文件所在目录
        # 因为编译时使用 --include-data-dir=app/assets=assets
        return os.path.join(get_app_root(), 'assets')
    else:
        # 开发环境：assets 在 app 目录下
        return os.path.join(get_app_root(), 'assets')
