"""PDF渲染器 - 处理PDF页面渲染、缩略图生成和缓存管理功能"""

import os
import time
import fitz  # PyMuPDF - 用于PDF页面渲染
import sys

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('pdf_renderer')

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

# 导入新的异步加载器和缓存管理器
from .async_loader import AsyncThumbnailLoader, AsyncPageRenderer
from ..performance.cache_manager import RenderCache, DiskCache

class PDFRenderer:
    """PDF渲染器 - 专门处理页面渲染和缓存功能"""
    
    def __init__(self):
        # 注意：信号需要在主QObject子类中定义
        # fitz_document 由 PDFProcessor 统一管理，不在子模块中初始化
        self.current_page = 0  # 当前页码（从0开始）
        self.zoom_factor = 2.0  # 缩放因子（设置为2.0，即200%作为新的100%基准）
        self.base_zoom = 2.0  # 基准缩放因子（用户看到的100%实际是200%基准）

        # 异步加载器
        self.thumbnail_loader = None
        self.page_renderer = None
        
        # 新的缓存系统
        self.render_cache = RenderCache(max_memory_mb=200, max_items=50)
        self.disk_cache = DiskCache(cache_dir="cache", max_size_mb=500)
        
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

        # 调试：检查 fitz_document 的来源
        doc_id = id(self.fitz_document) if self.fitz_document else None
        doc_len = len(self.fitz_document) if self.fitz_document else 0
        logger.debug(f"[render_page_at] fitz_document id: {doc_id}, 长度: {doc_len}")

        if not self.fitz_document or page_num < 0 or page_num >= len(self.fitz_document):
            logger.warning("文档未加载或页码无效")
            return None

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
            import traceback
            logger.error(traceback.format_exc())
            return None