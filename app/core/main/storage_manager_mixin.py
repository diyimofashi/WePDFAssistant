"""云存储插件管理混入类"""

from PyQt5.QtWidgets import QMessageBox
from app.utils.logger import get_logger

logger = get_logger('storage_manager_mixin')


class StorageManagerMixin:
    """云存储插件管理混入类 - 处理云存储插件相关功能"""

    def show_storage_settings(self):
        """显示云存储插件设置对话框"""
        try:
            if not hasattr(self, 'storage_plugin_manager') or not self.storage_plugin_manager:
                logger.warning("云存储插件管理器未初始化")
                QMessageBox.warning(self, "错误", "云存储插件管理器未初始化")
                return

            # 动态导入存储设置对话框
            from app.ui.storage_settings_dialog import StorageSettingsDialog
            
            # 显示云存储插件设置对话框
            dialog = StorageSettingsDialog(self)
            if dialog.exec_() == StorageSettingsDialog.Accepted:
                logger.info("云存储插件设置已关闭")
                # 重新加载文件列表面板
                if hasattr(self, 'file_list_panel'):
                    self.file_list_panel.load_current_plugin_info()
            else:
                logger.info("云存储插件设置已取消")

        except Exception as e:
            logger.error(f"显示云存储插件设置对话框时出错: {e}")
            QMessageBox.critical(self, "错误", f"打开云存储插件设置失败: {str(e)}")

    def upload_current_document_via_storage_plugin(self):
        """通过云存储插件上传当前文档"""
        try:
            if not hasattr(self, 'file_list_panel'):
                QMessageBox.warning(self, "错误", "文件列表面板未初始化")
                return

            # 调用文件列表面板的上传方法
            self.file_list_panel.upload_current_document()

        except Exception as e:
            logger.error(f"上传当前文档时出错: {e}")
            QMessageBox.critical(self, "错误", f"上传文档失败: {str(e)}")
