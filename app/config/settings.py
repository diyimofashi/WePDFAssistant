"""应用配置设置"""

import os

class AppSettings:
    """应用设置类"""
    
    # 应用信息
    APP_NAME = "极灵PDF"
    APP_VERSION = "1.0.0"
    ORGANIZATION = "极灵科技"
    
    # 窗口设置
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    WINDOW_MIN_WIDTH = 800
    WINDOW_MIN_HEIGHT = 600
    
    # 主题设置
    THEME = "light"  # dark/light
    
    # 文件设置
    SUPPORTED_FORMATS = ["*.pdf"]
    RECENT_FILES_LIMIT = 10
    
    # 预览设置
    DEFAULT_ZOOM = 100
    ZOOM_LEVELS = [25, 50, 75, 100, 125, 150, 200, 300, 400]
    
    # 文件记忆设置
    LAST_OPEN_DIR = ""
    LAST_SAVE_DIR = ""
    
    @classmethod
    def get_app_data_path(cls):
        """获取应用数据目录"""
        return os.path.join(os.path.expanduser("~"), ".flashpdf")
    
    @classmethod
    def get_last_open_dir(cls):
        """获取上次打开文件的目录"""
        return cls.LAST_OPEN_DIR if cls.LAST_OPEN_DIR else os.path.expanduser("~")
    
    @classmethod
    def set_last_open_dir(cls, file_path):
        """设置上次打开文件的目录"""
        if file_path:
            cls.LAST_OPEN_DIR = os.path.dirname(file_path)
    
    @classmethod
    def get_last_save_dir(cls):
        """获取上次保存文件的目录"""
        return cls.LAST_SAVE_DIR if cls.LAST_SAVE_DIR else os.path.expanduser("~")
    
    @classmethod
    def set_last_save_dir(cls, file_path):
        """设置上次保存文件的目录"""
        if file_path:
            cls.LAST_SAVE_DIR = os.path.dirname(file_path)