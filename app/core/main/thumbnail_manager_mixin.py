"""缩略图管理混入类 - 重构版"""

from app.utils.logger import get_logger

logger = get_logger('main')

class ThumbnailManagerMixin:
    """缩略图管理混入类 - 处理缩略图功能"""
    
    def split_pdf(self):
        """PDF拆分功能"""
        if not self.pdf_processor.pdf_document:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "请先打开PDF文件")
            return

        self.split_manager.show_split_dialog()

    def merge_pdf(self):
        """PDF合并功能"""
        self.merge_manager.show_merge_dialog()
    
    def show_barcode_settings(self):
        """显示条码设置对话框"""
        try:
            from app.ui.barcode_plugin_settings_dialog import BarcodeSettingsDialog
            dialog = BarcodeSettingsDialog(self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"显示条码设置对话框时出错: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"无法打开条码设置: {str(e)}")
    
    def barcode_split_pdf(self):
        """条码拆分功能"""
        if not self.pdf_processor.pdf_document:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "请先打开PDF文件")
            return
        
        # 直接打开条码拆分对话框
        from app.ui.barcode_split_dialog import BarcodeSplitDialog
        from app.core.barcode.barcode_split_processor import BarcodeSplitThread
        from PyQt5.QtWidgets import QDialog
        
        current_file_path = self.pdf_processor.current_file
        if not current_file_path:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "请先打开PDF文件")
            return
        
        barcode_dialog = BarcodeSplitDialog(self, current_file_path)
        if barcode_dialog.exec_() == QDialog.Accepted:
            config = barcode_dialog.get_config()
            
            # 检查是否有缓存的检测结果可以使用
            pre_detected_barcodes = None
            if (hasattr(self, 'last_barcode_detection_result') and 
                self.last_barcode_detection_result and
                self.last_barcode_detection_result['file_path'] == current_file_path and
                self.last_barcode_detection_result['config'] == config):
                # 检查缓存是否过期（5分钟内有效）
                from PyQt5.QtCore import QDateTime
                current_time = QDateTime.currentDateTime()
                cached_time = self.last_barcode_detection_result['timestamp']
                if cached_time.secsTo(current_time) < 300:  # 5分钟内
                    pre_detected_barcodes = self.last_barcode_detection_result['barcodes']
                    logger.info(f"使用缓存的条码检测结果，共 {len(pre_detected_barcodes)} 个条码")
            
            # 显示进度对话框
            self.show_progress_dialog("正在根据条码拆分PDF...", cancellable=False)
            
            # 创建条码拆分工作线程
            self.barcode_split_worker = BarcodeSplitThread(current_file_path, config, pre_detected_barcodes)
            self.barcode_split_worker.progress_updated.connect(self._on_barcode_split_progress)
            self.barcode_split_worker.finished.connect(self._on_barcode_split_finished)
            self.barcode_split_worker.error_occurred.connect(self._on_barcode_split_error)
            
            # 开始拆分
            self.barcode_split_worker.start()
    
    def _on_barcode_split_progress(self, percent: int, message: str):
        """条码拆分进度更新"""
        if self.progress_dialog:
            self.progress_dialog.setValue(percent)
            self.progress_dialog.setLabelText(message)
    
    def _on_barcode_split_finished(self, result):
        """条码拆分完成"""
        self.hide_progress_dialog()
        
        if result.success:
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("拆分完成")
            msg_box.setText(f"✅ {result.message}")
            msg_box.setIcon(QMessageBox.Information)
            
            open_dir_btn = msg_box.addButton("📂 打开目录", QMessageBox.ActionRole)
            msg_box.addButton("确定", QMessageBox.AcceptRole)
            
            msg_box.exec_()
            
            if msg_box.clickedButton() == open_dir_btn:
                # 打开用户设置的输出目录
                import subprocess
                import os
                try:
                    logger.debug(f"拆分结果信息: output_dir='{getattr(result, 'output_dir', 'N/A')}', files_created={getattr(result, 'files_created', 'N/A')}")
                    
                    # 从结果中获取输出目录
                    if hasattr(result, 'output_dir') and result.output_dir:
                        output_dir = result.output_dir
                        logger.debug(f"使用结果中的输出目录: {output_dir}")
                    elif result.files_created:
                        # 如果结果中没有输出目录，则使用第一个文件的目录
                        first_file = result.files_created[0]
                        output_dir = os.path.dirname(first_file)
                        logger.debug(f"使用第一个文件的目录: {output_dir}")
                    else:
                        # 如果都没有，则使用默认文档目录
                        output_dir = os.path.expanduser('~/Documents')
                        logger.debug(f"使用默认文档目录: {output_dir}")
                    
                    logger.debug(f"最终要打开的目录: {output_dir}")
                    
                    # 确保路径使用正确的分隔符
                    normalized_path = os.path.normpath(output_dir)
                    logger.debug(f"标准化后的路径: {normalized_path}")
                    
                    if os.path.exists(normalized_path):
                        subprocess.Popen(['explorer', normalized_path])
                    else:
                        # 如果目录不存在，尝试创建它
                        os.makedirs(normalized_path, exist_ok=True)
                        subprocess.Popen(['explorer', normalized_path])
                except Exception as e:
                    logger.error(f"打开输出目录失败: {e}")
                    QMessageBox.warning(self, "警告", f"无法打开输出目录: {str(e)}")
            
            self.show_message(f"条码拆分完成，共生成 {len(result.files_created)} 个文件")
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "拆分失败", f"❌ {result.message}")
    
    def _on_barcode_split_error(self, error_msg: str):
        """条码拆分错误"""
        self.hide_progress_dialog()
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "错误", f"❌ 条码拆分失败：{error_msg}")