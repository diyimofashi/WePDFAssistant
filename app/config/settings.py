"""应用配置设置"""

import os
import json
import sys

# 导入路径工具
from app.utils.app_path import get_config_dir

# 导入日志模块
from app.utils.logger import get_logger

logger = get_logger('settings')

class AppSettings:
    """应用设置类"""
    
    # 应用信息
    APP_NAME = "PDFAssistant"
    APP_VERSION = "1.0.0"
    ORGANIZATION = "PDFAssistant"
    
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

    # 日志设置
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # 设置文件路径
    SETTINGS_FILE = os.path.join(get_config_dir(), "app_settings.json")
    
    # 运行时设置
    _settings_cache = {}

    @classmethod
    def get_app_data_path(cls):
        """获取应用数据目录"""
        return get_config_dir()
    
    @classmethod
    def _load_settings(cls):
        """加载设置文件"""
        if not cls._settings_cache:
            if os.path.exists(cls.SETTINGS_FILE):
                try:
                    with open(cls.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        cls._settings_cache = json.load(f)
                    logger.debug(f"成功加载设置文件: {cls.SETTINGS_FILE}")
                    logger.debug(f"设置内容: {cls._settings_cache}")
                except Exception as e:
                    logger.error(f"加载设置失败: {e}")
                    cls._settings_cache = {}
            else:
                cls._settings_cache = {}
        return cls._settings_cache
    
    @classmethod
    def _save_settings(cls):
        """保存设置到文件"""
        try:
            os.makedirs(os.path.dirname(cls.SETTINGS_FILE), exist_ok=True)
            with open(cls.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(cls._settings_cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存设置到: {cls.SETTINGS_FILE}")
            logger.debug(f"保存的内容: {cls._settings_cache}")
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
    
    @classmethod
    def get_last_open_dir(cls):
        """获取上次打开文件的目录"""
        settings = cls._load_settings()
        return settings.get('last_open_dir', os.path.expanduser("~"))
    
    @classmethod
    def set_last_open_dir(cls, file_path):
        """设置上次打开文件的目录"""
        if file_path:
            settings = cls._load_settings()
            settings['last_open_dir'] = os.path.dirname(file_path)
            cls._save_settings()
    
    @classmethod
    def get_last_save_dir(cls):
        """获取上次保存文件的目录"""
        settings = cls._load_settings()
        return settings.get('last_save_dir', os.path.expanduser("~"))
    
    @classmethod
    def set_last_save_dir(cls, file_path):
        """设置上次保存文件的目录"""
        if file_path:
            settings = cls._load_settings()
            settings['last_save_dir'] = os.path.dirname(file_path)
            cls._save_settings()
    
    @classmethod
    def get_ocr_highlight_mode(cls):
        """获取OCR文本层高亮模式状态"""
        settings = cls._load_settings()
        return settings.get('ocr_highlight_mode', False)
    
    @classmethod
    def set_ocr_highlight_mode(cls, enabled):
        """设置OCR文本层高亮模式状态"""
        settings = cls._load_settings()
        settings['ocr_highlight_mode'] = bool(enabled)
        cls._save_settings()

    @classmethod
    def get_use_a4_scaling(cls):
        """获取是否使用A4缩放"""
        settings = cls._load_settings()
        return settings.get('use_a4_scaling', True)  # 默认启用A4缩放

    @classmethod
    def set_use_a4_scaling(cls, enabled):
        """设置是否使用A4缩放"""
        settings = cls._load_settings()
        settings['use_a4_scaling'] = bool(enabled)
        cls._save_settings()

    @classmethod
    def get_log_level(cls):
        """获取日志级别"""
        settings = cls._load_settings()
        return settings.get('log_level', cls.LOG_LEVEL)

    @classmethod
    def set_log_level(cls, level):
        """设置日志级别"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level.upper() not in valid_levels:
            logger.warning(f"无效的日志级别: {level}，使用默认值: {cls.LOG_LEVEL}")
            level = cls.LOG_LEVEL

        settings = cls._load_settings()
        settings['log_level'] = level.upper()
        cls._save_settings()

        # 实时应用日志级别
        from app.utils.logger import set_log_level
        set_log_level(level.upper())