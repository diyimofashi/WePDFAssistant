"""快捷键管理器
管理所有动作的快捷键注册、应用和更新
"""

from PyQt5.QtCore import QObject, pyqtSignal
from app.utils.logger import get_logger
from app.config.shortcut_config import ShortcutConfig

logger = get_logger('shortcut_manager')


class ShortcutManager(QObject):
    """快捷键管理器"""

    # 信号定义
    shortcut_changed = pyqtSignal(str, str)  # action_id, new_shortcut

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.action_registry = {}  # {action_id: action}
        logger.debug("快捷键管理器初始化完成")

    def register_action(self, action_id, action):
        """
        注册动作

        Args:
            action_id: 动作ID（如 "file.open"）
            action: QAction对象
        """
        if action_id in self.action_registry:
            logger.warning(f"动作 {action_id} 已注册，将被覆盖")

        self.action_registry[action_id] = action
        logger.debug(f"已注册动作: {action_id}")

        # 应用快捷键
        self._apply_shortcut_to_action(action_id, action)

    def unregister_action(self, action_id):
        """
        注销动作

        Args:
            action_id: 动作ID
        """
        if action_id in self.action_registry:
            del self.action_registry[action_id]
            logger.debug(f"已注销动作: {action_id}")

    def apply_shortcuts(self):
        """应用快捷键到所有已注册的动作"""
        for action_id, action in self.action_registry.items():
            self._apply_shortcut_to_action(action_id, action)

        logger.debug("已应用所有快捷键")

    def _apply_shortcut_to_action(self, action_id, action):
        """
        应用快捷键到指定动作

        Args:
            action_id: 动作ID
            action: QAction对象
        """
        shortcut = ShortcutConfig.get_shortcut(action_id)
        if shortcut:
            action.setShortcut(shortcut)
            logger.debug(f"应用快捷键: {action_id} -> {shortcut}")

    def update_shortcut(self, action_id, new_shortcut):
        """
        更新快捷键

        Args:
            action_id: 动作ID
            new_shortcut: 新的快捷键

        Returns:
            tuple: (success: bool, message: str)
        """
        # 检查快捷键冲突
        conflict = ShortcutConfig.check_conflict(new_shortcut, exclude_action_id=action_id)
        if conflict:
            action_name = conflict['name']
            category = conflict['category']
            message = f"快捷键 {new_shortcut} 已被 {category}/{action_name} 使用"
            logger.warning(message)
            return False, message

        # 检查动作是否已注册
        if action_id not in self.action_registry:
            logger.warning(f"动作 {action_id} 未注册")
            return False, f"动作 {action_id} 未注册"

        # 更新配置
        success = ShortcutConfig.set_shortcut(action_id, new_shortcut)
        if not success:
            return False, "更新快捷键配置失败"

        # 应用到动作
        action = self.action_registry[action_id]
        action.setShortcut(new_shortcut)

        # 发送信号
        self.shortcut_changed.emit(action_id, new_shortcut)

        logger.info(f"快捷键已更新: {action_id} -> {new_shortcut}")
        return True, "快捷键已更新"

    def get_action_shortcut(self, action_id):
        """
        获取动作的快捷键

        Args:
            action_id: 动作ID

        Returns:
            str: 快捷键字符串，如果动作不存在则返回None
        """
        return ShortcutConfig.get_shortcut(action_id)

    def check_conflict(self, shortcut, exclude_action_id=None):
        """
        检查快捷键是否冲突

        Args:
            shortcut: 要检查的快捷键
            exclude_action_id: 要排除的动作ID

        Returns:
            dict or None: 如果冲突，返回冲突信息；否则返回None
        """
        return ShortcutConfig.check_conflict(shortcut, exclude_action_id)

    def reset_to_default(self, action_id=None):
        """
        重置快捷键为默认值

        Args:
            action_id: 动作ID，如果为None则重置所有快捷键

        Returns:
            bool: 重置是否成功
        """
        if action_id is None:
            # 重置所有快捷键
            ShortcutConfig.reset_all_shortcuts()
            self.apply_shortcuts()
            logger.info("已重置所有快捷键为默认值")
            return True
        else:
            # 重置指定快捷键
            success = ShortcutConfig.reset_shortcut(action_id)
            if success:
                # 应用到动作
                if action_id in self.action_registry:
                    action = self.action_registry[action_id]
                    self._apply_shortcut_to_action(action_id, action)

                logger.info(f"已重置快捷键 {action_id} 为默认值")
            return success

    def get_registered_actions(self):
        """
        获取所有已注册的动作

        Returns:
            dict: {action_id: QAction}
        """
        return self.action_registry.copy()

    def get_action_info(self, action_id):
        """
        获取动作信息

        Args:
            action_id: 动作ID

        Returns:
            dict or None: {"action_id": str, "name": str, "shortcut": str, "action": QAction}
        """
        if action_id not in self.action_registry:
            return None

        action = self.action_registry[action_id]
        all_shortcuts = ShortcutConfig.get_all_shortcuts()

        if action_id in all_shortcuts:
            info = all_shortcuts[action_id].copy()
            info['action'] = action
            return info

        return None

    def search_actions(self, keyword):
        """
        搜索动作

        Args:
            keyword: 搜索关键词

        Returns:
            list: 匹配的动作ID列表
        """
        if not keyword:
            return list(self.action_registry.keys())

        keyword = keyword.lower()
        result = []

        all_shortcuts = ShortcutConfig.get_all_shortcuts()
        for action_id, info in all_shortcuts.items():
            # 搜索名称和快捷键
            if keyword in info['name'].lower() or keyword in info['current'].lower():
                result.append(action_id)

        return result
