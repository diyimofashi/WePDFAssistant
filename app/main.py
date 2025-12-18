"""极灵PDF主程序入口 - 优化版本"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.utils.logger import get_logger
logger = get_logger('main')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QHBoxLayout, 
                             QWidget, QLabel, QStatusBar, QMessageBox,
                             QDockWidget, QProgressDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

from app.config.settings import AppSettings
from app.ui.styles import AppStyles
from app.core.pdf_processor import PDFProcessor
from app.ui.virtual_scroll import VirtualScrollArea
from app.core.thumbnail_manager import ThumbnailManager

# 导入管理器模块
from app.ui.menu_manager import MenuManager
from app.ui.toolbar_manager import ToolbarManager
from app.managers.file_manager import FileManager
from app.managers.view_controller import ViewController
from app.managers.search_manager import SearchManager
from app.managers.split_manager import SplitManager


class AuroraPDF(QMainWindow):
    """极灵PDF主窗口 - 优化版本"""
    
    def __init__(self):
        super().__init__()
        self.pdf_processor = PDFProcessor()
        
        # 性能优化相关属性
        self.use_optimizations = True
        self.show_thumbnails = False
        self.render_width = 800
        self.render_height = 1000
        self.use_virtual_scroll = True
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._monitor_performance)
        self.performance_timer.start(5000)
        
        # 页面高度缓存
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
        
        # 进度对话框
        self.progress_dialog = None
        
        # 更新操作状态定时器
        self.update_actions_timer = QTimer(self)
        self.update_actions_timer.timeout.connect(self.update_save_actions_state)
        self.update_actions_timer.start(500)
        
        # 初始化管理器
        self._init_managers()
        
        # 连接PDF处理器信号
        self._connect_signals()
        
        # 初始化UI
        self.init_ui()
        self.apply_styles()
        
    def _init_managers(self):
        """初始化管理器"""
        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolbarManager(self)
        self.file_manager = FileManager(self)
        self.view_controller = ViewController(self)
        self.search_manager = SearchManager(self)
        self.split_manager = SplitManager(self)
        
    def _connect_signals(self):
        """连接PDF处理器信号"""
        self.pdf_processor.loading_progress.connect(self._on_loading_progress)
        self.pdf_processor.loading_finished.connect(self._on_pdf_loading_finished)
        self.pdf_processor.page_rendered.connect(self._on_page_rendered)
        self.pdf_processor.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.pdf_processor.operation_history_changed.connect(self._on_operation_history_changed)
        
        # 如果PDF处理器有页面变化信号，连接它
        if hasattr(self.pdf_processor, 'page_changed'):
            self.pdf_processor.page_changed.connect(self._on_page_changed)
        # 如果PDF处理器有缩放变化信号，连接它
        if hasattr(self.pdf_processor, 'zoom_changed'):
            self.pdf_processor.zoom_changed.connect(self._on_zoom_changed)
        
    def init_ui(self):
        """初始化UI界面"""
        try:
            logger.debug("开始初始化UI...")
            self.setWindowTitle(f"{AppSettings.APP_NAME} v{AppSettings.APP_VERSION}")
            self.setGeometry(100, 100, AppSettings.WINDOW_WIDTH, AppSettings.WINDOW_HEIGHT)
            self.setMinimumSize(AppSettings.WINDOW_MIN_WIDTH, AppSettings.WINDOW_MIN_HEIGHT)
            self.showMaximized()
            
            # 创建中央部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QHBoxLayout(central_widget)
            main_layout.setSpacing(0)
            main_layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建缩略图区域
            self.create_thumbnail_area(main_layout)
            
            # 创建PDF显示区域
            self.create_pdf_display_area(main_layout)
            
            # 创建菜单栏和工具栏
            self.menu_manager.create_menubar()
            self.toolbar_manager.create_main_toolbar()
            
            # 创建状态栏
            self.create_statusbar()
            
            self.show_message("🚀 优化版就绪 - 支持异步加载和虚拟滚动")
            logger.debug("UI初始化完成")
        except Exception as e:
            logger.error(f"UI初始化过程中出现错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = self.statusBar()
        self.status_label = QLabel("就绪")
        self.statusbar.addWidget(self.status_label)
        
        # 添加页码信息
        self.page_label = QLabel("")
        self.statusbar.addPermanentWidget(self.page_label)
        
        # 添加总页数标签（兼容旧代码）
        self.total_pages_label = QLabel("/ 0")
        self.statusbar.addPermanentWidget(self.total_pages_label)
        
        # 添加缩放信息
        self.zoom_label = QLabel("100%")
        self.statusbar.addPermanentWidget(self.zoom_label)
    
    def create_thumbnail_area(self, main_layout):
        """创建缩略图区域"""
        self.thumbnail_dock = QDockWidget("智能缩略图", self)
        self.thumbnail_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.thumbnail_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        self.thumbnail_dock.setStyleSheet("""
            QDockWidget { border: none; }
            QDockWidget::title { background-color: #F0F0F0; border: none; padding: 4px; text-align: left; }
            QDockWidget > QWidget { alignment: center; }
        """)
        
        self.thumbnail_dock.setMinimumWidth(250)
        self.thumbnail_dock.resize(280, self.thumbnail_dock.height())
        
        self.thumbnail_list = ThumbnailManager(self)
        self.thumbnail_list.set_pdf_processor(self.pdf_processor)
        
        self.thumbnail_list.thumbnail_clicked.connect(self.view_controller.on_thumbnail_clicked)
        self.thumbnail_list.thumbnail_right_clicked.connect(self.view_controller.on_thumbnail_right_clicked)
        
        if hasattr(self.thumbnail_list, 'page_editor') and self.thumbnail_list.page_editor:
            self.thumbnail_list.page_editor.state_changed.connect(self.update_save_actions_state)
        
        self.thumbnail_dock.setWidget(self.thumbnail_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.thumbnail_dock)
        self.thumbnail_dock.hide()
    
    def create_pdf_display_area(self, main_layout):
        """创建PDF显示区域"""
        self.virtual_scroll = VirtualScrollArea(self)
        self.virtual_scroll.page_visible.connect(self._on_page_visible)
        self.virtual_scroll.page_hidden.connect(self._on_page_hidden)
        self.virtual_scroll.page_changed.connect(self.on_virtual_scroll_page_changed)
        main_layout.addWidget(self.virtual_scroll)
        
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet(AppStyles.get_stylesheet(AppSettings.THEME))
        app = QApplication.instance()
        if app:
            app.setFont(QFont("微软雅黑", 10))
        
    def create_statusbar(self):
        """创建状态栏"""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.status_label = QLabel("📢 就绪")
        self.status_label.setIndent(5)
        self.statusBar.addWidget(self.status_label)
        
        self.performance_label = QLabel()
        self.performance_label.setIndent(10)
        self.statusBar.addPermanentWidget(self.performance_label)
    
    def update_save_actions_state(self):
        """更新保存操作的状态"""
        has_changes = self.pdf_processor.has_unsaved_changes()
        
        self.save_changes_action.setEnabled(has_changes)
        self.discard_changes_action.setEnabled(has_changes)
        
        can_undo = self.pdf_processor.can_undo()
        can_redo = self.pdf_processor.can_redo()
        
        logger.debug(f"操作历史状态 - 可撤销: {can_undo}, 可重做: {can_redo}, 有更改: {has_changes}")
        
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        
        if hasattr(self, 'undo_btn'):
            self.undo_btn.setEnabled(can_undo)
        if hasattr(self, 'redo_btn'):
            self.redo_btn.setEnabled(can_redo)
            
        operation_summary = self.pdf_processor.get_operation_summary()
        if has_changes:
            self.show_message(f"● 文档已修改 | {operation_summary}")
        else:
            self.show_message(operation_summary)
            
        if hasattr(self, 'repaint'):
            self.repaint()
    
    def show_message(self, message):
        """显示状态消息"""
        has_changes = (hasattr(self.pdf_processor, 'page_editor') and 
                      self.pdf_processor.page_editor and 
                      self.pdf_processor.page_editor.has_unsaved_changes())
        modified_indicator = " ● 文档已修改 | " if has_changes else ""
        self.status_label.setText(f"📢 {modified_indicator}{message}")
    
    def update_page_label(self):
        """更新页码显示"""
        if hasattr(self, 'page_label') and hasattr(self, 'pdf_processor'):
            if self.pdf_processor.current_page >= 0 and self.pdf_processor.total_pages > 0:
                self.page_label.setText(f"第 {self.pdf_processor.current_page + 1} / {self.pdf_processor.total_pages} 页")
            else:
                self.page_label.setText("")
    
    def update_zoom_label(self):
        """更新缩放显示"""
        if hasattr(self, 'zoom_label') and hasattr(self, 'pdf_processor'):
            self.zoom_label.setText(f"{self.pdf_processor.zoom_level:.0f}%")
    
    def _on_page_changed(self):
        """页面变化时的处理"""
        self.update_page_label()
        self.update_save_actions_state()
    
    def _on_zoom_changed(self):
        """缩放变化时的处理"""
        self.update_zoom_label()
    
    def _on_loading_progress(self, progress):
        """处理加载进度"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(progress)
    
    def _on_pdf_loading_finished(self):
        """PDF加载完成处理"""
        self.hide_progress_dialog()
        self.update_page_label()
        self.update_zoom_label()
        
        if hasattr(self, 'total_pages_label') and self.pdf_processor:
            total_pages = self.pdf_processor.get_total_pages()
            self.total_pages_label.setText(f"/ {total_pages}")
        
        if self.pdf_processor.fitz_document:
            current_file = self.pdf_processor.get_current_filename()
            file_name = os.path.basename(current_file) if current_file else "未知文件"
            self.show_message(f"✅ 成功加载: {file_name}")
        else:
            self.show_message("❌ 加载失败")
    
    def _on_page_rendered(self, page_num):
        """页面渲染完成处理"""
        if page_num == self.pdf_processor.current_page:
            self.update_page_label()
    
    def _on_thumbnail_ready(self, page_num, thumbnail):
        """缩略图准备完成处理"""
        if hasattr(self, 'thumbnail_list') and self.thumbnail_list:
            self.thumbnail_list.update_thumbnail(page_num, thumbnail)
    
    def _on_operation_history_changed(self):
        """操作历史变化处理"""
        self.update_save_actions_state()
    
    def split_pdf(self):
        """PDF拆分功能"""
        if not self.pdf_processor.pdf_document:
            QMessageBox.warning(self, "警告", "请先打开PDF文件")
            return
        
        self.split_manager.show_split_dialog()
    
    def convert_pdf_to_images(self):
        """PDF转图片功能"""
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
                
                total_pages = self.pdf_processor.get_total_pages()
                page_hint = QLabel(f"提示: 总页数 {total_pages} 页，支持格式: 单个页码(1,3,5)，连续范围(1-5)，混合(1,3,5-9)")
                page_hint.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
                page_layout.addWidget(page_hint)
                
                page_group.setLayout(page_layout)
                layout.addWidget(page_group)
                
                # 图片格式设置
                format_group = QGroupBox("图片设置")
                format_layout = QVBoxLayout()
                
                format_row = QHBoxLayout()
                format_row.addWidget(QLabel("图片格式:"))
                self.format_combo = QComboBox()
                formats = self.pdf_processor.get_supported_image_formats()
                self.format_combo.addItems(formats)
                jpeg_index = self.format_combo.findText("JPEG")
                if jpeg_index >= 0:
                    self.format_combo.setCurrentIndex(jpeg_index)
                format_row.addWidget(self.format_combo)
                format_row.addStretch()
                format_layout.addLayout(format_row)
                
                dpi_row = QHBoxLayout()
                dpi_row.addWidget(QLabel("分辨率 (DPI):"))
                self.dpi_combo = QComboBox()
                recommended_dpi = self.pdf_processor.get_recommended_dpi()
                for quality, dpi in recommended_dpi.items():
                    self.dpi_combo.addItem(f"{quality} ({dpi} DPI)", dpi)
                self.dpi_combo.setCurrentIndex(1)
                dpi_row.addWidget(self.dpi_combo)
                dpi_row.addStretch()
                format_layout.addLayout(dpi_row)
                
                format_group.setLayout(format_layout)
                layout.addWidget(format_group)
                
                # 转换信息
                info_group = QGroupBox("转换信息")
                info_layout = QVBoxLayout()
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
                for btn in self.findChildren(QPushButton):
                    if btn.text() in ["开始转换", "选择目录", "取消"]:
                        btn.setEnabled(enabled)
                
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
                
                if self.all_pages_radio.isChecked():
                    page_range = "all"
                else:
                    page_range = self.page_range_edit.text().strip()
                    if not page_range:
                        QMessageBox.warning(self, "警告", "请输入要转换的页面范围")
                        return
                
                image_format = self.format_combo.currentText()
                dpi = self.dpi_combo.currentData()
                
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)
                self._set_ui_enabled(False)
                
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
                self.progress_bar.setVisible(False)
                self._set_ui_enabled(True)
                
                if success:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("转换成功")
                    msg_box.setText(message)
                    msg_box.setIcon(QMessageBox.Information)
                    
                    open_dir_btn = msg_box.addButton("📂 打开目录", QMessageBox.ActionRole)
                    msg_box.addButton("确定", QMessageBox.AcceptRole)
                    
                    msg_box.exec_()
                    
                    if msg_box.clickedButton() == open_dir_btn:
                        import subprocess
                        import platform
                        
                        try:
                            system = platform.system()
                            if system == "Windows":
                                if os.path.exists(self.output_dir):
                                    os.startfile(self.output_dir)
                                else:
                                    subprocess.Popen(['explorer', self.output_dir], shell=True)
                            elif system == "Darwin":
                                subprocess.Popen(['open', self.output_dir])
                            else:
                                subprocess.Popen(['xdg-open', self.output_dir])
                        except Exception as e:
                            QMessageBox.warning(self, "警告", f"无法打开目录: {str(e)}")
                    
                    self.accept()
                else:
                    QMessageBox.critical(self, "转换失败", message)
        
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
    
    def undo_operation(self):
        """撤销操作"""
        try:
            success, message = self.pdf_processor.undo_operation()
            if success:
                self.show_message(f"✅ {message}")
                self.update_save_actions_state()
                self.view_controller.load_thumbnails()
                self.update_preview()
                if hasattr(self, 'repaint'):
                    self.repaint()
            else:
                if "没有可撤销的操作" in message:
                    self.show_message(f"ℹ️ {message}")
                else:
                    QMessageBox.warning(self, "撤销失败", message)
        except Exception as e:
            logger.error(f"撤销操作异常: {e}")
            QMessageBox.critical(self, "撤销失败", f"撤销操作发生异常: {str(e)}")

    def redo_operation(self):
        """重做操作"""
        try:
            success, message = self.pdf_processor.redo_operation()
            if success:
                self.show_message(f"✅ {message}")
                self.update_save_actions_state()
                self.view_controller.load_thumbnails()
                self.update_preview()
                if hasattr(self, 'repaint'):
                    self.repaint()
            else:
                if "没有可重做的操作" in message:
                    self.show_message(f"ℹ️ {message}")
                else:
                    QMessageBox.warning(self, "重做失败", message)
        except Exception as e:
            logger.error(f"重做操作异常: {e}")
            QMessageBox.critical(self, "重做失败", f"重做操作发生异常: {str(e)}")
    
    def clear_cache(self):
        """清理缓存"""
        self.pdf_processor.clear_render_cache()
        
        if hasattr(self.thumbnail_list, 'clear_cache'):
            self.thumbnail_list.clear_cache()
            
        if self.use_virtual_scroll and hasattr(self.virtual_scroll, 'clear_cache'):
            self.virtual_scroll.clear_cache()
            
        self.pdf_processor.optimize_memory_usage()
        
        self.show_message("🗑️ 所有缓存已清理")
    
    def _on_operation_history_changed(self):
        """操作历史记录发生变化时更新界面状态"""
        logger.debug("操作历史记录发生变化，更新界面状态")
        self.update_save_actions_state()
        
    def _on_loading_progress(self, value, message):
        """加载进度更新"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
            
    def _on_pdf_loading_finished(self, success, message):
        """PDF加载完成"""
        self.hide_progress_dialog()
        
        if success:
            if hasattr(self, 'thumbnail_list') and self.thumbnail_list:
                logger.debug("更新缩略图管理器中的PDF处理器")
                self.thumbnail_list.set_pdf_processor(self.pdf_processor)
            
            if self.pdf_processor.current_file:
                self.setWindowTitle(f"{AppSettings.APP_NAME} - {os.path.basename(self.pdf_processor.current_file)}")
            
            pdf_info = self.pdf_processor.get_pdf_info()
            if pdf_info:
                info_text = f"📄 {pdf_info['filename']} | 📖 共{pdf_info['page_count']}页 | 💾 {pdf_info['file_size']}"
                if pdf_info['is_encrypted']:
                    info_text += " | 🔒 已加密"
                
                self.show_message(info_text)
                logger.debug(f"PDF信息: {info_text}")
                
                self.pdf_processor.go_to_page(1)
                logger.debug("已跳转到第1页")
                
                total_pages = self.pdf_processor.get_total_pages()
                self.page_spinbox.setMaximum(total_pages)
                self.total_pages_label.setText(f"/ {total_pages}")
                
                self._force_refresh_preview()
                logger.debug("已强制刷新预览区域")
                                
                if self.show_thumbnails:
                    logger.debug("开始强制重新加载缩略图...")
                    self._force_reload_thumbnails()
                    logger.debug("缩略图强制重新加载完成")
                
                self.update_save_actions_state()
        else:
            QMessageBox.critical(self, "错误", message)
    
    def _force_refresh_preview(self):
        """强制刷新预览区域"""
        self.update_preview()
        
        if hasattr(self, 'preview_label') and self.preview_label:
            self.preview_label.update()
            self.preview_label.repaint()
    
    def _force_reload_thumbnails(self):
        """强制重新加载缩略图"""
        if hasattr(self, 'thumbnail_list') and self.thumbnail_list:
            self.thumbnail_list.clear_thumbnails()
        
        self.view_controller.load_thumbnails()
    
    def update_preview(self):
        """更新PDF预览显示"""
        logger.debug("开始更新预览...")
        if not self.pdf_processor.fitz_document:
            logger.debug("没有PDF文档加载")
            return
        
        try:
            logger.debug("PDF文档已加载")
            if self.pdf_processor.current_file:
                display_filename = self.pdf_processor.current_file
                if (hasattr(self.pdf_processor, 'page_editor') and 
                    self.pdf_processor.page_editor and 
                    self.pdf_processor.page_editor.get_original_filename()):
                    display_filename = self.pdf_processor.page_editor.get_original_filename()
                
                filename = os.path.basename(display_filename)
                has_changes = (hasattr(self.pdf_processor, 'page_editor') and 
                              self.pdf_processor.page_editor and 
                              self.pdf_processor.page_editor.has_unsaved_changes())
                modified_indicator = " ●" if has_changes else ""
                self.setWindowTitle(f"{AppSettings.APP_NAME} - {filename}{modified_indicator}")
            
            total_pages = self.pdf_processor.get_total_pages()
            self.page_spinbox.setMaximum(total_pages)
            self.total_pages_label.setText(f"/ {total_pages}")
            
            if self.show_thumbnails:
                self.view_controller.load_thumbnails()
            
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
            total_pages = self.pdf_processor.get_total_pages()
            logger.debug(f"总页数: {total_pages}")
            
            pages_data = []
            for page_num in range(total_pages):
                dimensions = self.pdf_processor.get_page_dimensions(page_num)
                if dimensions:
                    width = int(dimensions['width'] * self.pdf_processor.zoom_factor)
                    height = int(dimensions['height'] * self.pdf_processor.zoom_factor)
                else:
                    width = 800
                    height = 1100
                
                pages_data.append({
                    'page_num': page_num,
                    'width': width,
                    'height': height,
                    'zoom_factor': self.pdf_processor.zoom_factor
                })
            
            logger.debug(f"准备设置{len(pages_data)}页数据到虚拟滚动区域")
            self.virtual_scroll.set_pages_data(pages_data)
            
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
        logger.debug("转发到虚拟滚动区域...")
        self.virtual_scroll.on_page_rendered(page_num, pixmap)
        
    def _on_thumbnail_ready(self, page_num, pixmap):
        """缩略图就绪"""
        pass
        
    def _on_page_visible(self, page_num):
        """页面变为可见"""
        if hasattr(self.pdf_processor, 'render_pages_async'):
            self.pdf_processor.render_pages_async([page_num], self.render_width, self.render_height)
            
    def _on_page_hidden(self, page_num):
        """页面变为隐藏"""
        pass
        
    def _monitor_performance(self):
        """监控性能"""
        try:
            cache_stats = self.pdf_processor.get_cache_stats()
            
            if hasattr(self, 'performance_label'):
                perf_text = f"内存: {cache_stats['current_memory_usage_mb']:.1f}MB | "
                perf_text += f"缓存命中率: {cache_stats['page_cache_hit_rate']:.1%}"
                self.performance_label.setText(perf_text)
            
            if cache_stats['current_memory_usage_mb'] > cache_stats['max_memory_usage_mb'] * 0.8:
                self.pdf_processor.optimize_memory_usage()
                
        except Exception as e:
            logger.error(f"性能监控错误: {e}")
    
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
        if hasattr(self.pdf_processor, 'async_loader') and self.pdf_processor.async_loader:
            self.pdf_processor.async_loader.cancel()
        self.hide_progress_dialog()
        self.show_message("❌ 加载已取消")

    def on_virtual_scroll_page_changed(self, current_page):
        """处理虚拟滚动页面变更事件"""
        logger.debug(f"接收到虚拟滚动页面变更: {current_page}")
        if current_page != self.page_spinbox.value():
            logger.debug(f"页码变更: {self.page_spinbox.value()} -> {current_page}")
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setValue(current_page)
            self.page_spinbox.blockSignals(False)
                            
            if self.pdf_processor:
                total_pages = self.pdf_processor.get_total_pages()
                zoom_level = int(self.pdf_processor.get_zoom() * 100)
                self.show_message(f"⚡ 虚拟滚动模式 | 第 {current_page} 页 / 共 {total_pages} 页 | 缩放: {zoom_level}%")
                self.total_pages_label.setText(f"/ {total_pages}")
                            
                self.view_controller.update_thumbnail_selection(current_page)
    
    def resizeEvent(self, a0):
        """窗口大小变化事件"""
        super().resizeEvent(a0)
        self.resize_timer.start(100)
    
    def changeEvent(self, a0):
        """窗口状态变化事件"""
        super().changeEvent(a0)
        if a0.type() == a0.WindowStateChange:
            self.resize_timer.start(100)
    
    def _update_render_size(self):
        """更新渲染尺寸"""
        available_width = self.virtual_scroll.width() - 40
        available_height = self.virtual_scroll.height() - 40
        
        base_render_width = int(available_width * 0.7)
        base_render_height = int(available_height * 0.7)
        
        old_render_width = self.render_width
        old_render_height = self.render_height
        
        max_render_width = available_width - 100
        
        self.render_width = min(base_render_width, max_render_width)
        self.render_height = base_render_height
        
        if (self.pdf_processor.fitz_document and 
            (self.render_width != old_render_width or self.render_height != old_render_height)):
            self.pdf_processor.clear_render_cache()
            self.update_preview()

    def closeEvent(self, a0):
        """处理窗口关闭事件"""
        event = a0  # 保持向后兼容
        logger.debug("开始处理窗口关闭事件")
        
        if hasattr(self, 'update_actions_timer'):
            self.update_actions_timer.stop()
        
        has_unsaved_changes = False
        page_editor = None
        
        if hasattr(self.pdf_processor, 'page_editor') and self.pdf_processor.page_editor:
            page_editor = self.pdf_processor.page_editor
            has_unsaved_changes = page_editor.has_unsaved_changes()
            logger.debug(f"PDF处理器中的页面编辑器存在: {page_editor is not None}")
            logger.debug(f"是否有未保存的更改: {has_unsaved_changes}")
        elif hasattr(self, 'thumbnail_list') and self.thumbnail_list and hasattr(self.thumbnail_list, 'page_editor') and self.thumbnail_list.page_editor:
            page_editor = self.thumbnail_list.page_editor
            has_unsaved_changes = page_editor.has_unsaved_changes()
            logger.debug(f"缩略图管理器中的页面编辑器存在: {page_editor is not None}")
            logger.debug(f"是否有未保存的更改: {has_unsaved_changes}")
        else:
            logger.debug("页面编辑器不存在")
        
        if has_unsaved_changes:
            logger.debug("检测到未保存的更改，显示确认对话框")
            reply = QMessageBox.question(
                self, 
                "保存更改", 
                "文档已被修改，是否保存更改？", 
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, 
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                logger.debug("用户选择保存更改")
                success, message = page_editor.save_changes()
                if not success:
                    logger.error(f"保存失败: {message}")
                    QMessageBox.critical(self, "保存失败", message)
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                logger.debug("用户取消关闭")
                event.ignore()
                return
        else:
            logger.debug("没有未保存的更改")
        
        logger.debug("正常关闭程序")
        event.accept()

    # 代理方法 - 将调用转发给相应的管理器
    def open_file(self):
        return self.file_manager.open_file()
        
    def save_file(self):
        return self.file_manager.save_file()
        
    def save_as_file(self):
        return self.file_manager.save_as_file()
        
    def save_changes(self):
        return self.file_manager.save_changes()
        
    def discard_changes(self):
        return self.file_manager.discard_changes()
        
    def import_images(self):
        return self.file_manager.import_images()
        
    def zoom_in(self):
        return self.view_controller.zoom_in()
        
    def zoom_out(self):
        return self.view_controller.zoom_out()
        
    def fit_to_width(self):
        return self.view_controller.fit_to_width()
        
    def fit_to_height(self):
        return self.view_controller.fit_to_height()
        
    def set_actual_size(self):
        return self.view_controller.set_actual_size()
        
    def previous_page(self):
        return self.view_controller.previous_page()
        
    def next_page(self):
        return self.view_controller.next_page()
        
    def go_to_page(self, page_number=None):
        return self.view_controller.go_to_page(page_number)
        
    def _on_page_spinbox_changed(self, value):
        return self.view_controller.on_page_spinbox_changed(value)
        
    def toggle_thumbnails(self):
        return self.view_controller.toggle_thumbnails()
        
    def load_thumbnails(self):
        return self.view_controller.load_thumbnails()
        
    def on_thumbnail_clicked(self, page_num):
        return self.view_controller.on_thumbnail_clicked(page_num)
        
    def on_thumbnail_right_clicked(self, page_num):
        return self.view_controller.on_thumbnail_right_clicked(page_num)
        
    def update_thumbnail_selection(self, current_page):
        return self.view_controller.update_thumbnail_selection(current_page)
        
    def show_search_options(self):
        return self.search_manager.show_search_options()
        
    def search_text(self):
        return self.search_manager.search_text()
        
    def search_next(self):
        return self.search_manager.search_next()
        
    def search_previous(self):
        return self.search_manager.search_previous()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    app.setApplicationName(AppSettings.APP_NAME)
    app.setApplicationVersion(AppSettings.APP_VERSION)
    app.setOrganizationName(AppSettings.ORGANIZATION)
    
    viewer = AuroraPDF()
    viewer.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()