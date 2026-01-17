"""
OCR可搜索PDF管理器
用于创建临时的可搜索PDF文件，以支持PyMuPDF的原生搜索功能
"""

import os
import tempfile
import fitz
import traceback
from typing import Dict, Optional, Tuple
import threading
import time

from app.utils.logger import get_logger
from app.core.ocr.ocr_searchable_pdf import OCRSearchablePDF

logger = get_logger('ocr_searchable_manager')


class OCRSearchableManager:
    """
    OCR可搜索PDF管理器
    管理临时可搜索PDF的创建和生命周期
    """
    
    def __init__(self, ocr_plugin_manager=None, ocr_config_manager=None):
        self.ocr_plugin_manager = ocr_plugin_manager
        self.ocr_config_manager = ocr_config_manager
        self.temp_searchable_pdf_path = None
        self.original_pdf_path = None
        self.temp_dir = tempfile.gettempdir()
        self.lock = threading.Lock()
        
        # 存储页面OCR结果，用于增量更新
        self.page_ocr_results = {}  # {page_num: ocr_result}
        
    def create_temp_searchable_pdf(self, original_pdf_path: str, progress_callback=None) -> Tuple[bool, str]:
        """
        创建临时可搜索PDF
        
        Args:
            original_pdf_path: 原始PDF路径
            progress_callback: 进度回调函数
            
        Returns:
            (success, message) 元组
        """
        with self.lock:
            try:
                self.original_pdf_path = original_pdf_path
                
                # 生成临时文件路径
                temp_filename = f"temp_searchable_{int(time.time())}_{os.path.basename(original_pdf_path)}"
                self.temp_searchable_pdf_path = os.path.join(self.temp_dir, temp_filename)
                
                logger.info(f"开始创建临时可搜索PDF: {self.temp_searchable_pdf_path}")
                
                # 使用OCRSearchablePDF类创建可搜索PDF
                processor = OCRSearchablePDF(
                    ocr_plugin_manager=self.ocr_plugin_manager,
                    ocr_config_manager=self.ocr_config_manager
                )
                
                success = processor.pdf_to_searchable_pdf(
                    pdf_path=original_pdf_path,
                    output_path=self.temp_searchable_pdf_path,
                    show_text_boxes=False
                )
                
                if success:
                    logger.info(f"临时可搜索PDF创建成功: {self.temp_searchable_pdf_path}")
                    if progress_callback:
                        progress_callback(100, "临时可搜索PDF创建完成")
                    return True, f"临时可搜索PDF创建成功: {self.temp_searchable_pdf_path}"
                else:
                    logger.error("创建临时可搜索PDF失败")
                    if progress_callback:
                        progress_callback(0, "创建临时可搜索PDF失败")
                    return False, "创建临时可搜索PDF失败"
                    
            except Exception as e:
                logger.error(f"创建临时可搜索PDF时发生错误: {e}")
                logger.exception(e)
                if progress_callback:
                    progress_callback(0, f"创建失败: {str(e)}")
                return False, f"创建临时可搜索PDF失败: {str(e)}"
    
    def get_searchable_pdf_path(self) -> Optional[str]:
        """
        获取可搜索PDF的路径
        
        Returns:
            可搜索PDF的路径，如果不存在则返回None
        """
        if self.temp_searchable_pdf_path and os.path.exists(self.temp_searchable_pdf_path):
            return self.temp_searchable_pdf_path
        return None
    
    def get_or_create_searchable_pdf(self, original_pdf_path: str, progress_callback=None) -> Tuple[bool, str]:
        """
        获取或创建临时可搜索PDF
        
        Args:
            original_pdf_path: 原始PDF路径
            progress_callback: 进度回调函数
            
        Returns:
            (success, message) 元组
        """
        # 检查是否已有可用的临时可搜索PDF
        if self.temp_searchable_pdf_path and os.path.exists(self.temp_searchable_pdf_path):
            # 检查是否是同一原始文件
            if self.original_pdf_path == original_pdf_path:
                logger.debug(f"使用已存在的临时可搜索PDF: {self.temp_searchable_pdf_path}")
                if progress_callback:
                    progress_callback(100, "使用已存在的可搜索PDF")
                return True, f"已存在的可搜索PDF: {self.temp_searchable_pdf_path}"
            else:
                # 原始文件不同，需要创建新的
                logger.info("原始文件已改变，需要创建新的可搜索PDF")
                self.cleanup_temp_file()  # 清理旧的临时文件
        
        # 创建新的临时可搜索PDF
        return self.create_temp_searchable_pdf(original_pdf_path, progress_callback)
    
    def cleanup_temp_file(self):
        """
        清理临时文件
        """
        with self.lock:
            if self.temp_searchable_pdf_path and os.path.exists(self.temp_searchable_pdf_path):
                try:
                    os.remove(self.temp_searchable_pdf_path)
                    logger.info(f"已清理临时可搜索PDF: {self.temp_searchable_pdf_path}")
                except Exception as e:
                    logger.error(f"清理临时文件失败: {e}")
                finally:
                    self.temp_searchable_pdf_path = None
                    self.original_pdf_path = None
    
    def __del__(self):
        """
        析构函数，确保临时文件被清理
        """
        self.cleanup_temp_file()


