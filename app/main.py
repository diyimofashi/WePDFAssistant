"""极灵PDF主程序入口 - 现代化PDF阅读器（集成性能优化）"""

import sys
import os
import json

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('main')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QToolBar, QAction, QFileDialog, QSplitter,
                             QLabel, QStatusBar, QMessageBox, QPushButton,
                             QLineEdit, QSpinBox, QComboBox, QMenu, QMenuBar,
                             QScrollArea, QScrollBar, QDialog, QVBoxLayout as QDialogLayout, 
                             QHBoxLayout as QDialogLayout, QCheckBox, QPushButton as QPushButton, QGroupBox,
                             QSizePolicy, QProgressDialog)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QThread, QSettings, QCoreApplication
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QKeySequence
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

from app.config.settings import AppSettings
from app.ui.styles import AppStyles
from app.core.pdf_processor import PDFProcessor

# 导入优化组件
from app.ui.virtual_scroll import VirtualScrollArea
from app.core.thumbnail_manager import ThumbnailManager

class AuroraPDF(QMainWindow):
    """极灵PDF主窗口 - 现代化PDF阅读器界面（集成性能优化）"""
    
    def __init__(self):
        super().__init__()
        self.pdf_processor = PDFProcessor()
        
        # 性能优化相关
        self.use_optimizations = True  # 强制启用优化
        self.show_thumbnails = False
        self.progress_dialog = None
        self.render_width = 800
        self.render_height = 1000
        self.use_virtual_scroll = True  # 强制启用虚拟滚动
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._monitor_performance)
        self.performance_timer.start(5000)  # 每5秒监控一次
        self.progress_dialog = None
        
        # 连接PDF处理器信号（确保无论是否使用优化版本都连接信号）
        self.pdf_processor.loading_progress.connect(self._on_loading_progress)
        self.pdf_processor.loading_finished.connect(self._on_pdf_loading_finished)
        self.pdf_processor.page_rendered.connect(self._on_page_rendered)
        self.pdf_processor.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.pdf_processor.operation_history_changed.connect(self._on_operation_history_changed)
        self.pdf_processor.operation_history_changed.connect(self._on_operation_history_changed)
        
        # 搜索相关属性
        self.search_results = []
        self.current_search_index = -1
        self.last_search_text = ""
        self.search_case_sensitive = False
        self.search_whole_word = False
        
        # 连续浏览模式属性（仅保留必要属性）
        self.continuous_mode = True
        
        # 页面高度缓存（用于计算当前页）
        self.page_heights = []
        self.page_positions = []
        
        # 动态渲染尺寸
        self.render_width = 800
        self.render_height = 1100
        
        # 窗口大小调整防抖定时器
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_render_size)
        
        # 缩略图相关属性
        self.thumbnail_dock = None
        self.thumbnail_list = None
        self.thumbnails = []
        self.show_thumbnails = False
        
        # 创建定时器用于定期更新撤销/重做按钮状态
        self.update_actions_timer = QTimer(self)
        self.update_actions_timer.timeout.connect(self.update_save_actions_state)
        self.update_actions_timer.start(500)  # 每500毫秒更新一次
        
        self.init_ui()
        self.apply_styles()
        
    def init_ui(self):
        """初始化UI界面 - 按照极光PDF布局设计"""
        try:
            logger.debug("开始初始化UI...")
            # 设置窗口属性
            self.setWindowTitle(f"{AppSettings.APP_NAME} v{AppSettings.APP_VERSION}")
            self.setGeometry(100, 100, AppSettings.WINDOW_WIDTH, AppSettings.WINDOW_HEIGHT)
            self.setMinimumSize(AppSettings.WINDOW_MIN_WIDTH, AppSettings.WINDOW_MIN_HEIGHT)
            
            # 默认最大化窗口
            self.showMaximized()
            
            # 设置应用样式
            self.apply_styles()
            
            # 创建中央部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 创建主布局（水平布局，左侧缩略图，右侧PDF显示区域）
            main_layout = QHBoxLayout(central_widget)
            main_layout.setSpacing(0)
            main_layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建缩略图区域
            self.create_thumbnail_area(main_layout)
            
            # 创建PDF显示区域
            self.create_pdf_display_area(main_layout)
            
            # 创建菜单栏
            self.create_menubar()
            
            # 创建主工具栏
            self.create_main_toolbar()
            
            # 创建状态栏
            self.create_statusbar()
            
            # 显示欢迎信息
            welcome_msg = "🚀 优化版就绪 - 支持异步加载和虚拟滚动"
            self.show_message(welcome_msg)
            
            logger.debug("UI初始化完成")
        except Exception as e:
            logger.error(f"UI初始化过程中出现错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def create_thumbnail_area(self, main_layout):
        """创建缩略图区域"""
        from PyQt5.QtWidgets import QDockWidget
        
        # 创建停靠窗口作为缩略图区域
        title = "智能缩略图"
        self.thumbnail_dock = QDockWidget(title, self)
        self.thumbnail_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.thumbnail_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        # 去掉停靠窗口的边框
        self.thumbnail_dock.setStyleSheet("""
            QDockWidget {
                border: none;
            }
            QDockWidget::title {
                background-color: #F0F0F0;
                border: none;
                padding: 4px;
                text-align: left;
            }
            QDockWidget > QWidget {
                alignment: center;
            }
        """)
        
        # 设置缩略图容器的默认宽度，但允许调整
        self.thumbnail_dock.setMinimumWidth(250)
        self.thumbnail_dock.resize(280, self.thumbnail_dock.height())
        
        # 创建缩略图管理器
        self.thumbnail_list = ThumbnailManager(self)
        self.thumbnail_list.set_pdf_processor(self.pdf_processor)
        
        # 连接信号
        self.thumbnail_list.thumbnail_clicked.connect(self.on_thumbnail_clicked)
        self.thumbnail_list.thumbnail_right_clicked.connect(self.on_thumbnail_right_clicked)
        
        # 连接PageEditor状态变化信号
        if hasattr(self.thumbnail_list, 'page_editor') and self.thumbnail_list.page_editor:
            self.thumbnail_list.page_editor.state_changed.connect(self.update_save_actions_state)
        
        self.thumbnail_dock.setWidget(self.thumbnail_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.thumbnail_dock)
        
        # 默认隐藏缩略图
        self.thumbnail_dock.hide()
    
    def create_pdf_display_area(self, main_layout):
        """创建PDF显示区域 - 虚拟滚动模式"""
        
        # 创建虚拟滚动区域
        self.virtual_scroll = VirtualScrollArea(self)
        self.virtual_scroll.page_visible.connect(self._on_page_visible)
        self.virtual_scroll.page_hidden.connect(self._on_page_hidden)
        self.virtual_scroll.page_changed.connect(self.on_virtual_scroll_page_changed)
        main_layout.addWidget(self.virtual_scroll)
        
    def apply_styles(self):
        """应用样式"""
        # 设置应用样式表
        self.setStyleSheet(AppStyles.get_stylesheet(AppSettings.THEME))
        
        # 设置字体
        app = QApplication.instance()
        app.setFont(QFont("微软雅黑", 10))
        
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("📁 文件")
        
        open_action = QAction("📂 打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("💾 保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("💾 另存为", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)
        
        # 添加保存更改和放弃更改选项
        self.save_changes_action = QAction("✅ 保存更改", self)
        self.save_changes_action.setShortcut("Ctrl+Shift+S")
        self.save_changes_action.triggered.connect(self.save_changes)
        self.save_changes_action.setEnabled(False)
        file_menu.addAction(self.save_changes_action)
        
        self.discard_changes_action = QAction("❌ 放弃更改", self)
        self.discard_changes_action.setShortcut("Ctrl+D")
        self.discard_changes_action.triggered.connect(self.discard_changes)
        self.discard_changes_action.setEnabled(False)
        file_menu.addAction(self.discard_changes_action)
        
        file_menu.addSeparator()
        
        # 添加撤销和重做选项
        self.undo_action = QAction("↩️ 撤销", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self.undo_operation)
        self.undo_action.setEnabled(False)
        file_menu.addAction(self.undo_action)
        
        self.redo_action = QAction("↪️ 重做", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self.redo_operation)
        self.redo_action.setEnabled(False)
        file_menu.addAction(self.redo_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("👀 视图")
        
        # 缩略图停靠
        self.thumbnail_action = QAction("🖼️ 缩略图", self)
        self.thumbnail_action.setCheckable(True)
        self.thumbnail_action.setChecked(True)
        self.thumbnail_action.triggered.connect(self.toggle_thumbnails)  # 修复方法名
        view_menu.addAction(self.thumbnail_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("🛠️ 工具")
        
        # 搜索功能
        search_action = QAction("🔍 搜索", self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.show_search_options)  # 修复方法名
        tools_menu.addAction(search_action)
        
        # 合并PDF功能
        merge_action = QAction("🔗 合并PDF", self)
        merge_action.triggered.connect(self.merge_pdfs)
        tools_menu.addAction(merge_action)
        
        # 分割PDF功能
        split_action = QAction("✂️ 分割PDF", self)
        split_action.triggered.connect(self.split_pdf)
        tools_menu.addAction(split_action)
        
        # 转换菜单
        convert_menu = menubar.addMenu("🔄 转换")
        
        convert_to_image_action = QAction("🖼️ 转为图片", self)
        convert_to_image_action.setShortcut("Ctrl+I")
        convert_to_image_action.triggered.connect(self.convert_pdf_to_images)
        convert_menu.addAction(convert_to_image_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("❓ 帮助")
        
        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_main_toolbar(self):
        """创建完整的主工具栏 - 按照极光PDF布局设计"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # === 文件操作组 ===
        open_btn = QAction("📂 打开", self)
        open_btn.setToolTip("打开PDF文件 (Ctrl+O)")
        open_btn.setShortcut("Ctrl+O")
        open_btn.triggered.connect(self.open_file)
        toolbar.addAction(open_btn)
        
        save_btn = QAction("💾 保存", self)
        save_btn.setToolTip("保存PDF文件 (Ctrl+S)")
        save_btn.setShortcut("Ctrl+S")
        save_btn.triggered.connect(self.save_file)
        toolbar.addAction(save_btn)
        
        save_as_btn = QAction("💾 另存为", self)
        save_as_btn.setToolTip("另存为PDF文件 (Ctrl+Shift+S)")
        save_as_btn.setShortcut("Ctrl+Shift+S")
        save_as_btn.triggered.connect(self.save_as_file)
        toolbar.addAction(save_as_btn)
        
        toolbar.addSeparator()
        
        # 添加撤销和重做按钮
        self.undo_btn = QAction("↩️ 撤销", self)
        self.undo_btn.setToolTip("撤销上一步操作 (Ctrl+Z)")
        self.undo_btn.setShortcut("Ctrl+Z")
        self.undo_btn.triggered.connect(self.undo_operation)
        self.undo_btn.setEnabled(False)
        toolbar.addAction(self.undo_btn)
        
        self.redo_btn = QAction("↪️ 重做", self)
        self.redo_btn.setToolTip("重做上一步操作 (Ctrl+Y)")
        self.redo_btn.setShortcut("Ctrl+Y")
        self.redo_btn.triggered.connect(self.redo_operation)
        self.redo_btn.setEnabled(False)
        toolbar.addAction(self.redo_btn)
        
        toolbar.addSeparator()
        
        # === 视图控制组 ===
        zoom_in_btn = QAction("➕ 放大", self)
        zoom_in_btn.setToolTip("放大页面 (Ctrl++)")
        zoom_in_btn.setShortcut("Ctrl++")
        zoom_in_btn.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_btn)
        
        zoom_out_btn = QAction("➖ 缩小", self)
        zoom_out_btn.setToolTip("缩小页面 (Ctrl+-)")
        zoom_out_btn.setShortcut("Ctrl+-")
        zoom_out_btn.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_btn)
        
        fit_width_btn = QAction("↔️ 适应宽度", self)
        fit_width_btn.setToolTip("适应页面宽度")
        fit_width_btn.triggered.connect(lambda: self.fit_to_width())
        toolbar.addAction(fit_width_btn)
        
        fit_height_btn = QAction("↕️ 适应高度", self)
        fit_height_btn.setToolTip("适应页面高度")
        fit_height_btn.triggered.connect(lambda: self.fit_to_height())
        toolbar.addAction(fit_height_btn)
        
        actual_size_btn = QAction("1:1 原始尺寸", self)
        actual_size_btn.setToolTip("显示原始尺寸")
        actual_size_btn.triggered.connect(lambda: self.set_actual_size())
        toolbar.addAction(actual_size_btn)
        
        toolbar.addSeparator()
        
        # === 导航组 ===
        prev_page_btn = QAction("⬅️ 上一页", self)
        prev_page_btn.setToolTip("上一页 (PgUp)")
        prev_page_btn.setShortcut("PgUp")
        prev_page_btn.triggered.connect(self.previous_page)  # 修复方法名
        toolbar.addAction(prev_page_btn)
        
        next_page_btn = QAction("➡️ 下一页", self)
        next_page_btn.setToolTip("下一页 (PgDown)")
        next_page_btn.setShortcut("PgDown")
        next_page_btn.triggered.connect(self.next_page)
        toolbar.addAction(next_page_btn)
        
        # 页面数值输入框（用于显示和设置页码）
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setFixedWidth(60)
        self.page_spinbox.setAlignment(Qt.AlignCenter)
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setValue(1)
        self.page_spinbox.setToolTip("当前页码")
        self.page_spinbox.valueChanged.connect(self._on_page_spinbox_changed)
        self.page_spinbox.editingFinished.connect(self.go_to_page)  # 添加回车键支持
        toolbar.addWidget(self.page_spinbox)
        
        # 总页数标签
        self.total_pages_label = QLabel()
        toolbar.addWidget(self.total_pages_label)
        
        toolbar.addSeparator()
        
        # === 模式切换组 ===
        
        # 搜索按钮
        search_btn = QAction("🔍 搜索", self)
        search_btn.setToolTip("搜索文本 (Ctrl+F)")
        search_btn.setShortcut("Ctrl+F")
        search_btn.triggered.connect(self.show_search_options)  # 修复方法名
        toolbar.addAction(search_btn)
        
        # 缩略图按钮
        self.thumbnail_btn = QAction("📋 缩略图", self)
        self.thumbnail_btn.setCheckable(True)
        self.thumbnail_btn.setChecked(False)
        self.thumbnail_btn.setToolTip("显示/隐藏缩略图")
        self.thumbnail_btn.triggered.connect(self.toggle_thumbnails)
        toolbar.addAction(self.thumbnail_btn)
        
        toolbar.addSeparator()
        
        # === 转换工具组 ===
        
        # PDF转图片按钮
        convert_to_image_btn = QAction("🖼️ 转为图片", self)
        convert_to_image_btn.setToolTip("将PDF转换为单张图片")
        convert_to_image_btn.triggered.connect(self.convert_pdf_to_images)
        toolbar.addAction(convert_to_image_btn)

    def create_statusbar(self):
        """创建状态栏"""
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # 创建状态标签
        self.status_label = QLabel("📢 就绪")
        self.status_label.setIndent(5)
        self.statusBar.addWidget(self.status_label)
        
        # 创建性能监控标签
        self.performance_label = QLabel()
        self.performance_label.setIndent(10)
        self.statusBar.addPermanentWidget(self.performance_label)
        
    def update_save_actions_state(self):
        """更新保存操作的状态 - 基于操作历史记录管理器"""
        # 检查是否有未保存的更改（基于操作历史记录）
        has_changes = self.pdf_processor.has_unsaved_changes()
        
        # 更新保存/放弃更改按钮状态
        self.save_changes_action.setEnabled(has_changes)
        self.discard_changes_action.setEnabled(has_changes)
        
        # 更新撤销/重做状态（直接使用PDF处理器的操作历史记录）
        can_undo = self.pdf_processor.can_undo()
        can_redo = self.pdf_processor.can_redo()
        
        logger.debug(f"操作历史状态 - 可撤销: {can_undo}, 可重做: {can_redo}, 有更改: {has_changes}")
        
        # 更新菜单项状态
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        
        # 更新工具栏按钮状态
        if hasattr(self, 'undo_btn'):
            self.undo_btn.setEnabled(can_undo)
        if hasattr(self, 'redo_btn'):
            self.redo_btn.setEnabled(can_redo)
            
        # 更新状态栏信息
        operation_summary = self.pdf_processor.get_operation_summary()
        if has_changes:
            self.show_message(f"● 文档已修改 | {operation_summary}")
        else:
            self.show_message(operation_summary)
            
        # 立即强制更新界面状态
        if hasattr(self, 'repaint'):
            self.repaint()
    
    # ===== 页面导航功能 =====
    
    def previous_page(self):
        """上一页"""
        # 直接使用虚拟滚动模式
        self.virtual_scroll.scroll_page(-1)
        self.show_message("向上滚动")
    
    def next_page(self):
        """下一页"""
        # 直接使用虚拟滚动模式
        self.virtual_scroll.scroll_page(1)
        self.show_message("向下滚动")
    
    def go_to_page(self, page_number=None):
        """跳转到指定页面
        如果没有提供page_number，则从页面输入框获取页码
        """
        try:
            if page_number is None:
                # 从页面数值输入框获取页码
                page_number = self.page_spinbox.value()
            
            # 直接使用虚拟滚动模式
            if 1 <= page_number <= self.pdf_processor.get_total_pages():
                # 更新PDF处理器的当前页面
                self.pdf_processor.go_to_page(page_number)
                
                # 直接滚动到指定页面位置
                self.virtual_scroll.scroll_to_page(page_number - 1)
                self.show_message(f"跳转到第 {page_number} 页")
                
                # 更新页面信息显示
                current_page = self.pdf_processor.get_current_page()
                total_pages = self.pdf_processor.get_total_pages()
                
                # 更新页码控件
                self.page_spinbox.blockSignals(True)
                self.page_spinbox.setValue(current_page)
                self.page_spinbox.blockSignals(False)
                
                # 更新缩略图选中状态
                self.update_thumbnail_selection(current_page)
            else:
                self.show_message("❌ 无效的页码")
        except ValueError:
            self.show_message("❌ 请输入有效的页码")

    def _on_page_spinbox_changed(self, value):
        """处理页码数值输入框变化"""
        # 跳转到指定页面
        self.go_to_page(value)
        
    def toggle_virtual_scroll(self):
        """切换虚拟滚动"""
        # 强制启用虚拟滚动，不允许切换
        self.use_virtual_scroll = True
        self.virtual_scroll_action.setChecked(True)
        self.show_message("⚡ 虚拟滚动已强制启用，无法切换")
            
    def toggle_performance_monitor(self):
        """切换性能监控"""
        if self.performance_action.isChecked():
            self.performance_timer.start(1000)  # 每秒更新
            self.show_message("📊 性能监控已开启")
        else:
            self.performance_timer.start(5000)  # 每5秒更新
            self.show_message("📊 性能监控已关闭")
    
    # ===== 缩放控制功能 =====
    
    def zoom_in(self):
        """放大"""
        current_zoom = self.pdf_processor.get_zoom()  # 获取当前相对缩放值
        new_zoom = min(current_zoom * 1.2, 4.0)  # 最大放大到400%（用户看到的值）
        success, message = self.pdf_processor.set_zoom(new_zoom)
        if success:
            self.update_preview()
        self.show_message(message)
    
    def zoom_out(self):
        """缩小"""
        current_zoom = self.pdf_processor.get_zoom()  # 获取当前相对缩放值
        new_zoom = max(current_zoom / 1.2, 0.25)  # 最小缩小到25%（用户看到的值）
        success, message = self.pdf_processor.set_zoom(new_zoom)
        if success:
            self.update_preview()
        self.show_message(message)
    
    def fit_width(self):
        """适合宽度 - 设置为100%（新的基准，实际是300%）"""
        success, message = self.pdf_processor.set_zoom(1.0)  # 设置为100%（新基准）
        if success:
            self.update_preview()
        self.show_message("适合宽度显示")
    
    def fit_page(self):
        """适合页面 - 设置为100%（新的基准，实际是300%）"""
        success, message = self.pdf_processor.set_zoom(1.0)  # 设置为100%（新基准）
        if success:
            self.update_preview()
        self.show_message("适合页面显示")
                
    def print_file(self):
        """打印PDF文件"""
        if not self.pdf_processor.current_file:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return
        
        # 创建打印机对象
        printer = QPrinter(QPrinter.HighResolution)
        printer.setDocName(os.path.basename(self.pdf_processor.current_file))
        
        # 创建打印对话框
        print_dialog = QPrintDialog(printer, self)
        print_dialog.setWindowTitle("打印PDF")
        
        if print_dialog.exec_() == QPrintDialog.Accepted:
            try:
                # 使用PyMuPDF渲染当前页面并打印
                current_page = self.pdf_processor.get_current_page()
                page_pixmap = self.pdf_processor.render_page_at(current_page - 1, 800, 1000)
                
                if page_pixmap:
                    # 创建绘图器并绘制页面
                    painter = QPainter(printer)
                    # 缩放页面以适应打印区域
                    page_rect = printer.pageRect()
                    scaled_pixmap = page_pixmap.scaled(
                        page_rect.width(), page_rect.height(),
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    
                    # 在页面中央绘制
                    x = (page_rect.width() - scaled_pixmap.width()) // 2
                    y = (page_rect.height() - scaled_pixmap.height()) // 2
                    painter.drawPixmap(x, y, scaled_pixmap)
                    painter.end()
                    
                    self.show_message("🖨️ 打印完成")
                else:
                    QMessageBox.warning(self, "打印失败", "无法渲染页面进行打印")
            except Exception as e:
                QMessageBox.critical(self, "打印错误", f"打印过程中发生错误: {str(e)}")
        else:
            self.show_message("❌ 打印已取消")
    
    def resizeEvent(self, event):
        """窗口大小变化事件 - 重新计算PDF渲染尺寸"""
        super().resizeEvent(event)
        # 使用防抖定时器，避免频繁重渲染
        self.resize_timer.start(100)  # 100ms防抖延迟
    
    def changeEvent(self, event):
        """窗口状态变化事件 - 处理窗口最大化/最小化"""
        super().changeEvent(event)
        if event.type() == event.WindowStateChange:
            # 窗口状态改变时使用防抖定时器更新渲染尺寸
            self.resize_timer.start(100)  # 100ms防抖延迟
    
    def _update_render_size(self):
        """更新渲染尺寸"""
        # 获取可用的显示区域大小
        available_width = self.virtual_scroll.width() - 40  # 减去滚动条和边距
        available_height = self.virtual_scroll.height() - 40
        
        # 以窗口宽度的70%为基准渲染宽度
        base_render_width = int(available_width * 0.7)
        base_render_height = int(available_height * 0.7)
        
        # 根据窗口大小动态调整渲染尺寸 - 随窗口增大而增大
        old_render_width = self.render_width
        old_render_height = self.render_height
        
        # 确保渲染宽度不超过可用宽度
        max_render_width = available_width - 100  # 留出边距
        
        # 使用基准宽度，但不超过最大宽度
        self.render_width = min(base_render_width, max_render_width)
        self.render_height = base_render_height
        
        # 如果有PDF文件且渲染尺寸发生变化，重新渲染
        if (self.pdf_processor.fitz_document and 
            (self.render_width != old_render_width or self.render_height != old_render_height)):
            # 清除缓存以适应新的尺寸
            self.pdf_processor.clear_render_cache()
            self.update_preview()
        
    def show_message(self, message):
        """显示状态消息"""
        # 检查是否有未保存的更改
        has_changes = (hasattr(self.pdf_processor, 'page_editor') and 
                      self.pdf_processor.page_editor and 
                      self.pdf_processor.page_editor.has_unsaved_changes())
        modified_indicator = " ● 文档已修改 | " if has_changes else ""
        self.status_label.setText(f"📢 {modified_indicator}{message}")
    
    def convert_pdf_to_images(self):
        """将PDF转换为单张图片"""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                   QComboBox, QSpinBox, QPushButton, QGroupBox,
                                   QFileDialog, QProgressBar, QMessageBox,
                                   QRadioButton, QLineEdit)
        
        if not self.pdf_processor.fitz_document:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return
        
        class ConvertToImagesDialog(QDialog):
            def __init__(self, parent, pdf_processor):
                super().__init__(parent)
                self.pdf_processor = pdf_processor
                
                # 设置默认输出目录：当前文件所在目录，目录名与文件名一致（去掉后缀）
                if self.pdf_processor.current_file:
                    file_dir = os.path.dirname(self.pdf_processor.current_file)
                    file_name = os.path.basename(self.pdf_processor.current_file)
                    file_name_without_ext = os.path.splitext(file_name)[0]
                    self.output_dir = os.path.join(file_dir, file_name_without_ext)
                else:
                    self.output_dir = ""
                
                self.init_ui()
            
            def init_ui(self):
                self.setWindowTitle("PDF转图片")
                self.setFixedSize(500, 550)
                
                layout = QVBoxLayout()
                
                # 输出目录设置
                dir_group = QGroupBox("输出目录")
                dir_layout = QVBoxLayout()
                
                dir_btn_layout = QHBoxLayout()
                if self.output_dir:
                    self.dir_label = QLabel(self.output_dir)
                    self.dir_label.setStyleSheet("QLabel { color: #333; padding: 5px; background-color: #f0f8ff; border: 1px solid #4CAF50; border-radius: 3px; }")
                else:
                    self.dir_label = QLabel("未选择目录")
                    self.dir_label.setStyleSheet("QLabel { color: #666; padding: 5px; background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 3px; }")
                dir_btn_layout.addWidget(self.dir_label)
                
                select_dir_btn = QPushButton("选择目录")
                select_dir_btn.clicked.connect(self.select_output_dir)
                dir_btn_layout.addWidget(select_dir_btn)
                
                dir_layout.addLayout(dir_btn_layout)
                dir_group.setLayout(dir_layout)
                layout.addWidget(dir_group)
                
                # 页面选择设置
                page_group = QGroupBox("页面选择")
                page_layout = QVBoxLayout()
                
                # 页面范围选项
                page_range_layout = QHBoxLayout()
                page_range_layout.addWidget(QLabel("转换页面:"))
                
                self.all_pages_radio = QRadioButton("全部页面")
                self.all_pages_radio.setChecked(True)
                self.all_pages_radio.toggled.connect(self.on_page_range_changed)
                page_range_layout.addWidget(self.all_pages_radio)
                
                self.custom_pages_radio = QRadioButton("指定页面:")
                self.custom_pages_radio.toggled.connect(self.on_page_range_changed)
                page_range_layout.addWidget(self.custom_pages_radio)
                
                self.page_range_edit = QLineEdit()
                self.page_range_edit.setPlaceholderText("如: 1,3,5-9,11-14")
                self.page_range_edit.setEnabled(False)
                page_range_layout.addWidget(self.page_range_edit)
                
                page_layout.addLayout(page_range_layout)
                
                # 页面范围提示
                total_pages = self.pdf_processor.get_total_pages()
                page_hint = QLabel(f"提示: 总页数 {total_pages} 页，支持格式: 单个页码(1,3,5)，连续范围(1-5)，混合(1,3,5-9)")
                page_hint.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
                page_layout.addWidget(page_hint)
                
                page_group.setLayout(page_layout)
                layout.addWidget(page_group)
                
                # 图片格式设置
                format_group = QGroupBox("图片设置")
                format_layout = QVBoxLayout()
                
                # 图片格式
                format_row = QHBoxLayout()
                format_row.addWidget(QLabel("图片格式:"))
                self.format_combo = QComboBox()
                formats = self.pdf_processor.get_supported_image_formats()
                self.format_combo.addItems(formats)
                # 默认选择JPEG格式
                jpeg_index = self.format_combo.findText("JPEG")
                if jpeg_index >= 0:
                    self.format_combo.setCurrentIndex(jpeg_index)
                format_row.addWidget(self.format_combo)
                format_row.addStretch()
                format_layout.addLayout(format_row)
                
                # 图片分辨率
                dpi_row = QHBoxLayout()
                dpi_row.addWidget(QLabel("分辨率 (DPI):"))
                self.dpi_combo = QComboBox()
                recommended_dpi = self.pdf_processor.get_recommended_dpi()
                for quality, dpi in recommended_dpi.items():
                    self.dpi_combo.addItem(f"{quality} ({dpi} DPI)", dpi)
                self.dpi_combo.setCurrentIndex(1)  # 默认选择普通打印
                dpi_row.addWidget(self.dpi_combo)
                dpi_row.addStretch()
                format_layout.addLayout(dpi_row)
                
                format_group.setLayout(format_layout)
                layout.addWidget(format_group)
                
                # 转换信息
                info_group = QGroupBox("转换信息")
                info_layout = QVBoxLayout()
                
                total_pages = self.pdf_processor.get_total_pages()
                self.info_label = QLabel(f"总页数: {total_pages} 页")
                info_layout.addWidget(self.info_label)
                
                info_group.setLayout(info_layout)
                layout.addWidget(info_group)
                
                # 进度条
                self.progress_bar = QProgressBar()
                self.progress_bar.setVisible(False)
                layout.addWidget(self.progress_bar)
                
                # 按钮
                button_layout = QHBoxLayout()
                
                convert_btn = QPushButton("开始转换")
                convert_btn.clicked.connect(self.start_conversion)
                convert_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px; }")
                
                cancel_btn = QPushButton("取消")
                cancel_btn.clicked.connect(self.reject)
                
                button_layout.addWidget(convert_btn)
                button_layout.addStretch()
                button_layout.addWidget(cancel_btn)
                layout.addLayout(button_layout)
                
                self.setLayout(layout)
            
            def _set_ui_enabled(self, enabled: bool):
                """设置界面控件启用状态"""
                # 设置所有按钮状态
                for btn in self.findChildren(QPushButton):
                    if btn.text() in ["开始转换", "选择目录", "取消"]:
                        btn.setEnabled(enabled)
                
                # 设置其他控件状态
                self.format_combo.setEnabled(enabled)
                self.dpi_combo.setEnabled(enabled)
                self.all_pages_radio.setEnabled(enabled)
                self.custom_pages_radio.setEnabled(enabled)
                self.page_range_edit.setEnabled(enabled and self.custom_pages_radio.isChecked())
                self.dir_label.setEnabled(enabled)
            
            def on_page_range_changed(self):
                """页面范围选择改变事件"""
                self.page_range_edit.setEnabled(self.custom_pages_radio.isChecked())
            
            def select_output_dir(self):
                """选择输出目录"""
                directory = QFileDialog.getExistingDirectory(self, "选择图片保存目录")
                if directory:
                    self.output_dir = directory
                    self.dir_label.setText(directory)
                    self.dir_label.setStyleSheet("QLabel { color: #333; padding: 5px; background-color: #f0f8ff; border: 1px solid #4CAF50; border-radius: 3px; }")
            
            def start_conversion(self):
                """开始转换"""
                if not self.output_dir:
                    QMessageBox.warning(self, "警告", "请选择输出目录")
                    return
                
                # 获取页面范围
                if self.all_pages_radio.isChecked():
                    page_range = "all"
                else:
                    page_range = self.page_range_edit.text().strip()
                    if not page_range:
                        QMessageBox.warning(self, "警告", "请输入要转换的页面范围")
                        return
                
                # 获取用户选择的设置
                image_format = self.format_combo.currentText()
                dpi = self.dpi_combo.currentData()
                
                # 显示进度条
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # 无限进度条
                
                # 禁用界面控件，防止用户操作
                self._set_ui_enabled(False)
                
                # 执行转换（在子线程中执行以避免界面冻结）
                from PyQt5.QtCore import QThread, pyqtSignal
                
                class ConversionThread(QThread):
                    finished = pyqtSignal(bool, str)
                    
                    def __init__(self, pdf_processor, output_dir, dpi, image_format, page_range):
                        super().__init__()
                        self.pdf_processor = pdf_processor
                        self.output_dir = output_dir
                        self.dpi = dpi
                        self.image_format = image_format
                        self.page_range = page_range
                    
                    def run(self):
                        try:
                            success, message = self.pdf_processor.convert_pdf_to_images(
                                self.output_dir, self.dpi, self.image_format, self.page_range
                            )
                            self.finished.emit(success, message)
                        except Exception as e:
                            self.finished.emit(False, f"转换过程中发生错误: {str(e)}")
                
                self.conversion_thread = ConversionThread(
                    self.pdf_processor, self.output_dir, dpi, image_format, page_range
                )
                self.conversion_thread.finished.connect(self.on_conversion_finished)
                self.conversion_thread.start()
            
            def on_conversion_finished(self, success, message):
                """转换完成回调"""
                # 隐藏进度条
                self.progress_bar.setVisible(False)
                
                # 恢复界面控件状态
                self._set_ui_enabled(True)
                
                if success:
                    # 创建自定义消息框，包含打开目录选项
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("转换成功")
                    msg_box.setText(message)
                    msg_box.setIcon(QMessageBox.Information)
                    
                    # 添加打开目录按钮
                    open_dir_btn = msg_box.addButton("📂 打开目录", QMessageBox.ActionRole)
                    msg_box.addButton("确定", QMessageBox.AcceptRole)
                    
                    msg_box.exec_()
                    
                    # 如果点击了打开目录按钮
                    if msg_box.clickedButton() == open_dir_btn:
                        import subprocess
                        import platform
                        import os
                        
                        try:
                            # 根据操作系统打开目录
                            system = platform.system()
                            if system == "Windows":
                                # Windows需要特定的explorer命令格式
                                # 使用os.startfile()或者正确的explorer语法
                                if os.path.exists(self.output_dir):
                                    os.startfile(self.output_dir)
                                else:
                                    # 备用方法：使用explorer命令
                                    subprocess.Popen(['explorer', self.output_dir], shell=True)
                            elif system == "Darwin":  # macOS
                                subprocess.Popen(['open', self.output_dir])
                            else:  # Linux
                                subprocess.Popen(['xdg-open', self.output_dir])
                        except Exception as e:
                            QMessageBox.warning(self, "警告", f"无法打开目录: {str(e)}")
                    
                    self.accept()
                else:
                    QMessageBox.critical(self, "转换失败", message)
        
        # 显示转换对话框
        dialog = ConvertToImagesDialog(self, self.pdf_processor)
        dialog.exec_()
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>极灵PDF v1.0</h2>
        <p>一个功能强大的PDF文档处理工具</p>
        <p>支持PDF查看、编辑、转换、合并、分割等功能</p>
        <p>🎯 设计理念: 简单易用，功能强大</p>
        <p>新增功能: PDF转图片转换器</p>
        """
        
        QMessageBox.about(self, "关于", about_text)
        
    def open_file(self):
        """打开PDF文件"""
        logger.info("开始打开文件...")
        # 获取上次打开的目录
        last_dir = AppSettings.get_last_open_dir()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PDF文件", last_dir, "PDF文件 (*.pdf)")
        
        if file_path:
            logger.info(f"选择了文件: {file_path}")
            # 异步加载模式
            logger.info("使用异步加载模式...")
            self.show_progress_dialog("正在加载PDF文件...")
            success, message = self.pdf_processor.open_pdf(file_path, async_mode=True)
            
            if success:
                logger.info("异步加载启动成功")
                # 记忆打开文件的目录
                AppSettings.set_last_open_dir(file_path)
            else:
                logger.error(f"异步加载启动失败: {message}")
                self.hide_progress_dialog()
                QMessageBox.critical(self, "错误", message)
        else:
            logger.info("未选择文件")
            
    def save_file(self):
        """保存PDF文件"""
        if not self.pdf_processor.current_file:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return
        
        # 如果有未保存的更改，直接保存到原文件
        if (hasattr(self.pdf_processor, 'page_editor') and 
            self.pdf_processor.page_editor and 
            self.pdf_processor.page_editor.has_unsaved_changes()):
            
            success, message = self.pdf_processor.page_editor.save_changes()
            if success:
                self.show_message("✅ 更改已保存到原文件")
                # 更新保存操作状态
                self.update_save_actions_state()
                # 重新加载缩略图
                self.load_thumbnails()
            else:
                QMessageBox.critical(self, "保存失败", message)
        else:
            # 没有更改时执行另存为操作
            self.save_as_file()
    
    def save_as_file(self):
        """另存为PDF文件"""
        if not self.pdf_processor.current_file:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return
        
        # 获取上次保存的目录，如果没有则使用上次打开的目录
        last_save_dir = AppSettings.get_last_save_dir()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "另存为PDF文件", last_save_dir, "PDF文件 (*.pdf)")
        
        if file_path:
            success, message = self.pdf_processor.save_pdf(file_path)
            
            if success:
                # 记忆保存文件的目录
                AppSettings.set_last_save_dir(file_path)
                QMessageBox.information(self, "保存成功", message)
            else:
                QMessageBox.critical(self, "保存失败", message)
    
    def save_changes(self):
        """保存更改"""
        if (hasattr(self.pdf_processor, 'page_editor') and 
            self.pdf_processor.page_editor and 
            self.pdf_processor.page_editor.has_unsaved_changes()):
            
            success, message = self.pdf_processor.page_editor.save_changes()
            if success:
                self.show_message("✅ 更改已保存")
                self.save_changes_action.setEnabled(False)
                self.discard_changes_action.setEnabled(False)
                self.undo_action.setEnabled(False)
                self.redo_action.setEnabled(False)
                # 重新加载缩略图
                self.load_thumbnails()
            else:
                QMessageBox.critical(self, "保存失败", message)
        else:
            self.show_message("ℹ️ 没有需要保存的更改")
    
    def discard_changes(self):
        """放弃更改"""
        if (hasattr(self.pdf_processor, 'page_editor') and 
            self.pdf_processor.page_editor and 
            self.pdf_processor.page_editor.has_unsaved_changes()):
            
            reply = QMessageBox.question(
                self, 
                "确认放弃更改", 
                "确定要放弃所有未保存的更改吗？", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success, message = self.pdf_processor.page_editor.discard_changes()
                if success:
                    self.show_message("❌ 更改已放弃")
                    self.save_changes_action.setEnabled(False)
                    self.discard_changes_action.setEnabled(False)
                    self.undo_action.setEnabled(False)
                    self.redo_action.setEnabled(False)
                    # 重新加载缩略图
                    self.load_thumbnails()
                else:
                    QMessageBox.critical(self, "操作失败", message)
        else:
            self.show_message("ℹ️ 没有需要放弃的更改")
    
    def merge_pdfs(self):
        """合并PDF功能"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from PyQt5.QtCore import Qt
        
        # 选择多个PDF文件
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择要合并的PDF文件", "", "PDF文件 (*.pdf)")
        
        if not file_paths:
            return
        
        if len(file_paths) < 2:
            QMessageBox.information(self, "合并PDF", "至少需要选择两个PDF文件进行合并")
            return
        
        # 选择输出文件路径
        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存合并后的PDF文件", "", "PDF文件 (*.pdf)")
        
        if not output_path:
            return
        
        # 执行合并操作
        success, message = self.pdf_processor.merge_pdfs(file_paths, output_path)
        
        if success:
            QMessageBox.information(self, "合并PDF", "PDF文件合并成功！")
        else:
            QMessageBox.critical(self, "合并PDF", f"合并失败：{message}")

    def split_pdf(self):
        """分割PDF功能"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog
        import os
        
        if not self.pdf_processor.current_file:
            QMessageBox.information(self, "分割PDF", "请先打开PDF文件")
            return
        
        # 选择输出目录
        output_dir = QFileDialog.getExistingDirectory(self, "选择分割文件保存目录")
        
        if not output_dir:
            return
        
        # 询问分割方式
        pages_per_file, ok = QInputDialog.getInt(
            self, "分割PDF", "每份文件的页数（0表示按单页分割）:", 0, 0, 1000, 1)
        
        if not ok:
            return
        
        # 执行分割操作
        success, message = self.pdf_processor.split_pdf(output_dir, pages_per_file if pages_per_file > 0 else None)
        
        if success:
            QMessageBox.information(self, "分割PDF", "PDF文件分割成功！")
        else:
            QMessageBox.critical(self, "分割PDF", f"分割失败：{message}")
    
    def search_text(self):
        """搜索PDF中的文本"""
        search_text = self.search_lineedit.text().strip()
        
        if not search_text:
            QMessageBox.information(self, "搜索", "请输入要搜索的关键词")
            return
            
        if not self.pdf_processor.fitz_document:
            QMessageBox.information(self, "搜索", "请先打开PDF文件")
            return
        
        # 执行搜索
        success, result = self.pdf_processor.search_text(
            search_text, 
            self.search_case_sensitive, 
            self.search_whole_word
        )
        
        if success:
            # 保存搜索结果
            self.search_results = result['results']
            self.current_search_index = 0
            self.last_search_text = search_text
            
            # 显示搜索结果
            self.show_message(result['message'])
            
            # 高亮第一个匹配项
            if self.search_results:
                self.highlight_current_match()
            
            # 更新预览
            self.update_preview()
        else:
            self.show_message(f"搜索失败: {result}")
            QMessageBox.information(self, "搜索", result)
            
    def search_next(self):
        """搜索下一个匹配项"""
        if not self.search_results:
            QMessageBox.information(self, "搜索", "请先执行搜索")
            return
            
        if self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            
            # 跳转到匹配项所在页面
            result = self.search_results[self.current_search_index]
            self.pdf_processor.current_page = result['page_index']
            
            # 高亮当前匹配项
            self.highlight_current_match()
            
            # 更新预览
            self.update_preview()
            
            # 显示状态
            self.show_message(f"第 {self.current_search_index + 1} / {len(self.search_results)} 个匹配项")
        else:
            # 循环搜索，从头开始
            self.current_search_index = 0
            
            result = self.search_results[self.current_search_index]
            self.pdf_processor.current_page = result['page_index']
            
            self.highlight_current_match()
            self.update_preview()
            
            self.show_message(f"重新开始，第 1 / {len(self.search_results)} 个匹配项")
            
    def search_previous(self):
        """搜索上一个匹配项"""
        if not self.search_results:
            QMessageBox.information(self, "搜索", "请先执行搜索")
            return
            
        if self.current_search_index > 0:
            self.current_search_index -= 1
            
            # 跳转到匹配项所在页面
            result = self.search_results[self.current_search_index]
            self.pdf_processor.current_page = result['page_index']
            
            # 高亮当前匹配项
            self.highlight_current_match()
            
            # 更新预览
            self.update_preview()
            
            # 显示状态
            self.show_message(f"第 {self.current_search_index + 1} / {len(self.search_results)} 个匹配项")
        else:
            # 循环搜索，从最后一个开始
            self.current_search_index = len(self.search_results) - 1
            
            result = self.search_results[self.current_search_index]
            self.pdf_processor.current_page = result['page_index']
            
            self.highlight_current_match()
            self.update_preview()
            
            self.show_message(f"回到末尾，第 {len(self.search_results)} / {len(self.search_results)} 个匹配项")
            
    def highlight_current_match(self):
        """高亮当前匹配项"""
        if not self.search_results or self.current_search_index < 0:
            return
            
        # 清除之前的高亮
        self.pdf_processor.clear_highlights()
        
        # 高亮当前匹配项
        result = self.search_results[self.current_search_index]
        self.pdf_processor.highlight_search_result(
            result['page_index'], 
            result['rect']
        )
        
    def show_search_options(self):
        """显示搜索选项对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout as QDialogLayout, QHBoxLayout as QDialogLayout, QCheckBox, QPushButton, QGroupBox
        
        class SearchOptionsDialog(QDialog):
            def __init__(self, parent, case_sensitive, whole_word):
                super().__init__(parent)
                self.case_sensitive = case_sensitive
                self.whole_word = whole_word
                self.init_ui()
                
            def init_ui(self):
                self.setWindowTitle("搜索选项")
                self.setFixedSize(300, 200)
                
                layout = QVBoxLayout()
                
                # 搜索选项组
                options_group = QGroupBox("搜索选项")
                options_layout = QVBoxLayout()
                
                self.case_checkbox = QCheckBox("区分大小写")
                self.case_checkbox.setChecked(self.case_sensitive)
                options_layout.addWidget(self.case_checkbox)
                
                self.whole_word_checkbox = QCheckBox("全词匹配")
                self.whole_word_checkbox.setChecked(self.whole_word)
                options_layout.addWidget(self.whole_word_checkbox)
                
                options_group.setLayout(options_layout)
                layout.addWidget(options_group)
                
                # 按钮
                button_layout = QHBoxLayout()
                
                ok_button = QPushButton("确定")
                ok_button.clicked.connect(self.accept)
                button_layout.addWidget(ok_button)
                
                cancel_button = QPushButton("取消")
                cancel_button.clicked.connect(self.reject)
                button_layout.addWidget(cancel_button)
                
                layout.addLayout(button_layout)
                
                self.setLayout(layout)
        
        dialog = SearchOptionsDialog(
            self, 
            self.search_case_sensitive, 
            self.search_whole_word
        )
        
        if dialog.exec_() == QDialog.Accepted:
            self.search_case_sensitive = dialog.case_checkbox.isChecked()
            self.search_whole_word = dialog.whole_word_checkbox.isChecked()
            
            # 如果有搜索结果，重新搜索
            if self.last_search_text:
                self.search_text()
    
    def toggle_thumbnails(self):
        """切换缩略图显示/隐藏"""
        self.show_thumbnails = not self.show_thumbnails
        self.thumbnail_btn.setChecked(self.show_thumbnails)  # 更新按钮选中状态
        if self.show_thumbnails:
            self.thumbnail_dock.show()
            # 加载缩略图
            self.load_thumbnails()
        else:
            self.thumbnail_dock.hide()
    
    def load_thumbnails(self):
        """加载PDF页面缩略图"""
        if not self.pdf_processor.fitz_document:
            return
        
        # 使用缩略图管理器加载缩略图
        self.thumbnail_list.load_thumbnails()
    
    def on_thumbnail_clicked(self, page_num):
        """处理缩略图点击事件"""
        # 跳转到指定页面
        self.go_to_page(page_num)
        
        # 确保页面输入框更新
        self.page_spinbox.blockSignals(True)
        self.page_spinbox.setValue(page_num)
        self.page_spinbox.blockSignals(False)
    
    def on_thumbnail_right_clicked(self, page_num):
        """处理缩略图右键点击事件"""
        # 右键点击时已经自动选中了页面，这里可以添加其他处理逻辑
        logger.debug(f"右键点击第 {page_num} 页")
    
    def update_thumbnail_selection(self, current_page):
        """更新缩略图选中状态"""
        if self.thumbnail_list:
            self.thumbnail_list.update_thumbnail_selection(current_page)
    
    def undo_operation(self):
        """撤销操作 - 使用操作历史记录管理器"""
        try:
            # 直接使用PDF处理器的撤销功能
            success, message = self.pdf_processor.undo_operation()
            if success:
                self.show_message(f"✅ {message}")
                # 立即更新撤销/重做按钮状态
                self.update_save_actions_state()
                # 重新加载缩略图
                self.load_thumbnails()
                # 更新预览
                self.update_preview()
                # 强制界面刷新
                if hasattr(self, 'repaint'):
                    self.repaint()
            else:
                # 如果只是没有可撤销的操作，显示提示信息而不是错误
                if "没有可撤销的操作" in message:
                    self.show_message(f"ℹ️ {message}")
                else:
                    QMessageBox.warning(self, "撤销失败", message)
        except Exception as e:
            logger.error(f"撤销操作异常: {e}")
            QMessageBox.critical(self, "撤销失败", f"撤销操作发生异常: {str(e)}")

    def redo_operation(self):
        """重做操作 - 使用操作历史记录管理器"""
        try:
            # 直接使用PDF处理器的重做功能
            success, message = self.pdf_processor.redo_operation()
            if success:
                self.show_message(f"✅ {message}")
                # 立即更新撤销/重做按钮状态
                self.update_save_actions_state()
                # 重新加载缩略图
                self.load_thumbnails()
                # 更新预览
                self.update_preview()
                # 强制界面刷新
                if hasattr(self, 'repaint'):
                    self.repaint()
            else:
                # 如果只是没有可重做的操作，显示提示信息而不是错误
                if "没有可重做的操作" in message:
                    self.show_message(f"ℹ️ {message}")
                else:
                    QMessageBox.warning(self, "重做失败", message)
        except Exception as e:
            logger.error(f"重做操作异常: {e}")
            QMessageBox.critical(self, "重做失败", f"重做操作发生异常: {str(e)}")
    
    def clear_cache(self):
        """清理缓存"""
        # 清理PDF处理器缓存
        self.pdf_processor.clear_render_cache()
        
        # 清理缩略图缓存
        if hasattr(self.thumbnail_list, 'clear_cache'):
            self.thumbnail_list.clear_cache()
            
        # 清理虚拟滚动缓存
        if self.use_virtual_scroll and hasattr(self.virtual_scroll, 'clear_cache'):
            self.virtual_scroll.clear_cache()
            
        # 强制内存优化
        self.pdf_processor.optimize_memory_usage()
        
        self.show_message("🗑️ 所有缓存已清理")

    # ===== 性能优化相关方法 =====
    
    def _on_operation_history_changed(self):
        """操作历史记录发生变化时更新界面状态"""
        logger.debug("操作历史记录发生变化，更新界面状态")
        # 立即更新撤销/重做按钮状态
        self.update_save_actions_state()
        
    def _on_loading_progress(self, value, message):
        """加载进度更新"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
            
    def _on_pdf_loading_finished(self, success, message):
        """PDF加载完成"""
        # 隐藏进度对话框
        self.hide_progress_dialog()
        
        if success:
            # 更新缩略图管理器中的PDF处理器
            if hasattr(self, 'thumbnail_list') and self.thumbnail_list:
                logger.debug("更新缩略图管理器中的PDF处理器")
                self.thumbnail_list.set_pdf_processor(self.pdf_processor)
            
            # 更新界面标题
            if self.pdf_processor.current_file:
                self.setWindowTitle(f"{AppSettings.APP_NAME} - {os.path.basename(self.pdf_processor.current_file)}")
            
            # 显示PDF信息
            pdf_info = self.pdf_processor.get_pdf_info()
            if pdf_info:
                info_text = f"📄 {pdf_info['filename']} | 📖 共{pdf_info['page_count']}页 | 💾 {pdf_info['file_size']}"
                if pdf_info['is_encrypted']:
                    info_text += " | 🔒 已加密"
                
                self.show_message(info_text)
                logger.debug(f"PDF信息: {info_text}")
                
                # 确保显示第一页
                self.pdf_processor.go_to_page(1)
                logger.debug("已跳转到第1页")
                
                # 更新页码控件的最大值和总页数显示
                total_pages = self.pdf_processor.get_total_pages()
                self.page_spinbox.setMaximum(total_pages)
                self.total_pages_label.setText(f"/ {total_pages}")
                
                # 延迟更新预览区域，确保所有组件初始化完成
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, self._delayed_update_preview)
                logger.debug("已安排延迟更新预览区域")
                                
                # 如果缩略图面板是显示状态，加载缩略图
                if self.show_thumbnails:
                    logger.debug("开始加载缩略图...")
                    self.load_thumbnails()
                    logger.debug("缩略图加载完成")
                
                # 更新按钮状态
                self.update_save_actions_state()
        else:
            QMessageBox.critical(self, "错误", message)
    
    def _delayed_update_preview(self):
        """延迟更新预览区域，确保所有组件初始化完成"""
        logger.debug("延迟更新预览区域开始...")
        self.update_preview()
        logger.debug("延迟更新预览区域完成")
    
    def update_preview(self):
        """更新PDF预览显示"""
        logger.debug("开始更新预览...")
        if not self.pdf_processor.fitz_document:
            logger.debug("没有PDF文档加载")
            return
        
        try:
            logger.debug("PDF文档已加载")
            # 更新标题栏显示文件名
            if self.pdf_processor.current_file:
                # 显示原始文件名而不是临时文件名
                display_filename = self.pdf_processor.current_file
                if (hasattr(self.pdf_processor, 'page_editor') and 
                    self.pdf_processor.page_editor and 
                    self.pdf_processor.page_editor.get_original_filename()):
                    display_filename = self.pdf_processor.page_editor.get_original_filename()
                
                filename = os.path.basename(display_filename)
                # 检查是否有未保存的更改
                has_changes = (hasattr(self.pdf_processor, 'page_editor') and 
                              self.pdf_processor.page_editor and 
                              self.pdf_processor.page_editor.has_unsaved_changes())
                modified_indicator = " ●" if has_changes else ""
                self.setWindowTitle(f"{AppSettings.APP_NAME} - {filename}{modified_indicator}")
            
            # 更新页码控件范围
            total_pages = self.pdf_processor.get_total_pages()
            self.page_spinbox.setMaximum(total_pages)
            
            # 更新总页数标签
            self.total_pages_label.setText(f"/ {total_pages}")
            
            # 更新缩略图
            if self.show_thumbnails:
                self.load_thumbnails()
            
            # 使用虚拟滚动模式
            logger.debug("使用虚拟滚动模式")
            self._setup_virtual_scroll_data()
            self.virtual_scroll.update_content()
            
            logger.debug("预览更新完成")
        except Exception as e:
            logger.error(f"更新预览时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _setup_virtual_scroll_data(self):
        """设置虚拟滚动数据"""
        logger.debug("开始设置虚拟滚动数据...")
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            logger.debug("PDF处理器未准备好")
            return
            
        try:
            # 获取总页数
            total_pages = self.pdf_processor.get_total_pages()
            logger.debug(f"总页数: {total_pages}")
            
            # 构建页面数据
            pages_data = []
            for page_num in range(total_pages):
                # 获取页面尺寸
                dimensions = self.pdf_processor.get_page_dimensions(page_num)
                if dimensions:
                    width = int(dimensions['width'] * self.pdf_processor.zoom_factor)
                    height = int(dimensions['height'] * self.pdf_processor.zoom_factor)
                else:
                    # 使用默认尺寸
                    width = 800
                    height = 1100
                
                pages_data.append({
                    'page_num': page_num,
                    'width': width,
                    'height': height,
                    'zoom_factor': self.pdf_processor.zoom_factor
                })
            
            logger.debug(f"准备设置{len(pages_data)}页数据到虚拟滚动区域")
            # 设置虚拟滚动数据
            self.virtual_scroll.set_pages_data(pages_data)
            
            # 确保信号连接以处理页面渲染
            if hasattr(self.virtual_scroll, 'page_visible'):
                try:
                    self.virtual_scroll.page_visible.connect(self._on_page_visible)
                    logger.debug("虚拟滚动信号连接成功")
                except Exception as signal_error:
                    logger.debug(f"信号连接失败（可能已连接）: {signal_error}")
                
            logger.debug("虚拟滚动数据设置完成")
        except Exception as e:
            logger.error(f"设置虚拟滚动数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    def _on_page_rendered(self, page_num, pixmap):
        """页面渲染完成"""
        logger.debug(f"主窗口接收到第{page_num + 1}页渲染完成通知")
        # 直接转发到虚拟滚动区域
        logger.debug("转发到虚拟滚动区域...")
        self.virtual_scroll.on_page_rendered(page_num, pixmap)
        
    def _on_thumbnail_ready(self, page_num, pixmap):
        """缩略图就绪"""
        # 智能缩略图管理器会自动处理
        pass
        
    def _on_page_visible(self, page_num):
        """页面变为可见"""
        if hasattr(self.pdf_processor, 'render_pages_async'):
            self.pdf_processor.render_pages_async([page_num], self.render_width, self.render_height)
            
    def _on_page_hidden(self, page_num):
        """页面变为隐藏"""
        # 可以在这里清理隐藏页面的缓存
        pass
        
    def _monitor_performance(self):
        """监控性能"""
        # 直接执行性能监控，无需检查优化标志
        try:
            # 获取缓存统计
            cache_stats = self.pdf_processor.get_cache_stats()
            
            # 更新性能显示（如果状态栏有性能标签）
            if hasattr(self, 'performance_label'):
                perf_text = f"内存: {cache_stats['current_memory_usage_mb']:.1f}MB | "
                perf_text += f"缓存命中率: {cache_stats['page_cache_hit_rate']:.1%}"
                self.performance_label.setText(perf_text)
            
            # 自动优化内存
            if cache_stats['current_memory_usage_mb'] > cache_stats['max_memory_usage_mb'] * 0.8:
                self.pdf_processor.optimize_memory_usage()
                
        except Exception as e:
            logger.error(f"性能监控错误: {e}")
    
    def show_progress_dialog(self, title, cancellable=True):
        """显示进度对话框"""
        # 直接显示进度对话框，无需检查优化标志
        self.progress_dialog = QProgressDialog(title, "取消", 0, 100, self)
        self.progress_dialog.setWindowTitle("进度")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        
        if cancellable:
            self.progress_dialog.canceled.connect(self._cancel_loading)
                
    def hide_progress_dialog(self):
        """隐藏进度对话框"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
            
    def _cancel_loading(self):
        """取消加载"""
        if hasattr(self.pdf_processor, 'async_loader') and self.pdf_processor.async_loader:
            self.pdf_processor.async_loader.cancel()
        self.hide_progress_dialog()
        self.show_message("❌ 加载已取消")

    def on_virtual_scroll_page_changed(self, current_page):
        """处理虚拟滚动页面变更事件"""
        logger.debug(f"接收到虚拟滚动页面变更: {current_page}")
        # 更新页码显示（避免触发额外的事件）
        if current_page != self.page_spinbox.value():
            logger.debug(f"页码变更: {self.page_spinbox.value()} -> {current_page}")
            # 阻止信号以避免循环触发
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setValue(current_page)
            self.page_spinbox.blockSignals(False)
                            
            # 更新状态栏
            if self.pdf_processor:
                total_pages = self.pdf_processor.get_total_pages()
                zoom_level = int(self.pdf_processor.get_zoom() * 100)
                self.show_message(f"⚡ 虚拟滚动模式 | 第 {current_page} 页 / 共 {total_pages} 页 | 缩放: {zoom_level}%")
                # 更新总页数标签
                self.total_pages_label.setText(f"/ {total_pages}")
                            
                # 更新缩略图选中状态
                self.update_thumbnail_selection(current_page)

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        logger.debug("开始处理窗口关闭事件")
        
        # 停止定时器
        if hasattr(self, 'update_actions_timer'):
            self.update_actions_timer.stop()
        
        # 检查是否有未保存的更改
        has_unsaved_changes = False
        page_editor = None
        
        # 首先检查PDF处理器中的页面编辑器
        if hasattr(self.pdf_processor, 'page_editor') and self.pdf_processor.page_editor:
            page_editor = self.pdf_processor.page_editor
            has_unsaved_changes = page_editor.has_unsaved_changes()
            logger.debug(f"PDF处理器中的页面编辑器存在: {page_editor is not None}")
            logger.debug(f"是否有未保存的更改: {has_unsaved_changes}")
            logger.debug(f"临时文件: {getattr(page_editor, 'temp_file', 'None')}")
            logger.debug(f"原始文件: {getattr(page_editor, 'original_file', 'None')}")
            logger.debug(f"是否已修改: {getattr(page_editor, 'is_modified', 'None')}")
        # 然后检查缩略图管理器中的页面编辑器
        elif hasattr(self, 'thumbnail_list') and self.thumbnail_list and hasattr(self.thumbnail_list, 'page_editor') and self.thumbnail_list.page_editor:
            page_editor = self.thumbnail_list.page_editor
            has_unsaved_changes = page_editor.has_unsaved_changes()
            logger.debug(f"缩略图管理器中的页面编辑器存在: {page_editor is not None}")
            logger.debug(f"是否有未保存的更改: {has_unsaved_changes}")
            logger.debug(f"临时文件: {getattr(page_editor, 'temp_file', 'None')}")
            logger.debug(f"原始文件: {getattr(page_editor, 'original_file', 'None')}")
            logger.debug(f"是否已修改: {getattr(page_editor, 'is_modified', 'None')}")
        else:
            logger.debug("页面编辑器不存在")
        
        if has_unsaved_changes:
            logger.debug("检测到未保存的更改，显示确认对话框")
            # 显示确认对话框
            reply = QMessageBox.question(
                self, 
                "保存更改", 
                "文档已被修改，是否保存更改？", 
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, 
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                logger.debug("用户选择保存更改")
                # 保存更改
                success, message = page_editor.save_changes()
                if not success:
                    logger.error(f"保存失败: {message}")
                    QMessageBox.critical(self, "保存失败", message)
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                logger.debug("用户取消关闭")
                # 取消关闭
                event.ignore()
                return
        else:
            logger.debug("没有未保存的更改")
        
        # 正常关闭
        logger.debug("正常关闭程序")
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName(AppSettings.APP_NAME)
    app.setApplicationVersion(AppSettings.APP_VERSION)
    app.setOrganizationName(AppSettings.ORGANIZATION)
    
    # 创建主窗口
    viewer = AuroraPDF()
    viewer.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()