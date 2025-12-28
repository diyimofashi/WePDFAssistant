"""文件操作管理器模块"""

import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt
from app.utils.logger import get_logger
from app.config.settings import AppSettings

logger = get_logger('file_manager')


class FileManager:
    """文件操作管理器 - 负责文件的打开、保存、导入等操作"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        
    def open_file(self):
        """打开PDF文件或图片文件"""
        logger.info("开始打开文件...")
        last_dir = AppSettings.get_last_open_dir()

        # 添加图片文件格式支持
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent, "选择文件", last_dir, 
            "所有支持的文件 (*.pdf *.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp *.ico);;PDF文件 (*.pdf);;图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp *.ico);;所有文件 (*.*)")

        if file_path:
            logger.info(f"选择了文件: {file_path}")
            
            # 检查是否为图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.ico'}
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in image_extensions:
                # 直接打开图片文件
                self.parent.show_progress_dialog("正在加载图片文件...")
                success, message = self.parent.pdf_processor.open_pdf(file_path, async_mode=True)
                
                if success:
                    logger.info("异步加载启动成功")
                    AppSettings.set_last_open_dir(file_path)
                else:
                    logger.error(f"异步加载启动失败: {message}")
                    self.parent.hide_progress_dialog()
                    QMessageBox.critical(self.parent, "错误", message)
                return

            # 对于PDF文件，检查是否加密
            import PyPDF2
            is_encrypted = False
            try:
                reader = PyPDF2.PdfReader(file_path)
                is_encrypted = reader.is_encrypted
            except Exception as e:
                logger.warning(f"检查加密状态时出错: {e}")

            password = None
            if is_encrypted:
                # 弹出密码输入框，支持5次尝试
                from app.ui.password_dialog import PasswordDialog

                for attempt in range(5):
                    password = PasswordDialog.get_user_password(self.parent, "请输入密码")
                    if password is None:
                        logger.info("用户取消了密码输入")
                        return

                    # 验证密码是否正确
                    try:
                        test_reader = PyPDF2.PdfReader(file_path)
                        result = test_reader.decrypt(password)
                        if result > 0:
                            logger.info("密码验证成功")
                            break
                        else:
                            logger.warning(f"密码错误，第{attempt + 1}次尝试失败")
                            QMessageBox.warning(self.parent, "密码错误", f"密码错误，请重新输入（剩余{4 - attempt}次机会）")
                    except Exception as e:
                        logger.error(f"密码验证时出错: {e}")
                        QMessageBox.warning(self.parent, "密码错误", f"密码验证失败（剩余{4 - attempt}次机会）")
                else:
                    logger.error("密码尝试次数已达5次")
                    QMessageBox.critical(self.parent, "错误", "密码错误次数过多，无法打开文件")
                    return

            self.parent.show_progress_dialog("正在加载PDF文件...")
            success, message = self.parent.pdf_processor.open_pdf(file_path, async_mode=True, password=password)

            if success:
                logger.info("异步加载启动成功")
                AppSettings.set_last_open_dir(file_path)
            else:
                logger.error(f"异步加载启动失败: {message}")
                self.parent.hide_progress_dialog()
                QMessageBox.critical(self.parent, "错误", message)
        else:
            logger.info("未选择文件")
    
    def open_images_from_directory(self):
        """从目录打开所有图片并合并为PDF"""
        logger.info("开始从目录打开图片...")
        last_dir = AppSettings.get_last_open_dir()
        
        directory_path = QFileDialog.getExistingDirectory(
            self.parent, "选择包含图片的目录", last_dir)
        
        if directory_path:
            logger.info(f"选择了目录: {directory_path}")
            
            self.parent.show_progress_dialog("正在加载图片文件...")
            success, message = self.parent.pdf_processor.open_images_from_directory(directory_path, async_mode=True)
            
            if success:
                logger.info("异步加载启动成功")
                AppSettings.set_last_open_dir(directory_path)
            else:
                logger.error(f"异步加载启动失败: {message}")
                self.parent.hide_progress_dialog()
                QMessageBox.critical(self.parent, "错误", message)
        else:
            logger.info("未选择目录")
    
    def save_file(self):
        """保存PDF文件"""
        if not self.parent.pdf_processor.current_file:
            QMessageBox.information(self.parent, "提示", "📝 请先打开PDF文件")
            return

        # 检查是否有未保存的更改
        if (hasattr(self.parent.pdf_processor, 'page_editor') and
            self.parent.pdf_processor.page_editor and
            self.parent.pdf_processor.page_editor.has_unsaved_changes()):

            success, message = self.parent.pdf_processor.page_editor.save_changes()
            if success:
                self.parent.show_message("✅ 更改已保存到原文件")
                self.parent.update_save_actions_state()
                self.parent.load_thumbnails()
            else:
                QMessageBox.critical(self.parent, "保存失败", message)
        else:
            # 询问是否要加密保存
            reply = QMessageBox.question(
                self.parent,
                "保存方式",
                "是否要加密保存PDF文件？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.save_with_encryption(self.parent.pdf_processor.current_file)
            else:
                self._save_directly(self.parent.pdf_processor.current_file)

    def _save_directly(self, file_path):
        """直接保存PDF文件"""
        success, message = self.parent.pdf_processor.save_pdf(file_path)
        if success:
            self.parent.show_message("✅ 文件已保存")
        else:
            QMessageBox.critical(self.parent, "保存失败", message)

    def save_with_encryption(self, file_path):
        """加密保存PDF文件"""
        from app.ui.password_dialog import PasswordDialog

        password = PasswordDialog.get_user_password(self.parent, "请输入加密密码")
        if password is None:
            return

        if not password:
            QMessageBox.warning(self.parent, "提示", "密码不能为空")
            return

        success, message = self.parent.pdf_processor.encrypt_pdf(password, file_path)
        if success:
            self.parent.show_message("✅ 文件已加密保存")
            # 重新加载文件以更新加密状态
            self.parent.pdf_processor.open_pdf(file_path, async_mode=True, password=password)
        else:
            QMessageBox.critical(self.parent, "加密保存失败", message)
    
    def save_as_file(self):
        """另存为PDF文件"""
        if not self.parent.pdf_processor.current_file:
            QMessageBox.information(self.parent, "提示", "📝 请先打开PDF文件")
            return

        # 询问是否要加密保存
        reply = QMessageBox.question(
            self.parent,
            "另存为",
            "是否要加密保存PDF文件？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.save_as_with_encryption()
        else:
            self.save_as_without_encryption()

    def save_as_without_encryption(self):
        """另存为PDF文件（不加密）"""
        if not self.parent.pdf_processor.current_file:
            return

        # 获取当前文件的目录和文件名
        if self.parent.pdf_processor.current_file:
            current_dir = os.path.dirname(self.parent.pdf_processor.current_file)
            current_filename = os.path.basename(self.parent.pdf_processor.current_file)
            default_path = os.path.join(current_dir, current_filename)
        else:
            current_dir = AppSettings.get_last_save_dir()
            current_filename = "document.pdf"
            default_path = os.path.join(current_dir, current_filename)

        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "另存为PDF文件", default_path, "PDF文件 (*.pdf)")

        if file_path:
            success, message = self.parent.pdf_processor.save_pdf(file_path)
            if success:
                AppSettings.set_last_save_dir(file_path)
                QMessageBox.information(self.parent, "保存成功", message)
            else:
                QMessageBox.critical(self.parent, "保存失败", message)

    def save_as_with_encryption(self):
        """加密另存为PDF文件"""
        if not self.parent.pdf_processor.current_file:
            return

        # 获取当前文件的目录和文件名
        if self.parent.pdf_processor.current_file:
            current_dir = os.path.dirname(self.parent.pdf_processor.current_file)
            current_filename = os.path.basename(self.parent.pdf_processor.current_file)
            default_path = os.path.join(current_dir, current_filename)
        else:
            current_dir = AppSettings.get_last_save_dir()
            current_filename = "document.pdf"
            default_path = os.path.join(current_dir, current_filename)

        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "加密另存为PDF文件", default_path, "PDF文件 (*.pdf)")

        if not file_path:
            return

        # 输入密码
        from app.ui.password_dialog import PasswordDialog

        password = PasswordDialog.get_user_password(self.parent, "请输入加密密码")
        if password is None:
            return

        if not password:
            QMessageBox.warning(self.parent, "提示", "密码不能为空")
            return

        success, message = self.parent.pdf_processor.encrypt_pdf(password, file_path)
        if success:
            AppSettings.set_last_save_dir(file_path)
            QMessageBox.information(self.parent, "保存成功", message)
        else:
            QMessageBox.critical(self.parent, "加密保存失败", message)

    def encrypt_save_file(self):
        """加密保存PDF文件（直接覆盖源文档）"""
        if not self.parent.pdf_processor.current_file:
            QMessageBox.information(self.parent, "提示", "📝 请先打开PDF文件")
            return

        self.save_with_encryption(self.parent.pdf_processor.current_file)

    def encrypt_save_as_file(self):
        """加密另存为PDF文件（选择新目录存储成新文档）"""
        if not self.parent.pdf_processor.current_file:
            QMessageBox.information(self.parent, "提示", "📝 请先打开PDF文件")
            return

        self.save_as_with_encryption()
    
    def save_changes(self):
        """保存更改"""
        if (hasattr(self.parent.pdf_processor, 'page_editor') and 
            self.parent.pdf_processor.page_editor and 
            self.parent.pdf_processor.page_editor.has_unsaved_changes()):
            
            success, message = self.parent.pdf_processor.page_editor.save_changes()
            if success:
                self.parent.show_message("✅ 更改已保存")
                self.parent.save_changes_action.setEnabled(False)
                self.parent.discard_changes_action.setEnabled(False)
                self.parent.undo_action.setEnabled(False)
                self.parent.redo_action.setEnabled(False)
                self.parent.load_thumbnails()
            else:
                QMessageBox.critical(self.parent, "保存失败", message)
        else:
            self.parent.show_message("ℹ️ 没有需要保存的更改")
    
    def discard_changes(self):
        """放弃更改"""
        if (hasattr(self.parent.pdf_processor, 'page_editor') and 
            self.parent.pdf_processor.page_editor and 
            self.parent.pdf_processor.page_editor.has_unsaved_changes()):
            
            reply = QMessageBox.question(
                self.parent, 
                "确认放弃更改", 
                "确定要放弃所有未保存的更改吗？", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success, message = self.parent.pdf_processor.page_editor.discard_changes()
                if success:
                    self.parent.show_message("❌ 更改已放弃")
                    self.parent.save_changes_action.setEnabled(False)
                    self.parent.discard_changes_action.setEnabled(False)
                    self.parent.undo_action.setEnabled(False)
                    self.parent.redo_action.setEnabled(False)
                    self.parent.load_thumbnails()
                else:
                    QMessageBox.critical(self.parent, "操作失败", message)
        else:
            self.parent.show_message("ℹ️ 没有需要放弃的更改")
    
    def import_images(self):
        """导入图片到PDF"""
        formats_filter = self.parent.pdf_processor.get_supported_image_formats_filter()
        
        image_paths, _ = QFileDialog.getOpenFileNames(
            self.parent, 
            "选择要导入的图片文件", 
            "", 
            formats_filter
        )
        
        if not image_paths:
            logger.info("未选择图片文件")
            return
        
        logger.info(f"选择了{len(image_paths)}张图片文件")
        
        progress_dialog = QProgressDialog("正在导入图片...", "取消", 0, len(image_paths), self.parent)
        progress_dialog.setWindowTitle("导入图片")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        try:
            insert_after_page = -1
            if self.parent.pdf_processor.fitz_document:
                insert_after_page = self.parent.pdf_processor.current_page
            
            success, message = self.parent.pdf_processor.import_images(image_paths, insert_after_page)
            
            progress_dialog.close()
            
            if success:
                QMessageBox.information(self.parent, "导入成功", message)
                self._update_ui_after_import()
            else:
                QMessageBox.critical(self.parent, "导入失败", message)
                
        except Exception as e:
            progress_dialog.close()
            logger.error(f"导入图片过程中发生错误: {e}")
            QMessageBox.critical(self.parent, "错误", f"导入图片过程中发生错误: {str(e)}")
    
    def _update_ui_after_import(self):
        """导入图片后更新界面状态"""
        total_pages = self.parent.pdf_processor.get_total_pages()
        self.parent.page_spinbox.setMaximum(total_pages)
        self.parent.total_pages_label.setText(f" / {total_pages}")
        self.parent._force_refresh_preview()
        
        if self.parent.show_thumbnails:
            self.parent._force_reload_thumbnails()
        
        logger.info("界面状态已更新")