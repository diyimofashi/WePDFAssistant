"""PDF转换器 - 处理PDF转换和图片导入功能"""

import os
import fitz  # PyMuPDF - 用于PDF页面渲染
import sys
from PIL import Image
import io

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('pdf_conversion')

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

class PDFConversion:
    """PDF转换器 - 专门处理PDF转换和导入功能"""
    
    def __init__(self):
        # 注意：信号需要在主QObject子类中定义
        self.fitz_document = None  # PyMuPDF文档对象
        self.current_page = 0  # 当前页码（从0开始）
        self.current_doc_path = None  # 当前文档路径

    def open_pdf(self, filepath: str) -> tuple[bool, str]:
        """打开PDF文件"""
        try:
            if not os.path.exists(filepath):
                return False, f"文件不存在: {filepath}"
            
            # 关闭当前文档（如果有）
            if self.fitz_document:
                self.fitz_document.close()
            
            # 打开新文档
            self.fitz_document = fitz.open(filepath)
            self.current_doc_path = filepath
            self.current_page = 0
            
            return True, f"成功打开PDF: {filepath}"
        except Exception as e:
            logger.error(f"打开PDF失败: {e}")
            return False, f"打开PDF失败: {str(e)}"

    def _get_current_doc_path(self) -> str:
        """获取当前文档的路径"""
        return self.current_doc_path

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
            insert_after_page: 插入位置（0-based，-1表示末尾，0表示第一页后，1表示第二页后，等等）

        Returns:
            (success, message) 元组
        """
        if not image_paths:
            return False, "未选择图片文件"

        # 优先使用 page_editor（如果有），保证操作一致性
        if hasattr(self, 'page_editor') and self.page_editor and self.page_editor.temp_file:
            # 验证 fitz_document 的页数
            fitz_pages = len(self.fitz_document) if self.fitz_document else 0
            logger.info(f"[import_images] fitz_document页数: {fitz_pages}, insert_after_page: {insert_after_page}")

            # 如果有临时文件，使用 page_editor 的方法导入
            # insert_after_page 是 0-based，page_editor.insert_image_page 需要 1-based
            # insert_after_page=-1 表示在最后一页后插入
            if insert_after_page == -1:
                # 在最后一页后插入
                page_num_for_insert = fitz_pages
            elif insert_after_page < -1:
                # 无效值，设置为在最后一页后插入
                page_num_for_insert = fitz_pages
            else:
                # 在指定页后插入
                page_num_for_insert = insert_after_page + 1

            logger.info(f"[import_images] 转换后的page_num(1-based): {page_num_for_insert}")

            success_count = 0
            for image_path in image_paths:
                success, message = self.page_editor.insert_image_page(page_num_for_insert, image_path)
                if success:
                    success_count += 1
                    page_num_for_insert += 1  # 下一张图片插入到新插入页的后面

            if success_count == 0:
                return False, "所有图片都无法插入到PDF"

            return True, f"成功导入{success_count}/{len(image_paths)}张图片到PDF"

        # 原有逻辑：当没有 page_editor 时，直接操作 fitz_document
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
            self.current_page = 0

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
                    # 检查当前文档是否是图片类型（无法直接添加新页面的文档）
                    current_doc_is_image = False
                    try:
                        # 尝试在当前文档中创建一个新页面
                        # 如果失败，说明当前文档是图片类型
                        test_page_num = len(self.fitz_document)  # 在文档末尾尝试添加
                        test_page = self.fitz_document.new_page(test_page_num)
                        # 如果成功，删除测试页面
                        self.fitz_document.delete_page(test_page_num)
                    except:
                        # 如果失败，说明当前文档是图片类型，无法添加新页面
                        current_doc_is_image = True
                        
                    if current_doc_is_image:
                        # 创建新PDF文档，将当前内容复制到新文档
                        new_doc = fitz.open()
                        
                        # 复制当前文档的所有页面到新文档
                        for page_num in range(len(self.fitz_document)):
                            current_page = self.fitz_document[page_num]
                            
                            # 创建新页面
                            new_page = new_doc.new_page()
                            
                            # 尝试获取当前页面内容并复制到新页面
                            try:
                                # 获取当前页面的图片数据
                                pix = current_page.get_pixmap()
                                new_page.insert_image(new_page.rect, pixmap=pix)
                            except:
                                # 如果获取Pixmap失败，尝试其他方式
                                logger.warning("无法从当前页面获取Pixmap，尝试其他方法")
                        
                        # 关闭旧文档
                        self.fitz_document.close()
                        # 使用新文档
                        self.fitz_document = new_doc
                        # 标记这是新建文档，需要另存为
                        self.is_new_document = True
                        insert_position = len(new_doc) - 1 + success_count + 1  # 调整插入位置
                        logger.debug("从图片文档转换为PDF文档，标记为新建文档")
    
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
            
            return True, f"成功插入{success_count}/{len(image_paths)}张图片到PDF"
            
        except Exception as e:
            logger.error(f"插入图片失败: {e}")
            return False, f"插入图片失败: {str(e)}"
    
    def _insert_image_to_page(self, page, image_path: str) -> bool:
        """将图片插入到PDF页面"""
        try:
            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return False
            
            # 使用PIL获取图片尺寸信息，避免PyMuPDF将图片误认为PDF
            with Image.open(image_path) as img:
                img_width, img_height = img.size
            
            # 获取页面矩形区域
            page_rect = page.rect
            
            # 计算缩放比例，确保图片适应页面，同时保留边距
            margin = 50
            available_width = page_rect.width - 2 * margin
            available_height = page_rect.height - 2 * margin
            
            scale_width = available_width / img_width
            scale_height = available_height / img_height
            scale = min(scale_width, scale_height)  # 保持宽高比
            
            # 计算缩放后的图片尺寸
            scaled_width = img_width * scale
            scaled_height = img_height * scale
            
            # 计算居中位置
            x_center = (page_rect.width - scaled_width) / 2
            y_center = (page_rect.height - scaled_height) / 2
            
            # 创建适合页面的矩形区域
            fitz_rect = fitz.Rect(x_center, y_center, x_center + scaled_width, y_center + scaled_height)
            
            # 直接使用文件路径插入图片到页面
            # 这样可以避免PyMuPDF将图片误认为PDF的问题
            page.insert_image(fitz_rect, filename=image_path)
            
            return True
            
        except Exception as e:
            logger.error(f"插入图片到页面失败 {image_path}: {e}")
            
            # 如果上面的方法失败，尝试使用PIL进行预处理并创建Pixmap
            try:
                import io
                
                # 使用PIL打开图片并获取其字节
                with Image.open(image_path) as img:
                    # 将图片转换为RGB模式（如果需要）
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # 将图片保存到内存中的字节流
                    img_bytes_io = io.BytesIO()
                    img.save(img_bytes_io, format='JPEG', quality=95)
                    img_bytes = img_bytes_io.getvalue()
                
                # 重新计算尺寸（因为可能经过了转换）
                img_width, img_height = img.size
                page_rect = page.rect
                
                # 计算缩放比例，确保图片适应页面，同时保留边距
                margin = 50
                available_width = page_rect.width - 2 * margin
                available_height = page_rect.height - 2 * margin
                
                scale_width = available_width / img_width
                scale_height = available_height / img_height
                scale = min(scale_width, scale_height)  # 保持宽高比
                
                # 计算缩放后的图片尺寸
                scaled_width = img_width * scale
                scaled_height = img_height * scale
                
                # 计算居中位置
                x_center = (page_rect.width - scaled_width) / 2
                y_center = (page_rect.height - scaled_height) / 2
                
                # 创建适合页面的矩形区域
                fitz_rect = fitz.Rect(x_center, y_center, x_center + scaled_width, y_center + scaled_height)
                
                # 创建Pixmap并插入到页面
                # 使用fitz.Pixmap从字节数据创建
                pix = fitz.Pixmap(fitz.csRGB, img_bytes)
                
                # 插入到页面
                page.insert_image(fitz_rect, pixmap=pix)
                
                # 释放Pixmap资源
                pix = None
                
                return True
            except Exception as secondary_e:
                logger.error(f"使用备用方法插入图片到页面失败 {image_path}: {secondary_e}")
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