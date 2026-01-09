"""虚拟滚动组件
只渲染可视区域的页面，大幅提升大文件性能
"""

import sys
import os

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('virtual_scroll')

from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QContextMenuEvent
from .ocr_page_label import OCRPageLabel


class VirtualScrollArea(QScrollArea):
    """虚拟滚动区域 - 只渲染可视区域的页面"""
    
    # 信号定义
    page_visible = pyqtSignal(int)  # 页面变为可见
    page_hidden = pyqtSignal(int)  # 页面变为隐藏
    page_changed = pyqtSignal(int)  # 页面变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pages_data = []  # 页面数据列表
        self.visible_pages = set()  # 当前可见的页面
        self.rendered_pages = {}  # 已渲染的页面缓存
        self.placeholder_pages = {}  # 占位符页面
        
        # 虚拟滚动参数
        self.viewport_height = 0
        self.total_height = 0
        self.page_heights = []  # 每页的高度
        self.page_positions = []  # 每页的起始位置
        
        # 性能优化参数
        self.buffer_size = 1  # 可见区域上下各预渲染的页数
        self.render_delay = 200  # 增加渲染延迟到200ms
        
        # 延迟渲染定时器
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._delayed_render)
        
        # 初始化UI
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        # 设置滚动区域属性
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建虚拟容器
        self.virtual_widget = QWidget()
        self.virtual_widget_layout = QVBoxLayout(self.virtual_widget)
        self.virtual_widget_layout.setSpacing(0)
        self.virtual_widget_layout.setContentsMargins(0, 0, 0, 0)
        
        # 设置虚拟容器
        self.setWidget(self.virtual_widget)
        
        # 连接滚动事件
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
        
    def get_container_size(self):
        """获取容器的实际可用尺寸"""
        # 获取视口的尺寸作为容器尺寸
        viewport = self.viewport()
        width = viewport.width() - 40  # 减去一些边距和滚动条空间
        height = viewport.height() - 20  # 减去一些边距
        
        return width, height

    def update_content(self):
        """更新内容显示"""
        if self.pages_data:
            self._calculate_layout()
            self._update_virtual_widget()
            # 延迟渲染可见页面，确保布局完成，只调用一次避免重复渲染
            QTimer.singleShot(150, self._render_visible_pages)
        else:
            # 如果没有页面数据，尝试从父窗口获取
            parent = self.parent()
            while parent and not hasattr(parent, 'pdf_processor'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'pdf_processor'):
                pdf_processor = parent.pdf_processor
                if pdf_processor and pdf_processor.fitz_document:
                    # 构建页面数据
                    total_pages = pdf_processor.get_total_pages()
                    pages_data = []
                    for page_num in range(total_pages):
                        # 获取页面尺寸
                        page_dimensions = pdf_processor.get_page_dimensions(page_num)
                        if page_dimensions:
                            width = int(page_dimensions['width'] * pdf_processor.zoom_factor)
                            height = int(page_dimensions['height'] * pdf_processor.zoom_factor)
                        else:
                            width = 800  # 默认宽度
                            height = 1100  # 默认高度
                            
                        pages_data.append({
                            'page_num': page_num,
                            'width': width,
                            'height': height,
                            'zoom_factor': pdf_processor.zoom_factor
                        })
                    
                    self.set_pages_data(pages_data)
                else:
                    logger.warning("PDF处理器未准备好")
            else:
                logger.warning("父窗口没有PDF处理器")
                
    def set_pages_data(self, pages_data):
        """设置页面数据"""
        self.pages_data = pages_data
        self._calculate_layout()
        self._update_virtual_widget()
        # 立即渲染可见页面，确保内容立即显示
        QTimer.singleShot(50, self._render_visible_pages)
        
    def _calculate_layout(self):
        """计算页面布局"""
        self.page_heights = []
        self.page_positions = []
        self.total_height = 0
        
        # 预估页面高度（可以基于实际内容动态调整）
        default_height = 1100  # 默认页面高度
        page_spacing = 35  # 进一步增大页面间距到35像素，使页面之间有更明显的间隔
        
        for i, page_data in enumerate(self.pages_data):
            # 如果有实际高度则使用，否则使用默认高度
            height = page_data.get('height', default_height)
            
            self.page_heights.append(height)
            self.page_positions.append(self.total_height)
            # 计算页面位置时只增加页面高度和间距，不额外增加空间
            self.total_height += height + page_spacing
            
        # 设置虚拟容器的高度，确保使用整数，并增加一些额外空间
        self.virtual_widget.setMinimumHeight(int(self.total_height + 60))  # 增加额外空间到60像素
        
    def _update_virtual_widget(self):
        """更新虚拟容器"""
        # 清除现有子控件
        for i in reversed(range(self.virtual_widget_layout.count())):
            child = self.virtual_widget_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # 清除占位符页面
        self.placeholder_pages.clear()
        # 也要清除已渲染的页面记录
        self.rendered_pages.clear()
        self.visible_pages.clear()

        # 为每个页面创建占位符
        for i, page_data in enumerate(self.pages_data):
            # 创建页面容器 - 不设置固定宽度，让内容自适应
            page_container = QWidget()
            page_container.setProperty('page_index', i)

            # 设置容器位置和高度，宽度不限制（自适应）
            height = self.page_heights[i] if i < len(self.page_heights) else 1100
            adjusted_height = height + 40  # 增加额外空间到40像素
            y_position = self.page_positions[i]
            # 只设置Y位置和高度，宽度不设置，使用-1表示自适应
            page_container.setGeometry(0, int(y_position), -1, int(adjusted_height))
            # 设置最小高度
            page_container.setMinimumHeight(int(adjusted_height))

            # 使用水平布局实现居中
            container_layout = QHBoxLayout(page_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)

            # 创建占位符标签
            placeholder = QLabel(f"第 {i + 1} 页")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("""
                QLabel {
                    background-color: #F0F0F0;
                    border: 1px solid #CCCCCC;
                    color: #666666;
                    font-size: 14px;
                    margin: 2px;
                }
            """)

            # 添加占位符到布局并居中
            container_layout.addStretch()
            container_layout.addWidget(placeholder)
            container_layout.addStretch()

            self.placeholder_pages[i] = placeholder

            # 添加到布局
            self.virtual_widget_layout.addWidget(page_container)
        
    def update_page_ocr_layer(self, page_num, ocr_result, page_scale=1.0):
        """更新指定页面的OCR文本层"""
        # 如果页面已经渲染，直接更新其OCR文本层
        if page_num in self.rendered_pages:
            page_label = self.rendered_pages[page_num]
            if isinstance(page_label, OCRPageLabel):
                self._set_page_ocr_layer(page_num, page_label, ocr_result, page_scale)
            else:
                logger.warning(f"[VirtualScroll.update_page_ocr_layer] 页面{page_num + 1}不是OCRPageLabel类型")
        else:
            # 页面尚未渲染，存储OCR数据供后续渲染时使用
            if not hasattr(self, '_pending_ocr_data'):
                self._pending_ocr_data = {}
            # 存储OCR结果和缩放比例
            self._pending_ocr_data[page_num] = {
                'ocr_result': ocr_result,
                'page_scale': page_scale
            }
            logger.debug(f"[VirtualScroll.update_page_ocr_layer] 待处理的OCR数据: {len(self._pending_ocr_data)} 页")

    def set_all_pages_debug_mode(self, enabled):
        """设置所有页面的调试模式"""
        for page_num, page_label in self.rendered_pages.items():
            if isinstance(page_label, OCRPageLabel):
                page_label.set_debug_mode(enabled)

    def _has_ocr_data(self, page_num, pdf_processor):
        """检查页面是否有OCR数据"""
        # 检查待处理的OCR数据
        if hasattr(self, '_pending_ocr_data') and page_num in self._pending_ocr_data:
            return True

        # 检查PDF处理器的OCR结果
        if hasattr(pdf_processor, 'ocr_results') and page_num in pdf_processor.ocr_results:
            return True

        return False

    def _set_pdf_text_layer(self, page_num, page_label, pdf_processor, pixmap, actual_width, actual_height):
        """从PDF提取原生文本并创建文本层"""
        try:
            import fitz

            # 获取PDF页面
            page = pdf_processor.fitz_document[page_num]

            # 使用 dict 模式获取详细的文本信息
            # 包含每个字符的精确位置信息
            text_dict = page.get_text("dict")

            logger.debug(f"[VirtualScroll._set_pdf_text_layer] 第{page_num + 1}页提取到文本字典")

            if not text_dict or "blocks" not in text_dict:
                logger.warning(f"[VirtualScroll._set_pdf_text_layer] 第{page_num + 1}页没有文本块")
                return

            # 准备OCR格式的数据
            ocr_data = []

            for block in text_dict["blocks"]:
                if block.get("type") != 0:  # 只处理文本块
                    continue

                # 获取文本行的bbox和基线信息
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    line_bbox = line.get("bbox")  # (x0, y0, x1, y1)
                    if not line_bbox:
                        continue

                    # 合并同一行的所有span（文本片段）
                    line_text = ""
                    line_x0, line_x1 = line_bbox[0], line_bbox[2]
                    line_y0, line_y1 = line_bbox[1], line_bbox[3]

                    if "spans" in line:
                        for span in line["spans"]:
                            span_text = span.get("text", "")
                            if span_text:
                                line_text += span_text

                    if not line_text.strip():
                        continue

                    # 使用行的bbox - PyMuPDF的bbox是文本的精确包围盒
                    # 直接使用，不做任何调整
                    ocr_bbox = [
                        [line_bbox[0], line_bbox[1]],  # 左上
                        [line_bbox[2], line_bbox[1]],  # 右上
                        [line_bbox[2], line_bbox[3]],  # 右下
                        [line_bbox[0], line_bbox[3]]   # 左下
                    ]

                    ocr_data.append({
                        "text": line_text,
                        "bbox": ocr_bbox,
                        "confidence": 1.0,
                        "end": len(line_text)
                    })

            if ocr_data:
                # 计算缩放比例
                scale_x = pixmap.width() / actual_width if actual_width > 0 else 1.0
                scale_y = pixmap.height() / actual_height if actual_height > 0 else 1.0
                page_scale = max(scale_x, scale_y)

                logger.debug(f"[VirtualScroll._set_pdf_text_layer] 第{page_num + 1}页已提取{len(ocr_data)}个文本块，page_scale={page_scale}")

                # 设置文本层（完全透明）
                page_label.set_ocr_data(ocr_data, page_scale=page_scale)

        except Exception as e:
            logger.error(f"[VirtualScroll._set_pdf_text_layer] 提取PDF文本失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _set_page_ocr_layer(self, page_num, page_label, ocr_result=None, page_scale=1.0):
        """设置页面的OCR文本层"""
        try:
            # 如果没有提供OCR结果，则尝试从_pending_ocr_data中获取
            ocr_zoom_factor = None
            if ocr_result is None:
                logger.debug(f"[VirtualScroll._set_page_ocr_layer] OCR结果为空，尝试从待处理数据获取")
                if hasattr(self, '_pending_ocr_data') and page_num in self._pending_ocr_data:
                    pending_data = self._pending_ocr_data[page_num]
                    # 处理字典格式
                    if isinstance(pending_data, dict):
                        ocr_result = pending_data.get('ocr_result')
                        page_scale = pending_data.get('page_scale', page_scale)
                        ocr_zoom_factor = pending_data.get('zoom_factor', None)
                        logger.debug(f"[VirtualScroll._set_page_ocr_layer] 从待处理数据获取: page_scale={page_scale}, ocr_zoom_factor={ocr_zoom_factor}")
                    else:
                        ocr_result = pending_data
                else:
                    # 尝试从父窗口的PDF处理器获取OCR结果
                    parent = self.parent()
                    while parent and not hasattr(parent, 'pdf_processor'):
                        parent = parent.parent()

                    if parent and hasattr(parent, 'pdf_processor'):
                        pdf_processor = parent.pdf_processor
                        if hasattr(pdf_processor, 'ocr_results') and page_num in pdf_processor.ocr_results:
                            ocr_data = pdf_processor.ocr_results[page_num]
                            # 处理新的字典格式（包含zoom_factor）
                            if isinstance(ocr_data, dict):
                                ocr_result = ocr_data.get('ocr_result')
                                ocr_zoom_factor = ocr_data.get('zoom_factor', None)
                                logger.debug(f"[VirtualScroll._set_page_ocr_layer] 从PDF处理器获取OCR结果: ocr_zoom_factor={ocr_zoom_factor}")
                            else:
                                # 兼容旧格式（直接是OCRResult对象）
                                ocr_result = ocr_data

            # 检查OCR结果
            if ocr_result is None:
                logger.warning(f"[VirtualScroll._set_page_ocr_layer] OCR结果为None，无法设置文本层")
                return

            # 如果存储了OCR识别时的zoom_factor，需要计算缩放比率
            if ocr_zoom_factor is not None:
                # 获取当前的zoom_factor
                parent = self.parent()
                while parent and not hasattr(parent, 'pdf_processor'):
                    parent = parent.parent()

                if parent and hasattr(parent, 'pdf_processor'):
                    current_zoom_factor = parent.pdf_processor.zoom_factor
                    # 计算缩放比率：当前zoom_factor / OCR识别时的zoom_factor
                    scale_ratio = current_zoom_factor / ocr_zoom_factor if ocr_zoom_factor > 0 else 1.0
                    # 更新page_scale为缩放比率
                    page_scale = scale_ratio

            # 检查OCR结果数据
            if hasattr(ocr_result, 'data'):
                ocr_data = ocr_result.data
                if len(ocr_data) > 0:
                    logger.debug(f"[VirtualScroll._set_page_ocr_layer] 第一个文本块示例: {ocr_data[0].get('text', '')[:50]}...")
                page_label.set_ocr_data(ocr_data, page_scale=page_scale)
            elif isinstance(ocr_result, dict) and 'ocr_result' in ocr_result:
                # 处理存储的字典格式
                page_label.set_ocr_data(ocr_result['ocr_result'].data, page_scale=page_scale)
            else:
                logger.warning(f"[VirtualScroll._set_page_ocr_layer] OCR结果格式不正确: {type(ocr_result)}")

        except Exception as e:
            logger.error(f"设置第{page_num + 1}页OCR文本层失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_visible_range(self):
        """获取当前可见的页面范围"""
        if not self.pages_data:
            return 0, 0
            
        scroll_pos = self.verticalScrollBar().value()
        viewport_height = self.viewport().height()
        
        start_pos = scroll_pos
        end_pos = scroll_pos + viewport_height
        
        start_page = 0
        end_page = len(self.pages_data) - 1
        
        # 找到起始页面
        for i, pos in enumerate(self.page_positions):
            if pos <= end_pos:
                start_page = i
            else:
                break
                
        # 找到结束页面
        for i in range(len(self.page_positions) - 1, -1, -1):
            # 调整容差值以匹配页面间隔的增加
            if self.page_positions[i] + self.page_heights[i] + 40 >= start_pos:  # 增加容差到40像素
                end_page = i
            else:
                break
                
        # 扩展可见范围（包含缓冲区）
        buffer_size = getattr(self, 'buffer_size', 1)  # 减小缓冲区到1页
        start_page = max(0, start_page - buffer_size)
        end_page = min(len(self.pages_data) - 1, end_page + buffer_size)
        
        logger.debug(f"可见范围: {start_page} - {end_page}")
        return start_page, end_page
        
    def _on_scroll_changed(self, value):
        """滚动事件处理"""
        # 使用延迟渲染避免频繁更新
        self.render_timer.start(self.render_delay)
        
        # 通知主程序页面变更，以便更新页面输入框和缩略图选中状态
        current_page = self.get_current_page()
        
        # 发出信号通知页面变更
        self.page_changed.emit(current_page)
    
    def contextMenuEvent(self, event):
        """处理右键菜单事件"""
        # 获取父窗口
        parent = self.parent()
        while parent and not hasattr(parent, 'show_context_menu_at'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'show_context_menu_at'):
            # 将事件位置转换为父窗口坐标系
            global_pos = event.globalPos()
            local_pos = parent.mapFromGlobal(global_pos)
            parent.show_context_menu_at(local_pos)
        else:
            # 如果找不到有show_context_menu_at方法的父窗口，调用默认实现
            super().contextMenuEvent(event)
    
    def get_selected_text(self):
        """获取选中的文本
        
        Returns:
            str: 选中的文本，如果没有选中则返回None
        """
        try:
            # 遍历可见的页面标签
            for page_num in self.visible_pages:
                if page_num in self.rendered_pages:
                    page_label = self.rendered_pages[page_num]
                    if hasattr(page_label, 'get_selected_text'):
                        text = page_label.get_selected_text()
                        if text and text.strip():
                            return text.strip()
            return None
        except Exception as e:
            logger.error(f"获取选中文本失败: {e}")
            return None
    
    def get_page_at_position(self, pos):
        """获取指定位置的页码

        Args:
            pos: 相对于虚拟滚动区域的位置 (QPoint)

        Returns:
            int: 页码，如果无法获取则返回None
        """
        try:
            # 获取滚动条的值
            scroll_value = self.verticalScrollBar().value()

            # 计算实际Y坐标（包含滚动偏移）
            actual_y = pos.y() + scroll_value

            # 查找对应的页面（从前往后查找）
            for i, position in enumerate(self.page_positions):
                if i < len(self.page_heights):
                    page_top = position
                    page_bottom = position + self.page_heights[i]
                    if page_top <= actual_y < page_bottom:
                        return i

            # 如果没有找到，检查是否在最后一页的范围内（考虑页面间距）
            if self.page_positions:
                last_page_idx = len(self.page_positions) - 1
                last_page_top = self.page_positions[last_page_idx]
                last_page_height = self.page_heights[last_page_idx] if last_page_idx < len(self.page_heights) else 1100
                if last_page_top <= actual_y < last_page_top + last_page_height:
                    return last_page_idx

            return None
        except Exception as e:
            logger.error(f"[VirtualScroll.get_page_at_position] 获取页码失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

            
    def _delayed_render(self):
        """延迟渲染可见页面"""
        self._render_visible_pages()
        
    def _render_page(self, page_num):
        """渲染单个页面"""
        if page_num < 0 or page_num >= len(self.pages_data):
            return

        # 查找有PDF处理器的父窗口
        parent = self.parent()
        while parent and not hasattr(parent, 'pdf_processor'):
            parent = parent.parent()

        if parent and hasattr(parent, 'pdf_processor'):
            pdf_processor = parent.pdf_processor
            if pdf_processor:
                # 使用实际的渲染尺寸
                render_width = self.pages_data[page_num].get('width', 800)
                render_height = self.pages_data[page_num].get('height', 1100)
                pixmap = pdf_processor.render_page_at(page_num, render_width, render_height)
                if pixmap:
                    self.on_page_rendered(page_num, pixmap)
                else:
                    logger.warning(f"[VirtualScroll._render_page] 第{page_num + 1}页渲染失败")
            else:
                logger.warning("[VirtualScroll._render_page] PDF处理器不可用")
        else:
            logger.warning("[VirtualScroll._render_page] 父窗口没有PDF处理器")
            
    def _render_visible_pages(self):
        """渲染可见区域的页面"""
        if not self.pages_data:
            logger.debug("没有页面数据，无法渲染")
            return
            
        # 获取可见范围
        start_page, end_page = self.get_visible_range()
        
        # 找出需要新渲染的页面
        new_visible_pages = set(range(start_page, end_page + 1))
        
        # 渲染新可见的页面，按顺序渲染
        for page_num in sorted(new_visible_pages):
            if page_num not in self.visible_pages:
                self._render_page(page_num)
            # 额外检查：即使页面已在visible_pages中，也检查是否需要重新渲染
            elif page_num not in self.rendered_pages:
                self._render_page(page_num)
                
        # 隐藏不再可见的页面
        for page_num in list(self.visible_pages):
            if page_num not in new_visible_pages:
                self._hide_page(page_num)
                
        # 更新可见页面集合
        self.visible_pages = new_visible_pages
        
    def _hide_page(self, page_num):
        """隐藏指定页面"""
        # 显示占位符
        if page_num in self.placeholder_pages:
            self.placeholder_pages[page_num].show()
            
        # 隐藏已渲染的页面（增加安全检查）
        if page_num in self.rendered_pages:
            rendered_page = self.rendered_pages[page_num]
            # 检查对象是否仍然有效
            if rendered_page and rendered_page.parent():
                rendered_page.hide()
                
    def on_page_rendered(self, page_num, pixmap):
        """页面渲染完成回调"""
        if page_num >= len(self.pages_data):
            return

        if not pixmap:
            return

        try:
            # 创建OCR页面标签
            page_label = OCRPageLabel()
            page_label.setPixmap(pixmap)

            # 从父窗口获取当前的调试模式状态
            parent = self.parent()
            while parent and not hasattr(parent, '_ocr_debug_mode'):
                parent = parent.parent()

            if parent and hasattr(parent, '_ocr_debug_mode') and parent._ocr_debug_mode:
                page_label.set_debug_mode(True)
            # 设置页面样式，减小margin
            page_label.setStyleSheet("""
                OCRPageLabel {
                    background-color: #FFFFFF;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    padding: 2px;
                    margin: 2px;
                }
                OCRPageLabel > QLabel {
                    background-color: #FFFFFF;
                }
            """)

            # 设置页面大小为固定大小，不设置最小大小以避免布局问题
            height = self.page_heights[page_num] if page_num < len(self.page_heights) else 1100
            adjusted_height = int(height + 30)
            # 使用固定大小，确保页面不会被拉伸
            page_label.setFixedSize(int(pixmap.width()), adjusted_height)

            # 获取页面容器
            if page_num < self.virtual_widget_layout.count():
                page_container = self.virtual_widget_layout.itemAt(page_num).widget()
                if page_container:
                    # 获取容器的水平布局
                    if page_container.layout():
                        # 清除布局中的控件，但保留占位符
                        layout = page_container.layout()
                        while layout.count():
                            item = layout.itemAt(0)
                            widget = item.widget()
                            if widget:
                                if widget is not self.placeholder_pages.get(page_num):
                                    widget.setParent(None)
                                else:
                                    layout.removeItem(item)
                            else:
                                layout.removeItem(item)

                        # 添加OCR页面标签到布局中（占位符前面）
                        layout.insertWidget(1, page_label)
                    else:
                        # 如果没有布局，直接添加
                        page_label.setParent(page_container)
                        page_label.show()

                    # 缓存渲染的页面
                    self.rendered_pages[page_num] = page_label

                    # 隐藏占位符
                    if page_num in self.placeholder_pages:
                        self.placeholder_pages[page_num].hide()
                    else:
                        logger.debug(f"第{page_num + 1}页显示完成")
                else:
                    logger.debug(f"页面容器不存在")
            else:
                logger.debug(f"页面容器索引超出范围: {page_num}")

            # 如果该页面有OCR数据，设置OCR文本层
            # 计算页面缩放比例，使OCR文本位置正确
            if hasattr(self, 'parent') and self.parent():
                parent = self.parent()
                while parent and not hasattr(parent, 'pdf_processor'):
                    parent = parent.parent()

                if parent and hasattr(parent, 'pdf_processor'):
                    pdf_processor = parent.pdf_processor
                    # 获取页面实际尺寸
                    page_dimensions = pdf_processor.get_page_dimensions(page_num)
                    if page_dimensions:
                        actual_width = page_dimensions['width']
                        actual_height = page_dimensions['height']
                        # 计算缩放比例
                        scale_x = pixmap.width() / actual_width if actual_width > 0 else 1.0
                        scale_y = pixmap.height() / actual_height if actual_height > 0 else 1.0

                        # 检查是否有OCR数据
                        has_ocr_data = self._has_ocr_data(page_num, pdf_processor)
                        logger.debug(f"[VirtualScroll.on_page_rendered] 第{page_num+1}页 has_ocr_data={has_ocr_data}")

                        # 如果有OCR数据，设置OCR文本层
                        if has_ocr_data:
                            self._set_page_ocr_layer(page_num, page_label)
                        else:
                            # 如果没有OCR数据，尝试从PDF提取原生文本
                            logger.debug(f"[VirtualScroll.on_page_rendered] 第{page_num+1}页尝试从PDF提取原生文本")
                            self._set_pdf_text_layer(page_num, page_label, pdf_processor, pixmap, actual_width, actual_height)

        except Exception as e:
            logger.error(f"显示渲染页面 {page_num} 失败: {e}")

    def update_all_pages_scale(self):
        """更新所有已渲染页面的缩放比例"""
        if not hasattr(self, 'parent') or not self.parent():
            return

        parent = self.parent()
        while parent and not hasattr(parent, 'pdf_processor'):
            parent = parent.parent()

        if not parent or not hasattr(parent, 'pdf_processor'):
            return

        pdf_processor = parent.pdf_processor

        # 更新所有已渲染页面的OCR文本层
        for page_num, page_label in self.rendered_pages.items():
            if isinstance(page_label, OCRPageLabel) and hasattr(page_label, 'ocr_data') and page_label.ocr_data:
                # 重新调用_set_page_ocr_layer，它将根据OCR识别时的zoom_factor自动计算缩放比率
                # 不传递ocr_result和page_scale参数，让它自动获取并计算
                self._set_page_ocr_layer(page_num, page_label)
            
    def clear_cache(self):
        """清除渲染缓存"""
        # 清除所有渲染的页面
        for page_num, page_widget in list(self.rendered_pages.items()):
            if page_widget and page_widget.parent():
                page_widget.hide()
                page_widget.setParent(None)

        self.rendered_pages.clear()
        self.visible_pages.clear()

        # 清除待处理的OCR数据
        if hasattr(self, '_pending_ocr_data'):
            self._pending_ocr_data.clear()
            logger.debug("[VirtualScroll.clear_cache] 已清理待处理的OCR数据")

        # 重新显示占位符
        for placeholder in self.placeholder_pages.values():
            placeholder.show()
            
    def scroll_to_page(self, page_num):
        """滚动到指定页面"""
        if 0 <= page_num < len(self.page_positions):
            scroll_pos = self.page_positions[page_num]
            self.verticalScrollBar().setValue(int(scroll_pos))
            
    def update_page_ocr_layer(self, page_num, ocr_result, page_scale=1.0):
        """更新指定页面的OCR文本层"""
        # 如果页面已经渲染，直接更新其OCR文本层
        if page_num in self.rendered_pages:
            page_label = self.rendered_pages[page_num]
            if isinstance(page_label, OCRPageLabel):
                self._set_page_ocr_layer(page_num, page_label, ocr_result, page_scale)
            else:
                logger.warning(f"[VirtualScroll.update_page_ocr_layer] 页面{page_num + 1}不是OCRPageLabel类型")
        else:
            # 页面尚未渲染，存储OCR数据供后续渲染时使用
            if not hasattr(self, '_pending_ocr_data'):
                self._pending_ocr_data = {}
            # 存储OCR结果和缩放比例
            self._pending_ocr_data[page_num] = {
                'ocr_result': ocr_result,
                'page_scale': page_scale
            }
            logger.debug(f"[VirtualScroll.update_page_ocr_layer] 待处理的OCR数据: {len(self._pending_ocr_data)} 页")
    

    
    def get_current_page(self):
        """获取当前页面（基于滚动位置）"""
        scroll_pos = self.verticalScrollBar().value()
        
        current_page = 1  # 默认第一页
        for i, pos in enumerate(self.page_positions):
            if scroll_pos >= pos - 20:  # 调整容差到20像素以提高准确性
                current_page = i + 1  # 转换为1基索引
            else:
                break
                
        return current_page
        
    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        
        # 重新计算布局并延迟渲染
        self._calculate_layout()
        self.render_timer.start(self.render_delay)