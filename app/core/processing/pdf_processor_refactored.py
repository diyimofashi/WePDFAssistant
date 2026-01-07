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

    def __setattr__(self, name, value):
        """拦截属性设置，确保 fitz_document 的变更同步到所有模块"""
        if name == 'fitz_document':
            logger.info(f"[__setattr__] 拦截到 fitz_document 的设置: {type(value) if value else None}, id: {id(value) if value else None}")
            # 先设置属性
            object.__setattr__(self, name, value)
            # 同步到所有子模块
            if hasattr(self, '_sync_document_references'):
                logger.info("[__setattr__] 开始同步文档引用到所有模块...")
                self._sync_document_references()
                logger.info("[__setattr__] 文档引用同步完成")
        else:
            object.__setattr__(self, name, value)
    
    def __init__(self):
        super().__init__()

        # 唯一的共享文档对象
        self.fitz_document = None  # PyMuPDF文档对象
        self.pdf_document = None  # PyPDF2文档对象
        self.current_file = None
        self.current_page = 0  # 当前页码（从0开始）
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

        # 初始化所有功能模块
        PDFLoader.__init__(self)
        PDFRenderer.__init__(self)
        PDFNavigation.__init__(self)
        PDFSearch.__init__(self)
        PDFOperations.__init__(self)
        PDFConversion.__init__(self)
        PDFHistoryManager.__init__(self)

        # 关键：所有模块的 fitz_document 指向同一个对象
        # 由于多重继承，每个模块初始化时会创建自己的 fitz_document
        # 我们需要将它们全部替换为 PDFProcessor 的共享 fitz_document
        self._sync_document_references()

    def _sync_document_references(self):
        """同步所有模块的文档引用到 PDFProcessor 的共享 fitz_document"""
        # 由于 Python 的多重继承，每个模块都有独立的 fitz_document
        # 我们通过 __dict__ 直接访问实例属性并替换它们
        processor_doc = self.__dict__.get('fitz_document')
        processor_pdf = self.__dict__.get('pdf_document')

        logger.debug(f"[_sync_document_references] PDFProcessor.fitz_document id: {id(processor_doc) if processor_doc else None}")
        logger.debug(f"[_sync_document_references] PDFProcessor.pdf_document id: {id(processor_pdf) if processor_pdf else None}")

        # 查找所有子模块的文档引用并替换
        # 子模块通过 Python 的名称改写规则存储私有属性
        module_classes = [
            PDFLoader, PDFRenderer, PDFNavigation,
            PDFSearch, PDFOperations, PDFConversion
        ]

        for cls in module_classes:
            # 查找名称改写后的属性名（_ClassName__fitz_document）
            fitz_key = f'_{cls.__name__}__fitz_document'
            pdf_key = f'_{cls.__name__}__pdf_document'

            if fitz_key in self.__dict__:
                old_doc = self.__dict__[fitz_key]
                self.__dict__[fitz_key] = processor_doc
                logger.debug(f"已同步 {cls.__name__}.fitz_document: {id(old_doc) if old_doc else None} -> {id(processor_doc) if processor_doc else None}")

            if pdf_key in self.__dict__:
                old_pdf = self.__dict__[pdf_key]
                self.__dict__[pdf_key] = processor_pdf
                logger.debug(f"已同步 {cls.__name__}.pdf_document: {id(old_pdf) if old_pdf else None} -> {id(processor_pdf) if processor_pdf else None}")

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