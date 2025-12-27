"""
异步PDF加载器
提供后台线程加载PDF功能，避免阻塞UI主线程
"""

import os
import time
import sys

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('async_loader')

from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QProgressDialog, QMessageBox
import PyPDF2
from PyPDF2.errors import PdfReadError, PdfReadWarning
import fitz  # PyMuPDF


class AsyncPDFLoader(QThread):
    """异步PDF加载器线程"""

    # 信号定义
    loading_progress = pyqtSignal(int, str)  # 进度百分比, 状态信息
    loading_finished = pyqtSignal(bool, str, dict)  # 是否成功, 消息, PDF信息
    loading_error = pyqtSignal(str)  # 错误信息

    def __init__(self, file_path, password=None):
        super().__init__()
        self.file_path = file_path
        self.password = password
        self.is_cancelled = False
        self.should_cancel = False
        
    def run(self):
        """执行异步加载"""
        pdf_document = None

        try:
            self.loading_progress.emit(0, "开始加载PDF文件...")

            # 检查文件是否存在和可读
            if self.is_cancelled:
                return

            if not os.path.exists(self.file_path):
                self.loading_error.emit("文件不存在")
                return

            if not os.access(self.file_path, os.R_OK):
                self.loading_error.emit("文件不可读")
                return

            self.loading_progress.emit(10, "验证文件格式...")

            # 获取文件大小
            file_size = os.path.getsize(self.file_path)

            # 使用PyPDF2打开文件获取基本信息
            if self.is_cancelled:
                return

            self.loading_progress.emit(20, "读取PDF结构...")

            try:
                pdf_document = PyPDF2.PdfReader(self.file_path)

                # 检查是否加密
                if pdf_document.is_encrypted:
                    if self.password:
                        # 尝试使用密码解密
                        try:
                            result = pdf_document.decrypt(self.password)
                            if result == 0:
                                self.loading_error.emit("密码错误，无法解密PDF文件")
                                return
                        except Exception as e:
                            self.loading_error.emit(f"解密失败: {str(e)}")
                            return
                    else:
                        self.loading_error.emit("PDF文件已加密，需要密码才能打开")
                        return

                total_pages = len(pdf_document.pages)

                # 额外验证PDF文件完整性
                try:
                    # 尝试访问第一页来验证PDF是否可读
                    if total_pages > 0:
                        first_page = pdf_document.pages[0]
                        # 尝试获取页面的基本信息来验证完整性
                        _ = first_page.get('/MediaBox', [0, 0, 612, 792])
                except Exception:
                    # 如果访问页面失败，可能是文件损坏
                    self.loading_error.emit("PDF文件不完整或已损坏，无法访问页面内容")
                    return

            except PdfReadError as e:
                error_msg = str(e)
                # 检查是否是EOF marker错误
                if "EOF" in error_msg or "marker" in error_msg or "startxref" in error_msg:
                    # 尝试修复不完整的PDF文件
                    from app.utils.pdf_fixer import try_fix_pdf_file
                    fixed_file_path = try_fix_pdf_file(self.file_path)
                    if fixed_file_path:
                        try:
                            # 使用修复后的文件
                            pdf_document = PyPDF2.PdfReader(fixed_file_path)

                            # 检查是否加密
                            if pdf_document.is_encrypted:
                                if self.password:
                                    # 尝试使用密码解密
                                    try:
                                        result = pdf_document.decrypt(self.password)
                                        if result == 0:
                                            self.loading_error.emit("密码错误，无法解密PDF文件")
                                            return
                                    except Exception as e:
                                        self.loading_error.emit(f"解密失败: {str(e)}")
                                        return
                                else:
                                    self.loading_error.emit("PDF文件已加密，需要密码才能打开")
                                    return

                            total_pages = len(pdf_document.pages)

                            # 额外验证PDF文件完整性
                            try:
                                # 尝试访问第一页来验证PDF是否可读
                                if total_pages > 0:
                                    first_page = pdf_document.pages[0]
                                    # 尝试获取页面的基本信息来验证完整性
                                    _ = first_page.get('/MediaBox', [0, 0, 612, 792])
                            except Exception:
                                # 如果访问页面失败，可能是文件损坏
                                self.loading_error.emit("PDF文件不完整或已损坏，无法访问页面内容")
                                return
                        except Exception:
                            self.loading_error.emit(f"PDF文件不完整或已损坏，且自动修复失败: {error_msg}")
                            return
                    else:
                        self.loading_error.emit(f"PDF文件不完整或已损坏: {error_msg}")
                        return
                else:
                    self.loading_error.emit(f"PDF文件格式错误: {error_msg}")
                    return
            except Exception as e:
                error_msg = str(e)
                # 检查是否是EOF marker错误
                if "EOF" in error_msg or "marker" in error_msg or "startxref" in error_msg:
                    self.loading_error.emit(f"PDF文件不完整或已损坏: {error_msg}")
                else:
                    self.loading_error.emit(f"读取PDF失败: {error_msg}")
                return

            self.loading_progress.emit(40, "验证文档可访问性...")

            # 在异步加载中只验证文档基本信息，不创建PyMuPDF文档
            # PyMuPDF文档将在主线程中创建，避免Graftmaps错误

            self.loading_progress.emit(60, "提取文档信息...")

            # 提取文档元数据
            metadata = {}
            try:
                if hasattr(pdf_document, 'metadata') and pdf_document.metadata:
                    metadata = {str(k): str(v) for k, v in pdf_document.metadata.items()}
            except:
                pass

            self.loading_progress.emit(80, "准备渲染环境...")

            # 准备PDF信息字典 - 不包含fitz_document，在主线程中打开
            # 但需要传递加密状态信息
            pdf_info = {
                'filepath': self.file_path,
                'filename': os.path.basename(self.file_path),
                'file_size': file_size,
                'file_size_str': self._format_file_size(file_size),
                'total_pages': total_pages,
                'is_encrypted': pdf_document.is_encrypted,
                'metadata': metadata,
                'pdf_document': pdf_document,
                'password': self.password
            }

            # 模拟加载进度
            for i in range(80, 100, 5):
                if self.is_cancelled:
                    return
                self.loading_progress.emit(i, f"加载中... {i}%")
                self.msleep(50)  # 短暂延迟以显示进度

            self.loading_progress.emit(100, "加载完成")

            # 发送完成信号
            load_time = time.time() - self.thread().load_start_time if hasattr(self.thread(), 'load_start_time') else 0
            success_message = f"文件加载成功 ({pdf_info['file_size_str']}, {load_time:.2f}秒)"
            
            self.loading_finished.emit(True, success_message, pdf_info)

        except Exception as e:
            self.loading_error.emit(f"加载过程中发生未知错误: {str(e)}")
            
    def cancel(self):
        """取消加载"""
        self.is_cancelled = True
        self.should_cancel = True
        
    def _try_fix_pdf_file(self, file_path):
        """
        尝试修复不完整的PDF文件
        返回修复后的文件路径，如果修复失败则返回None
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 检查是否已有EOF标记
            if b'%%EOF' in content[-20:]:  # 检查最后20个字节
                return None  # 已有EOF标记，无需修复
            
            # 尝试添加基本的PDF尾部结构
            fixed_content = content + b'\ntrailer\n<<\n/Size 1\n>>\nstartxref\n' + str(len(content)).encode() + b'\n%%EOF\n'
            
            # 生成修复后的文件路径（使用临时文件）
            import tempfile
            import os
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='fixed_')
            
            try:
                with os.fdopen(temp_fd, 'wb') as tmp_file:
                    tmp_file.write(fixed_content)
                
                # 验证修复后的文件是否可以打开
                import PyPDF2
                from PyPDF2.errors import PdfReadError
                
                try:
                    test_doc = PyPDF2.PdfReader(temp_path)
                    # 如果能成功打开，返回临时文件路径
                    return temp_path
                except PdfReadError:
                    # 如果还是打不开，删除临时文件并返回None
                    os.close(temp_fd)  # 确保文件句柄已关闭
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return None
            except Exception:
                # 如果写入临时文件失败，确保清理
                os.close(temp_fd)  # 确保文件句柄已关闭
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return None
        except Exception:
            return None
    
    def _format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"


class AsyncThumbnailLoader(QThread):
    """异步缩略图加载器"""
    
    # 信号定义
    thumbnail_progress = pyqtSignal(int, int)  # 当前页, 总页数
    thumbnail_ready = pyqtSignal(int, object)  # 页码, QPixmap
    thumbnail_finished = pyqtSignal()  # 缩略图加载完成
    
    def __init__(self, fitz_document, zoom_factor=0.2):
        super().__init__()
        self.fitz_document = fitz_document
        self.zoom_factor = zoom_factor
        self.is_cancelled = False
        self.batch_size = 3  # 每批处理的页数
        
    def run(self):
        """异步加载缩略图"""
        if not self.fitz_document:
            return
            
        try:
            total_pages = len(self.fitz_document)
            
            # 分批加载缩略图，避免一次性处理过多
            for start_page in range(0, total_pages, self.batch_size):
                if self.is_cancelled:
                    break
                    
                end_page = min(start_page + self.batch_size, total_pages)
                
                # 加载当前批次的缩略图
                for page_num in range(start_page, end_page):
                    if self.is_cancelled:
                        break
                        
                    try:
                        # 生成缩略图
                        page = self.fitz_document[page_num]
                        mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                        pix = page.get_pixmap(matrix=mat)
                        
                        # 转换为QPixmap
                        img_data = pix.tobytes("ppm")
                        from PyQt5.QtGui import QImage, QPixmap
                        from PyQt5.QtCore import Qt
                        
                        image = QImage.fromData(img_data)
                        thumbnail = QPixmap.fromImage(image)
                        
                        # 发送缩略图就绪信号
                        self.thumbnail_ready.emit(page_num, thumbnail)
                        self.thumbnail_progress.emit(page_num + 1, total_pages)
                        
                    except Exception as e:
                        logger.error(f"生成第{page_num + 1}页缩略图失败: {e}")
                        continue
                        
                # 短暂延迟，让UI有时间响应
                self.msleep(10)
                
            if not self.is_cancelled:
                self.thumbnail_finished.emit()
                
        except Exception as e:
            logger.error(f"缩略图加载失败: {e}")
            
    def cancel(self):
        """取消缩略图加载"""
        self.is_cancelled = True


class AsyncPageRenderer(QThread):
    """异步页面渲染器"""
    
    # 信号定义
    page_rendered = pyqtSignal(int, object)  # 页码, QPixmap
    render_finished = pyqtSignal()  # 渲染完成
    
    def __init__(self, fitz_document, page_nums, zoom_factor, render_size=(800, 1000)):
        super().__init__()
        self.fitz_document = fitz_document
        self.page_nums = page_nums
        self.zoom_factor = zoom_factor
        self.render_size = render_size
        self.is_cancelled = False
        
    def run(self):
        """异步渲染页面"""
        if not self.fitz_document:
            return
            
        try:
            for page_num in self.page_nums:
                if self.is_cancelled:
                    break
                    
                try:
                    # 渲染页面
                    page = self.fitz_document[page_num]
                    mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                    pix = page.get_pixmap(
                        matrix=mat,
                        alpha=False,
                        colorspace=fitz.csRGB,
                        annots=True,
                        clip=page.rect
                    )
                    
                    # 转换为QPixmap
                    from PyQt5.QtGui import QImage, QPixmap
                    
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
                        img_data = pix.tobytes("ppm")
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_data)
                        
                    self.page_rendered.emit(page_num, pixmap)
                    
                except Exception as e:
                    logger.error(f"渲染第{page_num + 1}页失败: {e}")
                    continue
                    
            if not self.is_cancelled:
                self.render_finished.emit()
                
        except Exception as e:
            logger.error(f"页面渲染失败: {e}")
            
    def cancel(self):
        """取消渲染"""
        self.is_cancelled = True