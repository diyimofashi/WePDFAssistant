"""文件操作管理器模块"""

import os
import fitz  # PyMuPDF
import re
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QApplication
from PyQt5.QtCore import Qt
from app.utils.logger import get_logger
from app.config.settings import AppSettings
from app.ui.password_dialog import PasswordDialog

logger = get_logger('file_manager')


class FileManager:
    """文件操作管理器 - 负责文件的打开、保存、导入等操作"""

    def __init__(self, parent_window):
        self.parent = parent_window

    def _play_success_sound(self):
        """播放成功提示音"""
        try:
            QApplication.beep()
        except Exception as e:
            logger.debug(f"播放提示音失败: {e}")
        
    def open_file(self):
        """打开PDF文件、图片文件或多个文件"""
        last_dir = AppSettings.get_last_open_dir()

        # 弹出文件选择对话框，支持多选
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.parent, "选择文件", last_dir,
            "所有支持的文件 (*.pdf *.jpg *.jpeg *.png *.bmp *.gif *.tiff *.tif *.webp *.ico);;PDF文件 (*.pdf);;图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp *.ico);;所有文件 (*.*)"
        )

        # 如果用户没有选择文件，直接返回
        if not file_paths:
            logger.info("用户取消了文件选择")
            return

        # 如果选择了多个文件，创建临时PDF
        if len(file_paths) > 1:
            self._open_multiple_files_as_temp_pdf(file_paths)
        else:
            # 只选择了一个文件，直接打开
            file_path = file_paths[0]
            file_ext = os.path.splitext(file_path)[1].lower()
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}

            if file_ext in image_extensions:
                # 单个图片文件
                self._load_multiple_images([file_path])
            else:
                # PDF或其他文件
                self._open_pdf_file(file_path)
                AppSettings.set_last_open_dir(file_path)

    def _scan_and_classify_files(self, file_paths):
        """扫描文件并分类：图片文件、PDF文件、加密PDF文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
        pdf_files = []
        image_files = []
        encrypted_pdfs = []

        for file_path in file_paths:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in image_extensions:
                image_files.append(file_path)
            else:
                pdf_files.append(file_path)
                try:
                    doc = fitz.open(file_path)
                    if doc.needs_pass:
                        encrypted_pdfs.append(file_path)
                    doc.close()
                except Exception as e:
                    logger.warning(f"无法读取文件 {file_path}: {e}")

        return pdf_files, image_files, encrypted_pdfs

    def _ask_user_for_encrypted_files_action(self, encrypted_pdfs):
        """询问用户如何处理加密PDF文件"""
        encrypted_names = [os.path.basename(f) for f in encrypted_pdfs]
        msg = f"发现 {len(encrypted_pdfs)} 个加密PDF文件：\n\n"
        for name in encrypted_names[:5]:
            msg += f"  • {name}\n"
        if len(encrypted_names) > 5:
            msg += f"  ... 还有 {len(encrypted_names) - 5} 个\n"
        msg += "\n请选择处理方式："

        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle("发现加密PDF")
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Question)

        skip_btn = msg_box.addButton("跳过加密文件", QMessageBox.ActionRole)
        input_btn = msg_box.addButton("为每个加密文件输入密码", QMessageBox.ActionRole)
        cancel_btn = msg_box.addButton("取消操作", QMessageBox.RejectRole)

        msg_box.exec_()

        if msg_box.clickedButton() == skip_btn:
            return 'skip'
        elif msg_box.clickedButton() == cancel_btn:
            return 'cancel'
        else:
            return 'input_password'

    def _collect_passwords_for_encrypted_files(self, encrypted_pdfs):
        """为加密文件收集密码（每个文件最多3次尝试）"""
        passwords = {}

        for encrypted_path in encrypted_pdfs:
            filename = os.path.basename(encrypted_path)
            password = None

            for attempt in range(3):
                password = PasswordDialog.get_user_password(
                    self.parent,
                    f"请输入 {filename} 的密码（剩余 {3 - attempt} 次机会）"
                )

                if password is None:
                    logger.info(f"用户取消输入 {filename} 的密码")
                    break

                try:
                    test_doc = fitz.open(encrypted_path)
                    if test_doc.authenticate(password):
                        logger.info(f"密码验证成功: {filename}")
                        passwords[encrypted_path] = password
                        test_doc.close()
                        break
                    else:
                        logger.warning(f"密码错误，第 {attempt + 1} 次尝试失败: {filename}")
                        test_doc.close()
                        if attempt < 2:
                            QMessageBox.warning(
                                self.parent,
                                "密码错误",
                                f"密码错误，请重新输入\n剩余 {2 - attempt} 次机会"
                            )
                except Exception as e:
                    logger.warning(f"密码验证时出错: {filename}, {e}")
                    if attempt < 2:
                        QMessageBox.warning(
                            self.parent,
                            "错误",
                            f"密码验证时出错: {str(e)}\n剩余 {2 - attempt} 次机会"
                        )

        return passwords

    def _merge_files_to_temp_pdf(self, all_valid_files, encrypted_pdfs, passwords):
        """将所有有效文件合并到临时PDF"""
        from PyQt5.QtWidgets import QProgressDialog
        import tempfile

        temp_doc = fitz.open()
        a4_width = 595
        a4_height = 842
        padding = 40

        progress = QProgressDialog("正在合并文件...", "取消", 0, len(all_valid_files), self.parent)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        processed_files = []

        for i, file_path in enumerate(all_valid_files):
            progress.setValue(i)
            QApplication.processEvents()

            if progress.wasCanceled():
                temp_doc.close()
                logger.info("用户取消了文件合并")
                return None, None

            success = self._add_file_to_temp_pdf(
                temp_doc, file_path, encrypted_pdfs, passwords,
                a4_width, a4_height, padding
            )

            if success:
                processed_files.append(file_path)

        progress.setValue(len(all_valid_files))
        progress.close()

        return temp_doc, processed_files

    def _add_file_to_temp_pdf(self, temp_doc, file_path, encrypted_pdfs, passwords,
                               a4_width, a4_height, padding):
        """添加单个文件到临时PDF"""
        file_ext = os.path.splitext(file_path)[1].lower()
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}

        try:
            if file_ext in image_extensions:
                page = temp_doc.new_page(width=a4_width, height=a4_height)
                image_rect = fitz.Rect(padding, 0, a4_width - padding, a4_height)
                page.insert_image(image_rect, filename=file_path)
            else:
                pdf_doc = fitz.open(file_path)

                if file_path in encrypted_pdfs and passwords:
                    password = passwords.get(file_path)
                    if password:
                        if not pdf_doc.authenticate(password):
                            logger.warning(f"PDF密码错误或文件已损坏: {file_path}")
                            pdf_doc.close()
                            return False

                temp_doc.insert_pdf(pdf_doc)
                pdf_doc.close()

            return True
        except Exception as e:
            logger.warning(f"无法加载文件 {file_path}: {e}")
            return False

    def _save_temp_pdf_and_open(self, temp_doc, processed_files, original_file_paths):
        """保存临时PDF并打开"""
        import tempfile
        import uuid

        temp_filename = f"temp_merge_{uuid.uuid4().hex[:8]}.pdf"
        temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
        temp_doc.save(temp_path)
        temp_doc.close()

        success, message = self.parent.pdf_processor.open_pdf(temp_path, async_mode=True)
        if success:
            self.parent.pdf_processor.is_from_image = True
            self.parent.pdf_processor.current_file = None
            self.parent.pdf_processor.original_image_path = None
            self.parent.pdf_processor.is_temp_merge = True

            AppSettings.set_last_open_dir(original_file_paths[0])
            logger.info(f"成功打开临时合并PDF: {temp_path}")

            skipped_count = len(original_file_paths) - len(processed_files)
            if skipped_count > 0:
                QMessageBox.information(
                    self.parent,
                    "提示",
                    f"成功打开 {len(processed_files)} 个文件\n跳过 {skipped_count} 个文件"
                )
        else:
            logger.error(f"打开临时PDF失败: {message}")
            QMessageBox.critical(self.parent, "错误", message)

    def _open_multiple_files_as_temp_pdf(self, file_paths):
        """打开多个文件，创建临时PDF供用户保存"""
        try:
            # 第一步：扫描并分类文件
            pdf_files, image_files, encrypted_pdfs = self._scan_and_classify_files(file_paths)

            # 第二步：处理加密PDF
            if encrypted_pdfs:
                action = self._ask_user_for_encrypted_files_action(encrypted_pdfs)

                if action == 'skip':
                    pdf_files = [f for f in pdf_files if f not in encrypted_pdfs]
                    logger.info(f"用户选择跳过 {len(encrypted_pdfs)} 个加密PDF文件")
                elif action == 'cancel':
                    logger.info("用户取消操作")
                    return
                elif action == 'input_password':
                    passwords = self._collect_passwords_for_encrypted_files(encrypted_pdfs)
                    self.pdf_passwords = passwords
                    pdf_files = list(set(pdf_files) & set(passwords.keys()))

            # 第三步：合并文件
            all_valid_files = image_files + pdf_files
            passwords = getattr(self, 'pdf_passwords', {})

            temp_doc, processed_files = self._merge_files_to_temp_pdf(
                all_valid_files, encrypted_pdfs, passwords
            )

            if temp_doc is None:
                return

            if not processed_files:
                QMessageBox.warning(self.parent, "警告", "没有文件被成功处理")
                return

            # 第四步：保存并打开
            self._save_temp_pdf_and_open(temp_doc, processed_files, file_paths)

        except Exception as e:
            logger.error(f"合并文件时发生错误: {e}")
            QMessageBox.critical(self.parent, "错误", f"合并文件时发生错误: {str(e)}")
    
    def open_multiple_images(self):
        """打开多张图片文件"""
        last_dir = AppSettings.get_last_open_dir()

        # 支持多选图片文件
        image_paths, _ = QFileDialog.getOpenFileNames(
            self.parent, "选择多张图片文件", last_dir, 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.tif *.webp *.ico);;JPEG图片 (*.jpg *.jpeg);;PNG图片 (*.png);;BMP图片 (*.bmp);;所有文件 (*.*)"
        )

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
                # 保存打开的目录
                AppSettings.set_last_open_dir(image_paths[0])
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
                # 保存打开的目录
                AppSettings.set_last_open_dir(image_paths[0])
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
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
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
        is_encrypted = False
        try:
            doc = fitz.open(file_path)
            is_encrypted = doc.needs_pass
            doc.close()
        except Exception as e:
            logger.warning(f"检查加密状态时出错: {e}")

        password = None
        if is_encrypted:
            # 弹出密码输入框，支持5次尝试
            for attempt in range(5):
                password = PasswordDialog.get_user_password(self.parent, "请输入密码")
                if password is None:
                    logger.info("用户取消了密码输入")
                    return

                # 验证密码是否正确
                try:
                    test_doc = fitz.open(file_path)
                    if test_doc.authenticate(password):
                        logger.info("密码验证成功")
                        test_doc.close()
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
        # 检查是否是从图片打开的文档
        is_from_image = (hasattr(self.parent.pdf_processor, 'is_from_image') and
                         self.parent.pdf_processor.is_from_image)

        # 如果是从图片打开的文档，需要用户选择保存位置
        if is_from_image:
            self.save_as_without_encryption()
            return

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
                self._play_success_sound()
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

        # 如果是从图片打开的文档，需要用户选择保存位置
        if message == "is_from_image_save_required":
            last_dir = AppSettings.get_last_save_dir() or AppSettings.get_last_open_dir()
            output_path, _ = QFileDialog.getSaveFileName(
                self.parent,
                "保存PDF文件",
                last_dir,
                "PDF文件 (*.pdf);;所有文件 (*.*)",
                "PDF文件 (*.pdf)"
            )

            if not output_path:
                logger.info("用户取消了保存")
                return

            # 重新调用保存
            success, message = self.parent.pdf_processor.save_pdf(output_path)
            if success:
                self._play_success_sound()
                self.parent.show_message("✅ 文件已保存")
                AppSettings.set_last_save_dir(os.path.dirname(output_path))
                # 不需要重新打开，save_pdf 已经更新了文档状态
            else:
                QMessageBox.critical(self.parent, "保存失败", message)
        elif success:
            self._play_success_sound()
            self.parent.show_message("✅ 文件已保存")
            # 不需要重新打开文件，save_pdf 已经更新了文档状态
        else:
            QMessageBox.critical(self.parent, "保存失败", message)

    def save_with_encryption(self, file_path):
        """加密保存PDF文件"""
        # 检查是否是从图片打开的文档
        is_from_image_doc = (
            hasattr(self.parent.pdf_processor, 'is_from_image') and 
            self.parent.pdf_processor.is_from_image
        )

        password = PasswordDialog.get_user_password(self.parent, "请输入加密密码")
        if password is None:
            return

        if not password:
            QMessageBox.warning(self.parent, "提示", "密码不能为空")
            return

        success, message = self.parent.pdf_processor.encrypt_pdf(password, file_path)
        if success:
            self._play_success_sound()
            self.parent.show_message("✅ 文件已加密保存")
            AppSettings.set_last_save_dir(os.path.dirname(file_path))

            if is_from_image_doc:
                # 如果是从图片打开的文档，更新状态为已保存的PDF
                self.parent.pdf_processor.current_file = file_path
                self.parent.pdf_processor.is_from_image = False
                self.parent.pdf_processor.original_image_path = None
                # 不需要重新打开，encrypt_pdf 已经生成了加密文件
            else:
                # 重新加载加密后的文件以更新文档状态
                self.parent.pdf_processor.open_pdf(file_path, async_mode=True, password=password)
        else:
            QMessageBox.critical(self.parent, "加密保存失败", message)
    
    def save_as_file(self):
        """另存为PDF文件"""
        # 检查是否有打开的文档（包括临时文档）
        if not self.parent.pdf_processor.pdf_document:
            QMessageBox.information(self.parent, "提示", "📝 请先打开PDF文件")
            return False, "没有打开的文档"

        # 询问是否要加密保存
        reply = QMessageBox.question(
            self.parent,
            "另存为",
            "是否要加密保存PDF文件？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            return self.save_as_with_encryption()
        else:
            return self.save_as_without_encryption()

    def save_as_without_encryption(self):
        """另存为PDF文件（不加密）"""
        # 检查是否是从图片打开的文档
        is_from_image_doc = (
            hasattr(self.parent.pdf_processor, 'is_from_image') and
            self.parent.pdf_processor.is_from_image
        )

        # 检查是否为临时合并文档
        is_temp_merge_doc = (
            hasattr(self.parent.pdf_processor, 'is_temp_merge') and
            self.parent.pdf_processor.is_temp_merge
        )

        # 检查是否为新建文档
        is_new_document = (hasattr(self.parent.pdf_processor, 'is_new_document') and
                          self.parent.pdf_processor.is_new_document)

        # 获取当前文件的目录和文件名
        if self.parent.pdf_processor.current_file or is_from_image_doc:
            current_dir = AppSettings.get_last_save_dir() or os.path.expanduser("~")
            current_filename = "document.pdf"

            # 如果是图片文档，使用图片文件名作为基础
            if is_from_image_doc and hasattr(self.parent.pdf_processor, 'original_image_path') and self.parent.pdf_processor.original_image_path:
                image_filename = os.path.basename(self.parent.pdf_processor.original_image_path)
                base_name = os.path.splitext(image_filename)[0]
                current_filename = f"{base_name}.pdf"
            elif self.parent.pdf_processor.current_file:
                # 已有文件，使用原文件信息
                current_dir = os.path.dirname(self.parent.pdf_processor.current_file)
                current_filename = os.path.basename(self.parent.pdf_processor.current_file)

                # 对于新建文档，生成更合适的默认文件名
                if is_new_document:
                    if "多图片文档" in self.parent.pdf_processor.current_file:
                        # 从描述中提取图片数量
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

                # 检查当前文件是否是图片格式
                image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
                file_ext = os.path.splitext(current_filename)[1].lower()

                if file_ext in image_extensions:
                    # 如果原文件是图片格式，确保输出为PDF格式
                    base_name = os.path.splitext(current_filename)[0]
                    current_filename = base_name + ".pdf"
        else:
            current_dir = AppSettings.get_last_save_dir() or os.path.expanduser("~")
            current_filename = "document.pdf"

        default_path = os.path.join(current_dir, current_filename)

        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "保存PDF文件", default_path, "PDF文件 (*.pdf)")

        if not file_path:
            return False, "用户取消保存"

        success, message = self.parent.pdf_processor.save_pdf(file_path)
        if success:
            # 保存成功后，更新current_file并清除标记
            self.parent.pdf_processor.current_file = file_path
            if hasattr(self.parent.pdf_processor, 'is_new_document'):
                self.parent.pdf_processor.is_new_document = False
            if hasattr(self.parent.pdf_processor, 'is_from_image'):
                self.parent.pdf_processor.is_from_image = False
                self.parent.pdf_processor.original_image_path = None
            if hasattr(self.parent.pdf_processor, 'is_temp_merge'):
                self.parent.pdf_processor.is_temp_merge = False

            AppSettings.set_last_save_dir(os.path.dirname(file_path))
            self._play_success_sound()
            self.parent.show_message("✅ 文档保存成功")
            self.parent.update_save_actions_state()

            # 只有非临时文档才需要重新打开
            if not is_temp_merge_doc:
                self.parent.pdf_processor.open_pdf(file_path, async_mode=True)

            return True, "保存成功"
        else:
            QMessageBox.critical(self.parent, "保存失败", message)
            return False, message

    def save_as_with_encryption(self):
        """加密另存为PDF文件"""
        # 检查是否是从图片打开的文档
        is_from_image_doc = (
            hasattr(self.parent.pdf_processor, 'is_from_image') and
            self.parent.pdf_processor.is_from_image
        )

        # 获取当前文件的目录和文件名
        if is_from_image_doc and hasattr(self.parent.pdf_processor, 'original_image_path') and self.parent.pdf_processor.original_image_path:
            # 从图片文件名生成默认文件名
            image_filename = os.path.basename(self.parent.pdf_processor.original_image_path)
            base_name = os.path.splitext(image_filename)[0]
            current_filename = f"{base_name}.pdf"
            current_dir = AppSettings.get_last_save_dir() or os.path.expanduser("~")
        elif self.parent.pdf_processor.current_file:
            current_dir = os.path.dirname(self.parent.pdf_processor.current_file)
            current_filename = os.path.basename(self.parent.pdf_processor.current_file)

            # 检查当前文件是否是图片格式
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
            file_ext = os.path.splitext(current_filename)[1].lower()

            if file_ext in image_extensions:
                # 如果原文件是图片格式，确保输出为PDF格式
                base_name = os.path.splitext(current_filename)[0]
                current_filename = base_name + ".pdf"
        else:
            current_dir = AppSettings.get_last_save_dir() or os.path.expanduser("~")
            current_filename = "document.pdf"

        default_path = os.path.join(current_dir, current_filename)

        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "加密另存为PDF文件", default_path, "PDF文件 (*.pdf)")

        if not file_path:
            return False, "用户取消保存"

        # 输入密码
        password = PasswordDialog.get_user_password(self.parent, "请输入加密密码")
        if password is None:
            return False, "用户取消输入密码"

        if not password:
            QMessageBox.warning(self.parent, "提示", "密码不能为空")
            return False, "密码不能为空"

        success, message = self.parent.pdf_processor.encrypt_pdf(password, file_path)
        if success:
            self._play_success_sound()
            AppSettings.set_last_save_dir(os.path.dirname(file_path))
            QMessageBox.information(self.parent, "保存成功", message)

            if is_from_image_doc:
                # 如果是从图片打开的文档，更新状态为已保存的PDF
                self.parent.pdf_processor.current_file = file_path
                self.parent.pdf_processor.is_from_image = False
                self.parent.pdf_processor.original_image_path = None
                # 不需要重新打开，encrypt_pdf 已经生成了加密文件
            else:
                # 重新加载加密后的文件以更新文档状态
                self.parent.pdf_processor.open_pdf(file_path, async_mode=True, password=password)

            return True, "保存成功"
        else:
            QMessageBox.critical(self.parent, "加密保存失败", message)
            return False, message

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
                self._play_success_sound()
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
        # 更新工具栏的总页数标签（状态栏标签已移除）
        if hasattr(self.parent, 'toolbar_total_pages_label'):
            self.parent.toolbar_total_pages_label.setText(f"/ {total_pages}")
        self.parent._force_refresh_preview()

        if self.parent.show_thumbnails:
            self.parent._force_reload_thumbnails()