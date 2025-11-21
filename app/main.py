"""极灵PDF主程序入口 - 现代化PDF阅读器"""

import sys
import os

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QToolBar, QAction, QFileDialog, QSplitter,
                             QLabel, QStatusBar, QMessageBox, QPushButton,
                             QLineEdit, QSpinBox, QComboBox, QMenu, QMenuBar,
                             QScrollArea, QScrollBar)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter

from app.config.settings import AppSettings
from app.ui.styles import AppStyles
from app.core.pdf_processor import PDFProcessor

class AuroraPDF(QMainWindow):
    """极灵PDF主窗口 - 现代化PDF阅读器界面"""
    
    def __init__(self):
        super().__init__()
        self.pdf_processor = PDFProcessor()
        
        # 搜索相关属性
        self.search_results = []
        self.current_search_index = -1
        self.last_search_text = ""
        self.search_case_sensitive = False
        self.search_whole_word = False
        
        # 连续浏览模式属性
        self.scroll_area = None
        self.scroll_content = None
        self.continuous_mode = True
        
        # 页面高度缓存（用于计算当前页）
        self.page_heights = []
        self.page_positions = []
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI界面 - 按照极光PDF布局设计"""
        # 设置窗口属性
        self.setWindowTitle(f"{AppSettings.APP_NAME} v{AppSettings.APP_VERSION}")
        self.setGeometry(100, 100, AppSettings.WINDOW_WIDTH, AppSettings.WINDOW_HEIGHT)
        self.setMinimumSize(AppSettings.WINDOW_MIN_WIDTH, AppSettings.WINDOW_MIN_HEIGHT)
        
        # 设置应用样式
        self.apply_styles()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局（垂直布局，从上到下：工具栏、PDF显示区域）
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建PDF显示区域（中央主要区域）
        self.create_pdf_display_area(main_layout)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建主工具栏
        self.create_main_toolbar()
        
        # 创建状态栏
        self.create_statusbar()
        
        # 显示欢迎信息
        self.show_message("🟢 就绪 - 请点击'打开'按钮选择PDF文件")
        
    def create_pdf_display_area(self, main_layout):
        """创建PDF显示区域 - 支持连续滚动浏览"""
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建滚动内容容器
        self.scroll_content = QWidget()
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setSpacing(0)
        self.scroll_content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建PDF预览标签（初始状态）
        self.preview_label = QLabel("📄 请点击上方'打开'按钮选择PDF文件")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFont(QFont("微软雅黑", 14))
        
        self.scroll_content_layout.addWidget(self.preview_label)
        self.scroll_area.setWidget(self.scroll_content)
        
        # 连接滚动事件
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll_changed)
        
        # 添加到主布局
        main_layout.addWidget(self.scroll_area)
        
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
        
        # 浏览模式
        self.continuous_action = QAction("📜 连续浏览", self)
        self.continuous_action.setCheckable(True)
        self.continuous_action.setChecked(self.continuous_mode)
        self.continuous_action.setShortcut("Ctrl+M")
        self.continuous_action.triggered.connect(self.toggle_continuous_mode)
        view_menu.addAction(self.continuous_action)
        
        self.single_page_action = QAction("📄 单页浏览", self)
        self.single_page_action.setCheckable(True)
        self.single_page_action.setChecked(not self.continuous_mode)
        self.single_page_action.setShortcut("Ctrl+N")
        self.single_page_action.triggered.connect(self.toggle_single_page_mode)
        view_menu.addAction(self.single_page_action)
        
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
        self.page_spinbox.setFixedWidth(60)
        self.page_spinbox.valueChanged.connect(self.go_to_page)
        self.page_spinbox.setToolTip("输入页码直接跳转")
        toolbar.addWidget(self.page_spinbox)
        
        self.total_pages_label = QLabel("/ 1")
        self.total_pages_label.setFixedWidth(30)
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
        
    def create_statusbar(self):
        """创建状态栏"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        # 状态栏信息
        self.status_label = QLabel("🟢 就绪")
        self.status_label.setFont(QFont("微软雅黑", 9))
        statusbar.addWidget(self.status_label)
        
    def open_file(self):
        """打开PDF文件"""
        # 获取上次打开的目录
        last_dir = AppSettings.get_last_open_dir()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PDF文件", last_dir, "PDF文件 (*.pdf)")
        
        if file_path:
            success, message = self.pdf_processor.open_pdf(file_path)
            
            if success:
                # 记忆打开文件的目录
                AppSettings.set_last_open_dir(file_path)
                
                # 更新界面
                self.setWindowTitle(f"{AppSettings.APP_NAME} - {os.path.basename(file_path)}")
                
                # 显示PDF信息
                pdf_info = self.pdf_processor.get_pdf_info()
                if pdf_info:
                    info_text = f"📄 {pdf_info['filename']} | 📖 共{pdf_info['page_count']}页 | 💾 {pdf_info['file_size']}"
                    if pdf_info['is_encrypted']:
                        info_text += " | 🔒 已加密"
                    
                    self.show_message(info_text)
                    
                    # 更新预览区域
                    self.update_preview()
            else:
                QMessageBox.critical(self, "错误", message)
                
    def update_preview(self):
        """更新预览区域 - 显示PDF页面内容"""
        if self.pdf_processor.fitz_document:
            # 清空现有内容
            for i in reversed(range(self.scroll_content_layout.count())):
                child = self.scroll_content_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            if self.continuous_mode:
                # 连续浏览模式：渲染并显示所有页面
                total_pages = self.pdf_processor.get_total_pages()
                self.page_heights = []
                self.page_positions = []
                current_position = 0
                
                for page_num in range(total_pages):
                    # 设置当前页面并渲染
                    self.pdf_processor.go_to_page(page_num + 1)
                    pixmap = self.pdf_processor.render_page(550, 750)  # 稍小的尺寸以适应连续显示
                    if pixmap:
                        # 记录页面位置
                        self.page_positions.append(current_position)
                        
                        page_label = QLabel()
                        page_label.setPixmap(pixmap)
                        page_label.setAlignment(Qt.AlignCenter)
                        page_height = pixmap.height() + 30  # 包含边距和间距
                        
                        # 记录页面高度
                        self.page_heights.append(page_height)
                        
                        # 添加页面样式
                        page_label.setStyleSheet("""
                            QLabel {
                                background-color: #FFFFFF;
                                border: 1px solid #E0E0E0;
                                border-radius: 4px;
                                margin: 5px;
                                padding: 10px;
                            }
                        """)
                        
                        # 添加页面间距
                        if page_num > 0:
                            spacer = QLabel()
                            spacer.setFixedHeight(10)
                            self.scroll_content_layout.addWidget(spacer)
                            current_position += 10
                        
                        self.scroll_content_layout.addWidget(page_label)
                        current_position += page_height
            else:
                # 单页模式：只显示当前页面
                pixmap = self.pdf_processor.render_page(600, 800)
                if pixmap:
                    page_label = QLabel()
                    page_label.setPixmap(pixmap)
                    page_label.setAlignment(Qt.AlignCenter)
                    page_label.setStyleSheet("""
                        QLabel {
                            background-color: #FFFFFF;
                            border: 2px solid #E0E0E0;
                            border-radius: 8px;
                            padding: 20px;
                        }
                    """)
                    self.scroll_content_layout.addWidget(page_label)
                
            # 更新页面信息
            current_page = self.pdf_processor.get_current_page()
            total_pages = self.pdf_processor.get_total_pages()
            zoom_level = int(self.pdf_processor.get_zoom() * 100)
            
            # 更新页码控件
            self.page_spinbox.setMaximum(total_pages)
            self.page_spinbox.setValue(current_page)
            self.total_pages_label.setText(str(total_pages))
            
            # 更新状态栏
            mode_text = "📜 连续浏览模式" if self.continuous_mode else "📄 单页浏览模式"
            self.show_message(f"{mode_text} | 第 {current_page} 页 / 共 {total_pages} 页 | 缩放: {zoom_level}%")
        else:
            # 没有PDF文件时显示欢迎信息
            self.preview_label.clear()
            self.preview_label.setText("📄 请点击上方'打开'按钮选择PDF文件")
            self.preview_label.setAlignment(Qt.AlignCenter)
            self.preview_label.setFont(QFont("微软雅黑", 14))
        
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
        if self.continuous_mode:
            # 连续模式：向上滚动
            current_value = self.scroll_area.verticalScrollBar().value()
            scroll_amount = 800  # 滚动量
            self.scroll_area.verticalScrollBar().setValue(max(0, current_value - scroll_amount))
            self.show_message("📜 向上滚动")
        else:
            # 单页模式：传统翻页
            success, message = self.pdf_processor.previous_page()
            if success:
                self.update_preview()
            self.show_message(message)
    
    def next_page(self):
        """下一页"""
        if self.continuous_mode:
            # 连续模式：向下滚动
            current_value = self.scroll_area.verticalScrollBar().value()
            scroll_amount = 800  # 滚动量
            max_value = self.scroll_area.verticalScrollBar().maximum()
            self.scroll_area.verticalScrollBar().setValue(min(max_value, current_value + scroll_amount))
            self.show_message("📜 向下滚动")
        else:
            # 单页模式：传统翻页
            success, message = self.pdf_processor.next_page()
            if success:
                self.update_preview()
            self.show_message(message)
    
    def go_to_page(self, page_number):
        """跳转到指定页面"""
        if self.continuous_mode and self.page_positions:
            # 连续模式：直接滚动到页面位置
            if 1 <= page_number <= len(self.page_positions):
                scroll_position = self.page_positions[page_number - 1]
                self.scroll_area.verticalScrollBar().setValue(scroll_position)
                self.show_message(f"📜 跳转到第 {page_number} 页")
        else:
            # 单页模式：传统跳转
            success, message = self.pdf_processor.go_to_page(page_number)
            if success:
                self.update_preview()
            self.show_message(message)
    
    def on_scroll_changed(self, value):
        """滚动事件处理 - 实时更新页码"""
        if self.continuous_mode and self.page_positions:
            # 找到当前滚动位置对应的页面
            current_page = 1  # 默认第一页
            
            for i, position in enumerate(self.page_positions):
                if value >= position - 50:  # 给50像素的容差
                    current_page = i + 1
                else:
                    break
            
            # 更新页码显示（避免触发额外的事件）
            if current_page != self.page_spinbox.value():
                # 阻止信号以避免循环触发
                self.page_spinbox.blockSignals(True)
                self.page_spinbox.setValue(current_page)
                self.page_spinbox.blockSignals(False)
                
                # 更新状态栏
                total_pages = self.pdf_processor.get_total_pages()
                zoom_level = int(self.pdf_processor.get_zoom() * 100)
                self.show_message(f"📜 连续浏览模式 | 第 {current_page} 页 / 共 {total_pages} 页 | 缩放: {zoom_level}%")
    
    def scroll_to_current_page(self):
        """在连续模式中滚动到当前页面"""
        if self.continuous_mode and self.scroll_area and self.page_positions:
            current_page = self.pdf_processor.get_current_page()
            if 0 <= current_page - 1 < len(self.page_positions):
                scroll_position = self.page_positions[current_page - 1]
                self.scroll_area.verticalScrollBar().setValue(scroll_position)
    
    def toggle_continuous_mode(self):
        """切换到连续浏览模式"""
        if not self.continuous_mode:
            self.continuous_mode = True
            self.pdf_processor.set_continuous_mode(True, 3)
            self.update_preview()
            self.show_message("📜 已切换到连续浏览模式 - 可像网页一样滚动")
            
            # 更新菜单项状态
            self.continuous_action.setChecked(True)
            self.single_page_action.setChecked(False)
    
    def toggle_single_page_mode(self):
        """切换到单页浏览模式"""
        if self.continuous_mode:
            self.continuous_mode = False
            self.pdf_processor.set_continuous_mode(False)
            self.update_preview()
            self.show_message("📄 已切换到单页浏览模式 - 传统的翻页方式")
            
            # 更新菜单项状态
            self.continuous_action.setChecked(False)
            self.single_page_action.setChecked(True)
    
    # ===== 缩放控制功能 =====
    
    def zoom_in(self):
        """放大"""
        current_zoom = self.pdf_processor.get_zoom()
        new_zoom = min(current_zoom * 1.2, 4.0)  # 最大放大到400%
        success, message = self.pdf_processor.set_zoom(new_zoom)
        if success:
            self.update_preview()
        self.show_message(message)
    
    def zoom_out(self):
        """缩小"""
        current_zoom = self.pdf_processor.get_zoom()
        new_zoom = max(current_zoom / 1.2, 0.25)  # 最小缩小到25%
        success, message = self.pdf_processor.set_zoom(new_zoom)
        if success:
            self.update_preview()
        self.show_message(message)
    
    def fit_width(self):
        """适合宽度"""
        # 这里可以添加适合宽度的逻辑
        success, message = self.pdf_processor.set_zoom(1.0)  # 临时设置为100%
        if success:
            self.update_preview()
        self.show_message("适合宽度显示")
    
    def fit_page(self):
        """适合页面"""
        # 这里可以添加适合页面的逻辑
        success, message = self.pdf_processor.set_zoom(1.0)  # 临时设置为100%
        if success:
            self.update_preview()
        self.show_message("适合页面显示")
                
    def print_file(self):
        """打印PDF文件"""
        if not self.pdf_processor.current_file:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return
            
        QMessageBox.information(self, "打印", "🖨️ 打印功能开发中...")
        
    def toggle_continuous_mode(self):
        """切换到连续浏览模式"""
        if not self.continuous_mode:
            self.continuous_mode = True
            self.pdf_processor.set_continuous_mode(True, 3)
            self.update_preview()
            self.show_message("📜 已切换到连续浏览模式 - 可像网页一样滚动")
            
            # 更新菜单项状态
            self.continuous_action.setChecked(True)
            self.single_page_action.setChecked(False)
    
    def toggle_single_page_mode(self):
        """切换到单页浏览模式"""
        if self.continuous_mode:
            self.continuous_mode = False
            self.pdf_processor.set_continuous_mode(False)
            self.update_preview()
            self.show_message("📄 已切换到单页浏览模式 - 传统的翻页方式")
            
            # 更新菜单项状态
            self.continuous_action.setChecked(False)
            self.single_page_action.setChecked(True)
    
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
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QGroupBox
        
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
                

    
    def scroll_to_current_page(self):
        """滚动到当前页面位置"""
        if not self.continuous_mode or not self.pdf_processor.fitz_document:
            return
            
        current_page = self.pdf_processor.get_current_page()
        pages_per_view = self.pdf_processor.pages_per_view
        
        # 计算当前页在连续视图中的垂直位置
        page_height = 600  # 估算页面高度
        position = (current_page // pages_per_view) * (page_height * pages_per_view + 20 * pages_per_view)
        
        # 使用QTimer延迟滚动，确保界面更新后再滚动
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(position))
        
    def show_message(self, message):
        """显示状态消息"""
        self.status_label.setText(f"📢 {message}")

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