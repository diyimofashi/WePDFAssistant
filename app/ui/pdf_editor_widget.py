"""PDF编辑器组件，包含完整的UI（菜单栏+工具栏+内容区域）"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QMenuBar, QToolBar, QSplitter,
                             QLabel, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
import os

from app.core.processing.pdf_processor import PDFProcessor
from app.core.processing.thumbnail_manager import ThumbnailManager
from app.ui.virtual_scroll import VirtualScrollArea
from app.ui.menu_manager import MenuManager
from app.ui.toolbar_manager import ToolbarManager
from app.ui.context_menu_manager import ContextMenuManager
from app.ui.file_list_panel import FileListPanel
from app.managers.history_manager import HistoryManager
from app.managers.view_controller import ViewController
from app.managers.search_manager import SearchManager
from app.managers.split_manager import SplitManager
from app.managers.merge_manager import MergeManager
from app.ui.welcome_widget import WelcomeWidget
from app.utils.logger import get_logger


logger = get_logger('pdf_editor_widget')


class PDFEditorWidget(QWidget):
    """独立的PDF编辑器组件，包含完整的UI"""

    # 信号定义
    file_opened = pyqtSignal(str)  # 文件打开时发出
    file_saved = pyqtSignal(str)  # 文件保存时发出
    tab_title_changed = pyqtSignal(str)  # 标题改变时发出

    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.tab_index = -1
        self.unsaved_changes = False

        # 初始化PDF处理器
        self.pdf_processor = PDFProcessor()

        # 初始化管理器
        self.view_controller = ViewController(self)
        self.search_manager = SearchManager(self)
        self.split_manager = SplitManager(self)
        self.merge_manager = MergeManager(self)
        self.history_manager = HistoryManager(self)
        self.context_menu_manager = ContextMenuManager(self)

        # 初始化UI
        self.init_ui()

        # 如果有文件路径，打开文件
        if file_path and os.path.exists(file_path):
            self.open_file(file_path)

    def init_ui(self):
        """初始化UI"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 菜单栏
        self.menu_bar = QMenuBar()
        self.menu_manager = MenuManager(self)
        layout.addWidget(self.menu_bar)

        # 2. 工具栏
        self.tool_bar = QToolBar()
        self.tool_bar.setMovable(False)
        self.toolbar_manager = ToolbarManager(self, self.tool_bar)
        layout.addWidget(self.tool_bar)

        # 3. 内容容器（用于切换PDF查看器和欢迎界面）
        self.content_stack = QSplitter(Qt.Vertical)
        layout.addWidget(self.content_stack)

        # 4. 内容区域（分割器）
        self.main_splitter = QSplitter(Qt.Horizontal)

        # 左侧缩略图
        self.thumbnail_manager = ThumbnailManager(self.pdf_processor, self)
        self.thumbnail_panel = self.thumbnail_manager.get_panel()
        self.main_splitter.addWidget(self.thumbnail_panel)

        # 右侧PDF查看器
        self.scroll_area = VirtualScrollArea(self.pdf_processor)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMouseTracking(True)
        self.main_splitter.addWidget(self.scroll_area)

        # 设置分割器比例
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 4)
        self.main_splitter.setSizes([200, 800])

        self.content_stack.addWidget(self.main_splitter)

        # 5. 欢迎界面（历史记录）
        self.welcome_widget = WelcomeWidget(self, self.history_manager)
        self.welcome_widget.file_open_requested.connect(self.open_file)
        self.welcome_widget.close_requested.connect(self.show_pdf_viewer)
        self.content_stack.addWidget(self.welcome_widget)

        # 默认显示PDF查看器或欢迎界面
        if self.file_path:
            self.show_pdf_viewer()
        else:
            self.show_welcome()

    def open_file(self, file_path):
        """打开文件"""
        try:
            success, message = self.pdf_processor.open_pdf(file_path, async_mode=True)
            if success:
                self.file_path = file_path
                self.unsaved_changes = False
                self.update_tab_title(os.path.basename(file_path))
                self.show_pdf_viewer()
                self.file_opened.emit(file_path)
                logger.info(f"文件打开成功: {file_path}")
            else:
                QMessageBox.warning(self, "打开失败", f"无法打开文件: {file_path}\n{message}")
        except Exception as e:
            logger.error(f"打开文件失败: {e}")
            QMessageBox.critical(self, "错误", f"打开文件时出错: {str(e)}")

    def save_file(self, file_path=None):
        """保存文件"""
        try:
            save_path = file_path or self.file_path
            if not save_path:
                return False

            success, message = self.pdf_processor.save_pdf(save_path)
            if success:
                self.file_path = save_path
                self.unsaved_changes = False
                self.update_tab_title(os.path.basename(save_path))
                self.file_saved.emit(save_path)
                logger.info(f"文件保存成功: {save_path}")
                return True
            else:
                QMessageBox.warning(self, "保存失败", f"无法保存文件: {save_path}\n{message}")
                return False
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            QMessageBox.critical(self, "错误", f"保存文件时出错: {str(e)}")
            return False

    def show_pdf_viewer(self):
        """显示PDF查看器"""
        if self.content_stack.currentWidget() != self.main_splitter:
            self.content_stack.setCurrentWidget(self.main_splitter)

    def show_welcome(self):
        """显示欢迎界面（历史记录）"""
        if self.content_stack.currentWidget() != self.welcome_widget:
            self.content_stack.setCurrentWidget(self.welcome_widget)

    def toggle_history(self):
        """切换历史记录/PDF查看器"""
        if self.content_stack.currentWidget() == self.welcome_widget:
            self.show_pdf_viewer()
        else:
            self.show_welcome()

    def update_tab_title(self, title):
        """更新标签页标题"""
        if self.unsaved_changes:
            title = f"* {title}"
        self.tab_title_changed.emit(title)

    def mark_unsaved(self):
        """标记为未保存"""
        self.unsaved_changes = True
        self.update_tab_title(os.path.basename(self.file_path) if self.file_path else "未命名")

    def has_unsaved_changes(self):
        """是否有未保存的更改"""
        return self.unsaved_changes

    def close(self):
        """关闭编辑器"""
        self.pdf_processor.cleanup()
        super().close()
