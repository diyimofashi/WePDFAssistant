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

from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal


class VirtualScrollArea(QScrollArea):
    """虚拟滚动区域 - 只渲染可视区域的页面"""
    
    # 信号定义
    page_visible = pyqtSignal(int)  # 页面变为可见
    page_hidden = pyqtSignal(int)  # 页面变为隐藏
    
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
        
    def update_content(self):
        """更新内容显示"""
        logger.debug("虚拟滚动区域开始更新内容...")
        if self.pages_data:
            logger.debug(f"有页面数据，共{len(self.pages_data)}页")
            self._calculate_layout()
            self._update_virtual_widget()
            # 延迟渲染可见页面，确保布局完成
            QTimer.singleShot(50, self._render_visible_pages)
            logger.debug("虚拟滚动区域内容更新完成")
        else:
            logger.warning("没有页面数据，尝试从父窗口获取")
            # 如果没有页面数据，尝试从父窗口获取
            parent = self.parent()
            while parent and not hasattr(parent, 'pdf_processor'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'pdf_processor'):
                pdf_processor = parent.pdf_processor
                if pdf_processor and pdf_processor.fitz_document:
                    # 构建页面数据
                    total_pages = pdf_processor.get_total_pages()
                    logger.debug(f"从PDF处理器获取到{total_pages}页")
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
                    logger.debug("页面数据设置完成")
                else:
                    logger.warning("PDF处理器未准备好")
            else:
                logger.warning("父窗口没有PDF处理器")
                
    def set_pages_data(self, pages_data):
        """设置页面数据"""
        logger.debug(f"设置页面数据，共{len(pages_data)}页")
        self.pages_data = pages_data
        self._calculate_layout()
        self._update_virtual_widget()
        # 不要立即渲染页面，而是延迟渲染以避免界面卡顿
        QTimer.singleShot(100, self._render_visible_pages)
        logger.debug("页面数据设置完成")
        
    def _calculate_layout(self):
        """计算页面布局"""
        logger.debug(f"开始计算布局，共{len(self.pages_data)}页...")
        self.page_heights = []
        self.page_positions = []
        self.total_height = 0
        
        # 预估页面高度（可以基于实际内容动态调整）
        default_height = 1100  # 默认页面高度
        page_spacing = 5  # 页面间距，与传统滚动模式保持一致
        
        for i, page_data in enumerate(self.pages_data):
            # 如果有实际高度则使用，否则使用默认高度
            height = page_data.get('height', default_height)
            
            self.page_heights.append(height)
            self.page_positions.append(self.total_height)
            # 计算页面位置时只增加页面高度和间距，不额外增加空间
            self.total_height += height + page_spacing
            
        # 设置虚拟容器的高度，确保使用整数，并增加一些额外空间
        self.virtual_widget.setMinimumHeight(int(self.total_height + 50))  # 减少额外空间到50像素
        logger.debug(f"布局计算完成，总高度: {self.total_height}")
        
    def _update_virtual_widget(self):
        """更新虚拟容器"""
        logger.debug("开始更新虚拟容器...")
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
            # 创建页面容器
            page_container = QWidget()
            page_container.setProperty('page_index', i)
            
            # 设置容器大小和位置，确保使用整数
            height = self.page_heights[i] if i < len(self.page_heights) else 1100
            # 只增加少量额外空间以确保内容不会被截断
            adjusted_height = height + 10  # 减少额外空间到10像素
            y_position = self.page_positions[i]
            page_container.setGeometry(0, int(y_position), self.width(), int(adjusted_height))
            
            # 添加到布局，不添加额外的间距
            self.virtual_widget_layout.addWidget(page_container)
            
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
            
            # 设置占位符大小，确保使用整数
            placeholder.setGeometry(0, 0, self.width(), int(adjusted_height))
            placeholder.setParent(page_container)
            
            self.placeholder_pages[i] = placeholder
            
        logger.debug("虚拟容器更新完成")
        
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
            # 减少容差以避免页面间隔过大
            if self.page_positions[i] + self.page_heights[i] + 10 >= start_pos:  # 减少容差到10像素
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
        if hasattr(self.parent(), 'on_virtual_scroll_page_changed'):
            self.parent().on_virtual_scroll_page_changed(current_page)
            
    def _delayed_render(self):
        """延迟渲染可见页面"""
        self._render_visible_pages()
        
    def _render_page(self, page_num):
        """渲染单个页面"""
        logger.debug(f"开始渲染第{page_num + 1}页...")
        if page_num < 0 or page_num >= len(self.pages_data):
            logger.debug(f"页面号超出范围: {page_num}")
            return
            
        # 查找有PDF处理器的父窗口
        parent = self.parent()
        while parent and not hasattr(parent, 'pdf_processor'):
            parent = parent.parent()
            
        if parent and hasattr(parent, 'pdf_processor'):
            pdf_processor = parent.pdf_processor
            if pdf_processor:
                logger.debug(f"调用PDF处理器渲染第{page_num + 1}页...")
                # 使用实际的渲染尺寸
                render_width = self.pages_data[page_num].get('width', 800)
                render_height = self.pages_data[page_num].get('height', 1100)
                pixmap = pdf_processor.render_page_at(page_num, render_width, render_height)
                if pixmap:
                    logger.debug(f"第{page_num + 1}页渲染成功: {pixmap.width()} x {pixmap.height()}")
                    self.on_page_rendered(page_num, pixmap)
                else:
                    logger.debug(f"第{page_num + 1}页渲染失败")
            else:
                logger.debug("PDF处理器不可用")
        else:
            logger.debug("父窗口没有PDF处理器")
            
    def _render_visible_pages(self):
        """渲染可见区域的页面"""
        logger.debug("开始渲染可见页面...")
        if not self.pages_data:
            logger.debug("没有页面数据，无法渲染")
            return
            
        # 获取可见范围
        start_page, end_page = self.get_visible_range()
        logger.debug(f"可见页面范围: {start_page} - {end_page}")
        
        # 找出需要新渲染的页面
        new_visible_pages = set(range(start_page, end_page + 1))
        
        # 渲染新可见的页面，按顺序渲染
        for page_num in sorted(new_visible_pages):
            if page_num not in self.visible_pages:
                self._render_page(page_num)
                
        # 隐藏不再可见的页面
        for page_num in list(self.visible_pages):
            if page_num not in new_visible_pages:
                self._hide_page(page_num)
                
        # 更新可见页面集合
        self.visible_pages = new_visible_pages
        logger.debug("可见页面渲染完成")
        
    def _hide_page(self, page_num):
        """隐藏指定页面"""
        logger.debug(f"隐藏第{page_num + 1}页")
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
        logger.debug(f"虚拟滚动接收到第{page_num + 1}页渲染完成通知")
        if page_num >= len(self.pages_data):
            logger.debug(f"页面号超出范围: {page_num}")
            return
            
        if not pixmap:
            logger.debug(f"接收到空的pixmap对象")
            return
            
        try:
            logger.debug(f"开始显示第{page_num + 1}页: {pixmap.width()} x {pixmap.height()}")
            # 创建页面标签
            page_label = QLabel()
            page_label.setPixmap(pixmap)
            page_label.setAlignment(Qt.AlignCenter)
            
            # 设置页面样式，减小margin
            page_label.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    padding: 2px;
                    margin: 2px;
                }
            """)
            
            # 设置页面大小，确保使用整数
            height = self.page_heights[page_num] if page_num < len(self.page_heights) else 1100
            # 只增加少量额外高度以确保内容不会被截断
            adjusted_height = int(height + 10)  # 减少额外空间到10像素
            page_label.setMinimumSize(int(pixmap.width()), adjusted_height)
            page_label.resize(int(pixmap.width()), adjusted_height)
            
            # 获取页面容器
            if page_num < self.virtual_widget_layout.count():
                page_container = self.virtual_widget_layout.itemAt(page_num).widget()
                if page_container:
                    # 清除容器中已有的内容
                    for i in reversed(range(page_container.layout().count() if page_container.layout() else 0)):
                        child = page_container.layout().itemAt(i).widget() if page_container.layout() else None
                        if child:
                            child.setParent(None)
                    
                    # 添加到容器
                    page_label.setParent(page_container)
                    # 使用布局管理器而不是手动设置几何位置
                    page_label.setGeometry(0, 0, page_container.width(), adjusted_height)
                    page_label.show()
                    
                    # 缓存渲染的页面
                    self.rendered_pages[page_num] = page_label
                    
                    # 隐藏占位符
                    if page_num in self.placeholder_pages:
                        self.placeholder_pages[page_num].hide()
                        logger.debug(f"第{page_num + 1}页显示完成，占位符已隐藏")
                    else:
                        logger.debug(f"第{page_num + 1}页显示完成")
                else:
                    logger.debug(f"页面容器不存在")
            else:
                logger.debug(f"页面容器索引超出范围: {page_num}")
                
        except Exception as e:
            logger.error(f"显示渲染页面 {page_num} 失败: {e}")
            import traceback
            traceback.print_exc()
            
    def clear_cache(self):
        """清除渲染缓存"""
        # 清除所有渲染的页面
        for page_num, page_widget in list(self.rendered_pages.items()):
            if page_widget and page_widget.parent():
                page_widget.hide()
                page_widget.setParent(None)
            
        self.rendered_pages.clear()
        self.visible_pages.clear()
        
        # 重新显示占位符
        for placeholder in self.placeholder_pages.values():
            placeholder.show()
            
    def scroll_to_page(self, page_num):
        """滚动到指定页面"""
        if 0 <= page_num < len(self.page_positions):
            scroll_pos = self.page_positions[page_num]
            self.verticalScrollBar().setValue(int(scroll_pos))
            
    def get_current_page(self):
        """获取当前页面（基于滚动位置）"""
        scroll_pos = self.verticalScrollBar().value()
        
        current_page = 1  # 默认第一页
        for i, pos in enumerate(self.page_positions):
            if scroll_pos >= pos - 50:  # 给50像素的容差
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