class OCRSearchablePDFHandler:
    """
    OCR可搜索PDF处理器
    用于在OCR处理后创建临时可搜索PDF以支持搜索功能
    """
    
    def __init__(self, pdf_processor, ocr_plugin_manager=None, ocr_config_manager=None):
        self.pdf_processor = pdf_processor
        self.ocr_searchable_manager = OCRSearchableManager(
            ocr_plugin_manager=ocr_plugin_manager,
            ocr_config_manager=ocr_config_manager
        )
        self.is_using_searchable_pdf = False  # 标记当前是否在使用可搜索PDF
        self.original_document_backup = None  # 备份原始文档引用
    
    def enable_searchable_ocr_feature(self, progress_callback=None):
        """
        启用可搜索OCR功能，创建临时可搜索PDF
        
        Args:
            progress_callback: 进度回调函数
            
        Returns:
            (success, message) 元组
        """
        # 检查当前文档是否存在
        if not self.pdf_processor.fitz_document:
            return False, "没有打开的PDF文档"
        
        # 如果当前文档是临时生成的（例如导入图片后），我们直接基于当前文档创建可搜索PDF
        if not self.pdf_processor.current_file or not os.path.exists(self.pdf_processor.current_file):
            # 创建临时可搜索PDF直接从当前文档
            success, message = self._create_searchable_pdf_from_current_document(progress_callback)
            if success:
                logger.info("已启用可搜索OCR功能，基于当前文档创建可搜索PDF")
                return True, "已启用可搜索OCR功能，现在可以搜索OCR识别的文本"
            else:
                return False, message
        else:
            # 如果有真实文件路径，使用原有逻辑
            success, message = self.ocr_searchable_manager.get_or_create_searchable_pdf(
                self.pdf_processor.current_file,
                progress_callback
            )
            
            if success:
                searchable_pdf_path = self.ocr_searchable_manager.get_searchable_pdf_path()
                if searchable_pdf_path:
                    # 保存当前文档的备份引用
                    self.original_document_backup = self.pdf_processor.fitz_document
                    # 用可搜索PDF替换当前文档
                    if self.pdf_processor.fitz_document:
                        self.pdf_processor.fitz_document.close()
                    
                    # 打开可搜索PDF
                    self.pdf_processor.fitz_document = fitz.open(searchable_pdf_path)
                    self.is_using_searchable_pdf = True
                    
                    logger.info(f"已切换到可搜索PDF: {searchable_pdf_path}")
                    return True, "已启用可搜索OCR功能，现在可以搜索OCR识别的文本"
                else:
                    return False, "无法获取可搜索PDF路径"
            else:
                return False, message
    
    def _create_searchable_pdf_from_current_document(self, progress_callback=None):
        """
        从当前文档创建可搜索PDF（用于处理导入图片等临时文档的情况）
        
        Args:
            progress_callback: 进度回调函数
            
        Returns:
            (success, message) 元组
        """
        try:
            if not self.pdf_processor.fitz_document:
                return False, "没有打开的PDF文档"
            
            # 保存当前文档的备份引用
            self.original_document_backup = self.pdf_processor.fitz_document
            
            # 获取当前文档的总页数
            total_pages = len(self.pdf_processor.fitz_document)
            
            if progress_callback:
                progress_callback(10, "正在准备创建可搜索PDF...")
            
            # 创建新的可搜索PDF文档
            output_doc = fitz.open()
            
            # 遍历所有页面
            for i in range(total_pages):
                if progress_callback:
                    progress = 10 + int((i / total_pages) * 80)  # 10%-90%
                    progress_callback(progress, f"正在处理第 {i+1}/{total_pages} 页...")
                
                page = self.pdf_processor.fitz_document[i]
                
                # 获取页面图像
                matrix = fitz.Matrix(2.0, 2.0)  # 2倍缩放
                pix = page.get_pixmap(matrix=matrix)
                img_data = pix.tobytes("png")
                
                # 创建新页面
                new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(new_page.rect, stream=img_data)
                
                # 检查是否有对应的OCR结果，如果有则添加文本层
                if i in self.ocr_searchable_manager.page_ocr_results:
                    ocr_result = self.ocr_searchable_manager.page_ocr_results[i]
                    if ocr_result and ocr_result.is_success():
                        # 计算缩放比例
                        scale_x = new_page.rect.width / pix.width
                        scale_y = new_page.rect.height / pix.height
                        
                        # 使用OCRSearchablePDF的add_text_layer方法
                        processor = OCRSearchablePDF(
                            ocr_plugin_manager=self.ocr_searchable_manager.ocr_plugin_manager,
                            ocr_config_manager=self.ocr_searchable_manager.ocr_config_manager
                        )
                        processor.add_text_layer(new_page, ocr_result.data, scale_x, scale_y, show_text_boxes=False)
            
            if progress_callback:
                progress_callback(95, "正在保存可搜索PDF...")
            
            # 生成临时文件路径
            temp_dir = tempfile.gettempdir()
            temp_filename = f"temp_searchable_from_current_{int(time.time())}_{total_pages}pages.pdf"
            temp_searchable_pdf_path = os.path.join(temp_dir, temp_filename)
            
            # 保存输出PDF
            output_doc.save(temp_searchable_pdf_path, garbage=4, deflate=True, clean=True)
            output_doc.close()
            
            # 更新OCRSearchableManager的临时文件路径
            self.ocr_searchable_manager.temp_searchable_pdf_path = temp_searchable_pdf_path
            
            # 关闭当前文档
            if self.pdf_processor.fitz_document:
                self.pdf_processor.fitz_document.close()
            
            # 打开新的可搜索PDF
            self.pdf_processor.fitz_document = fitz.open(temp_searchable_pdf_path)
            self.is_using_searchable_pdf = True
            
            # 清除渲染缓存并触发重新渲染
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()
            
            if progress_callback:
                progress_callback(100, "可搜索PDF创建完成")
            
            logger.info(f"从当前文档创建了可搜索PDF: {temp_searchable_pdf_path}")
            return True, f"已从当前文档创建可搜索PDF: {temp_searchable_pdf_path}"
            
        except Exception as e:
            logger.error(f"从当前文档创建可搜索PDF时出错: {e}")
            logger.error(traceback.format_exc())
            return False, f"从当前文档创建可搜索PDF失败: {str(e)}"

    def disable_searchable_ocr_feature(self):
        """
        禁用可搜索OCR功能，恢复原始PDF
        """
        if self.is_using_searchable_pdf and self.original_document_backup:
            # 关闭当前可搜索PDF文档
            if self.pdf_processor.fitz_document:
                self.pdf_processor.fitz_document.close()
            
            # 恢复原始文档
            self.pdf_processor.fitz_document = self.original_document_backup
            self.original_document_backup = None
            self.is_using_searchable_pdf = False
            
            logger.info("已恢复原始PDF文档")
    
    def handle_page_ocr_completed(self, page_num, ocr_result):
        """
        处理单个页面的OCR完成事件
        """
        # 将页面OCR结果存储到管理器中
        self.ocr_searchable_manager.page_ocr_results[page_num] = ocr_result
        
        # 立即为当前页面创建或更新可搜索PDF，使当前页面立即变成可搜索的
        success, message = self._create_or_update_searchable_pdf_for_page(page_num, ocr_result)
        if success:
            logger.info(f"第{page_num+1}页OCR完成，已更新为可搜索PDF")
        else:
            logger.error(f"更新第{page_num+1}页为可搜索PDF失败: {message}")
            # 作为备选方案，尝试启用完整的可搜索OCR功能
            if not self.is_using_searchable_pdf:
                self.enable_searchable_ocr_feature()
        
    def handle_batch_ocr_completed(self, ocr_results_dict, progress_callback=None):
        """
        批量处理多个页面的OCR完成事件，一次性生成完整的可搜索PDF
        
        Args:
            ocr_results_dict: 包含所有页面OCR结果的字典 {page_num: ocr_result}
            progress_callback: 进度回调函数
        
        Returns:
            (success, message) 元组
        """
        try:
            # 检查当前文档是否有效
            if not self.pdf_processor.fitz_document:
                logger.error("没有打开的PDF文档")
                return False, "没有打开的PDF文档"
            
            # 更新管理器中的所有OCR结果
            self.ocr_searchable_manager.page_ocr_results.update(ocr_results_dict)
            
            # 使用当前文档作为基础，而不是原始文件
            original_doc = self.pdf_processor.fitz_document
            total_pages = len(original_doc)
            
            if progress_callback:
                progress_callback(10, "正在创建可搜索PDF...")
            
            # 创建新的PDF文档
            output_doc = fitz.open()
            
            # 遍历所有页面
            for i in range(total_pages):
                if progress_callback:
                    progress = 10 + int((i / total_pages) * 80)  # 10%-90%
                    progress_callback(progress, f"正在处理第 {i+1}/{total_pages} 页...")
                
                page = original_doc[i]
                
                # 获取页面图像
                matrix = fitz.Matrix(2.0, 2.0)  # 2倍缩放
                pix = page.get_pixmap(matrix=matrix)
                img_data = pix.tobytes("png")
                
                # 创建新页面
                new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(new_page.rect, stream=img_data)
                
                # 检查是否有对应的OCR结果
                if i in ocr_results_dict:
                    ocr_result = ocr_results_dict[i]
                    if ocr_result and ocr_result.is_success():
                        # 计算缩放比例
                        scale_x = new_page.rect.width / pix.width
                        scale_y = new_page.rect.height / pix.height
                        
                        # 使用OCRSearchablePDF的add_text_layer方法
                        processor = OCRSearchablePDF(
                            ocr_plugin_manager=self.ocr_searchable_manager.ocr_plugin_manager,
                            ocr_config_manager=self.ocr_searchable_manager.ocr_config_manager
                        )
                        processor.add_text_layer(new_page, ocr_result.data, scale_x, scale_y, show_text_boxes=False)
            
            if progress_callback:
                progress_callback(95, "正在保存可搜索PDF...")
            
            # 生成临时文件路径
            temp_dir = tempfile.gettempdir()
            # 使用时间戳和页面数作为临时文件名，避免依赖原始文件名
            temp_filename = f"temp_searchable_batch_{int(time.time())}_{total_pages}pages.pdf"
            temp_searchable_pdf_path = os.path.join(temp_dir, temp_filename)
            
            # 保存输出PDF
            output_doc.save(temp_searchable_pdf_path, garbage=4, deflate=True, clean=True)
            output_doc.close()
            
            # 更新OCRSearchableManager的临时文件路径
            self.ocr_searchable_manager.temp_searchable_pdf_path = temp_searchable_pdf_path
            # 不再设置original_pdf_path，因为当前文档可能是动态生成的
            
            # 切换到可搜索PDF
            if self.is_using_searchable_pdf and self.pdf_processor.fitz_document:
                self.pdf_processor.fitz_document.close()
            
            self.pdf_processor.fitz_document = fitz.open(temp_searchable_pdf_path)
            self.is_using_searchable_pdf = True
            
            # 清除渲染缓存并触发重新渲染
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()
            
            if progress_callback:
                progress_callback(100, "可搜索PDF创建完成")
            
            logger.info(f"批量OCR完成后创建了可搜索PDF: {temp_searchable_pdf_path}")
            return True, f"批量OCR完成，已创建可搜索PDF: {temp_searchable_pdf_path}"
            
        except Exception as e:
            logger.error(f"批量创建可搜索PDF时出错: {e}")
            logger.error(traceback.format_exc())
            return False, f"批量创建可搜索PDF失败: {str(e)}"
    
    def _create_or_update_searchable_pdf_for_page(self, page_num, ocr_result):
        """
        为单个页面创建或更新可搜索PDF（保留原有方法供其他用途使用）
        现在会使用所有已有的OCR结果来创建完整的可搜索PDF
        """
        try:
            # 为当前页面创建可搜索PDF
            # 检查当前文档是否有效
            if not self.pdf_processor.fitz_document:
                logger.error("没有打开的PDF文档")
                return False, "没有打开的PDF文档"
            
            # 使用当前文档作为基础，而不是原始文件
            original_doc = self.pdf_processor.fitz_document
            total_pages = len(original_doc)
            
            # 创建新的PDF文档
            output_doc = fitz.open()
            
            for i in range(total_pages):
                page = original_doc[i]
                
                # 获取页面图像
                matrix = fitz.Matrix(2.0, 2.0)  # 2倍缩放
                pix = page.get_pixmap(matrix=matrix)
                img_data = pix.tobytes("png")
                
                # 创建新页面
                new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(new_page.rect, stream=img_data)
                
                # 检查是否有该页面的OCR结果，如果有则添加文本层
                if i in self.ocr_searchable_manager.page_ocr_results:
                    page_ocr_result = self.ocr_searchable_manager.page_ocr_results[i]
                    if page_ocr_result and page_ocr_result.is_success():
                        # 计算缩放比例
                        scale_x = new_page.rect.width / pix.width
                        scale_y = new_page.rect.height / pix.height
                        
                        # 使用OCRSearchablePDF的add_text_layer方法
                        processor = OCRSearchablePDF(
                            ocr_plugin_manager=self.ocr_searchable_manager.ocr_plugin_manager,
                            ocr_config_manager=self.ocr_searchable_manager.ocr_config_manager
                        )
                        processor.add_text_layer(new_page, page_ocr_result.data, scale_x, scale_y, show_text_boxes=False)
                
                # 特别处理当前页面：如果OCR结果不同，则使用新的OCR结果
                if i == page_num and ocr_result and ocr_result.is_success() and ocr_result != self.ocr_searchable_manager.page_ocr_results.get(i):
                    # 重新添加当前页面的OCR结果，覆盖可能已存在的结果
                    scale_x = new_page.rect.width / pix.width
                    scale_y = new_page.rect.height / pix.height
                    
                    
                    processor = OCRSearchablePDF(
                        ocr_plugin_manager=self.ocr_searchable_manager.ocr_plugin_manager,
                        ocr_config_manager=self.ocr_searchable_manager.ocr_config_manager
                    )
                    processor.add_text_layer(new_page, ocr_result.data, scale_x, scale_y, show_text_boxes=False)
            
            # 生成临时文件路径
            temp_dir = tempfile.gettempdir()
            temp_filename = f"temp_searchable_page_{int(time.time())}_{page_num}.pdf"
            temp_searchable_pdf_path = os.path.join(temp_dir, temp_filename)
            
            # 保存输出PDF
            output_doc.save(temp_searchable_pdf_path, garbage=4, deflate=True, clean=True)
            output_doc.close()
            
            # 更新OCRSearchableManager的临时文件路径
            self.ocr_searchable_manager.temp_searchable_pdf_path = temp_searchable_pdf_path
            # 不再设置original_pdf_path，因为当前文档可能是动态生成的
            
            # 切换到可搜索PDF
            if self.is_using_searchable_pdf and self.pdf_processor.fitz_document:
                self.pdf_processor.fitz_document.close()
            
            self.pdf_processor.fitz_document = fitz.open(temp_searchable_pdf_path)
            self.is_using_searchable_pdf = True
            
            # 清除渲染缓存并触发重新渲染
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()
            
            logger.info(f"为第{page_num+1}页创建了可搜索PDF，共处理了{total_pages}页")
            return True, f"第{page_num+1}页OCR完成，已创建可搜索PDF"
            
        except Exception as e:
            logger.error(f"创建页面可搜索PDF时出错: {e}")
            logger.error(traceback.format_exc())
            return False, f"创建页面可搜索PDF失败: {str(e)}"
    
    def _update_existing_searchable_pdf_page(self, page_num, ocr_result):
        """
        更新现有可搜索PDF中的指定页面
        现在会使用所有已有的OCR结果来更新整个文档
        """
        try:
            current_searchable_path = self.ocr_searchable_manager.get_searchable_pdf_path()
            if not current_searchable_path:
                logger.error("没有找到现有的可搜索PDF")
                return False
            
            # 使用当前文档而不是原来可能已不存在的原始文件
            if not self.pdf_processor.fitz_document:
                logger.error("没有当前文档可用来更新")
                return False
            
            original_doc = self.pdf_processor.fitz_document
            total_pages = len(original_doc)
            
            # 创建新的可搜索PDF，使用所有页面和所有已有的OCR结果
            output_doc = fitz.open()
            
            for i in range(total_pages):
                original_page = original_doc[i]
                
                # 获取页面图像
                matrix = fitz.Matrix(2.0, 2.0)  # 2倍缩放
                pix = original_page.get_pixmap(matrix=matrix)
                img_data = pix.tobytes("png")
                
                # 创建新页面
                new_page = output_doc.new_page(width=original_page.rect.width, height=original_page.rect.height)
                new_page.insert_image(new_page.rect, stream=img_data)
                
                # 检查是否有该页面的OCR结果，如果有则添加文本层
                if i in self.ocr_searchable_manager.page_ocr_results:
                    page_ocr_result = self.ocr_searchable_manager.page_ocr_results[i]
                    if page_ocr_result and page_ocr_result.is_success():
                        # 计算缩放比例
                        scale_x = new_page.rect.width / pix.width
                        scale_y = new_page.rect.height / pix.height
                        
                        # 使用OCRSearchablePDF的add_text_layer方法
                        processor = OCRSearchablePDF(
                            ocr_plugin_manager=self.ocr_searchable_manager.ocr_plugin_manager,
                            ocr_config_manager=self.ocr_searchable_manager.ocr_config_manager
                        )
                        processor.add_text_layer(new_page, page_ocr_result.data, scale_x, scale_y, show_text_boxes=False)
                
                # 特别处理当前页面：如果OCR结果不同，则使用新的OCR结果
                if i == page_num and ocr_result and ocr_result.is_success() and ocr_result != self.ocr_searchable_manager.page_ocr_results.get(i):
                    # 重新添加当前页面的OCR结果，覆盖可能已存在的结果
                    scale_x = new_page.rect.width / pix.width
                    scale_y = new_page.rect.height / pix.height
                    
                    processor = OCRSearchablePDF(
                        ocr_plugin_manager=self.ocr_searchable_manager.ocr_plugin_manager,
                        ocr_config_manager=self.ocr_searchable_manager.ocr_config_manager
                    )
                    processor.add_text_layer(new_page, ocr_result.data, scale_x, scale_y, show_text_boxes=False)
            
            # 保存更新后的PDF
            updated_temp_filename = f"temp_searchable_updated_{int(time.time())}.pdf"
            updated_searchable_pdf_path = os.path.join(tempfile.gettempdir(), updated_temp_filename)
            
            output_doc.save(updated_searchable_pdf_path, garbage=4, deflate=True, clean=True)
            output_doc.close()
            
            # 更新临时文件路径
            old_path = self.ocr_searchable_manager.temp_searchable_pdf_path
            self.ocr_searchable_manager.temp_searchable_pdf_path = updated_searchable_pdf_path
            
            # 删除旧的临时文件
            try:
                if old_path and os.path.exists(old_path):
                    os.remove(old_path)
            except Exception as e:
                logger.warning(f"删除旧临时文件失败: {e}")
            
            # 如果当前正在使用可搜索PDF，重新打开
            if self.is_using_searchable_pdf:
                self.pdf_processor.fitz_document.close()
                self.pdf_processor.fitz_document = fitz.open(updated_searchable_pdf_path)
            
            # 清除渲染缓存并触发重新渲染
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()
            
            logger.info(f"已更新第{page_num+1}页的可搜索PDF，共处理了{total_pages}页")
            return True
            
        except Exception as e:
            logger.error(f"更新页面可搜索PDF时出错: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def get_current_document_path(self) -> str:
        """
        获取当前文档的路径（如果是可搜索PDF则返回可搜索PDF路径，否则返回原始路径）
        """
        if self.is_using_searchable_pdf:
            return self.ocr_searchable_manager.get_searchable_pdf_path() or self.pdf_processor.current_file
        else:
            return self.pdf_processor.current_file
    
    def cleanup(self):
        """
        清理资源
        """
        self.disable_searchable_ocr_feature()
        self.ocr_searchable_manager.cleanup_temp_file()