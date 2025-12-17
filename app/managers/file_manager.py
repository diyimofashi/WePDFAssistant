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
        """打开PDF文件"""
        logger.info("开始打开文件...")
        last_dir = AppSettings.get_last_open_dir()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent, "选择PDF文件", last_dir, "PDF文件 (*.pdf)")
        
        if file_path:
            logger.info(f"选择了文件: {file_path}")
            self.parent.show_progress_dialog("正在加载PDF文件...")
            success, message = self.parent.pdf_processor.open_pdf(file_path, async_mode=True)
            
            if success:
                logger.info("异步加载启动成功")
                AppSettings.set_last_open_dir(file_path)
            else:
                logger.error(f"异步加载启动失败: {message}")
                self.parent.hide_progress_dialog()
                QMessageBox.critical(self.parent, "错误", message)
        else:
            logger.info("未选择文件")
    
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
            self.save_as_file()
    
    def save_as_file(self):
        """另存为PDF文件"""
        if not self.parent.pdf_processor.current_file:
            QMessageBox.information(self.parent, "提示", "📝 请先打开PDF文件")
            return
        
        last_save_dir = AppSettings.get_last_save_dir()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "另存为PDF文件", last_save_dir, "PDF文件 (*.pdf)")
        
        if file_path:
            success, message = self.parent.pdf_processor.save_pdf(file_path)
            
            if success:
                AppSettings.set_last_save_dir(file_path)
                QMessageBox.information(self.parent, "保存成功", message)
            else:
                QMessageBox.critical(self.parent, "保存失败", message)
    
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