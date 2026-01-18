"""OCR管理混入类"""

import os
import traceback
import tempfile
import uuid
import subprocess
from base64 import b64encode
import fitz

from PyQt5.QtWidgets import QMessageBox, QApplication, QFileDialog, QProgressDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from app.utils.logger import get_logger
from app.ui.ocr_settings_dialog import OCRSettingsDialog
from app.core.ocr.ocr_plugin_interface import OCRResult, OCRErrorCode
from app.core.ocr.ocr_searchable_pdf import create_searchable_pdf
from app.core.ocr.ocr_searchable_manager import OCRSearchablePDFHandler

from app.config.settings import AppSettings
from app.ui.screenshot_result_dialog import ScreenshotOCRResultDialog

logger = get_logger('main')

class OCRManagerMixin:
    """OCR管理混入类 - 处理OCR相关功能"""

    def toggle_ocr_debug_mode(self):
        """切换OCR文本层高亮模式"""
        try:
            # 切换调试模式状态
            if not hasattr(self, '_ocr_debug_mode'):
                self._ocr_debug_mode = False

            self._ocr_debug_mode = not self._ocr_debug_mode

            # 更新菜单项状态
            if hasattr(self, 'ocr_debug_mode_action'):
                self.ocr_debug_mode_action.setChecked(self._ocr_debug_mode)

            # 更新所有已渲染页面的调试模式
            if hasattr(self, 'virtual_scroll_area') and self.virtual_scroll_area:
                self.virtual_scroll_area.set_all_pages_debug_mode(self._ocr_debug_mode)
            else:
                logger.warning(f"[toggle_ocr_debug_mode] virtual_scroll_area不存在或为空")

            # 显示提示信息
            mode_text = "启用" if self._ocr_debug_mode else "禁用"
            self.show_message(f"OCR文本层高亮模式已{mode_text}")
            
            # 保存设置到配置文件
            AppSettings.set_ocr_highlight_mode(self._ocr_debug_mode)
        except Exception as e:
            logger.error(f"切换OCR调试模式时出错: {e}")
    
    def show_ocr_settings(self):
        """显示OCR设置对话框"""
        try:
            dialog = OCRSettingsDialog(self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"显示OCR设置对话框时出错: {e}")
            
            QMessageBox.critical(self, "错误", f"无法打开OCR设置: {str(e)}")
    
    def perform_ocr_on_current_page(self):
        """对当前页面执行OCR识别"""
        try:
            # 检查是否有打开的文档（PDF或图片）
            if not self.pdf_processor.fitz_document:
                QMessageBox.warning(self, "警告", "请先打开PDF文件或图片文件")
                return
            
            # 获取当前页面
            current_page = self.pdf_processor.current_page
            if current_page < 0:
                QMessageBox.warning(self, "警告", "请先选择一个页面")
                return
            
            # 获取当前使用的OCR插件
            current_plugin_name = self.ocr_config_manager.get_current_plugin()
            if not current_plugin_name:
                QMessageBox.warning(self, "警告", "请先在OCR设置中选择一个OCR插件")
                return
            
            # 检查插件是否已加载
            if current_plugin_name not in self.ocr_plugin_manager.plugins:
                QMessageBox.critical(self, "错误", f"OCR插件 '{current_plugin_name}' 未加载")
                return
            
            # 在状态栏显示加载信息，防止重复点击
            self.show_message("正在执行OCR识别...")
            QApplication.processEvents()  # 确保状态栏更新立即显示
            
            try:
                # 获取插件实例
                plugin = self.ocr_plugin_manager.plugins[current_plugin_name]
                
                # 初始化插件（如果尚未初始化）
                if not plugin.is_initialized:
                    plugin_config = self.ocr_config_manager.get_plugin_config(current_plugin_name)
                    init_result = self.ocr_plugin_manager.initialize_plugin(current_plugin_name, plugin_config)
                    if not init_result.is_success():
                        QMessageBox.critical(self, "OCR初始化失败", f"插件初始化失败: {init_result.message}")
                        return
                
                # 获取当前页面的图像数据
                page_image_data = self.pdf_processor.get_page_image_data(current_page)
                if not page_image_data:
                    QMessageBox.critical(self, "错误", "无法获取页面图像数据")
                    return
                
                # 尝试不同的OCR识别方法
                # 方法1: 直接使用字节数据
                ocr_result = plugin.recognize_from_bytes(page_image_data)
                
                # 如果方法1失败，尝试方法2: 转换为Base64字符串
                if not ocr_result.is_success():
                    image_base64 = b64encode(page_image_data).decode('utf-8')
                    # 移除可能存在的前缀
                    if image_base64.startswith('data:image'):
                        # 提取纯Base64数据
                        image_base64 = image_base64.split(',')[1] if ',' in image_base64 else image_base64
                    ocr_result = plugin.recognize_from_base64(image_base64)
                
                # 如果方法2也失败，尝试方法3: 保存为临时文件并使用文件路径
                if not ocr_result.is_success():
                    # 使用完整路径避免短文件名问题
                    temp_dir = os.path.realpath(tempfile.gettempdir())
                    temp_filename = f"ocr_temp_{uuid.uuid4().hex}.png"
                    tmp_file_path = os.path.join(temp_dir, temp_filename)
                    
                    try:
                        # 将图像数据写入临时文件
                        with open(tmp_file_path, 'wb') as tmp_file:
                            tmp_file.write(page_image_data)
                        
                        # 确保文件已正确写入
                        if os.path.exists(tmp_file_path):
                            ocr_result = plugin.recognize_from_file(tmp_file_path)
                        else:
                            logger.error(f"临时文件创建失败: {tmp_file_path}")
                            ocr_result = OCRResult(
                                code=OCRErrorCode.FILE_NOT_FOUND,
                                message=f"临时文件创建失败: {tmp_file_path}",
                                plugin_name=plugin.plugin_name
                            )
                    except Exception as file_error:
                        logger.error(f"创建或写入临时文件时出错: {file_error}")
                        ocr_result = OCRResult(
                            code=OCRErrorCode.UNKNOWN_ERROR,
                            message=f"创建临时文件失败: {str(file_error)}",
                            plugin_name=plugin.plugin_name
                        )
                    finally:
                        # 清理临时文件
                        try:
                            if os.path.exists(tmp_file_path):
                                os.unlink(tmp_file_path)
                        except Exception as cleanup_error:
                            logger.warning(f"清理临时文件时出错: {cleanup_error}")
                
                # 处理OCR结果
                if ocr_result.is_success():
                    # 创建临时可搜索PDF以支持搜索功能
                    # 在OCR完成后确保回到原来的页面
                    self._create_ocr_searchable_pdf_for_current_page(current_page, ocr_result)
                    # 不再显示OCR结果对话框
                else:
                    QMessageBox.critical(self, "OCR识别失败", f"识别失败: {ocr_result.message}")
            
            finally:
                # 清除状态栏加载信息
                self.show_message("")
                
        except Exception as e:
            logger.error(f"执行OCR时出错: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"执行OCR时发生异常: {str(e)}")
    
    def perform_ocr_on_all_pages(self):
        """对所有页面执行OCR识别"""
        try:
            # 检查是否有打开的PDF文档
            if not self.pdf_processor.fitz_document:
                QMessageBox.warning(self, "警告", "请先打开PDF文件")
                return
            
            # 获取总页数
            total_pages = self.pdf_processor.get_total_pages()
            if total_pages == 0:
                QMessageBox.warning(self, "警告", "PDF文档为空")
                return
            
            # 获取当前使用的OCR插件
            current_plugin_name = self.ocr_config_manager.get_current_plugin()
            if not current_plugin_name:
                QMessageBox.warning(self, "警告", "请先在OCR设置中选择一个OCR插件")
                return
            
            # 检查插件是否已加载
            if current_plugin_name not in self.ocr_plugin_manager.plugins:
                QMessageBox.critical(self, "错误", f"OCR插件 '{current_plugin_name}' 未加载")
                return
            
            # 确认是否要处理所有页面
            reply = QMessageBox.question(
                self, 
                "确认", 
                f"将对所有 {total_pages} 页执行OCR识别，这可能需要较长时间。\n\n是否继续？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # 创建处理线程
            class AllPagesOCRThread(QThread):
                progress_updated = pyqtSignal(int, str, int)  # 当前页, 消息, 总页数
                page_ocr_finished = pyqtSignal(int, object, float)  # 页码, OCR结果, zoom_factor
                finished = pyqtSignal(bool, str, dict)  # 成功状态, 消息, 所有OCR结果字典
                
                def __init__(self, pdf_processor, ocr_plugin, ocr_plugin_manager, ocr_config_manager):
                    super().__init__()
                    self.pdf_processor = pdf_processor
                    self.ocr_plugin = ocr_plugin
                    self.ocr_plugin_manager = ocr_plugin_manager
                    self.ocr_config_manager = ocr_config_manager
                    self.should_stop = False
                
                def run(self):
                    try:
                        total_pages = self.pdf_processor.get_total_pages()
                        # 初始化插件（如果尚未初始化）
                        if not self.ocr_plugin.is_initialized:
                            plugin_config = self.ocr_config_manager.get_plugin_config(self.ocr_plugin.plugin_name)
                            init_result = self.ocr_plugin_manager.initialize_plugin(self.ocr_plugin.plugin_name, plugin_config)
                            if not init_result.is_success():
                                self.finished.emit(False, f"插件初始化失败: {init_result.message}", {})
                                return
                        
                        # 获取OCR识别时的zoom_factor
                        ocr_zoom_factor = self.pdf_processor.zoom_factor
                        
                        # 用于收集所有OCR结果
                        all_ocr_results = {}
                        
                        for page_num in range(total_pages):
                            if self.should_stop:
                                self.finished.emit(False, "OCR识别已取消", all_ocr_results)
                                return
                            
                            self.progress_updated.emit(page_num + 1, f"正在处理第 {page_num + 1}/{total_pages} 页...", total_pages)
                            
                            try:
                                # 获取当前页面的图像数据
                                page_image_data = self.pdf_processor.get_page_image_data(page_num)
                                if not page_image_data:
                                    logger.error(f"无法获取第 {page_num + 1} 页图像数据")
                                    all_ocr_results[page_num] = None  # 记录失败的页面
                                    continue
                                
                                # 尝试不同的OCR识别方法
                                # 方法1: 直接使用字节数据
                                ocr_result = self.ocr_plugin.recognize_from_bytes(page_image_data)
                                
                                # 如果方法1失败，尝试方法2: 转换为Base64字符串
                                if not ocr_result.is_success():
                                    image_base64 = b64encode(page_image_data).decode('utf-8')
                                    if image_base64.startswith('data:image'):
                                        image_base64 = image_base64.split(',')[1] if ',' in image_base64 else image_base64
                                    ocr_result = self.ocr_plugin.recognize_from_base64(image_base64)
                                
                                # 如果方法2也失败，尝试方法3: 保存为临时文件并使用文件路径
                                if not ocr_result.is_success():
                                    temp_dir = os.path.realpath(tempfile.gettempdir())
                                    temp_filename = f"ocr_temp_{uuid.uuid4().hex}.png"
                                    tmp_file_path = os.path.join(temp_dir, temp_filename)
                                    
                                    try:
                                        with open(tmp_file_path, 'wb') as tmp_file:
                                            tmp_file.write(page_image_data)
                                        
                                        if os.path.exists(tmp_file_path):
                                            ocr_result = self.ocr_plugin.recognize_from_file(tmp_file_path)
                                        else:
                                            logger.error(f"临时文件创建失败: {tmp_file_path}")
                                            ocr_result = OCRResult(
                                                code=OCRErrorCode.FILE_NOT_FOUND,
                                                message=f"临时文件创建失败: {tmp_file_path}",
                                                plugin_name=self.ocr_plugin.plugin_name
                                            )
                                    except Exception as file_error:
                                        logger.error(f"创建或写入临时文件时出错: {file_error}")
                                        ocr_result = OCRResult(
                                            code=OCRErrorCode.UNKNOWN_ERROR,
                                            message=f"创建临时文件失败: {str(file_error)}",
                                            plugin_name=self.ocr_plugin.plugin_name
                                        )
                                    finally:
                                        try:
                                            if os.path.exists(tmp_file_path):
                                                os.unlink(tmp_file_path)
                                        except Exception as cleanup_error:
                                            logger.warning(f"清理临时文件时出错: {cleanup_error}")
                                
                                # 存储OCR结果
                                all_ocr_results[page_num] = ocr_result
                                
                                if ocr_result.is_success():
                                    logger.info(f"第 {page_num + 1} 页OCR识别完成，识别到 {len(ocr_result.data) if isinstance(ocr_result.data, list) else 0} 个文本元素")
                                else:
                                    logger.warning(f"第 {page_num + 1} 页OCR识别失败: {ocr_result.message}")
                                
                            except Exception as e:
                                logger.error(f"第 {page_num + 1} 页OCR处理失败: {e}")
                                all_ocr_results[page_num] = None  # 记录失败的页面
                        
                        self.finished.emit(True, f"所有页面OCR识别完成，共处理 {total_pages} 页", all_ocr_results)
                        
                    except Exception as e:
                        logger.error(f"批量OCR识别失败: {e}")
                        logger.error(traceback.format_exc())
                        self.finished.emit(False, f"批量OCR识别失败: {str(e)}", {})
                
                def stop(self):
                    """停止OCR识别"""
                    self.should_stop = True
            
            # 显示进度对话框
            progress_dialog = QProgressDialog("正在对所有页面执行OCR识别...", "取消", 0, total_pages, self)
            progress_dialog.setWindowTitle("OCR识别进度")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()
            
            # 启动处理线程
            plugin = self.ocr_plugin_manager.plugins[current_plugin_name]
            self.all_pages_ocr_thread = AllPagesOCRThread(
                self.pdf_processor,
                plugin,
                self.ocr_plugin_manager,
                self.ocr_config_manager
            )
            
            # 连接信号
            self.all_pages_ocr_thread.progress_updated.connect(
                lambda value, msg, total: progress_dialog.setValue(value) or progress_dialog.setLabelText(msg)
            )
            
            # 注意：不再处理单个页面的OCR完成信号，改为在所有页面完成后统一处理
            # self.all_pages_ocr_thread.page_ocr_finished.connect(
            #     lambda page_num, ocr_result, zoom_factor: self._on_page_ocr_finished(page_num, ocr_result, zoom_factor)
            # )
            
            self.all_pages_ocr_thread.finished.connect(
                lambda success, message, all_ocr_results: self._on_all_pages_ocr_finished(success, message, progress_dialog, all_ocr_results)
            )
            
            progress_dialog.canceled.connect(
                lambda: self.all_pages_ocr_thread.stop() if hasattr(self.all_pages_ocr_thread, 'stop') else None
            )
            
            self.all_pages_ocr_thread.start()
            
        except Exception as e:
            logger.error(f"启动批量OCR时出错: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"启动批量OCR时发生异常: {str(e)}")
    
    def _on_page_ocr_finished(self, page_num, ocr_result, zoom_factor):
        """单页OCR完成回调"""
        try:
            if ocr_result and ocr_result.is_success():
                # 初始化OCR可搜索PDF处理器（如果尚未初始化）
                if not hasattr(self, 'ocr_searchable_handler') or not self.ocr_searchable_handler:
                    self.ocr_searchable_handler = OCRSearchablePDFHandler(
                        self.pdf_processor,
                        self.ocr_plugin_manager,
                        self.ocr_config_manager
                    )
                
                # 调用处理器的页面OCR完成回调方法
                self.ocr_searchable_handler.handle_page_ocr_completed(page_num, ocr_result)
                
                # 刷新页面显示
                self.pdf_processor.clear_render_cache()
                self.update_preview()
                
                # 确保回到原页面
                # 在处理导入图片后，需要确保页面索引仍然有效
                total_pages = self.pdf_processor.get_total_pages()
                target_page = min(page_num, total_pages - 1) if total_pages > 0 else page_num
                
                if hasattr(self, 'virtual_scroll'):
                    self.virtual_scroll.scroll_to_page(target_page)

        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页OCR结果时出错: {e}")
    
    def _on_page_ocr_finished(self, page_num, ocr_result, zoom_factor):
        """单页OCR完成回调（在批量OCR模式下不使用此方法，仅保留供其他功能使用）"""
        try:
            if ocr_result and ocr_result.is_success():
                # 初始化OCR可搜索PDF处理器（如果尚未初始化）
                if not hasattr(self, 'ocr_searchable_handler') or not self.ocr_searchable_handler:
                    self.ocr_searchable_handler = OCRSearchablePDFHandler(
                        self.pdf_processor,
                        self.ocr_plugin_manager,
                        self.ocr_config_manager
                    )
                    
                # 调用处理器的页面OCR完成回调方法
                self.ocr_searchable_handler.handle_page_ocr_completed(page_num, ocr_result)
                    
                # 刷新页面显示
                self.pdf_processor.clear_render_cache()
                self.update_preview()
                    
                # 确保回到原页面
                # 在处理导入图片后，需要确保页面索引仍然有效
                total_pages = self.pdf_processor.get_total_pages()
                target_page = min(page_num, total_pages - 1) if total_pages > 0 else page_num
                
                if hasattr(self, 'virtual_scroll'):
                    self.virtual_scroll.scroll_to_page(target_page)
    
        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页OCR结果时出错: {e}")

    def _on_all_pages_ocr_finished(self, success, message, progress_dialog, all_ocr_results):
        """所有页面OCR完成回调，一次性处理所有结果"""
        progress_dialog.close()
        
        if success:
            try:
                # 初始化OCR可搜索PDF处理器（如果尚未初始化）
                if not hasattr(self, 'ocr_searchable_handler') or not self.ocr_searchable_handler:
                    self.ocr_searchable_handler = OCRSearchablePDFHandler(
                        self.pdf_processor,
                        self.ocr_plugin_manager,
                        self.ocr_config_manager
                    )
                
                # 显示进度对话框
                batch_progress_dialog = QProgressDialog("正在生成可搜索PDF...", "取消", 0, 100, self)
                batch_progress_dialog.setWindowTitle("生成可搜索PDF")
                batch_progress_dialog.setWindowModality(Qt.WindowModal)
                
                # 定义进度回调函数
                def progress_callback(value, msg):
                    batch_progress_dialog.setValue(value)
                    batch_progress_dialog.setLabelText(msg)
                    QApplication.processEvents()  # 确保UI更新
                    
                    # 检查用户是否取消
                    if batch_progress_dialog.wasCanceled():
                        # 这里我们不能直接中断处理，因为是在同一线程中
                        # 可以记录取消状态并在后续实现中断功能
                        pass
                
                batch_progress_dialog.show()
                
                # 使用处理器的一次性批量处理方法
                success, msg = self.ocr_searchable_handler.handle_batch_ocr_completed(all_ocr_results, progress_callback)
                
                batch_progress_dialog.close()
                
                if success:
                    # 刷新页面显示
                    self.pdf_processor.clear_render_cache()
                    self.update_preview()
                    
                    # 批量OCR完成后尝试回到之前所在的页面（这里保持在当前显示的页面）
                    current_page_index = self.pdf_processor.current_page
                    if hasattr(self, 'virtual_scroll'):
                        self.virtual_scroll.scroll_to_page(current_page_index)
                    
                    self.show_message(f"✅ {message}，已生成可搜索PDF")
                else:
                    self.show_message(f"⚠️ {message}，但生成可搜索PDF时出现问题: {msg}")
                    
            except Exception as e:
                logger.error(f"批量处理OCR结果时出错: {e}")
                logger.error(traceback.format_exc())
                self.show_message(f"⚠️ {message}，但处理结果时出错: {str(e)}")
        else:
            QMessageBox.critical(self, "错误", f"❌ {message}")
            self.show_message("❌ 批量OCR识别失败")
    
    def create_searchable_pdf(self):
        """创建可搜索PDF"""
        # 检查是否有打开的PDF文档
        if not self.pdf_processor.pdf_document:
            QMessageBox.warning(self, "警告", "请先打开PDF文件")
            return
        
        # 检查是否有配置OCR插件
        current_plugin_name = self.ocr_config_manager.get_current_plugin()
        if not current_plugin_name:
            QMessageBox.warning(self, "警告", "请先在OCR设置中选择一个OCR插件")
            return
        
        # 获取输出文件路径
        current_file = self.pdf_processor.current_file
        if not current_file:
            QMessageBox.warning(self, "警告", "无法获取当前文件路径")
            return
        
        # 生成默认输出文件名
        file_dir = os.path.dirname(current_file)
        file_name = os.path.basename(current_file)
        name_without_ext = os.path.splitext(file_name)[0]
        default_output = os.path.join(file_dir, f"{name_without_ext}_searchable.pdf")
        
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "保存可搜索PDF",
            default_output,
            "PDF文件 (*.pdf)"
        )
        
        if not output_file:
            return

        # 创建处理线程
        class SearchablePDFThread(QThread):
            progress_updated = pyqtSignal(int, str)
            finished = pyqtSignal(bool, str)

            def __init__(self, input_file, output_file, ocr_plugin_manager, ocr_config_manager):
                super().__init__()
                self.input_file = input_file
                self.output_file = output_file
                self.ocr_plugin_manager = ocr_plugin_manager
                self.ocr_config_manager = ocr_config_manager

            def run(self):
                try:
                    self.progress_updated.emit(5, "正在打开PDF文件...")

                    def progress_callback(percent, message):
                        self.progress_updated.emit(percent, message)

                    success = create_searchable_pdf(
                        self.input_file,
                        self.output_file,
                        self.ocr_plugin_manager,
                        self.ocr_config_manager,
                        show_text_boxes=False,
                        progress_callback=progress_callback
                    )

                    if success:
                        self.progress_updated.emit(100, "可搜索PDF创建完成")
                        self.finished.emit(True, f"可搜索PDF已创建: {self.output_file}")
                    else:
                        self.finished.emit(False, "创建可搜索PDF失败")

                except Exception as e:
                    self.finished.emit(False, f"创建过程中出错: {str(e)}")
        
        # 显示进度对话框
        progress_dialog = QProgressDialog("正在创建可搜索PDF...", "取消", 0, 100, self)
        progress_dialog.setWindowTitle("进度")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # 启动处理线程
        self.searchable_pdf_thread = SearchablePDFThread(
            current_file, 
            output_file,
            self.ocr_plugin_manager,
            self.ocr_config_manager
        )
        self.searchable_pdf_thread.progress_updated.connect(
            lambda value, msg: progress_dialog.setValue(value)
        )
        self.searchable_pdf_thread.finished.connect(
            lambda success, message: self._on_searchable_pdf_finished(success, message, progress_dialog, output_file)
        )
        self.searchable_pdf_thread.start()
    
    def _on_searchable_pdf_finished(self, success, message, progress_dialog, output_file):
        """可搜索PDF创建完成回调"""
        progress_dialog.close()
        
        if success:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("完成")
            msg_box.setText(f"✅ {message}")
            msg_box.setIcon(QMessageBox.Information)

            open_in_app_btn = msg_box.addButton("打开", QMessageBox.ActionRole)
            open_dir_btn = msg_box.addButton("打开目录", QMessageBox.ActionRole)
            msg_box.addButton("确定", QMessageBox.AcceptRole)

            msg_box.exec_()

            if msg_box.clickedButton() == open_in_app_btn:
                # 在程序中打开生成的可搜索PDF文件
                try:
                    if os.path.exists(output_file):
                        success, message = self.pdf_processor.open_pdf(output_file, async_mode=True)
                        if not success:
                            QMessageBox.warning(self, "警告", f"打开文件失败: {message}")
                    else:
                        QMessageBox.warning(self, "警告", "文件不存在")
                except Exception as e:
                    logger.error(f"在程序中打开文件失败: {e}")
                    QMessageBox.warning(self, "警告", f"无法在程序中打开文件: {str(e)}")

            elif msg_box.clickedButton() == open_dir_btn:
                # 打开文件所在目录
                try:
                    output_dir = os.path.dirname(output_file)
                    output_dir = os.path.abspath(output_dir)
                    logger.info(f"打开目录: output_file={output_file}, output_dir={output_dir}")

                    if os.path.exists(output_file):
                        # 关键：/select, 与路径连成同一个参数
                        subprocess.Popen(['explorer', '/select,' + os.path.normpath(output_file)])
                    else:
                        subprocess.Popen(['explorer', output_dir])
                except Exception as e:
                    logger.error(f"打开目录失败: {e}")
                    QMessageBox.warning(self, "警告", f"无法打开目录: {str(e)}")
            
            self.show_message("✅ 可搜索PDF创建完成")
        else:
            QMessageBox.critical(self, "错误", f"❌ {message}")
            self.show_message("❌ 创建可搜索PDF失败")
    

    
    def _create_ocr_searchable_pdf_for_current_page(self, page_num, ocr_result):
        """为当前页面创建OCR可搜索PDF"""
        try:
            # 初始化OCR可搜索PDF处理器（如果尚未初始化）
            if not hasattr(self, 'ocr_searchable_handler') or not self.ocr_searchable_handler:
                self.ocr_searchable_handler = OCRSearchablePDFHandler(
                    self.pdf_processor,
                    self.ocr_plugin_manager,
                    self.ocr_config_manager
                )
            
            # 调用处理器的页面OCR完成回调方法
            self.ocr_searchable_handler.handle_page_ocr_completed(page_num, ocr_result)
            
            # 刷新页面显示
            self.pdf_processor.clear_render_cache()
            self.update_preview()
            
            # OCR完成后确保回到原页面
            # 在处理导入图片后，需要确保页面索引仍然有效
            total_pages = self.pdf_processor.get_total_pages()
            target_page = min(page_num, total_pages - 1) if total_pages > 0 else page_num
            
            if hasattr(self, 'virtual_scroll'):
                self.virtual_scroll.scroll_to_page(target_page)
            
            self.show_message(f"✅ 第{target_page+1}页OCR识别完成，已添加到可搜索PDF")
            
        except Exception as e:
            logger.error(f"创建OCR可搜索PDF时出错: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"创建OCR可搜索PDF失败: {str(e)}")
    
    def _ensure_temp_file_if_needed(self):
        """如果当前是原始文件，切换到临时文件以避免修改原始文件"""
        if not self.pdf_processor.fitz_document:
            return
        
        current_file = self.pdf_processor.current_file
        if not current_file:
            return
        
        # 检查是否已经是临时文件
        if current_file.startswith(tempfile.gettempdir()):
            logger.debug(f"当前已是临时文件: {current_file}")
            return
        
        # 创建临时文件
        temp_dir = os.path.realpath(tempfile.gettempdir())
        temp_filename = f"pypdf_temp_{uuid.uuid4().hex}.pdf"
        temp_file = os.path.join(temp_dir, temp_filename)
        
        try:
            # 保存当前文档到临时文件
            self.pdf_processor.fitz_document.save(temp_file, garbage=4, deflate=True)
            
            # 关闭当前文档
            self.pdf_processor.fitz_document.close()
            
            # 重新打开临时文件
            self.pdf_processor.fitz_document = fitz.open(temp_file)
            
            # 更新当前文件路径
            self.pdf_processor.current_file = temp_file
            
            logger.info(f"已切换到临时文件: {temp_file}")
            self.show_message(f"✅ 文档已切换到临时文件，原始文件不会被修改")
            
            # 标记文档有未保存的更改
            if hasattr(self.pdf_processor, 'page_editor') and self.pdf_processor.page_editor:
                self.pdf_processor.page_editor.is_modified = True
                self.pdf_processor.page_editor._emit_state_changed()
            
        except Exception as e:
            logger.error(f"切换到临时文件失败: {e}")
            raise
    
    def enable_ocr_searchable_pdf(self):
        """启用OCR可搜索PDF功能"""
        try:
            # 检查是否有打开的PDF文档
            if not self.pdf_processor.fitz_document:
                QMessageBox.warning(self, "警告", "请先打开PDF文件")
                return
            
            # 检查是否有配置OCR插件
            current_plugin_name = self.ocr_config_manager.get_current_plugin()
            if not current_plugin_name:
                QMessageBox.warning(self, "警告", "请先在OCR设置中选择一个OCR插件")
                return
            
            # 初始化OCR可搜索PDF处理器
            if not hasattr(self, 'ocr_searchable_handler') or not self.ocr_searchable_handler:
                self.ocr_searchable_handler = OCRSearchablePDFHandler(
                    self.pdf_processor,
                    self.ocr_plugin_manager,
                    self.ocr_config_manager
                )
            
            # 显示进度对话框
            progress_dialog = QProgressDialog("正在创建临时可搜索PDF以支持搜索功能...", "取消", 0, 100, self)
            progress_dialog.setWindowTitle("OCR可搜索PDF")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()
            
            def progress_callback(value, message):
                progress_dialog.setValue(value)
                progress_dialog.setLabelText(message)
                QApplication.processEvents()  # 确保进度条更新
            
            # 启用OCR可搜索功能
            success, message = self.ocr_searchable_handler.enable_searchable_ocr_feature(progress_callback)
            
            progress_dialog.close()
            
            if success:
                QMessageBox.information(self, "成功", f"✅ {message}\n\n现在可以搜索OCR识别的文本了！")
                self.show_message("OCR可搜索功能已启用")
            else:
                QMessageBox.critical(self, "错误", f"❌ {message}")
                self.show_message("OCR可搜索功能启用失败")
                
        except Exception as e:
            logger.error(f"启用OCR可搜索PDF功能时出错: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"启用OCR可搜索功能失败: {str(e)}")

    def disable_ocr_searchable_pdf(self):
        """禁用OCR可搜索PDF功能，恢复原始PDF"""
        try:
            if hasattr(self, 'ocr_searchable_handler') and self.ocr_searchable_handler:
                self.ocr_searchable_handler.disable_searchable_ocr_feature()
                self.show_message("OCR可搜索功能已禁用，恢复原始PDF")
            else:
                self.show_message("OCR可搜索功能未启用")
        except Exception as e:
            logger.error(f"禁用OCR可搜索PDF功能时出错: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"禁用OCR可搜索功能失败: {str(e)}")

    def start_screenshot_ocr_mode(self):
        """开始截图OCR模式"""
        try:
            # 检查是否有打开的文档
            if not self.pdf_processor.fitz_document:
                QMessageBox.warning(self, "警告", "请先打开PDF文件")
                return

            # 检查是否有配置OCR插件
            current_plugin_name = self.ocr_config_manager.get_current_plugin()
            if not current_plugin_name:
                QMessageBox.warning(self, "警告", "请先在OCR设置中选择一个OCR插件")
                return

            # 检查插件是否已加载
            if current_plugin_name not in self.ocr_plugin_manager.plugins:
                QMessageBox.critical(self, "错误", f"OCR插件 '{current_plugin_name}' 未加载")
                return

            # 检查虚拟滚动区域是否存在
            if not hasattr(self, 'virtual_scroll_area') or not self.virtual_scroll_area:
                QMessageBox.critical(self, "错误", "虚拟滚动区域未初始化")
                return

            # 检查当前是否有可见页面
            current_page = self.pdf_processor.current_page
            if current_page < 0:
                QMessageBox.warning(self, "警告", "当前没有可用的页面")
                return

            logger.debug(f"[start_screenshot_ocr_mode] 开始截图OCR模式，当前页: {current_page}")

            # 调用虚拟滚动区域的截图OCR模式
            self.virtual_scroll_area.enable_screenshot_ocr_mode(current_page, self)

            self.show_message("截图OCR模式已激活，请在页面上拖拽选择识别区域（按ESC取消）")

        except Exception as e:
            logger.error(f"启动截图OCR模式时出错: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"启动截图OCR模式失败: {str(e)}")

    def perform_screenshot_ocr(self, selection_rect, page_index):
        """
        执行截图OCR识别

        Args:
            selection_rect: 选区矩形（相对于页面的坐标）
            page_index: 页面索引
        """
        try:
            logger.debug(f"[perform_screenshot_ocr] 开始截图OCR，页面: {page_index}, 选区: {selection_rect}")

            # 检查是否有打开的文档
            if not self.pdf_processor.fitz_document:
                QMessageBox.warning(self, "警告", "文档未打开")
                return

            # 检查页面索引是否有效
            if page_index < 0 or page_index >= self.pdf_processor.get_total_pages():
                QMessageBox.warning(self, "警告", f"页面索引无效: {page_index}")
                return

            # 获取当前使用的OCR插件
            current_plugin_name = self.ocr_config_manager.get_current_plugin()
            if not current_plugin_name:
                QMessageBox.warning(self, "警告", "请先在OCR设置中选择一个OCR插件")
                return

            # 获取插件实例
            plugin = self.ocr_plugin_manager.plugins.get(current_plugin_name)
            if not plugin:
                QMessageBox.critical(self, "错误", f"OCR插件 '{current_plugin_name}' 未加载")
                return

            # 初始化插件（如果尚未初始化）
            if not plugin.is_initialized:
                plugin_config = self.ocr_config_manager.get_plugin_config(current_plugin_name)
                init_result = self.ocr_plugin_manager.initialize_plugin(current_plugin_name, plugin_config)
                if not init_result.is_success():
                    QMessageBox.critical(self, "OCR初始化失败", f"插件初始化失败: {init_result.message}")
                    return

            # 获取选区图像数据
            image_data = self._get_selection_image_data(page_index, selection_rect)
            if not image_data:
                QMessageBox.critical(self, "错误", "无法获取选区图像数据")
                return

            # 在状态栏显示加载信息
            self.show_message("正在进行OCR识别...")
            QApplication.processEvents()

            try:
                # 尝试不同的OCR识别方法
                # 方法1: 直接使用字节数据
                ocr_result = plugin.recognize_from_bytes(image_data)

                # 如果方法1失败，尝试方法2: 转换为Base64字符串
                if not ocr_result.is_success():
                    image_base64 = b64encode(image_data).decode('utf-8')
                    if image_base64.startswith('data:image'):
                        image_base64 = image_base64.split(',')[1] if ',' in image_base64 else image_base64
                    ocr_result = plugin.recognize_from_base64(image_base64)

                # 如果方法2也失败，尝试方法3: 保存为临时文件
                if not ocr_result.is_success():
                    temp_dir = os.path.realpath(tempfile.gettempdir())
                    temp_filename = f"screenshot_ocr_{uuid.uuid4().hex}.png"
                    tmp_file_path = os.path.join(temp_dir, temp_filename)

                    try:
                        with open(tmp_file_path, 'wb') as tmp_file:
                            tmp_file.write(image_data)

                        if os.path.exists(tmp_file_path):
                            ocr_result = plugin.recognize_from_file(tmp_file_path)
                        else:
                            logger.error(f"临时文件创建失败: {tmp_file_path}")
                            ocr_result = OCRResult(
                                code=OCRErrorCode.FILE_NOT_FOUND,
                                message=f"临时文件创建失败: {tmp_file_path}",
                                plugin_name=plugin.plugin_name
                            )
                    except Exception as file_error:
                        logger.error(f"创建或写入临时文件时出错: {file_error}")
                        ocr_result = OCRResult(
                            code=OCRErrorCode.UNKNOWN_ERROR,
                            message=f"创建临时文件失败: {str(file_error)}",
                            plugin_name=plugin.plugin_name
                        )
                    finally:
                        try:
                            if os.path.exists(tmp_file_path):
                                os.unlink(tmp_file_path)
                        except Exception as cleanup_error:
                            logger.warning(f"清理临时文件时出错: {cleanup_error}")

                # 显示OCR结果
                dialog = ScreenshotOCRResultDialog(ocr_result, self)
                dialog.exec_()

                if ocr_result.is_success():
                    self.show_message("✅ OCR识别完成")
                else:
                    self.show_message(f"⚠️ OCR识别失败: {ocr_result.message}")

            finally:
                self.show_message("")

        except Exception as e:
            logger.error(f"执行截图OCR时出错: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"执行截图OCR时发生异常: {str(e)}")

    def _get_selection_image_data(self, page_index, selection_rect):
        """
        获取选区图像数据

        Args:
            page_index: 页面索引
            selection_rect: 选区矩形（相对于页面的坐标）

        Returns:
            bytes: 图像数据（PNG格式）
        """
        try:
            if not self.pdf_processor.fitz_document:
                logger.error("PDF文档未打开")
                return None

            # 检查页面索引
            if page_index < 0 or page_index >= len(self.pdf_processor.fitz_document):
                logger.error(f"页面索引超出范围: {page_index}")
                return None

            # 获取页面
            page = self.pdf_processor.fitz_document[page_index]

            # 计算PDF文档中的实际坐标（需要除以缩放因子）
            zoom_factor = self.pdf_processor.zoom_factor
            pdf_rect = fitz.Rect(
                selection_rect.x() / zoom_factor,
                selection_rect.y() / zoom_factor,
                selection_rect.right() / zoom_factor,
                selection_rect.bottom() / zoom_factor
            )

            logger.debug(f"[_get_selection_image_data] 页面: {page_index}, 选区: {selection_rect}, PDF坐标: {pdf_rect}, 缩放: {zoom_factor}")

            # 使用与显示相同的缩放比例渲染选区
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            pix = page.get_pixmap(clip=pdf_rect, matrix=mat, alpha=False)

            # 转换为PNG格式
            img_data = pix.tobytes("png")

            logger.debug(f"[_get_selection_image_data] 成功获取图像数据，大小: {len(img_data)} 字节")

            return img_data

        except Exception as e:
            logger.error(f"获取选区图像数据时出错: {e}")
            logger.error(traceback.format_exc())
            return None