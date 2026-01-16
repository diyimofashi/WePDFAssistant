"""应用配置设置"""

import os
import json
import sys

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('settings')

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
    
    # 设置文件路径
    SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".aurora_pdf_settings.json")
    
    # 运行时设置
    _settings_cache = {}
    
    @classmethod
    def get_app_data_path(cls):
        """获取应用数据目录"""
        return os.path.join(os.path.expanduser("~"), ".aurora_pdf")
    
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