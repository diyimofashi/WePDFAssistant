"""PDF渲染器 - 处理PDF页面渲染、缩略图生成和缓存管理功能"""

import os
import tempfile
import fitz  # PyMuPDF - 用于PDF页面渲染
import sys
import time
import shutil

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('pdf_renderer')

from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

import traceback
from ..performance.cache_manager import RenderCache, DiskCache
from app.config.settings import AppSettings
from .pdf_conversion import PDFConversion
from ..editing.page_editor import PageEditor
from .pdf_operations import PDFOperations

# 简化的异步加载器占位类
class AsyncPageRenderer:
    """简化版异步页面渲染器占位"""
    def __init__(self, *args, **kwargs):
        pass

    def isRunning(self):
        return False

    def cancel(self):
        pass

    def wait(self):
        pass

    def start(self):
        pass

class AsyncThumbnailLoader:
    """简化版异步缩略图加载器占位"""
    def __init__(self, *args, **kwargs):
        pass

    def isRunning(self):
        return False

    def cancel(self):
        pass

    def wait(self):
        pass

    def start(self):
        pass


class PDFRenderer(QObject):
    """PDF渲染器 - 专门处理页面渲染和缓存功能"""

    # 信号定义
    loading_progress = pyqtSignal(int, str)  # 加载进度 (百分比, 消息)
    loading_finished = pyqtSignal(bool, str)  # 加载完成 (成功标志, 消息)
    page_loaded = pyqtSignal()  # 页面加载完成
    page_rendered = pyqtSignal(object)  # 页面渲染完成
    thumbnail_ready = pyqtSignal(int, object)  # 缩略图准备完成 (页码, 图片)
    operation_history_changed = pyqtSignal()  # 操作历史改变
    page_changed = pyqtSignal(int)  # 页面改变
    zoom_changed = pyqtSignal(float)  # 缩放改变

    def __init__(self, parent=None):
        super().__init__(parent)
        # fitz_document 由 PDFProcessor 统一管理，不在子模块中初始化
        self.fitz_document = None  # PyMuPDF 文档对象
        self.pdf_document = None  # 别名，用于向后兼容
        self.current_page = 0  # 当前页码（从0开始）
        self.current_file = None  # 当前文件路径
        self.zoom_factor = 2.0  # 缩放因子（设置为2.0，即200%作为新的100%基准）
        self.base_zoom = 2.0  # 基准缩放因子（用户看到的100%实际是200%基准）
        self.page_editor = None  # 页面编辑器

        # A4缩放设置
        self.use_a4_scaling = AppSettings.get_use_a4_scaling()  # 是否使用A4缩放

        # 异步加载器
        self.thumbnail_loader = None
        self.page_renderer = None

        # 新的缓存系统
        self.render_cache = RenderCache(max_memory_mb=200, max_items=50)
        # 使用系统缓存目录
        cache_dir = os.path.join(AppSettings.get_app_data_path(), "cache")
        self.disk_cache = DiskCache(cache_dir=cache_dir, max_size_mb=500)

        # 向后兼容的简单缓存
        self.simple_cache = {}
        self.cache_max_size = 10

        # 连续浏览模式属性
        self.continuous_mode = True  # 是否启用连续浏览模式
        self.pages_per_view = 3  # 连续模式下每次显示的页面数
        self.page_spacing = 20  # 页面间距（像素）

    def get_current_page(self):
        """获取当前页码（用户可见的页码，从1开始）"""
        return self.current_page + 1 if self.fitz_document else 0

    def get_total_pages(self):
        """获取总页数"""
        return len(self.fitz_document) if self.fitz_document else 0

    def set_zoom(self, zoom_factor):
        """设置缩放比例"""
        # 将用户的缩放值转换为实际缩放值
        actual_zoom = zoom_factor * self.base_zoom

        # 限制实际缩放范围在8%-6400%（对应用户看到的8%-6400%）
        if 0.08 <= zoom_factor <= 64.0:
            self.zoom_factor = actual_zoom
            # 清除渲染缓存，因为缩放级别已更改
            self.clear_render_cache()
            return True, f"缩放比例已设置为{int(zoom_factor * 100)}%"
        else:
            return False, "缩放比例必须在8%-6400%之间"

    def set_use_a4_scaling(self, enabled):
        """设置是否使用A4缩放"""
        self.use_a4_scaling = bool(enabled)
        AppSettings.set_use_a4_scaling(enabled)
        # 清除渲染缓存，因为缩放方式已更改
        self.clear_render_cache()
        logger.info(f"A4缩放设置已更新: {enabled}")

    def get_use_a4_scaling(self):
        """获取是否使用A4缩放"""
        return self.use_a4_scaling
    
    def get_zoom(self):
        """获取当前缩放比例（返回用户看到的相对值）"""
        return self.zoom_factor / self.base_zoom

    def render_page(self, width=800, height=1000):
        """渲染当前页面为高质量图像 - 优化显示效果和性能"""
        if not self.fitz_document:
            return None

        try:
            # 获取页面实际尺寸
            page = self.fitz_document[self.current_page]
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height

            # A4纸标准尺寸（点）
            A4_WIDTH = 595

            # 计算缩放因子：如果页面宽度超过A4宽度，自动缩放到A4宽度
            zoom = self.zoom_factor
            if page_width > A4_WIDTH:
                zoom = zoom * (A4_WIDTH / page_width)

            render_width = int(page_width * zoom)
            render_height = int(page_height * zoom)

            # 首先检查内存缓存
            cached_pixmap = self.render_cache.get_rendered_page(
                self.current_page, zoom, (render_width, render_height)
            )
            if cached_pixmap:
                return cached_pixmap

            # 检查磁盘缓存
            disk_key = f"page_{self.current_page}_zoom_{zoom:.2f}_size_{render_width}x{render_height}"
            disk_pixmap = self.disk_cache.get(disk_key)
            if disk_pixmap:
                # 将磁盘缓存的内容放入内存缓存
                self.render_cache.put_rendered_page(
                    self.current_page, zoom, (render_width, render_height), disk_pixmap
                )
                return disk_pixmap

            # 缓存未命中，进行渲染
            # 传递计算后的渲染尺寸，而不是固定的 width 和 height 参数
            return self._render_page_sync(self.current_page, render_width, render_height)

        except Exception as e:
            logger.error(f"渲染页面失败: {e}")
            return False
    
    def _render_page_sync(self, page_num, render_width=800, render_height=1000):
        """同步渲染指定页面

        Args:
            page_num: 页码
            render_width: 渲染宽度（如果为None，则根据页面尺寸和缩放因子计算）
            render_height: 渲染高度（如果为None，则根据页面尺寸和缩放因子计算）
        """
        try:
            # 获取页面
            page = self.fitz_document[page_num]

            # 获取页面实际尺寸
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height

            # A4纸标准尺寸（点）
            A4_WIDTH = 595

            # 计算缩放因子：如果页面宽度超过A4宽度，自动缩放到A4宽度
            zoom = self.zoom_factor
            if page_width > A4_WIDTH:
                zoom = zoom * (A4_WIDTH / page_width)
                logger.debug(f"页面{page_num}宽度({page_width:.1f})超过A4，自动缩放因子: {zoom:.2f}")

            # 如果没有传入渲染尺寸，则根据页面尺寸和缩放因子计算
            if render_width == 800 and render_height == 1000:
                # 使用默认值，说明需要计算
                render_width = int(page_width * zoom)
                render_height = int(page_height * zoom)

            # 创建变换矩阵进行缩放
            mat = fitz.Matrix(zoom, zoom)
            
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
                page_num, zoom, (render_width, render_height), pixmap
            )

            # 缓存到磁盘（异步进行，不阻塞）
            try:
                disk_key = f"page_{page_num}_zoom_{zoom:.2f}_size_{render_width}x{render_height}"
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

    def get_page_dimensions(self, page_num=None, apply_auto_scaling=True):
        """获取指定页面的尺寸信息

        Args:
            page_num: 页码（默认当前页）
            apply_auto_scaling: 是否应用自动缩放（统一缩放到A4宽度）
        """
        if not self.fitz_document:
            return None

        if page_num is None:
            page_num = self.current_page

        try:
            page = self.fitz_document[page_num]
            rect = page.rect
            width = rect.width
            height = rect.height

            # 如果需要应用自动缩放并且启用了A4缩放，统一缩放到A4宽度
            if apply_auto_scaling and self.use_a4_scaling:
                A4_WIDTH = 595
                # 计算缩放比例（所有页面都缩放到A4宽度）
                scale = A4_WIDTH / width
                width = A4_WIDTH
                height = height * scale

            return {
                'width': width,
                'height': height,
                'size': f"{rect.width:.1f} × {rect.height:.1f} 点"
            }
        except:
            return None

    def render_page_at(self, page_num, width=800, height=1000):
        """渲染指定页面为高质量图像 - 优化显示效果和性能"""
        logger.debug(f"开始渲染第{page_num + 1}页 (width={width}, height={height})")

        # 调试：检查 fitz_document 的来源
        doc_id = id(self.fitz_document) if self.fitz_document else None
        doc_len = len(self.fitz_document) if self.fitz_document else 0
        logger.debug(f"[render_page_at] fitz_document id: {doc_id}, 长度: {doc_len}")

        if not self.fitz_document or page_num < 0 or page_num >= len(self.fitz_document):
            logger.warning("文档未加载或页码无效")
            return None

        # 初始化渲染尺寸，用于异常处理
        render_width = width
        render_height = height

        try:
            # 检查文档是否仍然有效
            if not self.fitz_document:
                logger.warning("文档引用为空，无法渲染页面")
                return None

            # 尝试访问文档属性来检查是否仍然有效
            try:
                _ = len(self.fitz_document)  # 尝试获取文档长度
            except ValueError as e:
                if "closed" in str(e).lower() or "encrypted" in str(e).lower():
                    logger.warning(f"文档已关闭或加密，无法访问: {e}")
                    return None
                raise  # 重新抛出其他异常

            # 获取页面
            page = self.fitz_document[page_num]
            logger.debug(f"获取页面对象成功: {page}")

            # 获取页面实际尺寸
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            logger.debug(f"页面尺寸: {page_width} x {page_height}")

            # A4纸标准尺寸（点）
            A4_WIDTH = 595

            # 根据设置决定是否使用A4缩放
            if self.use_a4_scaling:
                # 所有页面统一缩放到A4宽度，然后应用zoom_factor
                # 计算缩放到A4宽度的缩放比例
                a4_scale = A4_WIDTH / page_width
                # 计算最终的缩放因子：A4缩放比例 * zoom_factor
                zoom = a4_scale * self.zoom_factor
                logger.debug(f"页面{page_num}原始宽度({page_width:.1f})缩放到A4({A4_WIDTH})，缩放比例={a4_scale:.2f}，总zoom={zoom:.2f}")
                # 渲染宽度 = A4宽度 * zoom_factor
                render_width = int(A4_WIDTH * self.zoom_factor)
                # 渲染高度 = 原始高度 * A4缩放比例 * zoom_factor
                render_height = int(page_height * zoom)
            else:
                # 不使用A4缩放，直接使用原始尺寸乘以zoom_factor
                zoom = self.zoom_factor
                logger.debug(f"页面{page_num}使用原始尺寸，zoom={zoom:.2f}")
                render_width = int(page_width * zoom)
                render_height = int(page_height * zoom)

            logger.debug(f"渲染尺寸: {render_width} x {render_height}")

            # 检查缓存
            cache_pixmap = self.render_cache.get_rendered_page(page_num, zoom, (render_width, render_height))
            if cache_pixmap:
                logger.debug("从缓存获取页面渲染结果")
                return cache_pixmap

            # 创建变换矩阵进行缩放
            mat = fitz.Matrix(zoom, zoom)
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
            self.render_cache.put_rendered_page(page_num, zoom, (render_width, render_height), pixmap)
            logger.debug("页面渲染结果已缓存")

            return pixmap

        except Exception as e:
            logger.error(f"渲染页面失败: {e}")
            logger.error(traceback.format_exc())
            # 返回错误提示图像，使用计算后的渲染尺寸
            error_pixmap = QPixmap(render_width, render_height)
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
            page_rect = page.rect
            page_width = page_rect.width

            # A4纸标准尺寸（点）
            A4_WIDTH = 595

            # 计算缩放比例
            scale = 0.2  # 基础缩放比例 20%
            if page_width > A4_WIDTH:
                # 如果页面宽度超过A4，调整缩放比例以保持缩略图的相对大小一致
                scale = scale * (A4_WIDTH / page_width)

            # 使用计算后的缩放比例生成缩略图
            mat = fitz.Matrix(scale, scale)

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
            
            # 使用和显示相同的缩放比例，确保OCR bbox坐标正确
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            
            # 渲染页面为图像
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # 统一转换为PNG格式，确保OCR引擎兼容性
            img_data = pix.tobytes("png")
            
            return img_data

        except Exception as e:
            logger.error(f"获取页面图像数据时出错: {e}")
            logger.error(traceback.format_exc())
            return None

    # ========== PDFProcessor 兼容方法 ==========

    def has_unsaved_changes(self):
        """检查是否有未保存的更改"""
        if self.page_editor:
            return self.page_editor.has_unsaved_changes()
        return False

    def undo_operation(self):
        """撤销操作"""
        if self.page_editor:
            return self.page_editor.undo()
        return False, "没有可撤销的操作"

    def redo_operation(self):
        """重做操作"""
        if self.page_editor:
            return self.page_editor.redo()
        return False, "没有可重做的操作"

    def delete_page(self, page_num):
        """删除指定页面"""
        if self.page_editor:
            return self.page_editor.delete_page(page_num)
        return False, "页面编辑器未初始化"

    def rotate_page(self, page_num, angle):
        """旋转指定页面"""
        if self.page_editor:
            return self.page_editor.rotate_page(page_num, angle)
        return False, "页面编辑器未初始化"

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
                    elif format.upper() == "PNG":
                        pix.save(output_path, "png")
                    elif format.upper() == "BMP":
                        pix.save(output_path, "bmp")
                    elif format.upper() == "TIFF" or format.upper() == "TIF":
                        pix.save(output_path, "tiff")
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

    def get_supported_image_formats(self):
        """获取支持的图片格式"""
        return ['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'gif', 'webp', 'ico']

    def get_supported_image_formats_filter(self) -> str:
        """获取文件选择对话框的格式过滤器"""
        formats = [
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
        return ";;".join(formats) + ";;所有文件 (*.*)"

    def get_recommended_dpi(self):
        """获取推荐的DPI"""
        return {
            "默认": 72,
            "屏幕显示": 96,
            "普通打印": 150,
            "高质量打印": 300,
            "超高质量": 600
        }

    def import_images(self, image_paths: list, insert_after_page: int = -1) -> tuple[bool, str]:
        """导入图片到PDF

        Args:
            image_paths: 图片文件路径列表
            insert_after_page: 插入位置（0-based，-1表示末尾）

        Returns:
            (success, message) 元组
        """
        try:
            # 保存 is_from_image 状态
            was_from_image = hasattr(self, 'is_from_image') and self.is_from_image
            original_image_path = getattr(self, 'original_image_path', None)

            conversion = PDFConversion()
            conversion.fitz_document = self.fitz_document
            conversion.current_file = self.current_file
            conversion.current_page = self.current_page

            # 如果有 page_editor，也传递给 conversion
            if self.page_editor:
                conversion.page_editor = self.page_editor

            success, message = conversion.import_images(image_paths, insert_after_page)

            if success:
                self.fitz_document = conversion.fitz_document
                self.pdf_document = self.fitz_document
                self.current_page = conversion.current_page

                # 如果之前是从图片打开的，仍然保持 is_from_image 状态
                if was_from_image:
                    self.current_file = None
                    self.is_from_image = True
                    self.original_image_path = original_image_path
                else:
                    self.current_file = conversion.current_file
                    self.is_from_image = False
                    self.original_image_path = None

                # 如果文档被替换（从图片创建新PDF），需要重新初始化 page_editor
                if self.page_editor:
                    new_page_editor = PageEditor(self)
                    self.page_editor = new_page_editor

            return success, message

        except Exception as e:
            logger.error(f"导入图片时出错: {e}")
            logger.error(traceback.format_exc())
            return False, f"导入图片失败: {str(e)}"

    def get_operation_summary(self):
        """获取操作摘要"""
        if self.page_editor:
            return self.page_editor.get_operation_summary()
        return "没有操作记录"

    def save_changes(self):
        """保存更改"""
        if self.page_editor:
            return self.page_editor.save()
        return False, "页面编辑器未初始化"

    def discard_changes(self):
        """放弃更改"""
        if self.page_editor:
            return self.page_editor.discard()
        return False, "页面编辑器未初始化"

    def encrypt_pdf(self, password, output_path):
        """加密PDF文件"""
        try:
            operations = PDFOperations()
            operations.fitz_document = self.fitz_document
            operations.current_file = self.current_file
            if hasattr(self, 'is_new_document'):
                operations.is_new_document = self.is_new_document

            success, message = operations.encrypt_pdf(password, output_path)

            if success:
                return True, message
            else:
                return False, message

        except Exception as e:
            logger.error(f"加密PDF时出错: {e}")
            return False, f"加密失败: {str(e)}"

    def _is_image_file(self, file_path):
        """判断是否为图片文件"""
        if not file_path:
            return False
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in image_extensions

    def open_pdf(self, file_path, async_mode=False, password=None):
        """打开PDF文件或图片文件"""
        try:
            if not os.path.exists(file_path):
                self.loading_finished.emit(False, f"文件不存在: {file_path}")
                return False, f"文件不存在: {file_path}"

            # 判断是否为图片文件
            is_image = self._is_image_file(file_path)

            # 关闭现有文档
            if self.fitz_document:
                self.fitz_document.close()

            # 如果是图片文件，创建临时PDF
            if is_image:
                # 创建新的PDF文档，使用A4纸规格
                new_doc = fitz.open()
                try:
                    # A4纸规格：210mm x 297mm，在点单位下为 595 x 842
                    a4_width = 595
                    a4_height = 842
                    padding = 40  # 左右padding（点）

                    # 创建A4规格的新页面
                    page = new_doc.new_page(width=a4_width, height=a4_height)

                    # 计算图片插入区域（去除左右padding）
                    image_rect = fitz.Rect(
                        padding,
                        0,
                        a4_width - padding,
                        a4_height
                    )

                    # 插入图片到指定区域（自动适应）
                    page.insert_image(image_rect, filename=file_path)

                    # 设置为新文档
                    self.fitz_document = new_doc
                    self.pdf_document = self.fitz_document
                    self.current_page = 0

                    # 标记为从图片打开的文档
                    self.is_from_image = True
                    self.original_image_path = file_path
                    self.current_file = None  # 图片文件不设为当前文件，待用户保存时选择

                    self.loading_finished.emit(True, f"成功打开文件: {os.path.basename(file_path)}")
                    return True, f"成功打开文件: {os.path.basename(file_path)}"

                except Exception as e:
                    new_doc.close()
                    logger.error(f"从图片创建PDF失败: {e}")
                    self.loading_finished.emit(False, f"打开图片失败: {str(e)}")
                    return False, f"打开图片失败: {str(e)}"
            else:
                # PDF文件，直接打开
                self.fitz_document = fitz.open(file_path)
                self.pdf_document = self.fitz_document  # 同步更新别名
                self.current_file = file_path
                self.current_page = 0

                # 标记为PDF文件
                self.is_from_image = False
                self.original_image_path = None

                # 处理密码
                if password and self.fitz_document:
                    if not self.fitz_document.authenticate(password):
                        self.loading_finished.emit(False, "密码错误")
                        return False, "密码错误"

                self.loading_finished.emit(True, f"成功打开文件: {os.path.basename(file_path)}")
                return True, f"成功打开文件: {os.path.basename(file_path)}"

        except Exception as e:
            logger.error(f"打开PDF文件时出错: {e}")
            self.loading_finished.emit(False, f"打开文件失败: {str(e)}")
            return False, f"打开文件失败: {str(e)}"

    def open_multiple_images(self, image_paths, async_mode=False, source_directory=None):
        """打开多个图片文件，创建多页PDF"""
        try:
            if not image_paths:
                return False, "未选择图片文件"

            # 创建新的PDF文档，使用A4纸规格
            new_doc = fitz.open()
            a4_width = 595
            a4_height = 842
            padding = 40

            # 插入图片的数量
            success_count = 0

            for image_path in image_paths:
                try:
                    # 创建A4规格的新页面
                    page = new_doc.new_page(width=a4_width, height=a4_height)

                    # 计算图片插入区域（去除左右padding）
                    image_rect = fitz.Rect(
                        padding,
                        0,
                        a4_width - padding,
                        a4_height
                    )

                    # 插入图片到指定区域（自动适应）
                    page.insert_image(image_rect, filename=image_path)

                    success_count += 1
                    logger.debug(f"成功添加图片: {image_path}")

                except Exception as inner_e:
                    logger.error(f"添加图片失败 {image_path}: {inner_e}")

            if success_count == 0:
                new_doc.close()
                return False, "所有图片都无法添加到PDF"

            # 关闭当前文档（如果有）
            if self.fitz_document:
                self.fitz_document.close()

            # 设置新文档
            self.fitz_document = new_doc
            self.pdf_document = self.fitz_document
            self.current_page = 0

            # 标记为从图片打开的文档
            self.is_from_image = True
            self.original_image_path = None
            self.current_file = None  # 多图片文件不设为当前文件，待用户保存时选择

            self.loading_finished.emit(True, f"成功打开{success_count}张图片")
            return True, f"成功打开{success_count}张图片"

        except Exception as e:
            logger.error(f"打开多图片文件时出错: {e}")
            logger.error(traceback.format_exc())
            self.loading_finished.emit(False, f"打开多图片文件失败: {str(e)}")
            return False, f"打开多图片文件失败: {str(e)}"

    def open_images_from_directory(self, directory_path, async_mode=False):
        """从目录打开图片"""
        return False, "目录图片打开功能待实现"

    def go_to_page(self, page_number):
        """跳转到指定页面"""
        try:
            if not self.fitz_document:
                return False, "没有打开的文档"

            # 检查页面范围
            if page_number < 1 or page_number > len(self.fitz_document):
                return False, f"页码超出范围: {page_number}"

            # 跳转页面（转换为0-based索引）
            self.current_page = page_number - 1
            self.page_changed.emit(self.current_page)
            return True, f"已跳转到第 {page_number} 页"

        except Exception as e:
            logger.error(f"跳转页面时出错: {e}")
            return False, f"跳转失败: {str(e)}"

    def fit_to_width(self, container_width):
        """适应宽度"""
        try:
            if not self.fitz_document or self.current_page < 0 or self.current_page >= len(self.fitz_document):
                return False, "没有打开的文档"

            # 获取当前页面尺寸
            page = self.fitz_document[self.current_page]
            rect = page.rect
            page_width = rect.width

            # 计算需要的缩放比例
            if page_width > 0:
                new_zoom = container_width / page_width
                self.set_zoom(new_zoom / self.base_zoom)
                return True, f"已适应宽度，缩放比例为 {int(new_zoom / self.base_zoom * 100)}%"

            return False, "页面宽度无效"

        except Exception as e:
            logger.error(f"适应宽度时出错: {e}")
            return False, f"适应宽度失败: {str(e)}"

    def _is_file_locked(self, filepath, timeout=2):
        """检查文件是否被锁定"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(filepath, 'a+'):
                    pass
                return False
            except (IOError, OSError):
                time.sleep(0.1)
        return True

    def save_pdf(self, file_path=None):
        """保存PDF文件"""
        temp_path = None
        try:
            if not self.fitz_document:
                return False, "没有打开的文档"

            # 如果是从图片打开的文档且没有指定保存路径，需要用户选择
            if not file_path and hasattr(self, 'is_from_image') and self.is_from_image:
                return False, "is_from_image_save_required"

            file_path = file_path or self.current_file
            if not file_path:
                return False, "没有指定保存路径"

            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='pypdf_save_')
            os.close(temp_fd)

            save_args = {
                'deflate': True,
                'clean': True,
                'garbage': 1
            }
            self.fitz_document.save(temp_path, **save_args)

            if self._is_file_locked(file_path):
                logger.warning("目标文件被锁定，无法保存")
                return False, "文件正在被其他程序使用，请关闭后再试"

            shutil.copy2(temp_path, file_path)

            if self.page_editor:
                self.page_editor.is_modified = False

            # 保存成功后，更新状态
            if hasattr(self, 'is_from_image') and self.is_from_image:
                self.is_from_image = False
                self.original_image_path = None
                self.current_file = file_path

            return True, f"文件已保存: {os.path.basename(file_path)}"

        except Exception as e:
            logger.error(f"保存PDF时出错: {e}")
            return False, f"保存失败: {str(e)}"
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

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
        logger.debug(f"PDFRenderer.search_text: 开始搜索文本 '{search_text}', 区分大小写: {match_case}, 全词匹配: {whole_word}")

        if not self.fitz_document:
            logger.debug("PDFRenderer.search_text: 未打开PDF文件")
            return False, "请先打开PDF文件"

        if not search_text.strip():
            logger.debug("PDFRenderer.search_text: 搜索文本为空")
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
            total_found = 0
            for page_num in pages_to_search:
                page = self.fitz_document[page_num]

                # 搜索当前页
                text_instances = page.search_for(
                    search_text,
                    flags=search_flags,
                    hit_max=1000
                )

                logger.debug(f"在页面 {page_num+1} 中找到 {len(text_instances)} 个匹配项")

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

                total_found += len(text_instances)

            logger.debug(f"总共找到 {total_found} 个匹配项，搜索文本: '{search_text}'")

            # 处理搜索结果
            if search_results:
                logger.debug(f"搜索成功，找到 {len(search_results)} 个匹配项")
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
                logger.debug(f"搜索完成，未找到匹配的文本: '{search_text}'")
                return False, "未找到匹配的文本"

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            logger.error(traceback.format_exc())
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

    def highlight_search_result(self, page_num, rect, color=(1, 1, 0, 0.4)):
        """高亮显示搜索结果（黄色半透明背景）"""
        if not self.fitz_document:
            return False

        try:
            # 获取页面
            page = self.fitz_document[page_num]

            # 添加高亮注释
            highlight = page.add_highlight_annot(rect)

            # 设置高亮颜色（黄色）
            highlight.set_colors(stroke=(1.0, 1.0, 0.0), fill=(1.0, 1.0, 0.0))
            highlight.set_opacity(0.3)
            highlight.update()

            # 设置注释内容，便于识别为搜索高亮
            highlight.set_info(content="Search Highlight", title="SearchHighlight")

            logger.debug(f"已添加高亮：页面{page_num+1}，位置{rect}")
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
                # 删除所有高亮注释（类型8）和带有搜索高亮标记的注释
                annotations_to_delete = []
                for annot in page.annots():
                    if annot.type[0] == 8:  # 高亮注释类型
                        # 检查是否是搜索高亮（通过内容或标题判断）
                        info = annot.info
                        if 'Search Highlight' in info.get('content', ''):
                            annotations_to_delete.append(annot)
                # 删除收集到的注释
                for annot in annotations_to_delete:
                    page.delete_annot(annot)
            else:
                # 清除所有页面的高亮
                for page_num in range(len(self.fitz_document)):
                    page = self.fitz_document[page_num]
                    annotations_to_delete = []
                    for annot in page.annots():
                        if annot.type[0] == 8:  # 高亮注释类型
                            # 检查是否是搜索高亮（通过内容或标题判断）
                            info = annot.info
                            if 'Search Highlight' in info.get('content', ''):
                                annotations_to_delete.append(annot)
                    # 删除收集到的注释
                    for annot in annotations_to_delete:
                        page.delete_annot(annot)

            return True
        except Exception as e:
            logger.error(f"清除高亮失败: {e}")
            return False

    def force_cleanup(self):
        """强制清理资源"""
        try:
            # 清理缓存
            if hasattr(self, 'render_cache'):
                self.render_cache.clear_all()

            # 关闭PDF文档
            if hasattr(self, 'fitz_document') and self.fitz_document:
                try:
                    self.fitz_document.close()
                except Exception as e:
                    logger.error(f"关闭PDF文档失败: {e}")

            logger.info("强制清理完成")
        except Exception as e:
            logger.error(f"强制清理失败: {e}")





