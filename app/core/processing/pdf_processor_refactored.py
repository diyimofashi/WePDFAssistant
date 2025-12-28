"""PDF处理核心功能 - 极灵PDF - 重构版"""

import os
import time
import PyPDF2
from PyPDF2.errors import PdfReadError, PdfReadWarning
import fitz  # PyMuPDF - 用于PDF页面渲染
import sys
import gc  # 导入垃圾回收模块

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('pdf_processor')

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

# 导入拆分的功能模块
from .pdf_loader import PDFLoader
from .pdf_renderer import PDFRenderer
from .pdf_navigation import PDFNavigation
from .pdf_search import PDFSearch
from .pdf_operations import PDFOperations
from .pdf_conversion import PDFConversion
from .pdf_history_manager import PDFHistoryManager

# 导入新的异步加载器和缓存管理器
from .async_loader import AsyncPDFLoader, AsyncThumbnailLoader, AsyncPageRenderer
from ..performance.cache_manager import RenderCache, DiskCache


class PDFProcessor(QObject, PDFLoader, PDFRenderer, PDFNavigation, PDFSearch, PDFOperations, PDFConversion, PDFHistoryManager):
    """PDF处理器 - 提供稳定可靠的PDF文件处理和渲染功能 - 重构版"""
    
    # 信号定义
    loading_progress = pyqtSignal(int, str)  # 加载进度
    loading_finished = pyqtSignal(bool, str)  # 加载完成
    thumbnail_ready = pyqtSignal(int, object)  # 缩略图就绪
    page_rendered = pyqtSignal(int, object)  # 页面渲染完成
    operation_history_changed = pyqtSignal()  # 操作历史记录发生变化
    
    def __init__(self):
        super().__init__()
        # 初始化所有功能模块
        PDFLoader.__init__(self)
        PDFRenderer.__init__(self)
        PDFNavigation.__init__(self)
        PDFSearch.__init__(self)
        PDFOperations.__init__(self)
        PDFConversion.__init__(self)
        PDFHistoryManager.__init__(self)
        
        self.current_file = None
        self.total_pages = 0  # 总页数
        self.file_size = 0  # 文件大小（字节）
        self.load_time = 0  # 加载时间（秒）
        self.last_error = ""  # 最后错误信息
        
        # 异步加载器
        self.async_loader = None
        
        # 页面编辑器
        self.page_editor = None
        
        # OCR结果存储
        self.ocr_results = {}
        
        # 多图片文档相关属性
        self.multi_image_paths = []  # 存储多图片文档的原始路径
        self.multi_image_source_dir = None  # 存储源目录路径
        self.is_new_document = False  # 标记是否为新建文档

    def __del__(self):
        """析构函数，确保资源被释放 - 防止Graftmaps错误"""
        try:
            # 安全地清理资源，避免访问已删除的属性
            if hasattr(self, 'fitz_document') and self.fitz_document:
                try:
                    self.fitz_document.close()
                except:
                    pass
                self.fitz_document = None
        except Exception:
            # 忽略所有析构时的异常，防止打印AttributeError
            pass

    def close_document(self):
        """关闭当前文档，释放资源 - 幂等操作"""
        try:
            # 安全关闭fitz_document
            if hasattr(self, 'fitz_document') and self.fitz_document:
                try:
                    self.fitz_document.close()
                except:
                    pass
                self.fitz_document = None
            
            # 清理其他资源
            self.pdf_document = None
            self.current_file = None
            self.current_page = 0
            logger.debug("文档已关闭")
            
            # 强制垃圾回收，避免解释器退出时fitz.Document.__del__报错
            gc.collect()
        except Exception as e:
            logger.error(f"关闭文档时出错: {e}")

    def force_cleanup(self):
        """强制清理资源，防止解释器退出时出现Graftmaps错误"""
        try:
            # 先调用正常的关闭流程
            self.close_document()
            
            # 额外确保fitz_document被置为None
            if hasattr(self, 'fitz_document'):
                self.fitz_document = None
            
            # 多次垃圾回收，确保对象被销毁
            for _ in range(3):
                gc.collect()
                
        except Exception as e:
            # 静默处理，避免在清理时崩溃
            pass