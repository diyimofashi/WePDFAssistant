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

    @classmethod
    def get_file_list_panel_visible(cls):
        """获取文件列表面板是否默认显示"""
        settings = cls._load_settings()
        return settings.get('file_list_panel_visible', False)  # 默认不显示

    @classmethod
    def set_file_list_panel_visible(cls, visible):
        """设置文件列表面板是否默认显示"""
        settings = cls._load_settings()
        settings['file_list_panel_visible'] = bool(visible)
        cls._save_settings()

    @classmethod
    def get_file_list_panel_width(cls):
        """获取文件列表面板宽度"""
        settings = cls._load_settings()
        return settings.get('file_list_panel_width', 600)  # 默认600像素

    @classmethod
    def set_file_list_panel_width(cls, width):
        """设置文件列表面板宽度"""
        settings = cls._load_settings()
        settings['file_list_panel_width'] = int(width)
        cls._save_settings()

    # ==================== 文件历史记录相关设置 ====================

    @classmethod
    def get_file_history(cls):
        """获取文件历史记录"""
        settings = cls._load_settings()
        return settings.get('file_history', {
            'max_recent': 20,
            'max_per_category': 10,
            'categories': {},
            'category_mapping': {},
            'custom_categories': []
        })

    @classmethod
    def _save_file_history(cls, history_data):
        """保存文件历史记录"""
        settings = cls._load_settings()
        settings['file_history'] = history_data
        cls._save_settings()

    @classmethod
    def get_recent_files(cls):
        """获取最近文件列表"""
        history = cls.get_file_history()
        return history.get('recent_files', [])

    @classmethod
    def add_recent_file(cls, file_path, filename, page_count=0):
        """添加最近文件记录"""
        import time
        history = cls.get_file_history()
        recent_files = history.get('recent_files', [])

        # 检查是否已存在该文件
        for record in recent_files:
            if record.get('path') == file_path:
                # 更新打开时间
                record['open_time'] = int(time.time())
                record['open_count'] = record.get('open_count', 0) + 1
                # 移动到列表开头
                recent_files.remove(record)
                recent_files.insert(0, record)
                cls._save_file_history(history)
                return

        # 创建新记录
        new_record = {
            'path': file_path,
            'filename': filename,
            'open_time': int(time.time()),
            'open_count': 1,
            'last_page': 0,
            'page_count': page_count
        }

        # 添加到列表开头
        recent_files.insert(0, new_record)

        # 检查数量限制
        max_recent = history.get('max_recent', 20)
        if len(recent_files) > max_recent:
            recent_files = recent_files[:max_recent]

        history['recent_files'] = recent_files
        cls._save_file_history(history)

    @classmethod
    def clear_recent_files(cls):
        """清除所有最近文件记录"""
        history = cls.get_file_history()
        history['recent_files'] = []
        cls._save_file_history(history)

    @classmethod
    def get_file_categories(cls):
        """获取分类记录"""
        history = cls.get_file_history()
        return history.get('categories', {})

    @classmethod
    def add_file_to_category(cls, file_path, filename, category_name, page_count=0):
        """添加文件到分类"""
        import time
        history = cls.get_file_history()
        categories = history.get('categories', {})

        if category_name not in categories:
            categories[category_name] = []

        category_files = categories[category_name]

        # 检查是否已存在该文件
        for record in category_files:
            if record.get('path') == file_path:
                # 更新打开时间
                record['open_time'] = int(time.time())
                record['open_count'] = record.get('open_count', 0) + 1
                # 移动到列表开头
                category_files.remove(record)
                category_files.insert(0, record)
                history['categories'] = categories
                cls._save_file_history(history)
                return

        # 创建新记录
        new_record = {
            'path': file_path,
            'filename': filename,
            'open_time': int(time.time()),
            'open_count': 1,
            'last_page': 0,
            'page_count': page_count
        }

        # 添加到列表开头
        category_files.insert(0, new_record)

        # 检查数量限制
        max_per_category = history.get('max_per_category', 10)
        if len(category_files) > max_per_category:
            category_files = category_files[:max_per_category]

        categories[category_name] = category_files
        history['categories'] = categories
        cls._save_file_history(history)

    @classmethod
    def get_category_mapping(cls):
        """获取目录到分类的映射"""
        history = cls.get_file_history()
        return history.get('category_mapping', {})

    @classmethod
    def set_category_mapping(cls, category_mapping):
        """设置目录到分类的映射"""
        history = cls.get_file_history()
        history['category_mapping'] = category_mapping
        cls._save_file_history(history)

    @classmethod
    def get_custom_categories(cls):
        """获取自定义分类列表"""
        history = cls.get_file_history()
        return history.get('custom_categories', [])

    @classmethod
    def add_custom_category(cls, category_name):
        """添加自定义分类"""
        history = cls.get_file_history()
        custom_categories = history.get('custom_categories', [])
        if category_name not in custom_categories:
            custom_categories.append(category_name)
            history['custom_categories'] = custom_categories
            cls._save_file_history(history)

    @classmethod
    def remove_custom_category(cls, category_name):
        """移除自定义分类"""
        history = cls.get_file_history()
        custom_categories = history.get('custom_categories', [])
        if category_name in custom_categories:
            custom_categories.remove(category_name)
            history['custom_categories'] = custom_categories
            cls._save_file_history(history)

    @classmethod
    def clear_category(cls, category_name):
        """清空指定分类的文件记录"""
        history = cls.get_file_history()
        categories = history.get('categories', {})
        if category_name in categories:
            categories[category_name] = []
            history['categories'] = categories
            cls._save_file_history(history)

    @classmethod
    def remove_file_from_recent(cls, file_path):
        """从最近文件中移除指定文件"""
        history = cls.get_file_history()
        recent_files = history.get('recent_files', [])
        recent_files = [f for f in recent_files if f.get('path') != file_path]
        history['recent_files'] = recent_files
        cls._save_file_history(history)

    @classmethod
    def remove_file_from_category(cls, category_name, file_path):
        """从指定分类中移除文件"""
        history = cls.get_file_history()
        categories = history.get('categories', {})
        if category_name in categories:
            categories[category_name] = [f for f in categories[category_name] if f.get('path') != file_path]
            history['categories'] = categories
            cls._save_file_history(history)

    @classmethod
    def update_file_last_page(cls, file_path, page_num):
        """更新文件的最后阅读页码"""
        history = cls.get_file_history()
        recent_files = history.get('recent_files', [])
        for record in recent_files:
            if record.get('path') == file_path:
                record['last_page'] = page_num
                break
        history['recent_files'] = recent_files
        cls._save_file_history(history)

    @classmethod
    def get_history_panel_visible(cls):
        """获取历史记录面板是否默认显示"""
        settings = cls._load_settings()
        return settings.get('history_panel_visible', False)  # 默认不显示

    @classmethod
    def set_history_panel_visible(cls, visible):
        """设置历史记录面板是否默认显示"""
        settings = cls._load_settings()
        settings['history_panel_visible'] = bool(visible)
        cls._save_settings()

    @classmethod
    def update_recent_file_page_count(cls, file_path, page_count):
        """更新最近文件的页数"""
        history = cls.get_file_history()
        recent_files = history.get('recent_files', [])

        for record in recent_files:
            if record.get('path') == file_path:
                record['page_count'] = page_count
                history['recent_files'] = recent_files
                cls._save_file_history(history)
                return

    @classmethod
    def update_category_file_page_count(cls, category_name, file_path, page_count):
        """更新分类中文件的页数"""
        history = cls.get_file_history()
        categories = history.get('categories', {})

        if category_name in categories:
            category_files = categories[category_name]
            for record in category_files:
                if record.get('path') == file_path:
                    record['page_count'] = page_count
                    history['categories'] = categories
                    cls._save_file_history(history)
                    return