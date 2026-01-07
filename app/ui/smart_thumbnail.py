"""
智能缩略图管理器
实现延迟加载和智能预加载的缩略图管理
"""

import sys
import os

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('smart_thumbnail')

from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QScrollArea, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect, QSize
from PyQt5.QtGui import QPixmap, QPainter, QColor, QIcon


class SmartThumbnailManager(QListWidget):
    """智能缩略图管理器 - 延迟加载和智能预加载"""
    
    # 信号定义
    thumbnail_clicked = pyqtSignal(int)
    thumbnail_right_clicked = pyqtSignal(int)
    thumbnail_hovered = pyqtSignal(int)  # 鼠标悬停
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.pdf_processor = None
        
        # 缩略图数据
        self.thumbnail_data = {}  # {page_num: {'pixmap': QPixmap, 'loading': bool, 'visible': bool}}
        self.total_pages = 0
        
        # 智能加载参数
        self.visible_range = 5  # 可见区域页数
        self.preload_range = 10  # 预加载范围（上下各多少页）
        self.thumbnail_size = (200, 234)  # 缩略图尺寸
        
        # 性能优化
        self.load_batch_size = 3  # 每批加载的缩略图数量
        self.load_delay = 50  # 加载延迟(ms)
        
        # 延迟加载定时器
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._load_delayed_thumbnails)
        
        # 悬停定时器
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._on_hover_delayed)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        # 设置列表属性
        self.setIconSize(QSize(*self.thumbnail_size))
        self.setSpacing(5)  # 增加间距
        self.setFlow(QListWidget.LeftToRight)  # 从左到右排列
        self.setResizeMode(QListWidget.Adjust)
        self.setWrapping(True)
        self.setMovement(QListWidget.Static)
        self.setViewMode(QListWidget.IconMode)
        self.setUniformItemSizes(True)
        
        # 滚动条策略
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 设置样式
        self.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                border: none;
                padding: 5px;
                outline: none;
                alignment: center;  /* 确保内容居中 */
            }
            QListWidget::item {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 5px;
                margin: 5px;
                background-color: #FAFAFA;
                text-align: center;
                width: 200px;  /* 固定宽度 */
                color: #333333;  /* 默认文本颜色 */
            }
            QListWidget::item:selected {
                border: 2px solid #007ACC;
                background-color: #E6F3FF;
                color: #333333;  /* 选中时保持深色文本 */
            }
            QListWidget::item:hover {
                border: 1px solid #666666;
                background-color: #F0F0F0;
                color: #333333;  /* 悬停时保持深色文本 */
            }
        """)
        
        # 连接事件
        self.itemClicked.connect(self._on_item_clicked)
        self.itemEntered.connect(self._on_item_entered)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        
        # 连接滚动事件
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
        
    def set_pdf_processor(self, pdf_processor):
        """设置PDF处理器"""
        self.pdf_processor = pdf_processor
        
        # 连接PDF处理器的缩略图信号
        if pdf_processor:
            pdf_processor.thumbnail_ready.connect(self._on_thumbnail_ready)
            pdf_processor.loading_progress.connect(self._on_loading_progress)
            
    def load_thumbnails(self):
        """加载缩略图（智能模式）"""
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            return
            
        self.total_pages = self.pdf_processor.get_total_pages()
        
        # 初始化缩略图数据
        self.thumbnail_data = {}
        for page_num in range(self.total_pages):
            self.thumbnail_data[page_num] = {
                'pixmap': None,
                'loading': False,
                'visible': False,
                'priority': 0  # 加载优先级
            }
        
        # 创建缩略图项
        self._create_thumbnail_items()
        
        # 延迟加载初始可见区域的缩略图
        self.load_timer.start(100)
        
    def _create_thumbnail_items(self):
        """创建缩略图项"""
        self.clear()
        
        for page_num in range(self.total_pages):
            # 创建列表项
            item = QListWidgetItem()
            item.setText(f"第 {page_num + 1} 页")
            item.setData(Qt.UserRole, page_num)
            item.setTextAlignment(Qt.AlignCenter)  # 文字居中
            
            # 设置占位符图标
            placeholder = self._create_placeholder()
            item.setIcon(QIcon(placeholder))
            
            self.addItem(item)
            
    def _create_placeholder(self):
        """创建缩略图占位符"""
        pixmap = QPixmap(*self.thumbnail_size)
        pixmap.fill(Qt.white)
        
        # 绘制占位符样式
        painter = QPainter(pixmap)
        painter.setPen(QColor('#CCCCCC'))
        painter.drawRect(0, 0, pixmap.width() - 1, pixmap.height() - 1)
        
        # 绘制加载图标或文字
        painter.setPen(QColor('#999999'))
        font = painter.font()
        font.setPointSize(20)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "加载中...")
        painter.end()
        
        return pixmap
        
    def _get_visible_range(self):
        """获取当前可见的缩略图范围"""
        if self.count() == 0:
            return 0, -1
            
        scroll_pos = self.verticalScrollBar().value()
        viewport_height = self.viewport().height()
        
        item_height = self.sizeHintForRow(0) + self.spacing() * 2
        if item_height <= 0:
            item_height = 250  # 估算值
            
        start_index = max(0, scroll_pos // item_height - 1)
        end_index = min(self.count() - 1, (scroll_pos + viewport_height) // item_height + 1)
        
        return start_index, end_index
        
    def _update_visibility(self):
        """更新缩略图可见性"""
        start_index, end_index = self._get_visible_range()
        
        # 更新可见性标记
        for page_num in range(self.total_pages):
            item = self.item(page_num)
            if item:
                rect = self.visualItemRect(item)
                is_visible = rect.intersects(QRect(0, 0, self.viewport().width(), self.viewport().height()))
                self.thumbnail_data[page_num]['visible'] = is_visible
                
                # 更新加载优先级
                if is_visible:
                    self.thumbnail_data[page_num]['priority'] = 3  # 最高优先级
                elif start_index - self.preload_range <= page_num <= end_index + self.preload_range:
                    self.thumbnail_data[page_num]['priority'] = 2  # 预加载优先级
                else:
                    self.thumbnail_data[page_num]['priority'] = 1  # 最低优先级
                    
    def _load_delayed_thumbnails(self):
        """延迟加载缩略图"""
        self._update_visibility()
        
        # 按优先级排序需要加载的缩略图
        to_load = []
        for page_num, data in self.thumbnail_data.items():
            if data['pixmap'] is None and not data['loading'] and data['priority'] > 0:
                to_load.append((page_num, data['priority']))
                
        # 按优先级排序
        to_load.sort(key=lambda x: x[1], reverse=True)
        
        # 分批加载
        batch_count = 0
        for page_num, priority in to_load:
            if batch_count >= self.load_batch_size:
                break
                
            self._load_single_thumbnail(page_num)
            batch_count += 1
            
        # 如果还有需要加载的，继续延迟加载
        if len(to_load) > self.load_batch_size:
            self.load_timer.start(self.load_delay)
            
    def _load_single_thumbnail(self, page_num):
        """加载单个缩略图"""
        if page_num >= self.total_pages:
            return
            
        # 标记为正在加载
        self.thumbnail_data[page_num]['loading'] = True
        
        # 使用PDF处理器异步加载缩略图
        if self.pdf_processor:
            try:
                # 先尝试从缓存获取
                cached_thumb = self.pdf_processor.render_thumbnail(page_num, *self.thumbnail_size)
                if cached_thumb:
                    self._on_thumbnail_ready(page_num, cached_thumb)
                else:
                    # 缓存未命中，异步加载
                    # 这里简化处理，实际可以调用PDF处理器的异步加载方法
                    pass
            except Exception as e:
                logger.error(f"加载缩略图 {page_num} 失败: {e}")
                self.thumbnail_data[page_num]['loading'] = False
                
    def _on_thumbnail_ready(self, page_num, pixmap):
        """缩略图加载完成回调"""
        if page_num not in self.thumbnail_data:
            return
            
        # 更新数据
        self.thumbnail_data[page_num]['pixmap'] = pixmap
        self.thumbnail_data[page_num]['loading'] = False
        
        # 更新UI
        item = self.item(page_num)
        if item and pixmap:
            item.setIcon(QIcon(pixmap))
            
    def _on_loading_progress(self, value, message):
        """加载进度更新"""
        # 可以在这里更新进度显示
        pass
        
    def _on_scroll_changed(self, value):
        """滚动事件处理"""
        # 延迟加载新的可见区域
        self.load_timer.start(self.load_delay)
        
    def _on_item_clicked(self, item):
        """缩略图点击事件"""
        page_num = item.data(Qt.UserRole)
        if page_num is not None:
            self.thumbnail_clicked.emit(page_num + 1)  # 转换为1基索引
            
    def _on_item_entered(self, item):
        """鼠标进入缩略图事件"""
        page_num = item.data(Qt.UserRole)
        if page_num is not None:
            # 延迟发送悬停信号，避免频繁触发
            self.hovered_page = page_num
            self.hover_timer.start(200)
            
    def _on_hover_delayed(self):
        """延迟悬停处理"""
        if hasattr(self, 'hovered_page'):
            self.thumbnail_hovered.emit(self.hovered_page + 1)
            
    def _on_context_menu(self, position):
        """右键菜单事件"""
        item = self.itemAt(position)
        if item:
            page_num = item.data(Qt.UserRole)
            if page_num is not None:
                # 选中右键点击的项
                self.clearSelection()
                item.setSelected(True)
                self.thumbnail_right_clicked.emit(page_num + 1)
                
                # 创建右键菜单（简化版）
                menu = self._create_context_menu(page_num + 1, self.mapToGlobal(position))
                if menu:
                    menu.exec_(position)
                    
    def _create_context_menu(self, page_num, position):
        """创建右键菜单（简化版）"""
        from PyQt5.QtWidgets import QMenu, QAction
        
        menu = QMenu(self)
        
        # 添加常用操作
        copy_action = QAction("复制页面", self)
        delete_action = QAction("删除页面", self)
        rotate_action = QAction("旋转页面", self)
        
        menu.addAction(copy_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(rotate_action)
        
        # 连接信号（简化处理）
        copy_action.triggered.connect(lambda: self._on_copy_page(page_num))
        delete_action.triggered.connect(lambda: self._on_delete_page(page_num))
        rotate_action.triggered.connect(lambda: self._on_rotate_page(page_num))
        
        return menu
        
    def _on_copy_page(self, page_num):
        """复制页面（简化处理）"""
        logger.debug(f"复制第 {page_num} 页")
        # TODO: 实现页面复制功能
        
    def _on_delete_page(self, page_num):
        """删除页面 - 调用PDF处理器的删除方法"""
        logger.debug(f"删除第 {page_num} 页")
        
        if self.pdf_processor:
            success, message = self.pdf_processor.delete_page(page_num)
            if success:
                # 通知主窗口更新界面
                if hasattr(self, 'parent') and self.parent:
                    self.parent.update_save_actions_state()
                    self.parent.load_thumbnails()
                    self.parent.update_preview()
            else:
                logger.error(f"页面删除失败: {message}")
        else:
            logger.error("PDF处理器未设置，无法删除页面")
        
    def _on_rotate_page(self, page_num):
        """旋转页面 - 调用PDF处理器的旋转方法"""
        logger.debug(f"旋转第 {page_num} 页")
        
        if self.pdf_processor:
            success, message = self.pdf_processor.rotate_page(page_num, 90)  # 默认旋转90度
            if success:
                # 通知主窗口更新界面
                if hasattr(self, 'parent') and self.parent:
                    self.parent.update_save_actions_state()
                    self.parent.load_thumbnails()
                    self.parent.update_preview()
            else:
                logger.error(f"页面旋转失败: {message}")
        else:
            logger.error("PDF处理器未设置，无法旋转页面")
        
    def update_thumbnail_selection(self, current_page):
        """更新缩略图选中状态"""
        if self.count() > 0 and 1 <= current_page <= self.count():
            # 清除之前的选中项
            self.clearSelection()
            
            # 选中当前页面
            item = self.item(current_page - 1)
            if item:
                item.setSelected(True)
                self.scrollToItem(item)
                
    def clear_cache(self):
        """清除缩略图缓存"""
        # 清除所有缓存的缩略图
        for page_num in self.thumbnail_data:
            self.thumbnail_data[page_num]['pixmap'] = None
            self.thumbnail_data[page_num]['loading'] = False
            
        # 重置所有项目为占位符
        for i in range(self.count()):
            item = self.item(i)
            if item:
                placeholder = self._create_placeholder()
                item.setIcon(QIcon(placeholder))
                
    def get_cache_stats(self):
        """获取缓存统计"""
        loaded_count = sum(1 for data in self.thumbnail_data.values() if data['pixmap'] is not None)
        loading_count = sum(1 for data in self.thumbnail_data.values() if data['loading'])
        visible_count = sum(1 for data in self.thumbnail_data.values() if data['visible'])
        
        return {
            'total': self.total_pages,
            'loaded': loaded_count,
            'loading': loading_count,
            'visible': visible_count,
            'cache_hit_rate': loaded_count / max(self.total_pages, 1)
        }