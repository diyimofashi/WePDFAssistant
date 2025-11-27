"""
优化版主程序入口 - 集成所有性能优化功能
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('optimized_main')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QToolBar, QAction, QFileDialog, QSplitter,
                             QLabel, QStatusBar, QMessageBox, QPushButton,
                             QLineEdit, QSpinBox, QComboBox, QMenu, QMenuBar,
                             QScrollArea, QScrollBar, QDialog, QGroupBox,
                             QSizePolicy, QProgressDialog, QVBoxLayout, QHBoxLayout)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

from app.config.settings import AppSettings
from app.ui.styles import AppStyles
from app.core.pdf_processor import PDFProcessor
from app.ui.virtual_scroll import VirtualScrollArea
from app.ui.smart_thumbnail import SmartThumbnailManager


class OptimizedAuroraPDF(QMainWindow):
    """优化版极灵PDF主窗口 - 集成所有性能优化"""
    
    def __init__(self):
        super().__init__()
        self.pdf_processor = PDFProcessor()
        
        # 连接PDF处理器信号
        self.pdf_processor.loading_progress.connect(self._on_loading_progress)
        self.pdf_processor.loading_finished.connect(self._on_pdf_loaded)
        self.pdf_processor.page_rendered.connect(self._on_page_rendered)
        self.pdf_processor.thumbnail_ready.connect(self._on_thumbnail_ready)
        
        # 搜索相关属性
        self.search_results = []
        self.current_search_index = -1
        self.last_search_text = ""
        self.search_case_sensitive = False
        self.search_whole_word = False
        
        # 性能监控
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._monitor_performance)
        self.performance_timer.start(5000)  # 每5秒监控一次
        
        # 连续浏览模式属性
        self.continuous_mode = True
        self.use_virtual_scroll = True  # 默认使用虚拟滚动
        
        # 页面高度缓存
        self.page_heights = []
        self.page_positions = []
        
        # 动态渲染尺寸
        self.render_width = 800
        self.render_height = 1100
        
        # 窗口大小调整防抖
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_render_size)
        
        # 进度对话框
        self.progress_dialog = None
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI界面"""
        # 设置窗口属性
        self.setWindowTitle(f"{AppSettings.APP_NAME} v{AppSettings.APP_VERSION} (优化版)")
        self.setGeometry(100, 100, AppSettings.WINDOW_WIDTH, AppSettings.WINDOW_HEIGHT)
        self.setMinimumSize(AppSettings.WINDOW_MIN_WIDTH, AppSettings.WINDOW_MIN_HEIGHT)
        
        # 默认最大化窗口
        self.showMaximized()
        
        # 设置应用样式
        self.apply_styles()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
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
        self.show_message("🚀 优化版就绪 - 支持异步加载和虚拟滚动")
        
    def create_thumbnail_area(self, main_layout):
        """创建缩略图区域"""
        from PyQt5.QtWidgets import QDockWidget
        
        # 创建停靠窗口
        self.thumbnail_dock = QDockWidget("智能缩略图", self)
        self.thumbnail_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.thumbnail_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        # 设置样式
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
        """)
        
        # 设置默认宽度
        self.thumbnail_dock.setMinimumWidth(250)
        self.thumbnail_dock.resize(280, self.thumbnail_dock.height())
        
        # 创建智能缩略图管理器
        self.thumbnail_manager = SmartThumbnailManager(self)
        self.thumbnail_manager.set_pdf_processor(self.pdf_processor)
        
        # 连接信号
        self.thumbnail_manager.thumbnail_clicked.connect(self.on_thumbnail_clicked)
        self.thumbnail_manager.thumbnail_right_clicked.connect(self.on_thumbnail_right_clicked)
        
        self.thumbnail_dock.setWidget(self.thumbnail_manager)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.thumbnail_dock)
        
        # 默认隐藏缩略图
        self.thumbnail_dock.hide()
        
    def create_pdf_display_area(self, main_layout):
        """创建PDF显示区域 - 支持虚拟滚动"""
        # 创建虚拟滚动区域
        self.virtual_scroll = VirtualScrollArea(self)
        self.virtual_scroll.page_visible.connect(self._on_page_visible)
        self.virtual_scroll.page_hidden.connect(self._on_page_hidden)
        
        # 备用传统滚动区域
        self.traditional_scroll = QScrollArea()
        self.traditional_scroll.setWidgetResizable(True)
        self.traditional_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.traditional_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.traditional_scroll.setAlignment(Qt.AlignCenter)
        
        # 创建传统滚动内容容器
        self.scroll_content = QWidget()
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setSpacing(0)
        self.scroll_content_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_content_layout.setAlignment(Qt.AlignCenter)
        
        # 设置样式
        self.traditional_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        
        self.traditional_scroll.setWidget(self.scroll_content)
        
        # 创建预览标签（初始状态）
        self.preview_label = QLabel("📄 请点击上方'打开'按钮选择PDF文件")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFont(QFont("微软雅黑", 14))
        
        self.scroll_content_layout.addWidget(self.preview_label)
        
        # 默认使用虚拟滚动
        self.current_scroll_area = self.virtual_scroll
        main_layout.addWidget(self.virtual_scroll)
        
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet(AppStyles.get_stylesheet(AppSettings.THEME))
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
        
        file_menu.addSeparator()
        exit_action = QAction("🚪 退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("👁️ 视图")
        
        # 虚拟滚动切换
        self.virtual_scroll_action = QAction("⚡ 虚拟滚动", self)
        self.virtual_scroll_action.setCheckable(True)
        self.virtual_scroll_action.setChecked(self.use_virtual_scroll)
        self.virtual_scroll_action.triggered.connect(self.toggle_virtual_scroll)
        view_menu.addAction(self.virtual_scroll_action)
        
        view_menu.addSeparator()
        
        self.continuous_action = QAction("📜 连续浏览", self)
        self.continuous_action.setCheckable(True)
        self.continuous_action.setChecked(self.continuous_mode)
        self.continuous_action.triggered.connect(self.toggle_continuous_mode)
        view_menu.addAction(self.continuous_action)
        
        # 性能监控
        view_menu.addSeparator()
        self.performance_action = QAction("📊 性能监控", self)
        self.performance_action.setCheckable(True)
        self.performance_action.triggered.connect(self.toggle_performance_monitor)
        view_menu.addAction(self.performance_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("❓ 帮助")
        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_main_toolbar(self):
        """创建主工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # 文件操作
        open_btn = QAction("📂 打开", self)
        open_btn.setToolTip("打开PDF文件 (Ctrl+O)")
        open_btn.setShortcut("Ctrl+O")
        open_btn.triggered.connect(self.open_file)
        toolbar.addAction(open_btn)
        
        toolbar.addSeparator()
        
        # 缩放控制
        zoom_in_btn = QAction("🔍 放大", self)
        zoom_in_btn.setToolTip("放大页面 (+)")
        zoom_in_btn.setShortcut("Ctrl++")
        zoom_in_btn.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_btn)
        
        zoom_out_btn = QAction("🔎 缩小", self)
        zoom_out_btn.setToolTip("缩小页面 (-)")
        zoom_out_btn.setShortcut("Ctrl+-")
        zoom_out_btn.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_btn)
        
        fit_width_btn = QAction("📏 适合宽度", self)
        fit_width_btn.setToolTip("适合宽度显示")
        fit_width_btn.setShortcut("Ctrl+W")
        fit_width_btn.triggered.connect(self.fit_width)
        toolbar.addAction(fit_width_btn)
        
        toolbar.addSeparator()
        
        # 页面导航
        prev_page_btn = QAction("⬅️ 上一页", self)
        prev_page_btn.setToolTip("上一页 (PageUp)")
        prev_page_btn.setShortcut("PageUp")
        prev_page_btn.triggered.connect(self.previous_page)
        toolbar.addAction(prev_page_btn)
        
        next_page_btn = QAction("➡️ 下一页", self)
        next_page_btn.setToolTip("下一页 (PageDown)")
        next_page_btn.setShortcut("PageDown")
        next_page_btn.triggered.connect(self.next_page)
        toolbar.addAction(next_page_btn)
        
        # 页码控件
        toolbar.addWidget(QLabel("页码:"))
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(1)
        self.page_spinbox.setFixedWidth(60)
        self.page_spinbox.valueChanged.connect(self.go_to_page)
        toolbar.addWidget(self.page_spinbox)
        
        self.total_pages_label = QLabel("/ 1")
        toolbar.addWidget(self.total_pages_label)
        
        toolbar.addSeparator()
        
        # 缩略图切换
        self.thumbnail_btn = QAction("📋 缩略图", self)
        self.thumbnail_btn.setToolTip("显示/隐藏缩略图")
        self.thumbnail_btn.setShortcut("Ctrl+T")
        self.thumbnail_btn.triggered.connect(self.toggle_thumbnails)
        toolbar.addAction(self.thumbnail_btn)
        
        # 缓存清理
        self.cache_btn = QAction("🗑️ 清理缓存", self)
        self.cache_btn.setToolTip("清理所有缓存")
        self.cache_btn.triggered.connect(self.clear_cache)
        toolbar.addAction(self.cache_btn)
        
    def create_statusbar(self):
        """创建状态栏"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        # 状态信息
        self.status_label = QLabel("🟢 就绪")
        statusbar.addWidget(self.status_label)
        
        # 性能信息
        self.performance_label = QLabel("")
        statusbar.addPermanentWidget(self.performance_label)
        
    # ===== 文件操作 =====
    
    def open_file(self):
        """打开PDF文件 - 异步加载"""
        last_dir = AppSettings.get_last_open_dir()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PDF文件", last_dir, "PDF文件 (*.pdf)"
        )
        
        if file_path:
            # 显示进度对话框
            self.show_progress_dialog("正在加载PDF文件...")
            
            # 异步打开PDF
            success, message = self.pdf_processor.open_pdf(file_path, async_mode=True)
            
            if not success:
                self.hide_progress_dialog()
                QMessageBox.critical(self, "错误", message)
            else:
                # 记忆目录
                AppSettings.set_last_open_dir(file_path)
                
    def _on_loading_progress(self, value, message):
        """加载进度更新"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
            
    def _on_pdf_loaded(self, success, message):
        """PDF加载完成"""
        self.hide_progress_dialog()
        
        if success:
            # 更新窗口标题
            self.setWindowTitle(f"{AppSettings.APP_NAME} - {os.path.basename(self.pdf_processor.current_file)}")
            
            # 更新界面
            self.update_preview()
            
            # 加载缩略图
            if self.thumbnail_dock.isVisible():
                self.thumbnail_manager.load_thumbnails()
                
            self.show_message(f"✅ {message}")
        else:
            QMessageBox.critical(self, "错误", message)
            
    def show_progress_dialog(self, title, cancellable=True):
        """显示进度对话框"""
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
        if self.pdf_processor.async_loader:
            self.pdf_processor.async_loader.cancel()
        self.hide_progress_dialog()
        self.show_message("❌ 加载已取消")
        
    # ===== 页面导航 =====
    
    def previous_page(self):
        """上一页"""
        success, message = self.pdf_processor.previous_page()
        if success:
            self.update_preview()
        self.show_message(message)
        
    def next_page(self):
        """下一页"""
        success, message = self.pdf_processor.next_page()
        if success:
            self.update_preview()
        self.show_message(message)
        
    def go_to_page(self, page_number):
        """跳转到指定页面"""
        if self.use_virtual_scroll and self.current_scroll_area == self.virtual_scroll:
            # 虚拟滚动模式
            self.virtual_scroll.scroll_to_page(page_number - 1)
        else:
            # 传统模式
            success, message = self.pdf_processor.go_to_page(page_number)
            if success:
                self.update_preview()
            self.show_message(message)
            
    def on_thumbnail_clicked(self, page_num):
        """缩略图点击事件"""
        self.go_to_page(page_num)
        
    def on_thumbnail_right_clicked(self, page_num):
        """缩略图右键点击事件"""
        # 简化的右键处理
        self.show_message(f"右键点击第 {page_num} 页")
        
    # ===== 缩放控制 =====
    
    def zoom_in(self):
        """放大"""
        current_zoom = self.pdf_processor.get_zoom()
        new_zoom = min(current_zoom * 1.2, 4.0)
        success, message = self.pdf_processor.set_zoom(new_zoom)
        if success:
            self.update_preview()
        self.show_message(message)
        
    def zoom_out(self):
        """缩小"""
        current_zoom = self.pdf_processor.get_zoom()
        new_zoom = max(current_zoom / 1.2, 0.25)
        success, message = self.pdf_processor.set_zoom(new_zoom)
        if success:
            self.update_preview()
        self.show_message(message)
        
    def fit_width(self):
        """适合宽度"""
        success, message = self.pdf_processor.set_zoom(1.0)
        if success:
            self.update_preview()
        self.show_message("适合宽度显示")
        
    def fit_page(self):
        """适合页面"""
        success, message = self.pdf_processor.set_zoom(1.0)
        if success:
            self.update_preview()
        self.show_message("适合页面显示")
        
    # ===== 视图切换 =====
    
    def toggle_virtual_scroll(self):
        """切换虚拟滚动"""
        self.use_virtual_scroll = self.virtual_scroll_action.isChecked()
        
        if self.use_virtual_scroll:
            # 切换到虚拟滚动
            if hasattr(self, 'main_layout'):
                self.main_layout.replaceWidget(self.traditional_scroll, self.virtual_scroll)
            self.traditional_scroll.hide()
            self.virtual_scroll.show()
            self.current_scroll_area = self.virtual_scroll
            self.show_message("⚡ 已切换到虚拟滚动模式")
        else:
            # 切换到传统滚动
            if hasattr(self, 'main_layout'):
                self.main_layout.replaceWidget(self.virtual_scroll, self.traditional_scroll)
            self.virtual_scroll.hide()
            self.traditional_scroll.show()
            self.current_scroll_area = self.traditional_scroll
            self.update_preview()  # 重新渲染
            self.show_message("📜 已切换到传统滚动模式")
            
    def toggle_continuous_mode(self):
        """切换连续浏览模式"""
        self.continuous_mode = self.continuous_action.isChecked()
        self.pdf_processor.set_continuous_mode(self.continuous_mode)
        self.update_preview()
        mode_text = "连续浏览模式" if self.continuous_mode else "单页浏览模式"
        self.show_message(f"📄 已切换到{mode_text}")
        
    def toggle_thumbnails(self):
        """切换缩略图显示"""
        if self.thumbnail_dock.isVisible():
            self.thumbnail_dock.hide()
            self.thumbnail_btn.setText("📋 缩略图")
        else:
            self.thumbnail_dock.show()
            self.thumbnail_btn.setText("📋 缩略图")
            if self.pdf_processor.fitz_document:
                self.thumbnail_manager.load_thumbnails()
                
    def toggle_performance_monitor(self):
        """切换性能监控"""
        if self.performance_action.isChecked():
            self.performance_timer.start(1000)  # 每秒更新
            self.show_message("📊 性能监控已开启")
        else:
            self.performance_timer.start(5000)  # 每5秒更新
            self.show_message("📊 性能监控已关闭")
            
    def clear_cache(self):
        """清理缓存"""
        # 清理PDF处理器缓存
        self.pdf_processor.clear_render_cache()
        
        # 清理缩略图缓存
        if hasattr(self, 'thumbnail_manager'):
            self.thumbnail_manager.clear_cache()
            
        # 清理虚拟滚动缓存
        if self.use_virtual_scroll:
            self.virtual_scroll.clear_cache()
            
        # 强制内存优化
        self.pdf_processor.optimize_memory_usage()
        
        self.show_message("🗑️ 所有缓存已清理")
        
    # ===== 界面更新 =====
    
    def update_preview(self):
        """更新预览区域"""
        if not self.pdf_processor.fitz_document:
            return
            
        if self.use_virtual_scroll and self.current_scroll_area == self.virtual_scroll:
            self._update_virtual_scroll()
        else:
            self._update_traditional_scroll()
            
        # 更新页面信息
        self._update_page_info()
        
    def _update_virtual_scroll(self):
        """更新虚拟滚动区域"""
        if not self.pdf_processor.fitz_document:
            return
            
        total_pages = self.pdf_processor.get_total_pages()
        
        # 准备页面数据
        pages_data = []
        for page_num in range(total_pages):
            # 获取页面尺寸
            page_dimensions = self.pdf_processor.get_page_dimensions(page_num)
            if page_dimensions:
                width = int(page_dimensions['width'] * self.pdf_processor.zoom_factor)
                height = int(page_dimensions['height'] * self.pdf_processor.zoom_factor)
            else:
                width = self.render_width
                height = self.render_height
                
            pages_data.append({
                'page_num': page_num,
                'width': width,
                'height': height,
                'zoom_factor': self.pdf_processor.zoom_factor
            })
            
        # 设置页面数据到虚拟滚动区域
        self.virtual_scroll.set_pages_data(pages_data)
        
    def _update_traditional_scroll(self):
        """更新传统滚动区域"""
        if not self.pdf_processor.fitz_document:
            return
            
        # 清空现有内容
        for i in reversed(range(self.scroll_content_layout.count())):
            child = self.scroll_content_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
                
        if self.continuous_mode:
            # 连续模式：渲染所有页面
            total_pages = self.pdf_processor.get_total_pages()
            for page_num in range(total_pages):
                pixmap = self.pdf_processor.render_page_at(page_num, self.render_width, self.render_height)
                if pixmap:
                    page_label = self._create_page_label(pixmap, page_num)
                    self.scroll_content_layout.addWidget(page_label)
        else:
            # 单页模式：只渲染当前页
            pixmap = self.pdf_processor.render_page(self.render_width, self.render_height)
            if pixmap:
                page_label = self._create_page_label(pixmap, self.pdf_processor.current_page)
                self.scroll_content_layout.addWidget(page_label)
                
    def _create_page_label(self, pixmap, page_num):
        """创建页面标签"""
        page_label = QLabel()
        page_label.setPixmap(pixmap)
        page_label.setAlignment(Qt.AlignCenter)
        page_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 5px;
                margin: 5px;
            }
        """)
        return page_label
        
    def _update_page_info(self):
        """更新页面信息"""
        current_page = self.pdf_processor.get_current_page()
        total_pages = self.pdf_processor.get_total_pages()
        zoom_level = int(self.pdf_processor.get_zoom() * 100)
        
        # 更新页码控件
        self.page_spinbox.setMaximum(total_pages)
        self.page_spinbox.setValue(current_page)
        self.total_pages_label.setText(str(total_pages))
        
        # 更新状态栏
        mode_text = "⚡ 虚拟滚动" if self.use_virtual_scroll else ("📜 连续" if self.continuous_mode else "📄 单页")
        self.show_message(f"{mode_text} | 第 {current_page} 页 / 共 {total_pages} 页 | 缩放: {zoom_level}%")
        
    # ===== 事件处理 =====
    
    def _on_page_visible(self, page_num):
        """页面变为可见 - 异步渲染"""
        if hasattr(self.pdf_processor, 'render_pages_async'):
            self.pdf_processor.render_pages_async([page_num], self.render_width, self.render_height)
            
    def _on_page_hidden(self, page_num):
        """页面变为隐藏"""
        # 可以在这里清理隐藏页面的缓存
        pass
        
    def _on_page_rendered(self, page_num, pixmap):
        """页面渲染完成"""
        if self.use_virtual_scroll:
            self.virtual_scroll.on_page_rendered(page_num, pixmap)
            
    def _on_thumbnail_ready(self, page_num, pixmap):
        """缩略图就绪"""
        # 智能缩略图管理器会自动处理
        pass
        
    def _monitor_performance(self):
        """监控性能"""
        try:
            # 获取缓存统计
            cache_stats = self.pdf_processor.get_cache_stats()
            
            # 更新性能显示
            perf_text = f"内存: {cache_stats['current_memory_usage_mb']:.1f}MB | "
            perf_text += f"缓存命中率: {cache_stats['page_cache_hit_rate']:.1%} | "
            perf_text += f"缩略图缓存: {cache_stats['thumbnail_cache_size']}项"
            
            self.performance_label.setText(perf_text)
            
            # 自动优化内存
            if cache_stats['current_memory_usage_mb'] > cache_stats['max_memory_usage_mb'] * 0.8:
                self.pdf_processor.optimize_memory_usage()
                
        except Exception as e:
            logger.error(f"性能监控错误: {e}")
            
    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        self.resize_timer.start(100)
        
    def _update_render_size(self):
        """更新渲染尺寸"""
        if self.use_virtual_scroll:
            available_width = self.virtual_scroll.width() - 40
            available_height = self.virtual_scroll.height() - 40
        else:
            available_width = self.traditional_scroll.width() - 40
            available_height = self.traditional_scroll.height() - 40
            
        # 动态调整渲染尺寸
        old_render_width = self.render_width
        old_render_height = self.render_height
        
        self.render_width = max(600, int(available_width * 0.7))
        self.render_height = max(800, int(available_height * 0.7))
        
        # 如果尺寸变化且已加载PDF，重新渲染
        if (self.pdf_processor.fitz_document and 
            (self.render_width != old_render_width or self.render_height != old_render_height)):
            self.pdf_processor.clear_render_cache()
            self.update_preview()
            
    def show_message(self, message):
        """显示状态消息"""
        self.status_label.setText(f"📢 {message}")
        
    def show_about(self):
        """显示关于信息"""
        about_text = f"""
        <h2>{AppSettings.APP_NAME} (优化版)</h2>
        <p>版本: {AppSettings.APP_VERSION}</p>
        <p>一个高性能的PDF文档处理工具</p>
        <p>🚀 新特性:</p>
        <ul>
            <li>异步PDF加载，避免UI阻塞</li>
            <li>虚拟滚动技术，支持大文件流畅浏览</li>
            <li>智能缓存管理，提升渲染性能</li>
            <li>延迟加载缩略图，节省内存</li>
            <li>实时性能监控</li>
        </ul>
        """
        
        QMessageBox.about(self, "关于", about_text)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName(f"{AppSettings.APP_NAME} (优化版)")
    app.setApplicationVersion(AppSettings.APP_VERSION)
    app.setOrganizationName(AppSettings.ORGANIZATION)
    
    # 创建主窗口
    viewer = OptimizedAuroraPDF()
    viewer.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()