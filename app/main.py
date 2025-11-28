"""极灵PDF主程序入口 - 现代化PDF阅读器（集成性能优化）"""

import sys
import os

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
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

from app.config.settings import AppSettings
from app.ui.styles import AppStyles
from app.core.pdf_processor import PDFProcessor

# 导入优化组件
from app.ui.virtual_scroll import VirtualScrollArea
from app.ui.smart_thumbnail import SmartThumbnailManager

class AuroraPDF(QMainWindow):
    """极灵PDF主窗口 - 现代化PDF阅读器界面（集成性能优化）"""
    
    def __init__(self):
        super().__init__()
        self.pdf_processor = PDFProcessor()
        
        # 性能优化相关
        self.use_optimizations = True  # 强制启用优化
        self.use_virtual_scroll = True  # 强制启用虚拟滚动
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._monitor_performance)
        self.performance_timer.start(5000)  # 每5秒监控一次
        self.progress_dialog = None
        
        # 连接PDF处理器信号（确保无论是否使用优化版本都连接信号）
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
        
        self.init_ui()
        
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
        
        # 创建智能缩略图管理器
        self.thumbnail_list = SmartThumbnailManager(self)
        self.thumbnail_list.set_pdf_processor(self.pdf_processor)
        
        # 连接信号
        self.thumbnail_list.thumbnail_clicked.connect(self.on_thumbnail_clicked)
        self.thumbnail_list.thumbnail_right_clicked.connect(self.on_thumbnail_right_clicked)
        
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
        
        file_menu.addSeparator()
        
        print_action = QAction("🖨️ 打印", self)
        print_action.setShortcut("Ctrl+P")
        print_action.triggered.connect(self.print_file)
        file_menu.addAction(print_action)
        
        file_menu.addSeparator()
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("✏️ 编辑")
        
        # 视图菜单
        view_menu = menubar.addMenu("👁️ 视图")
        
        # 虚拟滚动切换
        self.virtual_scroll_action = QAction("⚡ 虚拟滚动", self)
        self.virtual_scroll_action.setCheckable(True)
        self.virtual_scroll_action.setChecked(self.use_virtual_scroll)
        self.virtual_scroll_action.triggered.connect(self.toggle_virtual_scroll)
        view_menu.addAction(self.virtual_scroll_action)
        
        view_menu.addSeparator()
        
        # 浏览模式
        self.continuous_action = QAction("📜 连续浏览", self)
        self.continuous_action.setCheckable(True)
        self.continuous_action.setChecked(self.continuous_mode)
        self.continuous_action.setShortcut("Ctrl+M")
        self.continuous_action.triggered.connect(self.toggle_continuous_mode)
        view_menu.addAction(self.continuous_action)
        
        self.single_page_action = QAction("📄 单页浏览", self)
        self.single_page_action.setCheckable(True)
        # 强制设置为False，因为我们已经禁用了单页模式
        self.single_page_action.setChecked(False)
        self.single_page_action.setShortcut("Ctrl+N")
        self.single_page_action.triggered.connect(self.toggle_single_page_mode)
        view_menu.addAction(self.single_page_action)
        
        # 性能监控
        view_menu.addSeparator()
        self.performance_action = QAction("📊 性能监控", self)
        self.performance_action.setCheckable(True)
        self.performance_action.triggered.connect(self.toggle_performance_monitor)
        view_menu.addAction(self.performance_action)
        
        view_menu.addSeparator()
        
        # 工具菜单
        tools_menu = menubar.addMenu("🛠️ 工具")
        
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
        
        print_btn = QAction("🖨️ 打印", self)
        print_btn.setToolTip("打印PDF文件 (Ctrl+P)")
        print_btn.setShortcut("Ctrl+P")
        print_btn.triggered.connect(self.print_file)
        toolbar.addAction(print_btn)
        
        toolbar.addSeparator()
        
        # === 缩放控制组 ===
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
        
        fit_page_btn = QAction("📄 适合页面", self)
        fit_page_btn.setToolTip("适合页面显示")
        fit_page_btn.setShortcut("Ctrl+H")
        fit_page_btn.triggered.connect(self.fit_page)
        toolbar.addAction(fit_page_btn)
        
        toolbar.addSeparator()
        
        # === 页面导航组 ===
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
        
        # 页码输入框和显示
        toolbar.addWidget(QLabel("页码:"))
        
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(1)
        self.page_spinbox.setFixedWidth(80)  # 增加宽度以显示更多数字
        self.page_spinbox.valueChanged.connect(self.go_to_page)
        self.page_spinbox.setToolTip("输入页码直接跳转")
        toolbar.addWidget(self.page_spinbox)
        
        self.total_pages_label = QLabel("/ 1")
        self.total_pages_label.setFixedWidth(50)  # 增加宽度以显示更多数字
        toolbar.addWidget(self.total_pages_label)
        
        toolbar.addSeparator()
        
        # === 搜索功能 ===
        toolbar.addWidget(QLabel("搜索:"))
        
        self.search_lineedit = QLineEdit()
        self.search_lineedit.setPlaceholderText("输入关键词查找...")
        self.search_lineedit.setFixedWidth(180)
        self.search_lineedit.setToolTip("在PDF中搜索文本 (Ctrl+F)")
        self.search_lineedit.returnPressed.connect(self.search_text)
        toolbar.addWidget(self.search_lineedit)
        
        search_btn = QAction("🔍 查找", self)
        search_btn.setToolTip("搜索文本 (Ctrl+F)")
        search_btn.setShortcut("Ctrl+F")
        search_btn.triggered.connect(self.search_text)
        toolbar.addAction(search_btn)
        
        # 搜索导航按钮
        search_prev_btn = QAction("⬆️ 上一个", self)
        search_prev_btn.setToolTip("上一个匹配项 (Shift+F3)")
        search_prev_btn.setShortcut("Shift+F3")
        search_prev_btn.triggered.connect(self.search_previous)
        toolbar.addAction(search_prev_btn)
        
        search_next_btn = QAction("⬇️ 下一个", self)
        search_next_btn.setToolTip("下一个匹配项 (F3)")
        search_next_btn.setShortcut("F3")
        search_next_btn.triggered.connect(self.search_next)
        toolbar.addAction(search_next_btn)
        
        # 搜索选项按钮
        search_options_btn = QAction("⚙️ 选项", self)
        search_options_btn.setToolTip("搜索选项")
        search_options_btn.triggered.connect(self.show_search_options)
        toolbar.addAction(search_options_btn)
        
        # 缩略图切换按钮
        self.thumbnail_btn = QAction("📋 缩略图", self)  # 使用字体图标并添加文字
        self.thumbnail_btn.setToolTip("显示/隐藏缩略图")
        self.thumbnail_btn.setShortcut("Ctrl+T")
        self.thumbnail_btn.triggered.connect(self.toggle_thumbnails)
        toolbar.addAction(self.thumbnail_btn)
        
        # 缓存清理按钮
        self.cache_btn = QAction("🗑️ 清理缓存", self)
        self.cache_btn.setToolTip("清理所有缓存")
        self.cache_btn.triggered.connect(self.clear_cache)
        toolbar.addAction(self.cache_btn)
        
    def create_statusbar(self):
        """创建状态栏"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        # 状态栏信息
        self.status_label = QLabel("🟢 就绪")
        self.status_label.setFont(QFont("微软雅黑", 9))
        statusbar.addWidget(self.status_label)
        
        # 性能信息
        self.performance_label = QLabel("")
        self.performance_label.setFont(QFont("微软雅黑", 8))
        statusbar.addPermanentWidget(self.performance_label)
        
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
            
    def _on_pdf_loaded(self, success, message):
        """PDF加载完成回调"""
        # 隐藏进度对话框
        self.hide_progress_dialog()
        
        if success:
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
        else:
            QMessageBox.critical(self, "错误", message)
    
    def _delayed_update_preview(self):
        """延迟更新预览区域，确保所有组件初始化完成"""
        logger.debug("延迟更新预览区域开始...")
        self.update_preview()
        logger.debug("延迟更新预览区域完成")
    
    def update_preview(self):
        """更新预览区域 - 显示PDF页面内容"""
        logger.debug("开始更新预览...")
        if self.pdf_processor.fitz_document:
            logger.debug("PDF文档已加载")
            # 确保在异步加载完成后正确显示内容
            # 直接使用虚拟滚动模式 - 设置数据并更新页面
            logger.debug("使用虚拟滚动模式")
            try:
                # 虚拟滚动模式 - 设置数据并更新页面
                logger.debug("设置虚拟滚动数据...")
                self._setup_virtual_scroll_data()
                logger.debug("调用虚拟滚动区域更新内容...")
                # 使用延迟更新确保设置完成
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, self.virtual_scroll.update_content)
                logger.debug("虚拟滚动区域更新调用完成")
            except Exception as e:
                logger.error(f"虚拟滚动模式出错: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("没有PDF文档加载")
            # 没有PDF文件时显示欢迎信息
            self.preview_label.clear()
            self.preview_label.setText("📄 请点击上方'打开'按钮选择PDF文件")
            self.preview_label.setAlignment(Qt.AlignCenter)
            self.preview_label.setFont(QFont("微软雅黑", 14))
        
        logger.debug("预览更新完成")
    
    def save_file(self):
        """保存PDF文件"""
        if not self.pdf_processor.current_file:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return
        
        # 获取上次保存的目录，如果没有则使用上次打开的目录
        last_save_dir = AppSettings.get_last_save_dir()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF文件", last_save_dir, "PDF文件 (*.pdf)")
        
        if file_path:
            success, message = self.pdf_processor.save_pdf(file_path)
            
            if success:
                # 记忆保存文件的目录
                AppSettings.set_last_save_dir(file_path)
                QMessageBox.information(self, "保存成功", message)
            else:
                QMessageBox.critical(self, "保存失败", message)
    
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
    
    def go_to_page(self, page_number):
        """跳转到指定页面"""
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
    
    def toggle_continuous_mode(self):
        """切换到连续浏览模式"""
        # 强制启用连续模式，因为我们只使用虚拟滚动
        if not self.continuous_mode:
            self.continuous_mode = True
            self.pdf_processor.set_continuous_mode(True)
            self.show_message("⚡ 已切换到连续浏览模式 - 虚拟滚动技术")
            
            # 更新菜单项状态
            self.continuous_action.setChecked(True)
            self.single_page_action.setChecked(False)
    
    def toggle_single_page_mode(self):
        """切换到单页浏览模式"""
        # 不再支持单页模式，因为我们只使用虚拟滚动
        self.show_message("❌ 单页模式已禁用，仅支持连续浏览模式")
        
        # 保持连续模式启用
        self.continuous_mode = True
        self.pdf_processor.set_continuous_mode(True)
        self.continuous_action.setChecked(True)
        self.single_page_action.setChecked(False)
    
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
            
        QMessageBox.information(self, "打印", "🖨️ 打印功能开发中...")
    
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
        self.status_label.setText(f"📢 {message}")
    
    def show_about(self):
        """显示关于信息"""
        about_text = f"""
        <h2>{AppSettings.APP_NAME}</h2>
        <p>版本: {AppSettings.APP_VERSION}</p>
        <p>一个功能强大的PDF文档处理工具</p>
        <p>支持PDF查看、编辑、转换、合并、分割等功能</p>
        <p>🎯 设计理念: 简单易用，功能强大</p>
        """
        
        QMessageBox.about(self, "关于", about_text)
        
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
        if self.show_thumbnails:
            self.thumbnail_dock.show()
            self.thumbnail_btn.setText("📋 缩略图")
            # 加载缩略图
            self.load_thumbnails()
        else:
            self.thumbnail_dock.hide()
            self.thumbnail_btn.setText("📋 缩略图")
    
    def load_thumbnails(self):
        """加载PDF页面缩略图"""
        if not self.pdf_processor.fitz_document:
            return
        
        # 使用缩略图管理器加载缩略图
        self.thumbnail_list.load_thumbnails()
    
    def on_thumbnail_clicked(self, page_num):
        """处理缩略图点击事件"""
        # 跳转到指定页面
        self.go_to_page(page_num)  # 修复：缩略图已经传递了正确的1基索引页码
        
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
    
    def _on_loading_progress(self, value, message):
        """加载进度更新"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
            
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
                    self.virtual_scroll.page_visible.connect(self._on_virtual_page_visible)
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