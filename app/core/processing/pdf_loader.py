"""PDF加载器 - 处理PDF文件的打开和加载功能"""

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
logger = get_logger('pdf_loader')

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

# 导入新的异步加载器
from .async_loader import AsyncPDFLoader

class PDFLoader:
    """PDF加载器 - 专门处理PDF文件加载功能"""
    
    def __init__(self):
        # 注意：信号需要在主QObject子类中定义
        # fitz_document 和 pdf_document 由 PDFProcessor 统一管理，不在子模块中初始化
        self.current_file = None
        self.total_pages = 0  # 总页数
        self.current_page = 0  # 当前页码（从0开始）
        self.file_size = 0  # 文件大小（字节）
        self.load_time = 0  # 加载时间（秒）
        self.last_error = ""  # 最后错误信息

        # 异步加载器
        self.async_loader = None

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
            # 清除渲染缓存
            if hasattr(self, 'clear_render_cache'):
                self.clear_render_cache()

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
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
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
            self.last_error = ""
            
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
            self.last_error = ""
            
            # 计算适合的缩放比例
            self._calculate_image_zoom(image_path)
            
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
                self.last_error = ""

                # 计算加载时间
                if hasattr(self, 'async_loader') and self.async_loader:
                    self.load_time = time.time() - self.async_loader.load_start_time
                else:
                    # 对于图片加载，使用当前时间作为开始时间
                    self.load_time = 0.0
                
                # 计算适合的缩放比例
                self._calculate_image_zoom(image_info['filepath'])
                
                # 发送加载完成信号
                self.loading_finished.emit(True, message)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"打开PyMuPDF图片文档时出错: {error_msg}")
                self.loading_finished.emit(False, f"初始化渲染引擎失败: {error_msg}")
        else:
            # 发送加载失败信号
            self.loading_finished.emit(False, message)
    
    def open_multiple_images(self, image_paths, async_mode=True, source_directory=None):
        """打开多张图片文件，按顺序依次显示"""
        try:
            logger.info(f"开始加载{len(image_paths)}张图片...")
            
            if not image_paths:
                return False, "没有提供图片文件路径"
            
            if len(image_paths) == 1:
                # 单张图片使用现有方法
                return self.open_pdf(image_paths[0], async_mode)
            
            # 多张图片需要特殊处理
            if async_mode:
                return self.open_multiple_images_async(image_paths, source_directory)
            else:
                return self.open_multiple_images_sync(image_paths, source_directory)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"打开多张图片时出错: {error_msg}")
            return False, f"打开多张图片失败: {error_msg}"
    
    def open_multiple_images_async(self, image_paths, source_directory=None):
        """异步打开多张图片"""
        try:
            # 验证所有图片文件
            valid_paths = []
            for path in image_paths:
                if os.path.exists(path) and os.access(path, os.R_OK):
                    valid_paths.append(path)
                else:
                    logger.warning(f"跳过无效图片文件: {path}")
            
            if not valid_paths:
                return False, "没有有效的图片文件"
            
            # 取消之前的加载任务
            if self.async_loader and self.async_loader.isRunning():
                self.async_loader.cancel()
                self.async_loader.wait()
            
            # 创建多图片异步加载器
            from PyQt5.QtCore import QThread
            
            class AsyncMultipleImagesLoader(QThread):
                def __init__(self, parent, image_paths, source_directory=None):
                    super().__init__()
                    self.parent = parent
                    self.image_paths = image_paths
                    self.source_directory = source_directory
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
                        
                        # 验证所有图片文件是否可以被PyMuPDF打开
                        import fitz
                        valid_images = []
                        
                        for i, path in enumerate(self.image_paths):
                            if self.is_cancelled:
                                return
                            
                            try:
                                # 尝试打开图片
                                doc = fitz.open(path)
                                pages = len(doc)
                                doc.close()
                                
                                if pages > 0:
                                    valid_images.append({
                                        'filepath': path,
                                        'pages': pages,
                                        'index': i
                                    })
                                else:
                                    logger.warning(f"图片文件没有页面: {path}")
                                    
                            except Exception as e:
                                logger.warning(f"无法打开图片文件 {path}: {e}")
                                continue
                        
                        # 检查是否被取消
                        if self.is_cancelled:
                            return
                        
                        if not valid_images:
                            self.error = "没有有效的图片文件"
                            return
                        
                        # 按原始顺序排序
                        valid_images.sort(key=lambda x: x['index'])
                        
                        # 准备结果
                        result = {
                            'image_paths': [img['filepath'] for img in valid_images],
                            'total_pages': sum(img['pages'] for img in valid_images),
                            'image_count': len(valid_images),
                            'source_directory': self.source_directory,
                            'file_sizes': [os.path.getsize(img['filepath']) for img in valid_images]
                        }
                        
                        self.result = result
                        
                    except Exception as e:
                        self.error = str(e)
            
            # 创建加载器
            loader = AsyncMultipleImagesLoader(self, valid_paths, source_directory)
            self.async_loader = loader
            
            def on_multiple_images_load_complete():
                if loader.error:
                    self.loading_finished.emit(False, f"无法加载多张图片: {loader.error}")
                else:
                    self._on_multiple_images_loaded(True, f"成功加载{loader.result['image_count']}张图片，共{loader.result['total_pages']}页", loader.result)
            
            loader.finished.connect(on_multiple_images_load_complete)
            loader.start()
            
            return True, f"开始异步加载{len(valid_paths)}张图片..."
            
        except Exception as e:
            return False, f"启动多图片异步加载失败: {str(e)}"
    
    def open_multiple_images_sync(self, image_paths, source_directory=None):
        """同步打开多张图片"""
        try:
            # 强制关闭旧文档
            if self.fitz_document:
                try:
                    self.fitz_document.close()
                except:
                    pass
                self.fitz_document = None
            
            # 验证所有图片文件
            valid_paths = []
            for path in image_paths:
                if os.path.exists(path) and os.access(path, os.R_OK):
                    valid_paths.append(path)
                else:
                    logger.warning(f"跳过无效图片文件: {path}")
            
            if not valid_paths:
                return False, "没有有效的图片文件"
            
            # 创建新的PyMuPDF文档，将多张图片合并到一个文档中
            self.fitz_document = fitz.open()  # 创建空文档
            
            # 添加每张图片作为新页面
            for path in valid_paths:
                try:
                    # 直接在当前文档中创建新页面并插入图片
                    img = fitz.open(path)  # 打开图片
                    img_page = img[0]  # 获取图片页面
                    
                    # 获取图片尺寸
                    img_rect = img_page.rect
                    new_page = self.fitz_document.new_page(width=img_rect.width, height=img_rect.height)
                    
                    # 将图片插入到新页面
                    new_page.insert_image(new_page.rect, filename=path)
                    
                    img.close()
                except Exception as e:
                    logger.error(f"处理图片 {path} 时出错: {e}")
                    continue
            
            # 更新处理器状态
            self.current_file = f"多图片文档 - {len(valid_paths)}张图片" if not source_directory else f"目录: {os.path.basename(source_directory)}"
            self.total_pages = len(self.fitz_document)
            self.current_page = 0
            self.last_error = ""
            # 标记这是新建的多图片文档，需要另存为
            self.is_new_document = True
            # 设置多图片路径属性，用于状态栏显示
            self.multi_image_paths = valid_paths.copy()
            self.multi_image_source_dir = source_directory

            # 存储原始图片路径信息，供导航使用
            self.multi_image_paths = valid_paths
            self.multi_image_source_dir = source_directory
            
            # 计算文件总大小
            total_size = sum(os.path.getsize(path) for path in valid_paths if os.path.exists(path))
            
            # 计算适合的缩放比例（针对第一张图片）
            if valid_paths:
                self._calculate_image_zoom(valid_paths[0])
            
            return True, f"成功加载{len(valid_paths)}张图片，共{self.total_pages}页"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"同步加载多张图片时出错: {error_msg}")
            return False, f"加载多张图片失败: {error_msg}"
    
    def _on_multiple_images_loaded(self, success, message, result):
        """多张图片异步加载完成回调"""
        if success:
            try:
                # 强制关闭旧的fitz文档
                if self.fitz_document:
                    try:
                        self.fitz_document.close()
                    except:
                        pass
                    self.fitz_document = None
                
                # 创建新的PyMuPDF文档
                import fitz
                self.fitz_document = fitz.open()  # 创建空文档
                
                # 添加每张图片作为新页面
                for path in result['image_paths']:
                    try:
                        # 直接在当前文档中创建新页面并插入图片
                        img = fitz.open(path)  # 打开图片
                        img_page = img[0]  # 获取图片页面
                        
                        # 获取图片尺寸
                        img_rect = img_page.rect
                        new_page = self.fitz_document.new_page(width=img_rect.width, height=img_rect.height)
                        
                        # 将图片插入到新页面
                        new_page.insert_image(new_page.rect, filename=path)
                        
                        img.close()
                    except Exception as e:
                        logger.error(f"处理图片 {path} 时出错: {e}")
                        continue
                
                # 更新处理器状态
                if result['source_directory']:
                    self.current_file = f"目录: {os.path.basename(result['source_directory'])}"
                else:
                    self.current_file = f"多图片文档 - {len(result['image_paths'])}张图片"
                
                self.total_pages = len(self.fitz_document)
                self.current_page = 0
                self.last_error = ""
                # 标记这是新建的多图片文档，需要另存为
                self.is_new_document = True
                # 设置多图片路径属性，用于状态栏显示
                self.multi_image_paths = result['image_paths'].copy()
                self.multi_image_source_dir = result['source_directory']

                # 存储原始图片路径信息
                self.multi_image_paths = result['image_paths']
                self.multi_image_source_dir = result['source_directory']
                
                # 计算加载时间
                if hasattr(self, 'async_loader') and self.async_loader:
                    self.load_time = time.time() - self.async_loader.load_start_time
                else:
                    self.load_time = 0.0
                
                # 发送加载完成信号
                self.loading_finished.emit(True, message)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"初始化多图片文档时出错: {error_msg}")
                self.loading_finished.emit(False, f"初始化多图片文档失败: {error_msg}")
        else:
            # 发送加载失败信号
            self.loading_finished.emit(False, message)
    
    def open_images_from_directory(self, directory_path, async_mode=True):
        """从目录打开所有图片并合并为PDF"""
        try:
            # 获取目录中的所有图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
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
                # 打开图片并获取尺寸
                img = fitz.open(image_path)
                img_page = img[0]
                img_rect = img_page.rect
                
                # 创建新页面并插入图片
                new_page = new_doc.new_page(width=img_rect.width, height=img_rect.height)
                new_page.insert_image(new_page.rect, filename=image_path)
                
                img.close()
            
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
            self.last_error = ""
            # 标记这是新建的目录文档，需要另存为
            self.is_new_document = True
            # 设置多图片路径属性，用于状态栏显示
            self.multi_image_paths = image_files.copy()
            self.multi_image_source_dir = directory_path
            
            # 计算适合的缩放比例（针对第一张图片）
            if image_files:
                self._calculate_image_zoom(image_files[0])
            
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
                error_msg = "文件不存在"
                self.loading_finished.emit(False, error_msg)
                return False, error_msg

            if not os.access(file_path, os.R_OK):
                error_msg = "文件不可读"
                self.loading_finished.emit(False, error_msg)
                return False, error_msg

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
                            error_msg = "密码错误，无法解密PDF文件"
                            self.loading_finished.emit(False, error_msg)
                            return False, error_msg
                    except Exception as e:
                        error_msg = f"解密失败: {str(e)}"
                        self.loading_finished.emit(False, error_msg)
                        return False, error_msg
                else:
                    error_msg = "PDF文件已加密，需要密码才能打开"
                    self.loading_finished.emit(False, error_msg)
                    return False, error_msg

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
                                        error_msg = "密码错误，无法解密PDF文件"
                                        self.loading_finished.emit(False, error_msg)
                                        return False, error_msg
                                except Exception as e:
                                    error_msg = f"解密失败: {str(e)}"
                                    self.loading_finished.emit(False, error_msg)
                                    return False, error_msg
                            else:
                                error_msg = "PDF文件已加密，需要密码才能打开"
                                self.loading_finished.emit(False, error_msg)
                                return False, error_msg

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
                            error_msg = "PDF文件不完整或已损坏，无法访问页面内容"
                            self.loading_finished.emit(False, error_msg)
                            return False, error_msg

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
                                        error_msg = "密码错误，无法打开PDF文件"
                                        self.loading_finished.emit(False, error_msg)
                                        return False, error_msg
                                else:
                                    self.fitz_document.close()
                                    self.fitz_document = None
                                    error_msg = "PDF文件已加密，需要密码才能打开"
                                    self.loading_finished.emit(False, error_msg)
                                    return False, error_msg
                        except Exception as e:
                            error_msg = str(e)
                            # 检查是否是PyMuPDF无法打开损坏文档的错误
                            if "cannot open" in error_msg.lower() and ("broken" in error_msg.lower() or "damaged" in error_msg.lower()):
                                error_msg = f"PDF文件不完整或已损坏，无法渲染: {error_msg}"
                            elif "password" in error_msg.lower():
                                error_msg = "密码错误，无法打开PDF文件"
                            else:
                                error_msg = f"初始化渲染引擎失败: {error_msg}"
                            self.loading_finished.emit(False, error_msg)
                            return False, error_msg
                    except Exception as e:
                        error_msg = f"PDF文件不完整或已损坏，且自动修复失败: {str(e)}"
                        self.loading_finished.emit(False, error_msg)
                        return False, error_msg
                else:
                    error_msg = "PDF文件不完整或已损坏，无法访问页面内容"
                    self.loading_finished.emit(False, error_msg)
                    return False, error_msg

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
                            error_msg = "密码错误，无法打开PDF文件"
                            self.loading_finished.emit(False, error_msg)
                            return False, error_msg
                    else:
                        self.fitz_document.close()
                        self.fitz_document = None
                        error_msg = "PDF文件已加密，需要密码才能打开"
                        self.loading_finished.emit(False, error_msg)
                        return False, error_msg
            except Exception as e:
                error_msg = str(e)
                # 检查是否是PyMuPDF无法打开损坏文档的错误
                if "cannot open" in error_msg.lower() and ("broken" in error_msg.lower() or "damaged" in error_msg.lower()):
                    error_msg = f"PDF文件不完整或已损坏，无法渲染: {error_msg}"
                elif "password" in error_msg.lower():
                    error_msg = "密码错误，无法打开PDF文件"
                else:
                    error_msg = f"初始化渲染引擎失败: {error_msg}"
                self.loading_finished.emit(False, error_msg)
                return False, error_msg

            # 重置状态
            self.current_file = file_path
            self.total_pages = len(self.pdf_document.pages) if self.pdf_document else len(self.fitz_document)
            self.current_page = 0
            self.last_error = ""

            # 计算加载时间
            self.load_time = time.time() - start_time

            # 发射加载完成信号,触发UI更新和渲染
            success_message = f"文件打开成功 ({self.get_file_size_str()}, {self.load_time:.2f}秒)"
            self.loading_finished.emit(True, success_message)

            return True, success_message

        except PdfReadError as e:
            error_msg = str(e)
            # 检查是否是EOF marker错误
            if "EOF" in error_msg or "marker" in error_msg:
                self.last_error = f"PDF文件不完整或已损坏: {error_msg}"
            else:
                self.last_error = f"PDF文件格式错误: {error_msg}"
            self.loading_finished.emit(False, self.last_error)
            return False, self.last_error
        except Exception as e:
            error_msg = str(e)
            # 检查是否是EOF marker错误
            if "EOF" in error_msg or "marker" in error_msg:
                self.last_error = f"PDF文件不完整或已损坏: {error_msg}"
            else:
                self.last_error = f"无法打开PDF文件: {error_msg}"
            self.loading_finished.emit(False, self.last_error)
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
                self.last_error = ""

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