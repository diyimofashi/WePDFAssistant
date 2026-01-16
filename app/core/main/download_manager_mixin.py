"""下载管理混入类 - 重构版"""

from app.ui.download_file_dialog import show_download_file_dialog
from app.config.download_plugin_config import download_config_manager
from PyQt5.QtWidgets import QMessageBox
from app.ui.download_settings_dialog import DownloadSettingsDialog

from app.utils.logger import get_logger

logger = get_logger('main')

class DownloadManagerMixin:
    """下载管理混入类 - 处理下载功能"""
    
    def open_remote_file(self):
        """打开远程文件 - 使用下载插件下载并打开远程文件"""
        try:
            
            # 检查是否有配置的下载插件
            current_plugin = download_config_manager.get_current_plugin()
            if not current_plugin:
                reply = QMessageBox.question(
                    self,
                    "提示",
                    "当前未配置下载插件，是否前往设置？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.show_download_settings()
                return
            
            # 显示下载对话框
            downloaded_file_path = show_download_file_dialog(self)
            
            if downloaded_file_path:
                # 直接使用PDF处理器打开下载的文件
                self.current_file_path = downloaded_file_path
                success, message = self.pdf_processor.open_pdf(downloaded_file_path, async_mode=True)
                
                if success:
                    # 记住这是临时下载的文件，可能需要特殊处理
                    self.current_is_temp_file = True
                    QMessageBox.information(self, "成功", "远程文件已下载并打开")
                else:
                    # 检查是否是EOF marker错误
                    if "EOF" in message or "marker" in message or "不完整" in message or "已损坏" in message:
                        QMessageBox.critical(self, "错误", f"下载的PDF文件不完整或已损坏，无法打开\n错误信息: {message}")
                    else:
                        QMessageBox.critical(self, "错误", f"无法打开下载的文件: {message}")
            
        except Exception as e:
            logger.error(f"打开远程文件时出错: {e}")
            QMessageBox.critical(self, "错误", f"打开远程文件时发生错误: {str(e)}")
    
    def show_download_settings(self):
        """显示下载设置对话框"""
        try:
            
            dialog = DownloadSettingsDialog(self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"显示下载设置对话框时出错: {e}")
            QMessageBox.critical(self, "错误", f"无法打开下载设置: {str(e)}")