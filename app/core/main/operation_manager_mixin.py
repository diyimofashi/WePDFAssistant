"""操作管理混入类 - 重构版"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox
from app.utils.logger import get_logger
from app.ui.batch_crypto_dialog import BatchCryptoDialog

logger = get_logger('main')

class OperationManagerMixin:
    """操作管理混入类 - 处理编辑和操作功能"""
    
    def undo_operation(self):
        """撤销操作"""
        try:
            success, message = self.pdf_processor.undo_operation()
            if success:
                self.show_message(f"✅ {message}")
                self.update_save_actions_state()
                self.view_controller.load_thumbnails()
                self.update_preview()
                if hasattr(self, 'repaint'):
                    self.repaint()
            else:
                if "没有可撤销的操作" in message:
                    self.show_message(f"ℹ️ {message}")
                else:
                    QMessageBox.warning(self, "撤销失败", message)
        except Exception as e:
            logger.error(f"撤销操作异常: {e}")
            QMessageBox.critical(self, "撤销失败", f"撤销操作发生异常: {str(e)}")

    def redo_operation(self):
        """重做操作"""
        try:
            success, message = self.pdf_processor.redo_operation()
            if success:
                self.show_message(f"✅ {message}")
                self.update_save_actions_state()
                self.view_controller.load_thumbnails()
                self.update_preview()
                if hasattr(self, 'repaint'):
                    self.repaint()
            else:
                if "没有可重做的操作" in message:
                    self.show_message(f"ℹ️ {message}")
                else:
                    QMessageBox.warning(self, "重做失败", message)
        except Exception as e:
            logger.error(f"重做操作异常: {e}")
            QMessageBox.critical(self, "重做失败", f"重做操作发生异常: {str(e)}")
    
    def clear_cache(self):
        """清理缓存"""
        self.pdf_processor.clear_render_cache()
        
        if hasattr(self.thumbnail_list, 'clear_cache'):
            self.thumbnail_list.clear_cache()
            
        if self.use_virtual_scroll and hasattr(self.virtual_scroll, 'clear_cache'):
            self.virtual_scroll.clear_cache()
            
        self.pdf_processor.optimize_memory_usage()
        
        self.show_message("🗑️ 所有缓存已清理")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>极灵PDF v1.0</h2>
        <p>一个功能强大的PDF文档处理工具</p>
        <p>支持PDF查看、编辑、转换、合并、分割等功能</p>
        <p>🎯 设计理念: 简单易用，功能强大</p>
        <p>新增功能: PDF转图片转换器</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def show_shortcuts(self):
        """显示快捷键说明"""
        dialog = QDialog(self)
        dialog.setWindowTitle("快捷键说明")
        dialog.resize(500, 600)
        
        layout = QVBoxLayout()
        
        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        shortcuts_content = """
快捷键说明：

文件操作：
- Ctrl+O: 打开文件
- Ctrl+S: 保存文件
- Ctrl+Shift+S: 另存为/保存更改
- Ctrl+D: 放弃更改
- Ctrl+Q: 退出程序

编辑操作：
- Ctrl+Z: 撤销
- Ctrl+Y: 重做

视图操作：
- Ctrl++: 放大
- Ctrl+-: 缩小
- Ctrl+F: 搜索

页面导航：
- PgUp: 上一页
- PgDown: 下一页
"""
        shortcuts_text.setPlainText(shortcuts_content.strip())
        layout.addWidget(shortcuts_text)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def check_for_updates(self):
        """检查更新"""
        # 这里可以实现检查更新的逻辑
        QMessageBox.information(self, "检查更新", "当前已是最新版本 v1.0.0")
    
    def show_batch_crypto_dialog(self):
        """显示批量加解密对话框"""
        try:
            # 检查是否已存在对话框实例，避免重复创建
            if not hasattr(self, 'batch_crypto_dialog') or self.batch_crypto_dialog is None:
                self.batch_crypto_dialog = BatchCryptoDialog(self)
            self.batch_crypto_dialog.show()
            self.batch_crypto_dialog.raise_()  # 将对话框置于前台
            self.batch_crypto_dialog.activateWindow()  # 激活对话框窗口
        except Exception as e:
            logger.error(f"显示批量加解密对话框时出错: {e}")
            QMessageBox.critical(self, "错误", f"无法打开批量加解密功能: {str(e)}")