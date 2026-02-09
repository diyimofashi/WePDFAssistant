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
    def _migrate_to_sqlite_if_needed(cls, history):
        """如果需要，将JSON数据迁移到SQLite"""
        from app.managers.history_db import get_database

        # 检查迁移标记
        migration_key = '_sqlite_migrated'
        settings = cls._load_settings()

        if settings.get(migration_key):
            return

        # 检查是否有需要迁移的数据
        categories = history.get('categories', {})
        if not categories:
            # 没有旧数据，标记为已迁移
            settings[migration_key] = True
            cls._save_settings()
            return

        # 执行迁移
        try:
            db = get_database()
            success = db.migrate_from_json(history)

            if success:
                # 标记为已迁移
                settings[migration_key] = True
                cls._save_settings()
                logger.info("JSON数据已迁移到SQLite数据库")

                # 清空JSON中的categories数据以节省空间
                history['categories'] = {}
                cls._save_file_history(history)
            else:
                logger.warning("JSON数据迁移失败")
        except Exception as e:
            logger.error(f"数据迁移出错: {e}")

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

    @classmethod
    def get_use_tabbed_mode(cls):
        """获取是否使用多标签页模式"""
        settings = cls._load_settings()
        return settings.get('use_tabbed_mode', False)  # 默认使用单窗口模式

    @classmethod
    def set_use_tabbed_mode(cls, enabled):
        """设置是否使用多标签页模式"""
        settings = cls._load_settings()
        settings['use_tabbed_mode'] = bool(enabled)
        cls._save_settings()

    @classmethod
    def get_show_thumbnails_default(cls):
        """获取打开新文件时是否默认显示缩略图"""
        settings = cls._load_settings()
        return settings.get('show_thumbnails_default', True)  # 默认显示缩略图

    @classmethod
    def set_show_thumbnails_default(cls, enabled):
        """设置打开新文件时是否默认显示缩略图"""
        settings = cls._load_settings()
        settings['show_thumbnails_default'] = bool(enabled)
        cls._save_settings()

    # ==================== 文件历史记录相关设置 ====================


    @classmethod
    def get_file_history(cls):
        """获取文件历史记录"""
        settings = cls._load_settings()
        history = settings.get('file_history', {
            'max_recent': 20,
            'max_per_category': 10,
            'categories': {},
            'category_mapping': {},
            'custom_categories': []
        })

        # 检查是否需要迁移到SQLite
        cls._migrate_to_sqlite_if_needed(history)

        return history

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
        """获取分类记录（已废弃，保留用于兼容性）"""
        # 现在使用SQLite存储，此方法返回空字典
        return {}

    @classmethod
    def add_file_to_category_with_path(cls, file_path, filename, category_name, category_path, page_count=0):
        """添加文件到分类（带完整路径）"""
        import time
        history = cls.get_file_history()
        categories = history.get('categories', {})

        # 使用分类名称和路径的组合作为唯一键
        category_key = f"{category_name}|||{category_path}"

        if category_key not in categories:
            categories[category_key] = {
                'name': category_name,
                'path': category_path,
                'files': []
            }

        category_files = categories[category_key]['files']

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

        categories[category_key] = {
            'name': category_name,
            'path': category_path,
            'files': category_files
        }
        history['categories'] = categories
        cls._save_file_history(history)

    @classmethod
    def get_file_categories(cls):
        """获取分类记录（包含完整路径）"""
        history = cls.get_file_history()
        categories = history.get('categories', {})

        # 检查是否需要迁移旧数据
        needs_migration = False
        for key, value in categories.items():
            if not isinstance(value, dict) or 'files' not in value:
                needs_migration = True
                break

        # 如果需要迁移，进行数据迁移
        if needs_migration:
            logger.info("检测到旧格式分类数据，开始迁移...")
            migrated_categories = {}
            for old_key, files in categories.items():
                if isinstance(files, dict) and 'files' in files:
                    # 已经是新格式
                    migrated_categories[old_key] = files
                else:
                    # 旧格式，需要迁移
                    # 旧格式中，键是目录名（如 "1103"），文件列表中包含多个不同路径的文件
                    # 需要按完整路径重新分组
                    for file_record in files:
                        file_path = file_record.get('path', '')
                        if not file_path:
                            continue

                        # 获取文件的完整目录路径
                        file_dir = os.path.dirname(file_path)
                        dir_name = os.path.basename(file_dir)
                        parent_dir = os.path.basename(os.path.dirname(file_dir))

                        # 生成新格式的键和分类信息
                        if parent_dir:
                            new_key = f"{parent_dir}/{dir_name}|||{file_dir}"
                            category_name = f"{parent_dir}/{dir_name}"
                        else:
                            new_key = f"{dir_name}|||{file_dir}"
                            category_name = dir_name

                        if new_key not in migrated_categories:
                            migrated_categories[new_key] = {
                                'name': category_name,
                                'path': file_dir,
                                'files': []
                            }

                        # 添加文件到对应的分类
                        migrated_categories[new_key]['files'].append(file_record)

            # 保存迁移后的数据
            history['categories'] = migrated_categories
            cls._save_file_history(history)
            logger.info(f"数据迁移完成，共 {len(migrated_categories)} 个分类")

            return migrated_categories

        # 不需要迁移，直接返回新格式数据
        result = {}
        for key, value in categories.items():
            if isinstance(value, dict) and 'name' in value and 'path' in value:
                result[key] = value
            else:
                # 兼容旧格式（只有文件列表）
                result[key] = {
                    'name': key.split('|||')[0] if '|||' in key else key,
                    'path': key.split('|||')[1] if '|||' in key else '',
                    'files': value
                }
        return result

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
    def get_category_mapping(cls):
        """获取用户自定义的目录分类映射"""
        settings = cls._load_settings()
        return settings.get('category_mapping', {})

    @classmethod
    def set_category_mapping(cls, mapping):
        """设置用户自定义的目录分类映射"""
        settings = cls._load_settings()
        settings['category_mapping'] = mapping
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