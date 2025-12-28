"""上传管理混入类 - 重构版"""

import os
from app.utils.logger import get_logger

logger = get_logger('main')

class UploadManagerMixin:
    """上传管理混入类 - 处理上传功能"""
    
    def upload_current_document(self):
        """上传当前打开的文档"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            from PyQt5.QtWidgets import QApplication
            
            # 检查是否有打开的PDF文档
            if not self.pdf_processor.current_file:
                QMessageBox.warning(self, "警告", "请先打开PDF文件")
                return
            
            # 获取当前配置的上传插件
            current_plugin_name = self.upload_config_manager.get_current_plugin()
            if not current_plugin_name:
                QMessageBox.warning(self, "警告", "请先在上传设置中选择一个上传插件")
                return
            
            # 检查插件是否已加载
            if current_plugin_name not in self.upload_plugin_manager.plugins:
                QMessageBox.critical(self, "错误", f"上传插件 '{current_plugin_name}' 未加载")
                return
            
            # 检查插件是否已初始化，如果没有则初始化
            plugin = self.upload_plugin_manager.plugins[current_plugin_name]
            if not plugin.is_initialized:
                plugin_config = self.upload_config_manager.get_plugin_config(current_plugin_name)
                init_result = self.upload_plugin_manager.initialize_plugin(current_plugin_name, plugin_config)
                if not init_result.is_success():
                    QMessageBox.critical(self, "上传初始化失败", f"插件初始化失败: {init_result.message}")
                    return
            
            # 显示上传进度
            self.show_message("正在上传文档...")
            QApplication.processEvents()  # 确保状态栏更新立即显示
            
            try:
                # 使用插件上传当前文件
                current_file_path = self.pdf_processor.current_file
                file_name = os.path.basename(current_file_path)
                
                # 执行上传操作
                result = self.upload_plugin_manager.upload_with_plugin(
                    current_plugin_name,
                    file_path=current_file_path,
                    remote_path=file_name  # 使用原始文件名作为远程路径
                )
                
                if result.is_success():
                    message = f"✅ 文档上传成功!\n插件: {current_plugin_name}\n文件: {file_name}"
                    if result.data:
                        # 如果有返回的上传信息，也显示出来
                        if 'url' in result.data:
                            message += f"\n访问地址: {result.data['url']}"
                        elif 'remote_path' in result.data:
                            message += f"\n远程路径: {result.data['remote_path']}"
                    
                    QMessageBox.information(self, "上传成功", message)
                    self.show_message("文档上传成功")
                else:
                    QMessageBox.critical(self, "上传失败", f"❌ 上传失败:\n{result.message}")
                    self.show_message(f"上传失败: {result.message}")
            
            finally:
                # 清除状态栏上传信息
                self.show_message("")
                
        except Exception as e:
            logger.error(f"上传文档时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"上传文档时发生异常: {str(e)}")
    
    def show_upload_settings(self):
        """显示上传设置对话框"""
        try:
            from app.ui.upload_settings_dialog import UploadSettingsDialog
            dialog = UploadSettingsDialog(self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"显示上传设置对话框时出错: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"无法打开上传设置: {str(e)}")