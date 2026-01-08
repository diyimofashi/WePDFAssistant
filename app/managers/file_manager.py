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
        last_dir = AppSettings.get_last_open_dir()

        # 添加图片文件格式支持，支持多选
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.parent, "选择文件", last_dir, 
            "所有支持的文件 (*.pdf *.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp *.ico);;PDF文件 (*.pdf);;图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp *.ico);;所有文件 (*.*)")

        if file_paths:
            # 如果选择了多个文件，优先处理图片
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.ico'}
            image_files = []
            pdf_files = []
            
            for file_path in file_paths:
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in image_extensions:
                    image_files.append(file_path)
                else:
                    pdf_files.append(file_path)
            
            # 如果有图片文件，优先加载图片
            if image_files:
                self._load_multiple_images(image_files)
            # 如果没有图片但有PDF文件，加载第一个PDF
            elif pdf_files:
                self._open_pdf_file(pdf_files[0])
                # 只在这里保存目录,避免重复保存
                AppSettings.set_last_open_dir(pdf_files[0])
            else:
                # 如果选择了其他类型的文件,保存第一个文件的目录
                AppSettings.set_last_open_dir(file_paths[0])
        else:
            logger.info("未选择文件")
    
    def open_multiple_images(self):
        """打开多张图片文件"""
        last_dir = AppSettings.get_last_open_dir()

        # 支持多选图片文件
        image_paths, _ = QFileDialog.getOpenFileNames(
            self.parent, "选择多张图片文件", last_dir, 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp *.ico);;JPEG图片 (*.jpg *.jpeg);;PNG图片 (*.png);;BMP图片 (*.bmp);;所有文件 (*.*)")

        if image_paths:
            # 按文件名排序，确保按选择顺序显示
            self.parent.show_progress_dialog(f"正在加载{len(image_paths)}张图片...")
            success, message = self.parent.pdf_processor.open_multiple_images(image_paths, async_mode=True)

            if success:
                AppSettings.set_last_open_dir(image_paths[0])
            else:
                logger.error(f"多图片异步加载启动失败: {message}")
                self.parent.hide_progress_dialog()
                QMessageBox.critical(self.parent, "错误", message)
        else:
            logger.info("未选择图片文件")
    
    def _load_multiple_images(self, image_paths):
        """加载指定的多张图片文件"""
        if len(image_paths) == 1:
            # 单张图片直接加载
            self.parent.show_progress_dialog("正在加载图片文件...")
            success, message = self.parent.pdf_processor.open_pdf(image_paths[0], async_mode=True)
            
            if success:
                logger.info("异步加载启动成功")
            else:
                logger.error(f"异步加载启动失败: {message}")
                self.parent.hide_progress_dialog()
                QMessageBox.critical(self.parent, "错误", message)
        else:
            # 多张图片加载为多页文档
            self.parent.show_progress_dialog(f"正在加载{len(image_paths)}张图片...")
            success, message = self.parent.pdf_processor.open_multiple_images(image_paths, async_mode=True)
            
            if success:
                logger.info("多图片异步加载启动成功")
            else:
                logger.error(f"多图片异步加载启动失败: {message}")
                self.parent.hide_progress_dialog()
                QMessageBox.critical(self.parent, "错误", message)
    
    def open_image_directory(self):
        """打开目录，加载该目录下的所有图片"""
        last_dir = AppSettings.get_last_open_dir()
        
        directory_path = QFileDialog.getExistingDirectory(
            self.parent, "选择包含图片的目录", last_dir)
        
        if directory_path:
            # 获取目录下所有图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.ico'}
            image_files = []
            
            try:
                # 遍历目录获取所有图片文件
                for filename in os.listdir(directory_path):
                    file_path = os.path.join(directory_path, filename)
                    if os.path.isfile(file_path):
                        file_ext = os.path.splitext(filename)[1].lower()
                        if file_ext in image_extensions:
                            image_files.append(file_path)
                
                # 按文件名排序
                image_files.sort()
                
                if not image_files:
                    QMessageBox.information(self.parent, "提示", "所选目录中没有找到图片文件")
                    return

                # 加载所有图片
                self.parent.show_progress_dialog(f"正在加载目录中的{len(image_files)}张图片...")
                success, message = self.parent.pdf_processor.open_multiple_images(image_files, async_mode=True, source_directory=directory_path)

                if success:
                    # directory_path本身就是目录,不需要再调用dirname
                    # 设置为空字符串,让set_last_open_dir直接使用directory_path
                    # 这里用一个特殊处理:手动更新settings
                    settings = AppSettings._load_settings()
                    settings['last_open_dir'] = directory_path
                    AppSettings._save_settings()
                else:
                    logger.error(f"目录图片异步加载启动失败: {message}")
                    self.parent.hide_progress_dialog()
                    QMessageBox.critical(self.parent, "错误", message)
                    
            except Exception as e:
                logger.error(f"读取目录时发生错误: {e}")
                QMessageBox.critical(self.parent, "错误", f"读取目录时发生错误: {str(e)}")
        else:
            logger.info("未选择目录")
    
    def _open_pdf_file(self, file_path):
        """打开单个PDF文件"""
        # 检查是否加密
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
        else:
            logger.error(f"异步加载启动失败: {message}")
            self.parent.hide_progress_dialog()
            QMessageBox.critical(self.parent, "错误", message)
    
    def open_images_from_directory(self):
        """从目录打开所有图片并合并为PDF"""
        last_dir = AppSettings.get_last_open_dir()
        
        directory_path = QFileDialog.getExistingDirectory(
            self.parent, "选择包含图片的目录", last_dir)
        
        if directory_path:
            self.parent.show_progress_dialog("正在加载图片文件...")
            success, message = self.parent.pdf_processor.open_images_from_directory(directory_path, async_mode=True)

            if success:
                # directory_path本身就是目录,不需要再调用dirname
                settings = AppSettings._load_settings()
                settings['last_open_dir'] = directory_path
                AppSettings._save_settings()
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

        # 检查当前文件是否不是PDF扩展名（如实际是PDF但后缀是.jpg）
        is_non_pdf_extension = False
        if self.parent.pdf_processor.current_file:
            file_ext = os.path.splitext(self.parent.pdf_processor.current_file)[1].lower()
            if file_ext and file_ext != '.pdf':
                is_non_pdf_extension = True
                logger.debug(f"检测到非PDF扩展名文件: {file_ext}")

        # 检查是否为新建文档（如多图片文档）
        is_new_document = (hasattr(self.parent.pdf_processor, 'is_new_document') and
                          self.parent.pdf_processor.is_new_document)

        # 如果是新建文档或非PDF扩展名文件，直接调用另存为
        if is_new_document or is_non_pdf_extension:
            self.save_as_without_encryption()
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

        # 检查是否为新建文档
        is_new_document = (hasattr(self.parent.pdf_processor, 'is_new_document') and 
                          self.parent.pdf_processor.is_new_document)
        
        # 获取当前文件的目录和文件名
        if self.parent.pdf_processor.current_file:
            # 对于新建文档，生成更合适的默认文件名
            if is_new_document:
                current_dir = AppSettings.get_last_save_dir()
                if "多图片文档" in self.parent.pdf_processor.current_file:
                    # 从描述中提取图片数量
                    import re
                    match = re.search(r'(\d+)张图片', self.parent.pdf_processor.current_file)
                    if match:
                        current_filename = f"merged_images_{match.group(1)}pages.pdf"
                    else:
                        current_filename = "merged_images.pdf"
                elif "目录:" in self.parent.pdf_processor.current_file:
                    # 从目录名生成文件名
                    dir_name = self.parent.pdf_processor.current_file.replace("目录: ", "")
                    current_filename = f"directory_{dir_name}.pdf"
                else:
                    current_filename = "new_document.pdf"
            else:
                # 已有文件，使用原文件信息
                current_dir = os.path.dirname(self.parent.pdf_processor.current_file)
                current_filename = os.path.basename(self.parent.pdf_processor.current_file)
        else:
            current_dir = AppSettings.get_last_save_dir()
            current_filename = "document.pdf"

        default_path = os.path.join(current_dir, current_filename)

        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "保存PDF文件", default_path, "PDF文件 (*.pdf)")

        if file_path:
            success, message = self.parent.pdf_processor.save_pdf(file_path)
            if success:
                # 保存成功后，更新current_file并清除新建标记
                self.parent.pdf_processor.current_file = file_path
                if hasattr(self.parent.pdf_processor, 'is_new_document'):
                    self.parent.pdf_processor.is_new_document = False
                
                AppSettings.set_last_save_dir(file_path)
                self.parent.show_message("✅ 文档保存成功")
                self.parent.update_save_actions_state()
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
        
        progress_dialog = QProgressDialog("正在导入图片...", "取消", 0, len(image_paths), self.parent)
        progress_dialog.setWindowTitle("导入图片")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        try:
            insert_after_page = -1
            if self.parent.pdf_processor.fitz_document:
                insert_after_page = self.parent.pdf_processor.current_page
                total_pages = len(self.parent.pdf_processor.fitz_document)

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
        # 关键：清除渲染缓存，避免显示旧的缓存内容
        if hasattr(self.parent.pdf_processor, 'clear_render_cache'):
            self.parent.pdf_processor.clear_render_cache()

        # 清除虚拟滚动区域的缓存
        if hasattr(self.parent, 'virtual_scroll') and hasattr(self.parent.virtual_scroll, 'clear_cache'):
            self.parent.virtual_scroll.clear_cache()

        total_pages = self.parent.pdf_processor.get_total_pages()
        self.parent.page_spinbox.setMaximum(total_pages)
        self.parent.total_pages_label.setText(f" / {total_pages}")
        self.parent._force_refresh_preview()

        if self.parent.show_thumbnails:
            self.parent._force_reload_thumbnails()