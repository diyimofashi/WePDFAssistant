"""快捷键管理混入类"""

from PyQt5.QtWidgets import QMessageBox
from app.utils.logger import get_logger
from app.ui.shortcut_settings_dialog import ShortcutSettingsDialog

logger = get_logger('shortcut_manager_mixin')


class ShortcutManagerMixin:
    """快捷键管理混入类 - 处理快捷键相关功能"""

    def show_shortcut_settings(self):
        """显示快捷键设置对话框"""
        try:
            if not hasattr(self, 'shortcut_manager') or not self.shortcut_manager:
                logger.warning("快捷键管理器未初始化")
                QMessageBox.warning(self, "错误", "快捷键管理器未初始化")
                return

            # 显示快捷键设置对话框
            dialog = ShortcutSettingsDialog(self.shortcut_manager, self)
            if dialog.exec_() == ShortcutSettingsDialog.Accepted:
                logger.info("快捷键设置已关闭")
            else:
                logger.info("快捷键设置已取消")

        except Exception as e:
            logger.error(f"显示快捷键设置对话框时出错: {e}")
            QMessageBox.critical(self, "错误", f"打开快捷键设置失败: {str(e)}")
