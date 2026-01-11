"""快捷键配置管理器
管理所有功能的默认快捷键和用户自定义快捷键
"""

import os
import json
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.logger import get_logger

logger = get_logger('shortcut_config')


class ShortcutConfig:
    """快捷键配置管理器"""

    # 预定义的快捷键映射（动作ID -> 默认快捷键）
    DEFAULT_SHORTCUTS = {
        # 文件操作
        "file.open": ("打开文件", "Ctrl+O", "文件操作"),
        "file.save": ("保存文件", "Ctrl+S", "文件操作"),
        "file.save_as": ("另存为", "Ctrl+Shift+S", "文件操作"),
        "file.exit": ("退出", "Ctrl+Q", "文件操作"),

        # 编辑操作
        "edit.undo": ("撤销", "Ctrl+Z", "编辑操作"),
        "edit.redo": ("重做", "Ctrl+Y", "编辑操作"),
        "edit.copy": ("复制", "Ctrl+C", "编辑操作"),

        # 视图操作
        "view.zoom_in": ("放大", "Ctrl++", "视图操作"),
        "view.zoom_out": ("缩小", "Ctrl+-", "视图操作"),
        "view.fit_width": ("适合宽度", "Ctrl+W", "视图操作"),
        "view.fit_page": ("适合页面", "Ctrl+1", "视图操作"),
        "view.toggle_thumbnails": ("显示/隐藏缩略图", "Ctrl+T", "视图操作"),

        # 导航操作
        "nav.prev_page": ("上一页", "PgUp", "导航操作"),
        "nav.next_page": ("下一页", "PgDown", "导航操作"),
        "nav.first_page": ("第一页", "Ctrl+Home", "导航操作"),
        "nav.last_page": ("最后一页", "Ctrl+End", "导航操作"),
        "nav.jump_page": ("跳转到页面", "Ctrl+G", "导航操作"),

        # 工具操作
        "tools.search": ("搜索", "Ctrl+F", "工具"),
        "tools.screenshot_ocr": ("截图OCR", "Alt+S", "工具"),
        "tools.ocr_settings": ("OCR设置", "Ctrl+Shift+O", "工具"),
        "tools.barcode_split": ("条码拆分", "Ctrl+Shift+B", "工具"),
        "tools.upload": ("上传文档", "Ctrl+U", "工具"),
        "tools.download": ("下载文档", "Ctrl+Shift+D", "工具"),
        "tools.shortcuts": ("快捷键设置", "Ctrl+K", "工具"),

        # 转换操作
        "convert.export_image": ("导出为图片", "Ctrl+I", "转换"),
        "convert.import_images": ("导入图片", "Ctrl+Shift+I", "转换"),
    }

    # 设置文件路径
    SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".aurora_pdf_settings.json")
    SHORTCUTS_KEY = "shortcuts"

    # 运行时缓存
    _shortcuts_cache = None

    @classmethod
    def _load_shortcuts(cls):
        """从设置文件加载快捷键配置"""
        if cls._shortcuts_cache is None:
            cls._shortcuts_cache = {}

            # 尝试从配置文件加载
            if os.path.exists(cls.SETTINGS_FILE):
                try:
                    with open(cls.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        shortcuts = settings.get(cls.SHORTCUTS_KEY, {})

                        # 加载用户自定义的快捷键
                        for action_id, shortcut_info in shortcuts.items():
                            if action_id in cls.DEFAULT_SHORTCUTS:
                                current_shortcut = shortcut_info.get('current')
                                if current_shortcut:
                                    cls._shortcuts_cache[action_id] = current_shortcut

                    logger.debug(f"已加载 {len(cls._shortcuts_cache)} 个自定义快捷键")
                except Exception as e:
                    logger.error(f"加载快捷键配置失败: {e}")
                    cls._shortcuts_cache = {}

        return cls._shortcuts_cache

    @classmethod
    def _save_shortcuts(cls):
        """保存快捷键配置到文件"""
        try:
            # 读取现有设置
            existing_settings = {}
            if os.path.exists(cls.SETTINGS_FILE):
                with open(cls.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    existing_settings = json.load(f)

            # 更新快捷键配置
            shortcuts_config = {}
            for action_id in cls.DEFAULT_SHORTCUTS.keys():
                current_shortcut = cls.get_shortcut(action_id)
                name, default_shortcut, category = cls.DEFAULT_SHORTCUTS[action_id]
                shortcuts_config[action_id] = {
                    'name': name,
                    'default': default_shortcut,
                    'current': current_shortcut,
                    'category': category
                }

            existing_settings[cls.SHORTCUTS_KEY] = shortcuts_config

            # 保存到文件
            with open(cls.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing_settings, f, ensure_ascii=False, indent=2)

            logger.debug("快捷键配置已保存")
        except Exception as e:
            logger.error(f"保存快捷键配置失败: {e}")

    @classmethod
    def get_shortcut(cls, action_id):
        """
        获取指定功能的快捷键

        Args:
            action_id: 动作ID（如 "file.open"）

        Returns:
            str: 快捷键字符串（如 "Ctrl+O"），如果动作ID不存在则返回None
        """
        # 检查动作ID是否存在
        if action_id not in cls.DEFAULT_SHORTCUTS:
            logger.warning(f"未知的动作ID: {action_id}")
            return None

        # 优先使用用户自定义的快捷键
        shortcuts = cls._load_shortcuts()
        if action_id in shortcuts:
            return shortcuts[action_id]

        # 否则使用默认快捷键
        name, default_shortcut, category = cls.DEFAULT_SHORTCUTS[action_id]
        return default_shortcut

    @classmethod
    def set_shortcut(cls, action_id, shortcut):
        """
        设置指定功能的快捷键

        Args:
            action_id: 动作ID
            shortcut: 新的快捷键字符串

        Returns:
            bool: 设置是否成功
        """
        # 检查动作ID是否存在
        if action_id not in cls.DEFAULT_SHORTCUTS:
            logger.warning(f"未知的动作ID: {action_id}")
            return False

        # 检查快捷键是否与默认值相同
        name, default_shortcut, category = cls.DEFAULT_SHORTCUTS[action_id]
        if shortcut == default_shortcut:
            # 如果与默认值相同，从缓存中移除
            shortcuts = cls._load_shortcuts()
            if action_id in shortcuts:
                del shortcuts[action_id]
                cls._save_shortcuts()
            return True

        # 保存自定义快捷键
        shortcuts = cls._load_shortcuts()
        shortcuts[action_id] = shortcut
        cls._save_shortcuts()

        logger.debug(f"已设置快捷键: {action_id} -> {shortcut}")
        return True

    @classmethod
    def reset_shortcut(cls, action_id):
        """
        重置指定功能的快捷键为默认值

        Args:
            action_id: 动作ID

        Returns:
            bool: 重置是否成功
        """
        # 检查动作ID是否存在
        if action_id not in cls.DEFAULT_SHORTCUTS:
            logger.warning(f"未知的动作ID: {action_id}")
            return False

        # 从缓存中移除该快捷键
        shortcuts = cls._load_shortcuts()
        if action_id in shortcuts:
            del shortcuts[action_id]
            cls._save_shortcuts()

        logger.debug(f"已重置快捷键: {action_id}")
        return True

    @classmethod
    def reset_all_shortcuts(cls):
        """重置所有快捷键为默认值"""
        shortcuts = cls._load_shortcuts()
        shortcuts.clear()
        cls._save_shortcuts()

        logger.debug("已重置所有快捷键")

    @classmethod
    def get_all_shortcuts(cls):
        """
        获取所有快捷键配置

        Returns:
            dict: {action_id: {"name": str, "default": str, "current": str, "category": str}}
        """
        result = {}
        for action_id in cls.DEFAULT_SHORTCUTS.keys():
            name, default_shortcut, category = cls.DEFAULT_SHORTCUTS[action_id]
            current_shortcut = cls.get_shortcut(action_id)
            result[action_id] = {
                'name': name,
                'default': default_shortcut,
                'current': current_shortcut,
                'category': category
            }
        return result

    @classmethod
    def check_conflict(cls, shortcut, exclude_action_id=None):
        """
        检查快捷键是否冲突

        Args:
            shortcut: 要检查的快捷键
            exclude_action_id: 要排除的动作ID（检查时跳过该动作）

        Returns:
            dict or None: 如果冲突，返回 {"action_id": str, "name": str}；否则返回None
        """
        if not shortcut:
            return None

        for action_id in cls.DEFAULT_SHORTCUTS.keys():
            # 排除指定的动作ID
            if action_id == exclude_action_id:
                continue

            # 比较快捷键
            current_shortcut = cls.get_shortcut(action_id)
            if current_shortcut == shortcut:
                name, _, category = cls.DEFAULT_SHORTCUTS[action_id]
                return {
                    'action_id': action_id,
                    'name': name,
                    'category': category
                }

        return None

    @classmethod
    def get_shortcuts_by_category(cls, category=None):
        """
        按分类获取快捷键

        Args:
            category: 分类名称，如果为None则返回所有快捷键

        Returns:
            dict: {action_id: {"name": str, "default": str, "current": str, "category": str}}
        """
        all_shortcuts = cls.get_all_shortcuts()

        if category is None:
            return all_shortcuts

        result = {}
        for action_id, info in all_shortcuts.items():
            if info['category'] == category:
                result[action_id] = info

        return result

    @classmethod
    def get_categories(cls):
        """获取所有分类"""
        categories = set()
        for _, _, category in cls.DEFAULT_SHORTCUTS.values():
            categories.add(category)
        return sorted(list(categories))
