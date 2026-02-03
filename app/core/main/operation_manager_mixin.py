"""操作管理混入类"""
import os
import markdown2
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox, QTextBrowser
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
        from app.utils.app_path import get_app_root
        
        # 使用 app_path 模块获取应用根目录,支持编译后环境
        app_root = get_app_root()
        about_file_path = os.path.join(app_root, "about.md")
        
        # 如果不存在,尝试 app 目录(开发环境)
        if not os.path.exists(about_file_path):
            about_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "about.md")

        if not os.path.exists(about_file_path):
            logger.warning(f"关于文件不存在: {about_file_path}")
            QMessageBox.about(self, "关于", "PDFAssistant v1.0\n一个功能强大的PDF文档处理工具")
            return

        try:
            with open(about_file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()

            # 转换Markdown为HTML
            html_content = markdown2.markdown(markdown_text, extras=['tables', 'fenced-code-blocks'])
            
            # 处理图片路径:将相对路径转换为绝对路径
            from app.utils.app_path import get_assets_dir
            import re
            import platform

            assets_dir = get_assets_dir()

            # 在 Windows 上使用绝对路径,在 Linux/macOS 上使用 file:// URL
            if platform.system() == 'Windows':
                # Windows: 直接使用绝对路径,QTextBrowser 支持
                assets_path = assets_dir.replace('\\', '/')
                html_content = html_content.replace('./assets/', assets_path + '/')
            else:
                # Linux/macOS: 使用 file:// URL
                assets_url = assets_dir.replace('\\', '/')
                if not assets_url.startswith('/'):
                    assets_url = '/' + assets_url
                html_content = html_content.replace('./assets/', f'file://{assets_url}/')

            # 添加固定尺寸的 img 标签
            html_content = re.sub(
                r'<img([^>]+)>',
                r'<img width="200" height="200"\1>',
                html_content
            )

            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("关于")
            dialog.resize(600, 550)

            layout = QVBoxLayout()

            # 使用QTextBrowser显示富文本内容
            text_browser = QTextBrowser()
            text_browser.setHtml(html_content)
            text_browser.setOpenExternalLinks(True)  # 允许打开外部链接

            # 设置样式
            text_browser.setStyleSheet("""
                QTextBrowser {
                    font-size: 12px;
                    padding: 10px;
                }
                QTextBrowser img {
                    max-width: 200px;
                    max-height: 200px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 4px;
                    margin: 10px 0;
                }
                h1 {
                    color: #2c3e50;
                    font-size: 24px;
                    margin-bottom: 15px;
                }
                h2 {
                    color: #34495e;
                    font-size: 18px;
                    margin-bottom: 10px;
                }
                p {
                    color: #34495e;
                    margin: 5px 0;
                }
                code {
                    background-color: #f5f5f5;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: monospace;
                }
                blockquote {
                    border-left: 4px solid #3498db;
                    padding-left: 15px;
                    color: #555;
                    margin: 10px 0;
                }
            """)

            layout.addWidget(text_browser)

            # 添加确定按钮
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            logger.error(f"读取关于文件时出错: {e}")
            QMessageBox.about(self, "关于", "PDFAssistant v1.0\n一个功能强大的PDF文档处理工具")
    
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