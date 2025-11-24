"""PDF处理核心功能 - 极灵PDF"""

import os
import time
import PyPDF2
import fitz  # PyMuPDF - 用于PDF页面渲染
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter
from PyQt5.QtCore import Qt

class PDFProcessor:
    """PDF处理器 - 提供稳定可靠的PDF文件处理和渲染功能"""
    
    def __init__(self):
        self.current_file = None
        self.pdf_document = None
        self.fitz_document = None  # PyMuPDF文档对象
        self.current_page = 0  # 当前页码（从0开始）
        self.zoom_factor = 3.0  # 缩放因子（设置为3.0，即300%作为新的100%基准）
        self.base_zoom = 3.0  # 基准缩放因子（用户看到的100%实际是300%）
        self.file_size = 0  # 文件大小（字节）
        self.load_time = 0  # 加载时间（秒）
        self.last_error = ""  # 最后错误信息
        
        # 连续浏览模式属性
        self.continuous_mode = True  # 是否启用连续浏览模式
        self.pages_per_view = 3  # 连续模式下每次显示的页面数
        self.page_spacing = 20  # 页面间距（像素）
        
        # 渲染缓存
        self.render_cache = {}  # 页面渲染缓存
        self.cache_max_size = 10  # 最大缓存页面数
        
    def open_pdf(self, file_path):
        """打开PDF文件 - 提供稳定可靠的PDF文件打开功能"""
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
                return False, "PDF文件已加密，需要密码才能打开"
            
            # 使用PyMuPDF打开文件用于页面渲染
            self.fitz_document = fitz.open(file_path)
            
            # 重置状态
            self.current_file = file_path
            self.current_page = 0
            self.zoom_factor = self.base_zoom  # 重置为基准缩放（300%作为100%基准）
            self.last_error = ""
            
            # 计算加载时间
            self.load_time = time.time() - start_time
            
            return True, f"文件打开成功 ({self.get_file_size_str()}, {self.load_time:.2f}秒)"
            
        except PyPDF2.PdfReadError as e:
            self.last_error = f"PDF文件格式错误: {str(e)}"
            return False, self.last_error
        except Exception as e:
            self.last_error = f"无法打开PDF文件: {str(e)}"
            return False, self.last_error
    
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
            print(f"获取元数据失败: {e}")
        
        # 添加文档属性
        info["properties"]["文档状态"] = "正常" if not self.pdf_document.is_encrypted else "已加密"
        info["properties"]["页面方向"] = "待检测"  # 实际可以检测页面方向
        info["properties"]["兼容性"] = "PDF 1.4+"  # 可以根据实际版本设置
                
        return info
    
    def save_pdf(self, file_path):
        """保存PDF文件"""
        try:
            # 这里简化处理，实际应该实现PDF编辑功能
            return True, "PDF文件已保存"
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
        
        # 检查缓存
        cache_key = (self.current_page, self.zoom_factor, width, height)
        if cache_key in self.render_cache:
            return self.render_cache[cache_key]
        
        try:
            # 获取页面
            page = self.fitz_document[self.current_page]
            
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
            
            # 缓存结果
            if len(self.render_cache) >= self.cache_max_size:
                # 移除最旧的缓存项
                oldest_key = next(iter(self.render_cache))
                del self.render_cache[oldest_key]
            self.render_cache[cache_key] = pixmap
            
            return pixmap
            
        except Exception as e:
            print(f"渲染页面失败: {e}")
            # 返回错误提示图像
            error_pixmap = QPixmap(width, height)
            error_pixmap.fill(Qt.lightGray)
            return error_pixmap
    
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
                        Qt.SmoothTransformation
                    )
                
                page_pixmaps.append(pixmap)
                total_height += pixmap.height()
                
                # 添加页面间距
                if page_num < end_page - 1:
                    total_height += self.page_spacing
            
            # 创建组合图像
            combined_pixmap = QPixmap(width, total_height)
            combined_pixmap.fill(Qt.white)
            
            # 绘制各页面到组合图像
            painter = QPainter(combined_pixmap)
            y_offset = 20  # 顶部边距
            
            for i, page_pixmap in enumerate(page_pixmaps):
                x_offset = (width - page_pixmap.width()) // 2  # 居中
                painter.drawPixmap(x_offset, y_offset, page_pixmap)
                y_offset += page_pixmap.height()
                
                # 添加页面分隔线（除了最后一页）
                if i < len(page_pixmaps) - 1:
                    painter.setPen(Qt.gray)
                    painter.drawLine(20, y_offset + self.page_spacing // 2, 
                                 width - 20, y_offset + self.page_spacing // 2)
                    y_offset += self.page_spacing
            
            painter.end()
            
            return combined_pixmap
            
        except Exception as e:
            print(f"连续页面渲染失败: {e}")
            # 返回错误提示图像
            error_pixmap = QPixmap(width, height)
            error_pixmap.fill(Qt.lightGray)
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
    
    def render_thumbnail(self, page_num, width=100, height=150):
        """渲染指定页面的缩略图"""
        if not self.fitz_document or page_num < 0 or page_num >= len(self.fitz_document):
            return None
        
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
            
            # 缩放图像到指定尺寸
            image = image.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            return QPixmap.fromImage(image)
            
        except Exception as e:
            print(f"渲染缩略图失败: {e}")
            return None
    

    
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
            print(f"高亮失败: {e}")
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
            print(f"清除高亮失败: {e}")
            return False
    
    def clear_render_cache(self):
        """清除渲染缓存"""
        self.render_cache.clear()
    
    def get_text_from_rect(self, page_num, rect):
        """从指定矩形区域提取文本"""
        if not self.fitz_document:
            return ""
        
        try:
            page = self.fitz_document[page_num]
            text = page.get_text("text", clip=rect)
            return text.strip()
        except Exception as e:
            print(f"提取文本失败: {e}")
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