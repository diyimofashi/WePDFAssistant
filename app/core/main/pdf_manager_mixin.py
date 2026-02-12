"""PDF管理混入类"""

import os
import traceback
import subprocess
import platform

from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                   QComboBox, QPushButton, QGroupBox,
                                   QFileDialog, QProgressBar, QMessageBox,
                                   QRadioButton, QLineEdit)
from PyQt5.QtGui import QContextMenuEvent
from app.utils.logger import get_logger
from app.config.settings import AppSettings

logger = get_logger('main')

class PDFManagerMixin:
    """PDF管理混入类 - 处理PDF加载和文件操作"""
    
    def _on_loading_progress(self, value, message):
        """加载进度更新"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
            
    def _on_pdf_loading_finished(self, success, message):
        """PDF/图片加载完成"""
        self.hide_progress_dialog()

        if success:
            if hasattr(self, 'thumbnail_list') and self.thumbnail_list:
                logger.debug("更新缩略图管理器中的PDF处理器")
                self.thumbnail_list.set_pdf_processor(self.pdf_processor)

            if self.pdf_processor.current_file:
                self.setWindowTitle(f"{AppSettings.APP_NAME} - {os.path.basename(self.pdf_processor.current_file)}")

            # 异步添加文件到历史记录（不阻塞UI）
            if hasattr(self, 'history_manager') and self.history_manager and self.pdf_processor.current_file:
                try:
                    file_path = self.pdf_processor.current_file
                    total_pages = self.pdf_processor.get_total_pages()
                    # 使用QTimer延迟执行，确保不阻塞渲染
                    QTimer.singleShot(100, lambda: self._async_add_to_history(file_path, total_pages))
                except Exception as e:
                    logger.debug(f"准备添加历史记录失败: {e}")

            # 更新缩放信息（页面信息和缩放信息已移除，此调用保留兼容性）
            # self.update_zoom_label() # 已注释掉实际调用

            # 更新工具栏的总页数标签
            if hasattr(self, 'toolbar_total_pages_label') and self.pdf_processor:
                try:
                    total_pages = self.pdf_processor.get_total_pages()
                    self.toolbar_total_pages_label.setText(f"/ {total_pages}")
                except Exception as e:
                    logger.error(f"更新工具栏总页数显示失败: {e}")
                    if hasattr(self, 'toolbar_total_pages_label'):
                        self.toolbar_total_pages_label.setText("/ 0")
            
                
            # 更新虚拟滚动区域内容（已经包含了滚动到第一页和渲染的调用）
            if hasattr(self, 'virtual_scroll') and self.pdf_processor.fitz_document:
                try:
                    # 构建页面数据
                    total_pages = self.pdf_processor.get_total_pages()
                    pages_data = []
                    for page_num in range(total_pages):
                        # 获取页面尺寸（应用自动缩放，但不乘zoom_factor）
                        page_dimensions = self.pdf_processor.get_page_dimensions(page_num, apply_auto_scaling=True)
                        if page_dimensions:
                            # 存储应用了自动缩放后的尺寸，render_page_at会乘以zoom_factor
                            width = int(page_dimensions['width'])
                            height = int(page_dimensions['height'])
                        else:
                            width = 800  # 默认宽度
                            height = 1100  # 默认高度

                        pages_data.append({
                            'page_num': page_num,
                            'width': width,
                            'height': height,
                            'zoom_factor': self.pdf_processor.zoom_factor
                        })

                    self.virtual_scroll.set_pages_data(pages_data)

                    # 触发虚拟滚动区域更新和渲染（update_content内部会延迟渲染）
                    self.virtual_scroll.update_content()

                    # 延迟滚动到第一页
                    QTimer.singleShot(200, lambda: self.virtual_scroll.scroll_to_page(0) if hasattr(self.virtual_scroll, 'scroll_to_page') else None)
                except Exception as e:
                    logger.error(f"设置虚拟滚动页面数据失败: {e}")
                    traceback.print_exc()
            
            # 显示成功消息
            if self.pdf_processor.fitz_document:
                current_file = self.pdf_processor.current_file
                file_name = os.path.basename(current_file) if current_file else "未知文件"
                total_pages = self.pdf_processor.get_total_pages()
                
                # 检查是否为多图片文档
                if hasattr(self.pdf_processor, 'multi_image_paths') and self.pdf_processor.multi_image_paths:
                    image_count = len(self.pdf_processor.multi_image_paths)
                    source_info = ""
                    if self.pdf_processor.multi_image_source_dir:
                        source_info = f" | 来源: {os.path.basename(self.pdf_processor.multi_image_source_dir)}"
                    self.show_message(f"🖼️ 成功加载{image_count}张图片: {file_name} | 共 {total_pages} 页{source_info}")
                    logger.debug(f"多图片文档加载完成: {image_count}张图片，共{total_pages}页")
                # 检查是否为图片文件
                elif current_file and any(current_file.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.ico']):
                    self.show_message(f"🖼️ 成功加载图片: {file_name} | 共 {total_pages} 页")
                    logger.debug(f"图片加载完成: {file_name}")
                else:
                    self.show_message(f"✅ 成功加载: {file_name}")
                    logger.debug(f"PDF加载完成: {file_name}")
            
            # 清除渲染缓存，确保使用最新的缩放设置
            self.pdf_processor.clear_render_cache()
            
            # 加载缩略图（如果需要）
            if self.show_thumbnails:
                self.view_controller.load_thumbnails()
            
            self.update_save_actions_state()
        else:
            QMessageBox.critical(self, "错误", message)

        # 更新欢迎界面显示
        self._update_welcome_display()

    def _async_add_to_history(self, file_path, page_count):
        """异步添加文件到历史记录"""
        try:
            logger.debug(f"准备添加到历史记录: file_path={file_path}, page_count={page_count}")
            if hasattr(self, 'history_manager') and self.history_manager:
                self.history_manager.add_file_to_history(file_path, page_count)
                logger.info(f"已异步添加到历史记录: {os.path.basename(file_path)}")
                # 如果欢迎界面正在显示，刷新历史记录
                if hasattr(self, 'welcome_widget') and self.welcome_widget:
                    self.welcome_widget.refresh_history()
            else:
                logger.warning("history_manager 未初始化，无法添加历史记录")
        except Exception as e:
            logger.error(f"异步添加历史记录失败: {e}")

    def _update_welcome_display(self):
        """更新欢迎界面显示"""
        # 如果有PDF文档，显示PDF显示区域
        if self.pdf_processor.fitz_document:
            if hasattr(self, 'stacked_widget') and hasattr(self, 'virtual_scroll'):
                self.stacked_widget.setCurrentWidget(self.virtual_scroll)
        else:
            # 没有PDF文档，显示欢迎界面
            if hasattr(self, 'welcome_widget') and self.welcome_widget and hasattr(self, 'stacked_widget'):
                self.stacked_widget.setCurrentWidget(self.welcome_widget)
                # 不再自动刷新，避免重复加载
    
    def _render_current_page_immediately(self):
        """立即渲染当前页面"""
        try:
            # 确保PDF处理器和虚拟滚动区域都已准备好
            if (hasattr(self, 'pdf_processor') and 
                self.pdf_processor.fitz_document and 
                hasattr(self, 'virtual_scroll')):
                
                # 直接调用PDF处理器渲染当前页面
                current_page = 0  # 对于图片，总是第一页
                page_dimensions = self.pdf_processor.get_page_dimensions(current_page)
                
                if page_dimensions:
                    width = int(page_dimensions['width'] * self.pdf_processor.zoom_factor)
                    height = int(page_dimensions['height'] * self.pdf_processor.zoom_factor)
                    
                    # 直接渲染页面
                    pixmap = self.pdf_processor.render_page_at(current_page, width, height)
                    
                    if pixmap:
                        logger.debug(f"直接渲染页面成功: {pixmap.width()} x {pixmap.height()}")
                        # 调用虚拟滚动区域的页面渲染完成回调
                        self.virtual_scroll.on_page_rendered(current_page, pixmap)
        except Exception as e:
            logger.error(f"立即渲染当前页面失败: {e}")
            traceback.print_exc()
            
    def _start_rendering_current_page(self):
        """开始渲染当前页面"""
        if hasattr(self, 'virtual_scroll') and hasattr(self.pdf_processor, 'current_page'):
            try:
                # 确保虚拟滚动区域已准备好
                if hasattr(self.virtual_scroll, '_render_visible_pages'):
                    # 立即渲染可见页面
                    self.virtual_scroll._render_visible_pages()
            except Exception as e:
                logger.error(f"开始渲染当前页面失败: {e}")
    
    def _force_refresh_preview(self):
        """强制刷新预览区域"""
        self.update_preview()
        
        if hasattr(self, 'preview_label') and self.preview_label:
            self.preview_label.update()
            self.preview_label.repaint()
    
    def _force_reload_thumbnails(self):
        """强制重新加载缩略图"""
        if hasattr(self, 'thumbnail_list') and self.thumbnail_list:
            self.thumbnail_list.clear()
        
        self.view_controller.load_thumbnails()
    
    def _ensure_image_displayed(self):
        """确保图片正确显示 - 修复图片加载后不显示的问题"""
        try:
            logger.debug("执行额外的图片显示检查...")
            
            # 检查PDF处理器是否准备就绪
            if not self.pdf_processor or not self.pdf_processor.fitz_document:
                logger.debug("PDF处理器未准备好")
                return
            
            # 强制跳转到第一页（对于图片文件）
            self.pdf_processor.current_page = 0
            logger.debug("强制设置当前页面为第0页")
            
            # 检查虚拟滚动区域是否有页面数据
            if not hasattr(self, 'virtual_scroll') or not self.virtual_scroll.pages_data:
                logger.debug("虚拟滚动区域没有页面数据，重新设置...")
                self._setup_virtual_scroll_data()
                
                # 等待虚拟滚动区域数据设置完成
                QTimer.singleShot(150, self._retry_ensure_image_displayed)
                return
            
            # 强制触发虚拟滚动区域的页面渲染
            if hasattr(self, 'virtual_scroll'):
                # 清除虚拟滚动区域的渲染缓存
                if hasattr(self.virtual_scroll, 'clear_cache'):
                    self.virtual_scroll.clear_cache()
                    logger.debug("已清除虚拟滚动区域缓存")
                
                # 重新更新内容
                self.virtual_scroll.update_content()
                logger.debug("已重新更新虚拟滚动内容")
                
                # 延迟触发渲染以确保布局完成
                QTimer.singleShot(100, self._force_render_current_page)
                QTimer.singleShot(300, self._force_render_current_page)
                
                logger.debug("已触发额外的图片显示检查")
            
        except Exception as e:
            logger.error(f"确保图片显示时出错: {e}")
            logger.error(traceback.format_exc())
    
    def _retry_ensure_image_displayed(self):
        """重试确保图片显示"""
        try:
            logger.debug("重试图片显示检查...")
            if hasattr(self, 'virtual_scroll') and self.virtual_scroll.pages_data:
                self.virtual_scroll.update_content()
                QTimer.singleShot(100, self._force_render_current_page)
                logger.debug("重试图片显示完成")
            else:
                logger.debug("重试时虚拟滚动区域仍未准备好")
        except Exception as e:
            logger.error(f"重试确保图片显示时出错: {e}")
    
    def _force_render_current_page(self):
        """强制渲染当前页面"""
        try:
            logger.debug("强制渲染当前页面...")
            
            if (hasattr(self, 'pdf_processor') and 
                self.pdf_processor.fitz_document and 
                hasattr(self, 'virtual_scroll')):
                
                # 确保当前页面设置为0（图片的第一页）
                self.pdf_processor.current_page = 0
                
                # 确保虚拟滚动区域已准备好
                if hasattr(self.virtual_scroll, '_render_visible_pages'):
                    # 立即渲染可见页面
                    self.virtual_scroll._render_visible_pages()
                    logger.debug("已强制渲染可见页面")
                
                # 直接渲染第一页（对于图片文件通常是第0页）
                page_num = 0
                page_dimensions = self.pdf_processor.get_page_dimensions(page_num)
                
                if page_dimensions:
                    width = int(page_dimensions['width'] * self.pdf_processor.zoom_factor)
                    height = int(page_dimensions['height'] * self.pdf_processor.zoom_factor)
                    
                    logger.debug(f"准备直接渲染页面: {page_num}, 尺寸: {width} x {height}")
                    
                    # 直接渲染页面
                    pixmap = self.pdf_processor.render_page_at(page_num, width, height)
                    
                    if pixmap:
                        logger.debug(f"直接强制渲染页面成功: {pixmap.width()} x {pixmap.height()}")
                        # 调用虚拟滚动区域的页面渲染完成回调
                        self.virtual_scroll.on_page_rendered(page_num, pixmap)
                        
                        # 额外确保虚拟滚动区域更新显示
                        self.virtual_scroll.update()
                        logger.debug("已更新虚拟滚动区域显示")
                    else:
                        logger.debug("直接强制渲染页面失败，返回空pixmap")
                        
                        # 尝试再次渲染
                        QTimer.singleShot(200, self._retry_force_render_current_page)
                else:
                    logger.debug(f"无法获取页面{page_num}的尺寸信息")
            
        except Exception as e:
            logger.error(f"强制渲染当前页面失败: {e}")
            logger.error(traceback.format_exc())
    
    def _retry_force_render_current_page(self):
        """重试强制渲染当前页面"""
        try:
            logger.debug("重试强制渲染当前页面...")
            if (hasattr(self, 'pdf_processor') and 
                self.pdf_processor.fitz_document and 
                hasattr(self, 'virtual_scroll')):
                
                page_num = 0
                page_dimensions = self.pdf_processor.get_page_dimensions(page_num)
                
                if page_dimensions:
                    width = int(page_dimensions['width'] * self.pdf_processor.zoom_factor)
                    height = int(page_dimensions['height'] * self.pdf_processor.zoom_factor)
                    
                    pixmap = self.pdf_processor.render_page_at(page_num, width, height)
                    
                    if pixmap:
                        logger.debug(f"重试渲染页面成功: {pixmap.width()} x {pixmap.height()}")
                        self.virtual_scroll.on_page_rendered(page_num, pixmap)
                    else:
                        logger.debug("重试渲染页面仍然失败")
        except Exception as e:
            logger.error(f"重试强制渲染当前页面失败: {e}")
    
    def update_preview(self):
        """更新PDF预览显示"""
        logger.debug("开始更新预览...")
        if not self.pdf_processor.fitz_document:
            logger.debug("没有PDF文档加载")
            return
        
        try:
            logger.debug("PDF文档已加载")
            if self.pdf_processor.current_file:
                display_filename = self.pdf_processor.current_file
                if (hasattr(self.pdf_processor, 'page_editor') and 
                    self.pdf_processor.page_editor and 
                    self.pdf_processor.page_editor.get_original_filename()):
                    display_filename = self.pdf_processor.page_editor.get_original_filename()
                
                filename = os.path.basename(display_filename)
                has_changes = (hasattr(self.pdf_processor, 'page_editor') and 
                              self.pdf_processor.page_editor and 
                              self.pdf_processor.page_editor.has_unsaved_changes())
                modified_indicator = " ●" if has_changes else ""
                self.setWindowTitle(f"{AppSettings.APP_NAME} - {filename}{modified_indicator}")
            
            total_pages = self.pdf_processor.get_total_pages()
            self.page_spinbox.setMaximum(total_pages)
            # 更新工具栏的总页码标签
            if hasattr(self, 'toolbar_total_pages_label'):
                self.toolbar_total_pages_label.setText(f"/ {total_pages}")
            
            if self.show_thumbnails:
                self.view_controller.load_thumbnails()
            
            logger.debug("使用虚拟滚动模式")
            self._setup_virtual_scroll_data()
            self.virtual_scroll.update_content()
            
            logger.debug("预览更新完成")
        except Exception as e:
            logger.error(f"更新预览时出错: {e}")
            logger.error(traceback.format_exc())
    
    def _setup_virtual_scroll_data(self):
        """设置虚拟滚动数据"""
        logger.debug("开始设置虚拟滚动数据...")
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            logger.debug("PDF处理器未准备好")
            return
            
        try:
            total_pages = self.pdf_processor.get_total_pages()
            logger.debug(f"总页数: {total_pages}")
            
            pages_data = []
            for page_num in range(total_pages):
                dimensions = self.pdf_processor.get_page_dimensions(page_num)
                if dimensions:
                    # 存储缩放后的尺寸（已经应用了A4缩放），不乘zoom_factor
                    width = int(dimensions['width'])
                    height = int(dimensions['height'])
                else:
                    width = 800
                    height = 1100

                pages_data.append({
                    'page_num': page_num,
                    'width': width,
                    'height': height,
                    'zoom_factor': self.pdf_processor.zoom_factor
                })
            
            logger.debug(f"准备设置{len(pages_data)}页数据到虚拟滚动区域")
            self.virtual_scroll.set_pages_data(pages_data)
            
            if hasattr(self.virtual_scroll, 'page_visible'):
                try:
                    self.virtual_scroll.page_visible.connect(self._on_page_visible)
                    logger.debug("虚拟滚动信号连接成功")
                except Exception as signal_error:
                    logger.debug(f"信号连接失败（可能已连接）: {signal_error}")
                
            logger.debug("虚拟滚动数据设置完成")
        except Exception as e:
            logger.error(f"设置虚拟滚动数据失败: {e}")
            logger.error(traceback.format_exc())
    
    def convert_pdf_to_images(self):
        """PDF转图片功能"""
        if not self.pdf_processor.fitz_document:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return

        from app.ui.convert_to_images_dialog import ConvertToImagesDialog
        dialog = ConvertToImagesDialog(self, self.pdf_processor)
        dialog.exec_()
    
    # 代理方法 - 将调用转发给相应的管理器
    def open_file(self):
        return self.file_manager.open_file()
    
    def open_multiple_images(self):
        """打开多张图片"""
        return self.file_manager.open_multiple_images()
    
    def open_image_directory(self):
        """打开图片目录"""
        return self.file_manager.open_image_directory()

    def save_file(self):
        return self.file_manager.save_file()

    def save_as_file(self):
        return self.file_manager.save_as_file()

    def encrypt_save_file(self):
        return self.file_manager.encrypt_save_file()

    def encrypt_save_as_file(self):
        return self.file_manager.encrypt_save_as_file()

    def save_changes(self):
        return self.file_manager.save_changes()
        
    def discard_changes(self):
        return self.file_manager.discard_changes()
        
    def import_images(self):
        return self.file_manager.import_images()
        
    def open_images_from_directory(self):
        """从目录打开图片文件"""
        return self.file_manager.open_images_from_directory()
    
    def show_context_menu_at(self, position):
        """在指定位置显示右键菜单
        
        Args:
            position: 鼠标位置 (QPoint)
        """
        if hasattr(self, 'context_menu_manager'):
            # 创建一个模拟的鼠标事件
            global_pos = self.mapToGlobal(position)
            event = QContextMenuEvent(
                QContextMenuEvent.Mouse,
                position,
                global_pos
            )
            self.context_menu_manager.show_context_menu(event)
            logger.debug(f"在位置 {position} 显示右键菜单")
