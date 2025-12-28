"""PDF处理核心功能 - 极灵PDF"""

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

# 导入新的异步加载器和缓存管理器
from .async_loader import AsyncPDFLoader, AsyncThumbnailLoader, AsyncPageRenderer
from ..performance.cache_manager import RenderCache, DiskCache

# 导入操作历史记录管理器
from ..editing.operation_history import OperationHistory, OperationType, OperationFactory

class PDFProcessor(QObject):
    """PDF处理器 - 提供稳定可靠的PDF文件处理和渲染功能"""
    
    # 信号定义
    loading_progress = pyqtSignal(int, str)  # 加载进度
    loading_finished = pyqtSignal(bool, str)  # 加载完成
    thumbnail_ready = pyqtSignal(int, object)  # 缩略图就绪
    page_rendered = pyqtSignal(int, object)  # 页面渲染完成
    operation_history_changed = pyqtSignal()  # 操作历史记录发生变化
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.pdf_document = None
        self.fitz_document = None  # PyMuPDF文档对象
        self.total_pages = 0  # 总页数
        self.current_page = 0  # 当前页码（从0开始）
        self.zoom_factor = 2.0  # 缩放因子（设置为2.0，即200%作为新的100%基准）
        self.base_zoom = 2.0  # 基准缩放因子（用户看到的100%实际是200%）
        self.file_size = 0  # 文件大小（字节）
        self.load_time = 0  # 加载时间（秒）
        self.last_error = ""  # 最后错误信息
        
        # 连续浏览模式属性
        self.continuous_mode = True  # 是否启用连续浏览模式
        self.pages_per_view = 3  # 连续模式下每次显示的页面数
        self.page_spacing = 20  # 页面间距（像素）
        
        # 异步加载器
        self.async_loader = None
        self.thumbnail_loader = None
        self.page_renderer = None
        
        # 新的缓存系统
        self.render_cache = RenderCache(max_memory_mb=200, max_items=50)
        self.disk_cache = DiskCache(cache_dir="cache", max_size_mb=500)
        
        # 向后兼容的简单缓存
        self.simple_cache = {}
        self.cache_max_size = 10
        
        # 页面编辑器
        self.page_editor = None
        
        # OCR结果存储
        self.ocr_results = {}
        
        # 操作历史记录管理器
        self.operation_history = OperationHistory(max_history_size=100)
        # 连接操作历史记录变化信号
        self.operation_history.history_changed.connect(self.operation_history_changed.emit)

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

    def open_pdf(self, file_path, async_mode=True, password=None):
        """打开PDF文件或图片文件 - 支持异步和同步模式"""
        # 检查是否为图片文件
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.ico'}
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in image_extensions:
            # 如果是图片文件，根据async_mode参数决定使用哪种方法
            if async_mode:
                return self.open_image_as_pdf_async(file_path)
            else:
                return self.open_image_as_pdf_sync(file_path)
        else:
            # 否则按原有逻辑处理PDF文件
            # 在打开新文件前，先关闭旧文档
            self.close_document()

            if async_mode:
                return self.open_pdf_async(file_path, password)
            else:
                return self.open_pdf_sync(file_path, password)
    
    def open_image_as_pdf(self, image_path, async_mode=True):
        """将图片作为PDF打开"""
        try:
            # 使用PyMuPDF打开图片，它会自动将其视为单页PDF
            self.fitz_document = fitz.open(image_path)
            self.pdf_document = None  # 图片模式下不需要PyPDF2文档
            self.current_file = image_path
            self.total_pages = len(self.fitz_document)
            self.current_page = 0
            self.zoom_factor = self.base_zoom  # 重置为基准缩放
            self.last_error = ""
            
            # 清除缓存
            self.clear_render_cache()
            
            # 发送加载完成信号
            self.loading_finished.emit(True, f"成功打开图片文件，共{self.total_pages}页")
            
            return True, f"成功打开图片文件，共{self.total_pages}页"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"打开图片文件时出错: {error_msg}")
            return False, f"无法打开图片文件: {error_msg}"
    
    def open_image_as_pdf_sync(self, image_path):
        """同步将图片作为PDF打开"""
        try:
            # 使用PyMuPDF打开图片，它会自动将其视为单页PDF
            self.fitz_document = fitz.open(image_path)
            self.pdf_document = None  # 图片模式下不需要PyPDF2文档
            self.current_file = image_path
            self.total_pages = len(self.fitz_document)
            self.current_page = 0
            self.zoom_factor = self.base_zoom  # 重置为基准缩放
            self.last_error = ""
            
            # 清除缓存
            self.clear_render_cache()
            
            return True, f"成功打开图片文件，共{self.total_pages}页"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"打开图片文件时出错: {error_msg}")
            return False, f"无法打开图片文件: {error_msg}"
    
    def open_image_as_pdf_async(self, image_path):
        """异步将图片作为PDF打开"""
        try:
            # 检查文件是否存在和可读
            if not os.path.exists(image_path):
                return False, "文件不存在"

            if not os.access(image_path, os.R_OK):
                return False, "文件不可读"

            # 取消之前的加载任务
            if self.async_loader and self.async_loader.isRunning():
                self.async_loader.cancel()
                self.async_loader.wait()

            # 创建异步加载器 - 为图片文件使用现有的加载器
            # 但我们需要在后台线程中验证图片文件
            from PyQt5.QtCore import QThread
            
            class AsyncImageLoader(QThread):
                def __init__(self, parent, image_path):
                    super().__init__()
                    self.parent = parent
                    self.image_path = image_path
                    self.result = None
                    self.error = None
                    self.load_start_time = time.time()
                    self.is_cancelled = False
                    
                def cancel(self):
                    """取消加载操作"""
                    self.is_cancelled = True
                    
                def run(self):
                    try:
                        # 检查是否被取消
                        if self.is_cancelled:
                            return
                        
                        # 尝试用PyMuPDF打开图片文件
                        import fitz
                        doc = fitz.open(self.image_path)
                        total_pages = len(doc)
                        doc.close()
                        
                        # 检查是否被取消
                        if self.is_cancelled:
                            return
                        
                        # 准备图片信息
                        image_info = {
                            'filepath': self.image_path,
                            'total_pages': total_pages,
                            'file_size': os.path.getsize(self.image_path)
                        }
                        
                        self.result = image_info
                    except Exception as e:
                        self.error = str(e)
                        
            # 创建加载器
            loader = AsyncImageLoader(self, image_path)
            # 保存加载器引用，以便在回调中访问加载开始时间
            self.async_loader = loader
            
            def on_image_load_complete():
                if loader.error:
                    self.loading_finished.emit(False, f"无法打开图片文件: {loader.error}")
                else:
                    # 调用图片加载完成的处理
                    self._on_image_loaded(True, f"成功打开图片文件，共{loader.result['total_pages']}页", loader.result)
            
            loader.finished.connect(on_image_load_complete)
            loader.start()

            return True, "开始异步加载图片文件..."

        except Exception as e:
            return False, f"启动异步加载失败: {str(e)}"
    
    def _on_image_loaded(self, success, message, image_info):
        """图片异步加载完成回调"""
        if success:
            try:
                # 强制关闭旧的fitz文档，防止重复打开导致Graftmaps错误
                if self.fitz_document:
                    try:
                        self.fitz_document.close()
                    except:
                        pass
                    self.fitz_document = None

                # 在主线程中打开PyMuPDF文档
                self.fitz_document = fitz.open(image_info['filepath'])
                
                # 更新处理器状态
                self.current_file = image_info['filepath']
                self.total_pages = len(self.fitz_document)
                self.current_page = 0
                self.zoom_factor = self.base_zoom
                self.last_error = ""
                
                # 清除缓存
                self.clear_render_cache()
                
                # 计算加载时间
                if hasattr(self, 'async_loader') and self.async_loader:
                    self.load_time = time.time() - self.async_loader.load_start_time
                else:
                    # 对于图片加载，使用当前时间作为开始时间
                    self.load_time = 0.0
                
                # 发送加载完成信号
                self.loading_finished.emit(True, message)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"打开PyMuPDF图片文档时出错: {error_msg}")
                self.loading_finished.emit(False, f"初始化渲染引擎失败: {error_msg}")
        else:
            # 发送加载失败信号
            self.loading_finished.emit(False, message)
    
    def open_images_from_directory(self, directory_path, async_mode=True):
        """从目录打开所有图片并合并为PDF"""
        try:
            # 获取目录中的所有图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.ico'}
            image_files = []
            
            for file_name in os.listdir(directory_path):
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext in image_extensions:
                    image_files.append(os.path.join(directory_path, file_name))
            
            if not image_files:
                return False, "目录中没有找到支持的图片文件"
            
            # 按文件名排序
            image_files.sort()
            
            # 创建一个新的PDF文档，将所有图片添加为页面
            new_doc = fitz.open()  # 创建空的PDF文档
            
            for image_path in image_files:
                # 打开图片
                img_doc = fitz.open(image_path)
                # 将图片插入到PDF中
                new_doc.insert_pdf(img_doc)
                img_doc.close()
            
            # 关闭旧文档并设置新文档
            if self.fitz_document:
                try:
                    self.fitz_document.close()
                except:
                    pass
                self.fitz_document = None
            
            self.fitz_document = new_doc
            self.pdf_document = None  # 目录模式下使用PyMuPDF文档
            self.current_file = f"Directory: {directory_path}"
            self.total_pages = len(self.fitz_document)
            self.current_page = 0
            self.zoom_factor = self.base_zoom  # 重置为基准缩放
            self.last_error = ""
            
            # 清除缓存
            self.clear_render_cache()
            
            # 发送加载完成信号
            self.loading_finished.emit(True, f"成功加载 {len(image_files)} 张图片，合并为 {self.total_pages} 页")
            
            return True, f"成功加载 {len(image_files)} 张图片，合并为 {self.total_pages} 页"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"从目录打开图片时出错: {error_msg}")
            return False, f"无法从目录打开图片: {error_msg}"
    
    def open_pdf_sync(self, file_path, password=None):
        """同步打开PDF文件（原有逻辑）"""
        try:
            # 记录开始时间
            start_time = time.time()

            # 检查文件是否存在和可读
            if not os.path.exists(file_path):
                return False, "文件不存在"

            if not os.access(file_path, os.R_OK):
                return False, "文件不可读"

            # 获取文件大小
            self.file_size = os.path.getsize(file_path)

            # 使用PyPDF2打开文件获取基本信息
            self.pdf_document = PyPDF2.PdfReader(file_path)

            # 检查是否加密
            if self.pdf_document.is_encrypted:
                if password:
                    # 尝试使用密码解密
                    try:
                        result = self.pdf_document.decrypt(password)
                        if result == 0:
                            return False, "密码错误，无法解密PDF文件"
                    except Exception as e:
                        return False, f"解密失败: {str(e)}"
                else:
                    return False, "PDF文件已加密，需要密码才能打开"

            # 额外验证PDF文件完整性
            total_pages = len(self.pdf_document.pages)
            try:
                # 尝试访问第一页来验证PDF是否可读
                if total_pages > 0:
                    first_page = self.pdf_document.pages[0]
                    # 尝试获取页面的基本信息来验证完整性
                    _ = first_page.get('/MediaBox', [0, 0, 612, 792])
            except Exception:
                # 如果访问页面失败，可能是文件损坏
                # 尝试修复不完整的PDF文件
                from app.utils.pdf_fixer import try_fix_pdf_file
                fixed_file_path = try_fix_pdf_file(file_path)
                if fixed_file_path:
                    try:
                        # 使用修复后的文件
                        self.pdf_document = PyPDF2.PdfReader(fixed_file_path)

                        # 检查是否加密
                        if self.pdf_document.is_encrypted:
                            if password:
                                # 尝试使用密码解密
                                try:
                                    result = self.pdf_document.decrypt(password)
                                    if result == 0:
                                        return False, "密码错误，无法解密PDF文件"
                                except Exception as e:
                                    return False, f"解密失败: {str(e)}"
                            else:
                                return False, "PDF文件已加密，需要密码才能打开"

                        total_pages = len(self.pdf_document.pages)

                        # 额外验证PDF文件完整性
                        try:
                            # 尝试访问第一页来验证PDF是否可读
                            if total_pages > 0:
                                first_page = self.pdf_document.pages[0]
                                # 尝试获取页面的基本信息来验证完整性
                                _ = first_page.get('/MediaBox', [0, 0, 612, 792])
                        except Exception:
                            # 如果访问页面失败，可能是文件损坏
                            return False, "PDF文件不完整或已损坏，无法访问页面内容"

                        # 使用PyMuPDF打开修复后的文件用于页面渲染
                        try:
                            # 先用普通方式打开PyMuPDF文档
                            self.fitz_document = fitz.open(fixed_file_path)

                            # 验证PyMuPDF文档是否可以访问
                            if self.fitz_document.is_encrypted:
                                # 如果文档加密，使用密码进行认证
                                if password:
                                    auth_status = self.fitz_document.authenticate(password)
                                    if not auth_status:
                                        self.fitz_document.close()
                                        self.fitz_document = None
                                        return False, "密码错误，无法打开PDF文件"
                                else:
                                    self.fitz_document.close()
                                    self.fitz_document = None
                                    return False, "PDF文件已加密，需要密码才能打开"
                        except Exception as e:
                            error_msg = str(e)
                            # 检查是否是PyMuPDF无法打开损坏文档的错误
                            if "cannot open" in error_msg.lower() and ("broken" in error_msg.lower() or "damaged" in error_msg.lower()):
                                return False, f"PDF文件不完整或已损坏，无法渲染: {error_msg}"
                            elif "password" in error_msg.lower():
                                return False, "密码错误，无法打开PDF文件"
                            else:
                                return False, f"初始化渲染引擎失败: {error_msg}"
                    except Exception as e:
                        error_msg = str(e)
                        return False, f"PDF文件不完整或已损坏，且自动修复失败: {error_msg}"
                else:
                    return False, "PDF文件不完整或已损坏，无法访问页面内容"

            # 使用PyMuPDF打开文件用于页面渲染
            try:
                # 先关闭旧的fitz文档
                if self.fitz_document:
                    try:
                        self.fitz_document.close()
                    except:
                        pass
                    self.fitz_document = None

                # 先用普通方式打开PyMuPDF文档
                self.fitz_document = fitz.open(file_path)

                # 验证PyMuPDF文档是否可以访问
                if self.fitz_document.is_encrypted:
                    # 如果文档加密，使用密码进行认证
                    if password:
                        auth_status = self.fitz_document.authenticate(password)
                        if not auth_status:
                            self.fitz_document.close()
                            self.fitz_document = None
                            return False, "密码错误，无法打开PDF文件"
                    else:
                        self.fitz_document.close()
                        self.fitz_document = None
                        return False, "PDF文件已加密，需要密码才能打开"
            except Exception as e:
                error_msg = str(e)
                # 检查是否是PyMuPDF无法打开损坏文档的错误
                if "cannot open" in error_msg.lower() and ("broken" in error_msg.lower() or "damaged" in error_msg.lower()):
                    return False, f"PDF文件不完整或已损坏，无法渲染: {error_msg}"
                elif "password" in error_msg.lower():
                    return False, "密码错误，无法打开PDF文件"
                else:
                    return False, f"初始化渲染引擎失败: {error_msg}"

            # 重置状态
            self.current_file = file_path
            self.total_pages = len(self.pdf_document.pages) if self.pdf_document else len(self.fitz_document)
            self.current_page = 0
            self.zoom_factor = self.base_zoom  # 重置为基准缩放（300%作为100%基准）
            self.last_error = ""

            # 清除缓存
            self.clear_render_cache()

            # 计算加载时间
            self.load_time = time.time() - start_time

            return True, f"文件打开成功 ({self.get_file_size_str()}, {self.load_time:.2f}秒)"

        except PdfReadError as e:
            error_msg = str(e)
            # 检查是否是EOF marker错误
            if "EOF" in error_msg or "marker" in error_msg:
                self.last_error = f"PDF文件不完整或已损坏: {error_msg}"
            else:
                self.last_error = f"PDF文件格式错误: {error_msg}"
            return False, self.last_error
        except Exception as e:
            error_msg = str(e)
            # 检查是否是EOF marker错误
            if "EOF" in error_msg or "marker" in error_msg:
                self.last_error = f"PDF文件不完整或已损坏: {error_msg}"
            else:
                self.last_error = f"无法打开PDF文件: {error_msg}"
            return False, self.last_error
    
    def open_pdf_async(self, file_path, password=None):
        """异步打开PDF文件"""
        try:
            # 检查文件是否存在和可读
            if not os.path.exists(file_path):
                return False, "文件不存在"

            if not os.access(file_path, os.R_OK):
                return False, "文件不可读"

            # 取消之前的加载任务
            if self.async_loader and self.async_loader.isRunning():
                self.async_loader.cancel()
                self.async_loader.wait()

            # 创建异步加载器
            self.async_loader = AsyncPDFLoader(file_path, password)

            # 连接信号
            self.async_loader.loading_progress.connect(self.loading_progress.emit)
            self.async_loader.loading_finished.connect(self._on_pdf_loaded)
            self.async_loader.loading_error.connect(self._on_load_error)

            # 记录加载开始时间
            self.async_loader.load_start_time = time.time()

            # 开始异步加载
            self.async_loader.start()

            return True, "开始异步加载PDF文件..."

        except Exception as e:
            return False, f"启动异步加载失败: {str(e)}"
    
    def _on_pdf_loaded(self, success, message, pdf_info):
        """异步加载完成回调"""
        if success:
            try:
                # 强制关闭旧的fitz文档，防止重复打开导致Graftmaps错误
                if self.fitz_document:
                    try:
                        self.fitz_document.close()
                    except:
                        pass
                    self.fitz_document = None

                # 在主线程中打开PyMuPDF文档
                self.fitz_document = fitz.open(pdf_info['filepath'])

                # 验证文档是否可以访问 - 这里需要处理加密验证
                # 注意：如果文档仍然加密，说明密码不正确
                if self.fitz_document.is_encrypted:
                    # 如果文档加密，使用密码进行认证
                    password = pdf_info.get('password')
                    if password:
                        auth_status = self.fitz_document.authenticate(password)
                        if not auth_status:
                            self.fitz_document.close()
                            self.fitz_document = None
                            self.loading_finished.emit(False, "密码错误，无法打开PDF文件")
                            return
                    else:
                        self.fitz_document.close()
                        self.fitz_document = None
                        self.loading_finished.emit(False, "PDF文件已加密，需要密码才能打开")
                        return

                # 更新处理器状态
                self.current_file = pdf_info['filepath']
                self.file_size = pdf_info['file_size']
                self.pdf_document = pdf_info['pdf_document']
                # 计算总页数 - 考虑到可能是图片文件
                if self.pdf_document:
                    self.total_pages = len(self.pdf_document.pages)
                else:
                    # 如果是图片文件，使用fitz_document的页面数
                    self.total_pages = len(self.fitz_document)
                self.current_page = 0
                self.zoom_factor = self.base_zoom
                self.last_error = ""

                # 清除缓存
                self.clear_render_cache()

                # 计算加载时间
                self.load_time = time.time() - self.async_loader.load_start_time

                # 发送加载完成信号
                self.loading_finished.emit(True, message)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"打开PyMuPDF文档时出错: {error_msg}")
                # 检查错误信息是否与密码相关
                if "password" in error_msg.lower() or "incorrect" in error_msg.lower() or "wrong" in error_msg.lower():
                    self.loading_finished.emit(False, "密码错误，无法打开PDF文件")
                else:
                    self.fitz_document = None
                    self.loading_finished.emit(False, f"初始化渲染引擎失败: {error_msg}")
        else:
            # 发送加载失败信号
            self.loading_finished.emit(False, message)
    
    def _on_load_error(self, error_message):
        """异步加载错误回调"""
        self.last_error = error_message
        self.loading_finished.emit(False, error_message)
    
    def get_file_size_str(self):
        """获取文件大小格式化字符串"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
    
    def get_pdf_info(self):
        """获取PDF详细信息 - 包含文档属性、元数据和统计信息"""
        if not self.pdf_document:
            return None
            
        info = {
            "filename": os.path.basename(self.current_file) if self.current_file else "",
            "filepath": self.current_file if self.current_file else "",
            "file_size": self.get_file_size_str(),
            "page_count": len(self.pdf_document.pages),
            "is_encrypted": self.pdf_document.is_encrypted,
            "load_time": f"{self.load_time:.2f}秒",
            "metadata": {},
            "properties": {}
        }
        
        # 获取文档属性
        try:
            if hasattr(self.pdf_document, 'metadata') and self.pdf_document.metadata:
                metadata = self.pdf_document.metadata
                
                # 标准元数据字段映射
                metadata_mapping = {
                    '/Title': '标题',
                    '/Author': '作者', 
                    '/Subject': '主题',
                    '/Keywords': '关键词',
                    '/Creator': '创建者',
                    '/Producer': '生产者',
                    '/CreationDate': '创建日期',
                    '/ModDate': '修改日期'
                }
                
                for key, value in metadata.items():
                    # 清理元数据键名
                    clean_key = str(key).replace('/', '')
                    
                    # 使用友好的显示名称
                    display_key = metadata_mapping.get(key, clean_key)
                    
                    # 处理日期格式
                    if 'Date' in key and len(str(value)) > 10:
                        try:
                            # 简化日期显示
                            value = str(value)[:10] + "..."
                        except:
                            pass
                    
                    info["metadata"][display_key] = str(value)
        except Exception as e:
            logger.error(f"获取元数据失败: {e}")
        
        # 添加文档属性
        info["properties"]["文档状态"] = "正常" if not self.pdf_document.is_encrypted else "已加密"
        info["properties"]["页面方向"] = "待检测"  # 实际可以检测页面方向
        info["properties"]["兼容性"] = "PDF 1.4+"  # 可以根据实际版本设置
                
        return info
    
    def save_pdf(self, file_path):
        """保存PDF文件到指定路径"""
        try:
            if not self.fitz_document:
                return False, "请先打开PDF文件"
            
            # 如果存在页面编辑器且有未保存的更改，则使用编辑器的保存功能
            if (hasattr(self, 'page_editor') and 
                self.page_editor and 
                self.page_editor.has_unsaved_changes()):
                
                # 如果page_editor的临时文件存在，则保存临时文件
                if self.page_editor.temp_file and os.path.exists(self.page_editor.temp_file):
                    import shutil
                    shutil.copy2(self.page_editor.temp_file, file_path)
                    return True, f"PDF文件已保存到: {file_path}"
            
            # 如果没有编辑或没有临时文件，则直接保存当前文档
            # 使用PyMuPDF保存当前文档
            self.fitz_document.save(file_path)
            return True, f"PDF文件已保存到: {file_path}"
            
        except Exception as e:
            return False, f"保存失败: {str(e)}"
    
    def merge_pdfs(self, file_paths, output_path):
        """合并多个PDF文件"""
        try:
            merger = PyPDF2.PdfMerger()
            
            for file_path in file_paths:
                with open(file_path, 'rb') as file:
                    merger.append(file)
            
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
                
            return True, "PDF合并成功"
        except Exception as e:
            return False, f"合并失败: {str(e)}"
    
    def split_pdf(self, output_dir, pages_per_file=None):
        """分割PDF文件"""
        if not self.pdf_document:
            return False, "请先打开PDF文件"
            
        try:
            if pages_per_file:
                # 按指定页数分割
                pass
            else:
                # 按单页分割
                for i, page in enumerate(self.pdf_document.pages):
                    writer = PyPDF2.PdfWriter()
                    writer.add_page(page)
                    
                    output_path = os.path.join(output_dir, f"page_{i+1}.pdf")
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                        
            return True, "PDF分割成功"
        except Exception as e:
            return False, f"分割失败: {str(e)}"
    
    def encrypt_pdf(self, password, output_path):
        """加密PDF文件"""
        if not self.pdf_document:
            return False, "请先打开PDF文件"
            
        try:
            writer = PyPDF2.PdfWriter()
            
            # 复制所有页面
            for page in self.pdf_document.pages:
                writer.add_page(page)
            
            # 加密
            writer.encrypt(password)
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
                
            return True, "PDF加密成功"
        except Exception as e:
            return False, f"加密失败: {str(e)}"
    
    # ===== 页面导航功能 =====
    
    def get_current_page(self):
        """获取当前页码（用户可见的页码，从1开始）"""
        return self.current_page + 1 if self.fitz_document else 0
    
    def get_total_pages(self):
        """获取总页数"""
        return len(self.fitz_document) if self.fitz_document else 0
    
    def go_to_page(self, page_number):
        """跳转到指定页面 - 增强版本，支持边界检测和状态反馈"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        total_pages = len(self.fitz_document)
        
        # 验证页码输入
        if not isinstance(page_number, int) or page_number < 1:
            return False, f"页码无效，请输入1-{total_pages}之间的数字"
        
        # 转换用户页码（1开始）为内部页码（0开始）
        internal_page = page_number - 1
        
        if 0 <= internal_page < total_pages:
            self.current_page = internal_page
            return True, f"已跳转到第{page_number}页"
        elif internal_page >= total_pages:
            # 超过最后一页时，跳转到最后一页
            self.current_page = total_pages - 1
            return True, f"已跳转到最后一页（第{total_pages}页）"
        else:
            return False, f"页码无效，请输入1-{total_pages}之间的数字"
    
    def next_page(self):
        """下一页 - 增强版本，支持循环浏览"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        total_pages = len(self.fitz_document)
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            return True, f"已跳转到第{self.current_page + 1}页"
        else:
            # 已经是最后一页时，可选择循环到第一页
            if total_pages > 1:
                self.current_page = 0
                return True, "已回到第一页"
            else:
                return False, "已经是最后一页"
    
    def previous_page(self):
        """上一页 - 增强版本，支持循环浏览"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        total_pages = len(self.fitz_document)
        
        if self.current_page > 0:
            self.current_page -= 1
            return True, f"已跳转到第{self.current_page + 1}页"
    
    def get_page_image_data(self, page_num):
        """获取指定页面的图像数据（用于OCR识别）"""
        try:
            if not self.fitz_document:
                logger.error("PDF文档未打开")
                return None
            
            # 检查页面范围
            if page_num < 0 or page_num >= len(self.fitz_document):
                logger.error(f"页面号超出范围: {page_num}")
                return None
            
            # 获取页面
            page = self.fitz_document[page_num]
            
            # 设置渲染参数（300 DPI以获得高质量图像）
            zoom = 2.0  # 2倍缩放以获得更好的OCR效果
            mat = fitz.Matrix(zoom, zoom)
            
            # 渲染页面为图像
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # 统一转换为PNG格式，确保OCR引擎兼容性
            img_data = pix.tobytes("png")
            
            return img_data
            
        except Exception as e:
            logger.error(f"获取页面图像数据时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        else:
            # 已经是第一页时，可选择循环到最后一页
            if total_pages > 1:
                self.current_page = total_pages - 1
                return True, f"已跳转到最后一页（第{total_pages}页）"
            else:
                return False, "已经是第一页"
    
    def set_zoom(self, zoom_factor):
        """设置缩放比例 - 基于新的基准缩放（用户看到的100%实际是300%）"""
        # 将用户的缩放值转换为实际缩放值
        actual_zoom = zoom_factor * self.base_zoom
        
        # 限制实际缩放范围在75%-1200%（对应用户看到的25%-400%）
        if 0.25 <= zoom_factor <= 4.0:
            self.zoom_factor = actual_zoom
            # 清除渲染缓存，因为缩放级别已更改
            self.clear_render_cache()
            return True, f"缩放比例已设置为{int(zoom_factor * 100)}%"
        else:
            return False, "缩放比例必须在25%-400%之间"
    
    def get_zoom(self):
        """获取当前缩放比例（返回用户看到的相对值）"""
        return self.zoom_factor / self.base_zoom
    
    def render_page(self, width=800, height=1000):
        """渲染当前页面为高质量图像 - 优化显示效果和性能"""
        if not self.fitz_document:
            return None
        
        try:
            # 获取页面实际尺寸
            page_rect = self.fitz_document[self.current_page].rect
            render_width = int(page_rect.width * self.zoom_factor)
            render_height = int(page_rect.height * self.zoom_factor)
            
            # 首先检查内存缓存
            cached_pixmap = self.render_cache.get_rendered_page(
                self.current_page, self.zoom_factor, (render_width, render_height)
            )
            if cached_pixmap:
                return cached_pixmap
            
            # 检查磁盘缓存
            disk_key = f"page_{self.current_page}_zoom_{self.zoom_factor:.2f}_size_{render_width}x{render_height}"
            disk_pixmap = self.disk_cache.get(disk_key)
            if disk_pixmap:
                # 将磁盘缓存的内容放入内存缓存
                self.render_cache.put_rendered_page(
                    self.current_page, self.zoom_factor, (render_width, render_height), disk_pixmap
                )
                return disk_pixmap
            
            # 缓存未命中，进行渲染
            return self._render_page_sync(self.current_page, width, height)
            
        except Exception as e:
            logger.error(f"渲染页面失败: {e}")
            return False
    
    def _render_page_sync(self, page_num, width=800, height=1000):
        """同步渲染指定页面"""
        try:
            # 获取页面
            page = self.fitz_document[page_num]
            
            # 获取页面实际尺寸
            page_rect = page.rect
            render_width = int(page_rect.width * self.zoom_factor)
            render_height = int(page_rect.height * self.zoom_factor)
            
            # 创建变换矩阵进行缩放
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            
            # 渲染页面为图像 - 使用优化的渲染参数
            pix = page.get_pixmap(
                matrix=mat,
                alpha=False,  # 不使用alpha通道，提高性能
                colorspace=fitz.csRGB,  # 使用RGB色彩空间
                annots=True,  # 包含注释
                clip=page.rect  # 限定渲染区域
            )
            
            # 获取图像尺寸
            img_width = pix.width
            img_height = pix.height
            
            # 直接创建QPixmap，避免中间转换步骤，提升性能
            if hasattr(pix, 'samples') and pix.samples is not None:
                # 使用像素数据直接创建QImage然后转换为QPixmap
                image = QImage(
                    pix.samples, 
                    img_width, 
                    img_height, 
                    img_width * 3,  # RGB每个像素3字节
                    QImage.Format_RGB888
                )
                pixmap = QPixmap.fromImage(image)
            else:
                # 备用方法：直接转换为QPixmap
                img_data = pix.tobytes("ppm")  # 使用PPM格式更快
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
            
            # 缓存结果到内存缓存
            self.render_cache.put_rendered_page(
                page_num, self.zoom_factor, (render_width, render_height), pixmap
            )
            
            # 缓存到磁盘（异步进行，不阻塞）
            try:
                disk_key = f"page_{page_num}_zoom_{self.zoom_factor:.2f}_size_{render_width}x{render_height}"
                self.disk_cache.put(disk_key, pixmap)
            except:
                pass  # 磁盘缓存失败不影响主流程
            
            return pixmap
            
        except Exception as e:
            logger.error(f"渲染页面失败: {e}")
            return False
    
    def render_pages_async(self, page_nums, width=800, height=1000):
        """异步渲染多个页面"""
        if not self.fitz_document:
            return False
        
        try:
            # 取消之前的渲染任务
            if self.page_renderer and self.page_renderer.isRunning():
                self.page_renderer.cancel()
                self.page_renderer.wait()
            
            # 创建异步渲染器
            self.page_renderer = AsyncPageRenderer(
                self.fitz_document, page_nums, self.zoom_factor, (width, height)
            )
            
            # 连接信号
            self.page_renderer.page_rendered.connect(
                lambda page_num, pixmap: self._on_page_rendered(page_num, pixmap, (width, height))
            )
            
            # 开始异步渲染
            self.page_renderer.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动异步渲染失败: {e}")
            return False
    
    def _on_page_rendered(self, page_num, pixmap, render_size):
        """页面渲染完成回调"""
        # 缓存渲染结果
        self.render_cache.put_rendered_page(
            page_num, self.zoom_factor, render_size, pixmap
        )
        
        # 发送渲染完成信号
        self.page_rendered.emit(page_num, pixmap)
    
    def render_continuous_pages(self, width=800, height=1000):
        """渲染连续的多页内容 - 支持网页式浏览"""
        if not self.fitz_document:
            return None
        
        try:
            total_pages = len(self.fitz_document)
            current_page = self.current_page
            
            # 计算要渲染的页面范围
            start_page = max(0, current_page)
            end_page = min(total_pages, start_page + self.pages_per_view)
            
            # 创建垂直布局的图像容器
            total_height = 0
            page_pixmaps = []
            
            # 创建变换矩阵进行缩放
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            
            # 渲染每一页
            for page_num in range(start_page, end_page):
                page = self.fitz_document[page_num]
                
                # 渲染页面 - 使用优化参数
                pix = page.get_pixmap(
                    matrix=mat,
                    alpha=False,
                    colorspace=fitz.csRGB,
                    annots=True,
                    clip=page.rect  # 限定渲染区域
                )
                
                # 直接转换为QPixmap，避免中间步骤
                if hasattr(pix, 'samples') and pix.samples is not None:
                    image = QImage(
                        pix.samples,
                        pix.width,
                        pix.height,
                        pix.width * 3,
                        QImage.Format_RGB888
                    )
                    pixmap = QPixmap.fromImage(image)
                else:
                    # 备用方法：直接转换为QPixmap
                    img_data = pix.tobytes("ppm")
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                
                # 调整页面宽度以适应显示区域
                if pixmap.width() > width - 40:  # 留出边距
                    pixmap = pixmap.scaledToWidth(
                        width - 40,  # 留出边距
                        QtCore.SmoothTransformation
                    )
                
                page_pixmaps.append(pixmap)
                total_height += pixmap.height()
                
                # 添加页面间距
                if page_num < end_page - 1:
                    total_height += self.page_spacing
            
            # 创建组合图像
            combined_pixmap = QPixmap(width, total_height)
            combined_pixmap.fill(QtCore.white)
            
            # 绘制各页面到组合图像
            painter = QPainter(combined_pixmap)
            y_offset = 20  # 顶部边距
            
            for i, page_pixmap in enumerate(page_pixmaps):
                x_offset = (width - page_pixmap.width()) // 2  # 居中
                painter.drawPixmap(x_offset, y_offset, page_pixmap)
                y_offset += page_pixmap.height()
                
                # 添加页面分隔线（除了最后一页）
                if i < len(page_pixmaps) - 1:
                    painter.setPen(QtCore.gray)
                    painter.drawLine(20, y_offset + self.page_spacing // 2, 
                                 width - 20, y_offset + self.page_spacing // 2)
                    y_offset += self.page_spacing
            
            painter.end()
            
            return combined_pixmap
            
        except Exception as e:
            logger.error(f"连续页面渲染失败: {e}")
            # 返回错误提示图像
            error_pixmap = QPixmap(width, height)
            error_pixmap.fill(QtCore.lightGray)
            return error_pixmap
    
    def set_continuous_mode(self, enabled=True, pages_per_view=3):
        """设置连续浏览模式"""
        self.continuous_mode = enabled
        self.pages_per_view = max(1, min(10, pages_per_view))  # 限制1-10页
    
    def get_page_dimensions(self, page_num=None):
        """获取指定页面的尺寸信息"""
        if not self.fitz_document:
            return None
            
        if page_num is None:
            page_num = self.current_page
            
        try:
            page = self.fitz_document[page_num]
            rect = page.rect
            return {
                'width': rect.width,
                'height': rect.height,
                'size': f"{rect.width:.1f} × {rect.height:.1f} 点"
            }
        except:
            return None
    
    def render_page_at(self, page_num, width=800, height=1000):
        """渲染指定页面为高质量图像 - 优化显示效果和性能"""
        logger.debug(f"开始渲染第{page_num + 1}页 (width={width}, height={height})")
        if not self.fitz_document or page_num < 0 or page_num >= len(self.fitz_document):
            logger.warning("文档未加载或页码无效")
            return None

        try:
            # 获取页面
            page = self.fitz_document[page_num]
            logger.debug(f"获取页面对象成功: {page}")

            # 获取页面实际尺寸
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            logger.debug(f"页面尺寸: {page_width} x {page_height}")

            # 根据页面实际尺寸和缩放因子计算渲染尺寸
            render_width = int(page_width * self.zoom_factor)
            render_height = int(page_height * self.zoom_factor)
            logger.debug(f"渲染尺寸: {render_width} x {render_height}")

            # 检查缓存
            cache_pixmap = self.render_cache.get_rendered_page(page_num, self.zoom_factor, (render_width, render_height))
            if cache_pixmap:
                logger.debug("从缓存获取页面渲染结果")
                return cache_pixmap

            # 创建变换矩阵进行缩放
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            logger.debug(f"创建变换矩阵: {mat}")

            # 渲染页面为图像 - 使用优化的渲染参数
            logger.debug("开始渲染页面...")
            pix = page.get_pixmap(
                matrix=mat,
                alpha=False,  # 不使用alpha通道，提高性能
                colorspace=fitz.csRGB,  # 使用RGB色彩空间
                annots=True,  # 包含注释
                clip=page.rect  # 限定渲染区域
            )
            logger.debug(f"页面渲染完成: {pix.width} x {pix.height}")

            # 获取图像尺寸
            img_width = pix.width
            img_height = pix.height

            # 直接创建QPixmap，避免中间转换步骤，提升性能
            if hasattr(pix, 'samples') and pix.samples is not None:
                # 使用像素数据直接创建QImage然后转换为QPixmap
                logger.debug("使用像素数据创建QImage...")
                image = QImage(
                    pix.samples, 
                    img_width, 
                    img_height, 
                    img_width * 3,  # RGB每个像素3字节
                    QImage.Format_RGB888
                )
                pixmap = QPixmap.fromImage(image)
                logger.debug(f"QPixmap创建成功: {pixmap.width()} x {pixmap.height()}")
            else:
                # 备用方法：直接转换为QPixmap
                logger.debug("使用备用方法创建QPixmap...")
                img_data = pix.tobytes("ppm")  # 使用PPM格式更快
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                logger.debug(f"QPixmap创建成功: {pixmap.width()} x {pixmap.height()}")

            # 缓存结果到新的缓存系统
            self.render_cache.put_rendered_page(page_num, self.zoom_factor, (render_width, render_height), pixmap)
            logger.debug("页面渲染结果已缓存")

            return pixmap

        except Exception as e:
            logger.error(f"渲染页面失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 返回错误提示图像
            error_pixmap = QPixmap(width, height)
            error_pixmap.fill(QtCore.lightGray)
            return error_pixmap
    
    def get_total_pages(self):
        """获取总页数"""
        if self.fitz_document:
            return len(self.fitz_document)
        return 0
        
    def get_current_page(self):
        """获取当前页码（1基索引）"""
        return self.current_page + 1
    
    def render_thumbnail(self, page_num, width=100, height=141):
        """渲染指定页面的缩略图 - 优化版本"""
        if not self.fitz_document or page_num < 0 or page_num >= len(self.fitz_document):
            return None
        
        try:
            # 首先检查缓存
            cached_thumb = self.render_cache.get_thumbnail(page_num, (width, height))
            if cached_thumb:
                return cached_thumb
            
            # 检查磁盘缓存
            disk_key = f"thumb_{page_num}_size_{width}x{height}"
            disk_thumb = self.disk_cache.get(disk_key)
            if disk_thumb:
                # 将磁盘缓存的内容放入内存缓存
                self.render_cache.put_thumbnail(page_num, (width, height), disk_thumb)
                return disk_thumb
            
            # 缓存未命中，生成缩略图
            thumbnail = self._render_thumbnail_sync(page_num, width, height)
            
            if thumbnail:
                # 缓存结果
                self.render_cache.put_thumbnail(page_num, (width, height), thumbnail)
                
                # 缓存到磁盘
                try:
                    self.disk_cache.put(disk_key, thumbnail)
                except:
                    pass
            
            return thumbnail
            
        except Exception as e:
            logger.error(f"渲染缩略图失败: {e}")
            return None
    
    def _render_thumbnail_sync(self, page_num, width=100, height=141):
        """同步生成缩略图"""
        try:
            # 获取页面
            page = self.fitz_document[page_num]
            
            # 使用固定缩放比例生成缩略图
            mat = fitz.Matrix(0.2, 0.2)  # 20%缩放
            
            # 渲染页面为图像
            pix = page.get_pixmap(matrix=mat)
            
            # 转换为QImage
            img_data = pix.tobytes("ppm")
            image = QImage.fromData(img_data)
            
            # 创建带边框的缩略图容器（容器比内容页大2%）
            # 先创建原始尺寸的Pixmap
            original_pixmap = QPixmap.fromImage(image)
            
            # 计算带边框的容器尺寸（比内容大2%）
            extra_width = int(original_pixmap.width() * 0.01)
            extra_height = int(original_pixmap.height() * 0.01)
            container_width = original_pixmap.width() + extra_width * 2
            container_height = original_pixmap.height() + extra_height * 2
            
            # 创建容器
            container_pixmap = QPixmap(container_width, container_height)
            container_pixmap.fill(QtCore.white)  # 白色背景
            
            # 在容器中绘制带边框的页面
            painter = QPainter(container_pixmap)
            # 绘制边框
            pen = QPen(QColor("#CCCCCC"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawRect(0, 0, container_width - 1, container_height - 1)
            
            # 居中绘制页面内容
            x_offset = (container_width - original_pixmap.width()) // 2
            y_offset = (container_height - original_pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, original_pixmap)
            painter.end()
            
            # 缩放到最终尺寸，保持边框完整显示
            scaled_pixmap = container_pixmap.scaled(width, height, QtCore.KeepAspectRatio, QtCore.SmoothTransformation)
            
            # 确保边框可见，创建最终的显示Pixmap
            final_pixmap = QPixmap(width, height)
            final_pixmap.fill(QtCore.transparent)
            
            # 居中绘制缩放后的带边框图像
            painter = QPainter(final_pixmap)
            x_offset = (width - scaled_pixmap.width()) // 2
            y_offset = (height - scaled_pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
            painter.end()
            
            return final_pixmap
            
        except Exception as e:
            logger.error(f"渲染缩略图失败: {e}")
            return None
    
    def load_thumbnails_async(self, start_page=0, end_page=None):
        """异步加载缩略图"""
        if not self.fitz_document:
            return False
        
        try:
            total_pages = len(self.fitz_document)
            if end_page is None:
                end_page = total_pages
            
            # 取消之前的缩略图加载任务
            if self.thumbnail_loader and self.thumbnail_loader.isRunning():
                self.thumbnail_loader.cancel()
                self.thumbnail_loader.wait()
            
            # 创建异步缩略图加载器
            self.thumbnail_loader = AsyncThumbnailLoader(self.fitz_document)
            
            # 连接信号
            self.thumbnail_loader.thumbnail_ready.connect(self._on_thumbnail_ready)
            self.thumbnail_loader.thumbnail_progress.connect(
                lambda current, total: self.loading_progress.emit(
                    int(current / total * 100), f"加载缩略图 {current}/{total}"
                )
            )
            
            # 开始异步加载
            self.thumbnail_loader.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动异步缩略图加载失败: {e}")
            return False
    
    def _on_thumbnail_ready(self, page_num, pixmap):
        """缩略图就绪回调"""
        # 标准化缩略图尺寸
        standard_thumb = self._standardize_thumbnail(pixmap, 200, 234)
        
        # 缓存缩略图
        if standard_thumb:
            self.render_cache.put_thumbnail(page_num, (200, 234), standard_thumb)
            
            # 发送缩略图就绪信号
            self.thumbnail_ready.emit(page_num, standard_thumb)
    
    def _standardize_thumbnail(self, pixmap, width, height):
        """标准化缩略图尺寸"""
        try:
            # 缩放到指定尺寸
            scaled_pixmap = pixmap.scaled(width, height, QtCore.KeepAspectRatio, QtCore.SmoothTransformation)
            
            # 创建指定尺寸的容器
            final_pixmap = QPixmap(width, height)
            final_pixmap.fill(QtCore.white)
            
            # 居中绘制
            painter = QPainter(final_pixmap)
            x_offset = (width - scaled_pixmap.width()) // 2
            y_offset = (height - scaled_pixmap.height()) // 2
            painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
            painter.end()
            
            return final_pixmap
            
        except Exception as e:
            logger.error(f"标准化缩略图失败: {e}")
            return pixmap  # 返回原始图片作为备用
    

    
    # ===== 搜索功能 =====
    
    def search_text(self, search_text, match_case=False, whole_word=False, 
                   search_backwards=False, start_page=None):
        """
        在PDF中搜索文本
        
        Args:
            search_text: 要搜索的文本
            match_case: 是否区分大小写
            whole_word: 是否全词匹配
            search_backwards: 是否向后搜索
            start_page: 开始搜索的页面（None表示从当前页开始）
            
        Returns:
            (success, result_info) 元组
        """
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        if not search_text.strip():
            return False, "请输入搜索内容"
        
        try:
            # 确定开始搜索的页面
            if start_page is None:
                start_page = self.current_page
            
            total_pages = len(self.fitz_document)
            
            # 搜索结果列表
            search_results = []
            
            # 搜索范围（向前或向后）
            if search_backwards:
                # 向后搜索：从当前页向前搜索到第1页
                pages_to_search = list(range(start_page, -1, -1))
            else:
                # 向前搜索：从当前页向后搜索到最后一页
                pages_to_search = list(range(start_page, total_pages))
            
            # 搜索标志
            search_flags = 0
            if match_case:
                search_flags |= fitz.TEXT_PRESERVE_LIGATURES
            if whole_word:
                search_flags |= fitz.TEXT_PRESERVE_WHITESPACE
            
            # 执行搜索
            for page_num in pages_to_search:
                page = self.fitz_document[page_num]
                
                # 搜索当前页
                text_instances = page.search_for(
                    search_text,
                    flags=search_flags
                )
                
                # 记录搜索结果
                for rect in text_instances:
                    search_results.append({
                        'page': page_num + 1,  # 转换为用户页码
                        'page_index': page_num,
                        'rect': rect,
                        'text': search_text,
                        'position': {
                            'x': rect.x0,
                            'y': rect.y0,
                            'width': rect.width,
                            'height': rect.height
                        }
                    })
            
            # 处理搜索结果
            if search_results:
                # 如果有搜索结果，跳转到第一个匹配项
                first_result = search_results[0]
                self.current_page = first_result['page_index']
                
                return True, {
                    'total_matches': len(search_results),
                    'current_match': 1,
                    'results': search_results,
                    'message': f"找到 {len(search_results)} 个匹配项"
                }
            else:
                return False, "未找到匹配的文本"
                
        except Exception as e:
            return False, f"搜索失败: {str(e)}"
    
    def search_next(self, search_text, match_case=False, whole_word=False):
        """搜索下一个匹配项"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        try:
            # 从当前页的下一个位置开始搜索
            start_page = self.current_page + 1
            
            return self.search_text(search_text, match_case, whole_word, 
                                  search_backwards=False, start_page=start_page)
        except Exception as e:
            return False, f"搜索失败: {str(e)}"
    
    def search_previous(self, search_text, match_case=False, whole_word=False):
        """搜索上一个匹配项"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        try:
            # 从当前页的前一个位置开始搜索
            start_page = self.current_page - 1
            
            return self.search_text(search_text, match_case, whole_word, 
                                  search_backwards=True, start_page=start_page)
        except Exception as e:
            return False, f"搜索失败: {str(e)}"
    
    def highlight_search_result(self, page_num, rect, color=(1, 1, 0, 0.3)):
        """高亮显示搜索结果"""
        if not self.fitz_document:
            return False
        
        try:
            # 获取页面
            page = self.fitz_document[page_num]
            
            # 添加高亮注释
            highlight = page.add_highlight_annot(rect)
            
            # 设置高亮颜色（黄色透明）
            highlight.set_colors(stroke=color)
            highlight.update()
            
            return True
        except Exception as e:
            logger.error(f"高亮失败: {e}")
            return False
    
    def clear_highlights(self, page_num=None):
        """清除高亮标记"""
        if not self.fitz_document:
            return False
        
        try:
            if page_num is not None:
                # 清除指定页面的高亮
                page = self.fitz_document[page_num]
                for annot in page.annots():
                    if annot.type[0] == 8:  # 高亮注释类型
                        page.delete_annot(annot)
            else:
                # 清除所有页面的高亮
                for page_num in range(len(self.fitz_document)):
                    page = self.fitz_document[page_num]
                    for annot in page.annots():
                        if annot.type[0] == 8:  # 高亮注释类型
                            page.delete_annot(annot)
            
            return True
        except Exception as e:
            logger.error(f"清除高亮失败: {e}")
            return False
    
    def close_pdf(self):
        """关闭当前PDF文件句柄"""
        if self.fitz_document:
            self.fitz_document.close()
            self.fitz_document = None
        self.pdf_document = None
        self.current_file = None
        self.current_page = 0
        self.zoom_factor = 1.0
        # 清除渲染缓存
        self.clear_render_cache()
    
    def load_pdf(self, file_path):
        """加载PDF文件"""
        success, message = self.open_pdf(file_path)
        if success:
            # 重置页面相关状态
            self.current_page = 0
            self.zoom_factor = self.base_zoom
            # 清除渲染缓存
            self.clear_render_cache()
        return success, message
    
    def clear_render_cache(self):
        """清除渲染缓存"""
        # 清除新缓存系统
        self.render_cache.clear_all()
        self.disk_cache.clear_all()
        
        # 清除旧的简单缓存
        self.simple_cache.clear()
    
    def get_cache_stats(self):
        """获取缓存统计信息"""
        return self.render_cache.get_stats()
    
    def cleanup_cache(self):
        """手动清理缓存"""
        self.render_cache._auto_cleanup()
    
    def optimize_memory_usage(self):
        """优化内存使用"""
        stats = self.get_cache_stats()
        
        # 如果内存使用超过80%，清理缓存
        if stats['current_memory_usage_mb'] > stats['max_memory_usage_mb'] * 0.8:
            self.cleanup_cache()
            
            # 再次检查，如果还是太高，强制清理
            stats = self.get_cache_stats()
            if stats['current_memory_usage_mb'] > stats['max_memory_usage_mb'] * 0.9:
                self.render_cache.clear_all()
    
    def get_text_from_rect(self, page_num, rect):
        """从指定矩形区域提取文本"""
        if not self.fitz_document:
            return ""
        
        try:
            page = self.fitz_document[page_num]
            text = page.get_text("text", clip=rect)
            return text.strip()
        except Exception as e:
            logger.error(f"提取文本失败: {e}")
            return ""
    
    def close_document(self):
        """关闭当前文档"""
        if self.fitz_document:
            self.fitz_document.close()
            self.fitz_document = None
        self.pdf_document = None
        self.current_file = None
        self.current_page = 0
        self.zoom_factor = 1.0
        # 清除渲染缓存
        self.clear_render_cache()
        # 清空操作历史记录
        self.operation_history.clear_history()
    
    # ===== 操作历史记录相关方法 =====
    
    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return self.operation_history.can_undo()
    
    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return self.operation_history.can_redo()
    
    def undo_operation(self) -> tuple[bool, str]:
        """撤销上一个操作"""
        try:
            operation = self.operation_history.undo()
            if operation:
                # 执行实际的撤销逻辑
                success = self._execute_undo(operation)
                if success:
                    return True, f"撤销成功: {operation.description}"
                else:
                    # 如果撤销执行失败，恢复操作历史记录
                    self.operation_history.redo()
                    return False, "撤销操作执行失败"
            else:
                return False, "没有可撤销的操作"
        except Exception as e:
            logger.error(f"撤销操作失败: {e}")
            return False, f"撤销失败: {str(e)}"
    
    def redo_operation(self) -> tuple[bool, str]:
        """重做下一个操作"""
        try:
            operation = self.operation_history.redo()
            if operation:
                # 执行实际的重做逻辑
                success = self._execute_redo(operation)
                if success:
                    return True, f"重做成功: {operation.description}"
                else:
                    # 如果重做执行失败，恢复操作历史记录
                    self.operation_history.undo()
                    return False, "重做操作执行失败"
            else:
                return False, "没有可重做的操作"
        except Exception as e:
            logger.error(f"重做操作失败: {e}")
            return False, f"重做失败: {str(e)}"
    
    def _execute_undo(self, operation) -> bool:
        """执行撤销操作"""
        try:
            # 根据操作类型执行相应的撤销逻辑
            if operation.operation_type == OperationType.PAGE_ADD:
                # 撤销添加页面：删除该页面
                page_number = operation.parameters.get('page_number')
                return self._delete_page_by_number(page_number - 1)  # 转换为0基索引
            
            elif operation.operation_type == OperationType.PAGE_DELETE:
                # 撤销删除页面：恢复该页面
                page_data = operation.before_state
                return self._restore_page(page_data)
            
            elif operation.operation_type == OperationType.TEXT_ADD:
                # 撤销添加文本：删除该文本
                page_number = operation.parameters.get('page_number')
                position = operation.parameters.get('position')
                return self._delete_text(page_number - 1, position)
            
            elif operation.operation_type == OperationType.TEXT_EDIT:
                # 撤销编辑文本：恢复原始文本
                page_number = operation.parameters.get('page_number')
                old_text = operation.before_state.get('text')
                position = operation.parameters.get('position')
                return self._restore_text(page_number - 1, old_text, position)
            
            elif operation.operation_type == OperationType.ROTATE:
                # 撤销旋转：反向旋转
                page_number = operation.parameters.get('page_number')
                angle = operation.parameters.get('angle')
                return self._rotate_page(page_number - 1, -angle)
            
            # 其他操作类型的撤销逻辑...
            else:
                logger.warning(f"未实现的撤销操作类型: {operation.operation_type}")
                return False
                
        except Exception as e:
            logger.error(f"执行撤销操作失败: {e}")
            return False
    
    def _execute_redo(self, operation) -> bool:
        """执行重做操作"""
        try:
            # 根据操作类型执行相应的重做逻辑
            if operation.operation_type == OperationType.PAGE_ADD:
                # 重做添加页面：重新添加该页面
                page_data = operation.after_state
                return self._add_page_from_data(page_data)
            
            elif operation.operation_type == OperationType.PAGE_DELETE:
                # 重做删除页面：再次删除该页面
                page_number = operation.parameters.get('page_number')
                return self._delete_page_by_number(page_number - 1)
            
            elif operation.operation_type == OperationType.TEXT_ADD:
                # 重做添加文本：重新添加该文本
                page_number = operation.parameters.get('page_number')
                text = operation.parameters.get('text')
                position = operation.parameters.get('position')
                return self._add_text(page_number - 1, text, position)
            
            elif operation.operation_type == OperationType.TEXT_EDIT:
                # 重做编辑文本：重新应用编辑
                page_number = operation.parameters.get('page_number')
                new_text = operation.after_state.get('text')
                position = operation.parameters.get('position')
                return self._edit_text(page_number - 1, new_text, position)
            
            elif operation.operation_type == OperationType.ROTATE:
                # 重做旋转：重新旋转
                page_number = operation.parameters.get('page_number')
                angle = operation.parameters.get('angle')
                return self._rotate_page(page_number - 1, angle)
            
            # 其他操作类型的重做逻辑...
            else:
                logger.warning(f"未实现的重做操作类型: {operation.operation_type}")
                return False
                
        except Exception as e:
            logger.error(f"执行重做操作失败: {e}")
            return False
    
    def add_operation_to_history(self, operation_type: OperationType, **kwargs):
        """添加操作到历史记录"""
        return self.operation_history.add_operation(operation_type, **kwargs)
    
    def get_operation_history_info(self) -> dict:
        """获取操作历史记录信息"""
        return self.operation_history.get_history_info()
    
    def has_unsaved_changes(self) -> bool:
        """检查是否有未保存的更改"""
        return self.operation_history.has_unsaved_changes()
    
    def get_operation_summary(self) -> str:
        """获取操作历史摘要"""
        return self.operation_history.get_operation_summary()
    
    def clear_operation_history(self):
        """清空操作历史记录"""
        self.operation_history.clear_history()
    
    # 以下是具体的操作实现方法（简化示例）
    
    def _delete_page_by_number(self, page_index: int) -> bool:
        """删除指定页面"""
        try:
            if self.fitz_document and 0 <= page_index < len(self.fitz_document):
                self.fitz_document.delete_page(page_index)
                logger.info(f"删除页面: {page_index + 1}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除页面失败: {e}")
            return False
    
    def _restore_page(self, page_data: dict) -> bool:
        """恢复被删除的页面"""
        # 实际实现需要根据page_data恢复页面
        logger.info("恢复页面")
        return True
    
    def _delete_text(self, page_index: int, position: dict) -> bool:
        """删除指定位置的文本"""
        logger.info(f"删除页面 {page_index + 1} 上的文本")
        return True
    
    def _restore_text(self, page_index: int, text: str, position: dict) -> bool:
        """恢复被删除的文本"""
        logger.info(f"恢复页面 {page_index + 1} 上的文本: {text}")
        return True
    
    def _add_text(self, page_index: int, text: str, position: dict) -> bool:
        """添加文本"""
        logger.info(f"在页面 {page_index + 1} 上添加文本: {text}")
        return True
    
    def _edit_text(self, page_index: int, text: str, position: dict) -> bool:
        """编辑文本"""
        logger.info(f"编辑页面 {page_index + 1} 上的文本: {text}")
        return True
    
    def _rotate_page(self, page_index: int, angle: int) -> bool:
        """旋转页面"""
        try:
            if self.fitz_document and 0 <= page_index < len(self.fitz_document):
                page = self.fitz_document[page_index]
                page.set_rotation(angle)
                logger.info(f"旋转页面 {page_index + 1}: {angle}度")
                return True
            return False
        except Exception as e:
            logger.error(f"旋转页面失败: {e}")
            return False
    
    def _add_page_from_data(self, page_data: dict) -> bool:
        """从数据添加页面"""
        logger.info("从数据添加页面")
        return True
    
    # ===== PDF转图片功能 =====
    
    def convert_pdf_to_images(self, output_dir: str, dpi: int = 150, format: str = "JPEG", page_range: str = "all") -> tuple[bool, str]:
        """将PDF转换为图片
        
        Args:
            output_dir: 输出目录路径
            dpi: 图片分辨率（每英寸点数）
            format: 图片格式（PNG/JPEG等）
            page_range: 页面范围，格式如 "all", "1,3,5-9,11-14"
            
        Returns:
            (success, message) 元组
        """
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        try:
            # 检查输出目录是否存在，不存在则创建
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 检查输出目录是否可写
            if not os.access(output_dir, os.W_OK):
                return False, f"输出目录不可写: {output_dir}"
            
            total_pages = len(self.fitz_document)
            
            # 解析页面范围
            page_numbers = self._parse_page_range(page_range, total_pages)
            if not page_numbers:
                return False, f"无效的页面范围: {page_range}"
            
            success_count = 0
            
            # 创建变换矩阵，设置DPI
            zoom_factor = dpi / 72.0  # 72 DPI是PDF的标准分辨率
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            
            # 逐页转换
            for page_num in page_numbers:
                try:
                    page = self.fitz_document[page_num]
                    
                    # 渲染页面为图像
                    pix = page.get_pixmap(
                        matrix=mat,
                        alpha=False,
                        colorspace=fitz.csRGB
                    )
                    
                    # 生成输出文件名
                    filename = f"page_{page_num + 1:03d}.{format.lower()}"
                    output_path = os.path.join(output_dir, filename)
                    
                    # 保存图片
                    if format.upper() == "JPEG" or format.upper() == "JPG":
                        pix.save(output_path, "jpeg")
                    else:
                        pix.save(output_path)
                    
                    success_count += 1
                    
                except Exception as page_error:
                    logger.error(f"转换第{page_num + 1}页失败: {page_error}")
            
            if success_count == len(page_numbers):
                return True, f"成功转换所有{len(page_numbers)}页到目录: {output_dir}"
            elif success_count > 0:
                return True, f"成功转换{success_count}/{len(page_numbers)}页到目录: {output_dir}"
            else:
                return False, "转换失败，所有页面都无法转换"
                
        except Exception as e:
            logger.error(f"PDF转图片失败: {e}")
            return False, f"转换失败: {str(e)}"
    
    def _parse_page_range(self, page_range: str, total_pages: int) -> list[int]:
        """解析页面范围字符串
        
        Args:
            page_range: 页面范围字符串，如 "all", "1,3,5-9,11-14"
            total_pages: 总页数
            
        Returns:
            页面编号列表（从0开始）
        """
        if page_range.lower() == "all":
            return list(range(total_pages))
        
        page_numbers = []
        parts = page_range.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                # 处理范围，如 "5-9"
                range_parts = part.split('-')
                if len(range_parts) == 2:
                    try:
                        start = int(range_parts[0].strip()) - 1  # 转换为0基索引
                        end = int(range_parts[1].strip()) - 1
                        if 0 <= start <= end < total_pages:
                            page_numbers.extend(range(start, end + 1))
                    except ValueError:
                        continue
            else:
                # 处理单个页码
                try:
                    page_num = int(part) - 1  # 转换为0基索引
                    if 0 <= page_num < total_pages:
                        page_numbers.append(page_num)
                except ValueError:
                    continue
        
        # 去重并排序
        return sorted(set(page_numbers))
    
    def get_supported_image_formats(self) -> list[str]:
        """获取支持的图片格式列表"""
        return ["PNG", "JPEG", "BMP", "TIFF"]
    
    def get_recommended_dpi(self) -> dict[str, int]:
        """获取推荐的DPI设置"""
        return {
            "屏幕显示": 96,
            "普通打印": 150,
            "高质量打印": 300,
            "超高质量": 600
        }
    
    # 示例操作方法（供其他模块调用）
    
    def add_page(self, page_number: int, page_data: dict) -> tuple[bool, str]:
        """添加页面并记录操作"""
        try:
            # 实际添加页面的逻辑
            success = True  # 这里应该是实际的添加逻辑
            
            if success:
                # 记录操作到历史记录
                operation = OperationFactory.create_page_add_operation(page_number, page_data)
                self.add_operation_to_history(operation.operation_type, **{
                    'description': operation.description,
                    'parameters': operation.parameters,
                    'after_state': operation.after_state
                })
                return True, "页面添加成功"
            else:
                return False, "页面添加失败"
                
        except Exception as e:
            return False, f"添加页面失败: {str(e)}"
    
    def delete_page(self, page_number: int) -> tuple[bool, str]:
        """删除页面并记录操作"""
        try:
            # 获取页面数据用于撤销
            page_data = self._get_page_data(page_number)
            
            # 实际删除页面的逻辑
            success = self._delete_page_by_number(page_number - 1)
            
            if success:
                # 记录操作到历史记录
                operation = OperationFactory.create_page_delete_operation(page_number, page_data)
                self.add_operation_to_history(operation.operation_type, **{
                    'description': operation.description,
                    'parameters': operation.parameters,
                    'before_state': operation.before_state
                })
                return True, "页面删除成功"
            else:
                return False, "页面删除失败"
                
        except Exception as e:
            return False, f"删除页面失败: {str(e)}"
    
    def _get_page_data(self, page_number: int) -> dict:
        """获取页面数据（用于撤销操作）"""
        # 实际实现需要获取页面的完整数据
        return {
            'page_number': page_number,
            'content': f"页面{page_number}的内容"
        }
    
    def rotate_page(self, page_number: int, angle: int) -> tuple[bool, str]:
        """旋转页面并记录操作"""
        try:
            # 实际旋转页面的逻辑
            success = self._rotate_page(page_number - 1, angle)
            
            if success:
                # 记录操作到历史记录
                operation = OperationFactory.create_rotation_operation(page_number, angle)
                self.add_operation_to_history(operation.operation_type, **{
                    'description': operation.description,
                    'parameters': operation.parameters
                })
                return True, "页面旋转成功"
            else:
                return False, "页面旋转失败"
                
        except Exception as e:
            return False, f"旋转页面失败: {str(e)}"
    
    # ===== 图片导入功能 =====
    
    def import_images(self, image_paths: list, insert_after_page: int = -1) -> tuple[bool, str]:
        """导入图片到PDF
        
        Args:
            image_paths: 图片文件路径列表
            insert_after_page: 插入位置（-1表示末尾，0表示第一页前，其他表示在指定页后）
            
        Returns:
            (success, message) 元组
        """
        if not image_paths:
            return False, "未选择图片文件"
        
        try:
            # 验证图片文件
            valid_image_paths = self._validate_image_files(image_paths)
            if not valid_image_paths:
                return False, "未找到有效的图片文件"
            
            # 场景1: 无打开PDF - 创建新PDF
            if not self.fitz_document:
                return self._create_pdf_from_images(valid_image_paths)
            
            # 场景2: 有打开PDF - 在当前页后插入
            if insert_after_page == -1:
                insert_after_page = len(self.fitz_document) - 1
            elif insert_after_page < -1:
                insert_after_page = -1
            
            return self._insert_images_after_page(valid_image_paths, insert_after_page)
                
        except Exception as e:
            logger.error(f"导入图片失败: {e}")
            return False, f"导入图片失败: {str(e)}"
    
    def _validate_image_files(self, image_paths: list) -> list:
        """验证图片文件有效性"""
        valid_paths = []
        supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif']
        
        for image_path in image_paths:
            if not os.path.exists(image_path):
                logger.warning(f"图片文件不存在: {image_path}")
                continue
                
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext not in supported_formats:
                logger.warning(f"不支持的图片格式: {image_path}")
                continue
                
            valid_paths.append(image_path)
        
        return valid_paths
    
    def _create_pdf_from_images(self, image_paths: list) -> tuple[bool, str]:
        """从图片创建新PDF"""
        try:
            # 创建新的PDF文档
            new_doc = fitz.open()
            
            # 逐张图片添加到PDF
            success_count = 0
            for image_path in image_paths:
                try:
                    # 创建新页面
                    page = new_doc.new_page()
                    
                    # 插入图片到页面
                    success = self._insert_image_to_page(page, image_path)
                    if success:
                        success_count += 1
                        logger.info(f"成功添加图片: {image_path}")
                    else:
                        logger.error(f"添加图片失败: {image_path}")
                        
                except Exception as e:
                    logger.error(f"处理图片失败 {image_path}: {e}")
            
            if success_count == 0:
                new_doc.close()
                return False, "所有图片都无法添加到PDF"
            
            # 关闭当前文档（如果有）
            if self.fitz_document:
                self.fitz_document.close()
            
            # 设置新文档
            self.fitz_document = new_doc
            self.current_file = None  # 新创建的PDF没有文件路径
            self.current_page = 0
            
            # 重置渲染缓存
            self.render_cache.clear_all()
            
            # 发送文档已加载信号
            self.loading_finished.emit(True, f"成功创建PDF，包含{success_count}张图片")
            
            return True, f"成功创建PDF，添加了{success_count}/{len(image_paths)}张图片"
            
        except Exception as e:
            logger.error(f"创建PDF失败: {e}")
            return False, f"创建PDF失败: {str(e)}"
    
    def _insert_images_after_page(self, image_paths: list, after_page: int) -> tuple[bool, str]:
        """在指定页后插入图片"""
        try:
            success_count = 0
            
            # 计算插入位置（从after_page+1开始）
            insert_position = after_page + 1
            
            for image_path in image_paths:
                try:
                    # 在指定位置创建新页面
                    page = self.fitz_document.new_page(insert_position)
                    
                    # 插入图片到页面
                    success = self._insert_image_to_page(page, image_path)
                    if success:
                        success_count += 1
                        insert_position += 1  # 移动到下一个插入位置
                        logger.info(f"成功插入图片: {image_path}")
                    else:
                        # 删除失败的页面
                        self.fitz_document.delete_page(insert_position)
                        logger.error(f"插入图片失败: {image_path}")
                        
                except Exception as e:
                    logger.error(f"处理图片失败 {image_path}: {e}")
            
            if success_count == 0:
                return False, "所有图片都无法插入到PDF"
            
            # 更新当前页码（如果需要）
            if self.current_page > after_page:
                self.current_page += success_count
            
            # 清空缓存，因为页面结构已改变
            self.render_cache.clear_all()
            
            # 发送页面更新信号
            # 注意：当前没有定义page_count_changed信号，使用loading_finished信号通知页面变化
            self.loading_finished.emit(True, f"页面数量已更新，当前共{len(self.fitz_document)}页")
            
            return True, f"成功插入{success_count}/{len(image_paths)}张图片到PDF"
            
        except Exception as e:
            logger.error(f"插入图片失败: {e}")
            return False, f"插入图片失败: {str(e)}"
    
    def _insert_image_to_page(self, page, image_path: str) -> bool:
        """将图片插入到PDF页面"""
        try:
            # 获取页面矩形区域
            page_rect = page.rect
            
            # 计算图片在页面中的位置和尺寸
            # 这里可以优化为保持宽高比，居中显示等
            img_rect = fitz.Rect(50, 50, page_rect.width - 50, page_rect.height - 50)
            
            # 插入图片到页面
            page.insert_image(img_rect, filename=image_path)
            
            return True
            
        except Exception as e:
            logger.error(f"插入图片到页面失败 {image_path}: {e}")
            return False
    
    def get_supported_image_formats_for_import(self) -> list[str]:
        """获取支持导入的图片格式列表"""
        return [
            "所有图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.webp *.ico *.svg)",
            "PNG 图片 (*.png)",
            "JPEG 图片 (*.jpg *.jpeg)",
            "BMP 图片 (*.bmp)",
            "TIFF 图片 (*.tiff *.tif)",
            "GIF 图片 (*.gif)",
            "WebP 图片 (*.webp)",
            "ICO 图标 (*.ico)",
            "SVG 矢量图 (*.svg)"
        ]
    
    def get_supported_image_formats_filter(self) -> str:
        """获取文件选择对话框的格式过滤器"""
        formats = self.get_supported_image_formats_for_import()
        return ";;".join(formats) + ";;所有文件 (*.*)"