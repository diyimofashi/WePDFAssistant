"""PDFAssistant主窗口基础类"""
import sys
import traceback

from PyQt5.QtWidgets import (QApplication, QMainWindow, QHBoxLayout, 
                             QWidget, QLabel, QMessageBox,
                             QDockWidget, QProgressDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from app.config.settings import AppSettings
from app.ui.styles import AppStyles
from app.core.processing.pdf_processor import PDFProcessor
from app.ui.virtual_scroll import VirtualScrollArea
from app.core.processing.thumbnail_manager import ThumbnailManager

from app.ui.menu_manager import MenuManager
from app.ui.toolbar_manager import ToolbarManager
from app.ui.context_menu_manager import ContextMenuManager
from app.ui.file_list_panel import FileListPanel
from app.managers.file_manager import FileManager
from app.managers.view_controller import ViewController
from app.managers.search_manager import SearchManager
from app.managers.split_manager import SplitManager
from app.managers.merge_manager import MergeManager
from app.managers.ocr_plugin_manager import OCRPluginManager
from app.config.ocr_plugin_config import ocr_config_manager
from app.managers.upload_plugin_manager import UploadPluginManager
from app.config.upload_plugin_config import upload_config_manager
from app.managers.download_plugin_manager import download_plugin_manager
from app.config.download_plugin_config import download_config_manager
from app.managers.shortcut_manager import ShortcutManager
from app.utils.logger import get_logger



class MainWindowBase(QMainWindow):
    """PDFAssistant主窗口基础类"""
    
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

        # 文件列表面板相关属性
        self.file_list_panel = None
        self.file_list_dock = None
        
        # 进度对话框
        self.progress_dialog = None
        
        # 条码检测结果缓存
        self.last_barcode_detection_result = None
        
        # 更新操作状态定时器
        self.update_actions_timer = QTimer(self)
        self.update_actions_timer.timeout.connect(self.update_save_actions_state)
        self.update_actions_timer.start(500)
        
        # 标记当前文件是否为临时下载的文件
        self.current_is_temp_file = False
        
        # 初始化管理器
        self._init_managers()
        
        # 连接PDF处理器信号
        self._connect_signals()
        
        # 初始化UI
        self.init_ui()
        self.apply_styles()
        
        # 加载OCR高亮模式设置
        self._load_ocr_highlight_mode_setting()
    
    def _init_managers(self):
        """初始化管理器"""
        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolbarManager(self)
        self.context_menu_manager = ContextMenuManager(self)
        self.file_manager = FileManager(self)
        self.view_controller = ViewController(self)
        self.search_manager = SearchManager(self)
        self.split_manager = SplitManager(self)
        self.merge_manager = MergeManager(self)
        # 初始化OCR管理器
        self.ocr_plugin_manager = OCRPluginManager()
        self.ocr_config_manager = ocr_config_manager
        # 自动加载所有OCR插件
        self.ocr_plugin_manager.load_all_plugins()

        # 初始化上传插件管理器
        self.upload_plugin_manager = UploadPluginManager()
        self.upload_config_manager = upload_config_manager
        # 自动加载所有上传插件
        self.upload_plugin_manager.load_all_plugins()

        # 初始化下载插件管理器
        self.download_plugin_manager = download_plugin_manager
        self.download_config_manager = download_config_manager
        # 自动加载所有下载插件
        self.download_plugin_manager.load_plugins()

        # 初始化快捷键管理器
        self.shortcut_manager = ShortcutManager(self)

        # 初始化文件列表面板
        self.file_list_panel = FileListPanel(self)
        self.file_list_dock = None
        
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
    
    def _load_ocr_highlight_mode_setting(self):
        """加载OCR高亮模式设置"""
        logger = get_logger('main')
        try:
            ocr_highlight_enabled = AppSettings.get_ocr_highlight_mode()
            
            # 设置内部状态
            self._ocr_debug_mode = ocr_highlight_enabled
            
            # 更新菜单项状态
            if hasattr(self, 'ocr_debug_mode_action'):
                self.ocr_debug_mode_action.setChecked(ocr_highlight_enabled)
            
            # 如果当前存在虚拟滚动区域，更新其高亮模式
            if hasattr(self, 'virtual_scroll_area') and self.virtual_scroll_area:
                self.virtual_scroll_area.set_all_pages_debug_mode(ocr_highlight_enabled)
                
            logger.debug(f"OCR高亮模式设置已加载: {ocr_highlight_enabled}")
        except Exception as e:
            logger.error(f"加载OCR高亮模式设置时出错: {e}")
    
    def init_ui(self):
        """初始化UI界面"""
        try:
            logger = get_logger('main')
            
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

            # 创建文件列表面板区域
            self.create_file_list_area(main_layout)
            
            # 创建PDF显示区域
            self.create_pdf_display_area(main_layout)
            
            # 创建菜单栏和工具栏
            self.menu_manager.create_menubar()
            self.toolbar_manager.create_main_toolbar()
            
            # 创建状态栏
            self.create_statusbar()
            
            # 初始化缩略图显示状态
            self.show_thumbnails = False  # 初始时缩略图是隐藏的
            if hasattr(self, 'thumbnail_action'):
                self.thumbnail_action.setChecked(False)  # 确保菜单中的缩略图动作状态与实际状态一致
            
            self.show_message("🚀 优化版就绪 - 支持异步加载和虚拟滚动")
            logger.debug("UI初始化完成")
        except Exception as e:
            logger = get_logger('main')
            logger.error(f"UI初始化过程中出现错误: {e}")
            logger.error(traceback.format_exc())
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = self.statusBar()
        self.status_label = QLabel("就绪")
        self.statusbar.addWidget(self.status_label)
    
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

    def create_file_list_area(self, main_layout):
        """创建文件列表面板区域"""
        from app.utils.plugin_checker import check_download_plugin

        # 只有在有下载插件时才创建
        if not check_download_plugin():
            return

        # 设置面板为不可见（默认隐藏）
        self.file_list_panel.hide()

        # 添加到右侧停靠区域
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_list_panel)
        self.file_list_dock = self.file_list_panel

    def toggle_file_list_panel(self):
        """切换文件列表面板的显示/隐藏"""
        if self.file_list_dock:
            if self.file_list_dock.isVisible():
                self.file_list_dock.hide()
            else:
                self.file_list_dock.show()
                # 面板会自动加载当前插件并刷新文件列表
                self.file_list_panel.load_current_plugin()

    def update_file_list_panel(self):
        """更新文件列表面板"""
        if not self.file_list_panel or not self.file_list_dock.isVisible():
            return

        # 重新加载当前插件（会自动加载文件列表）
        self.file_list_panel.load_current_plugin()
    
    def create_pdf_display_area(self, main_layout):
        """创建PDF显示区域"""
        self.virtual_scroll = VirtualScrollArea(self)
        self.virtual_scroll_area = self.virtual_scroll  # 同时创建别名
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
    
    def update_save_actions_state(self):
        """更新保存操作的状态"""
        has_changes = self.pdf_processor.has_unsaved_changes()
        
        operation_summary = self.pdf_processor.get_operation_summary()
        if has_changes:
            self.show_message(f"● 文档已修改 | {operation_summary}")
        else:
            self.show_message(operation_summary)
            
        if hasattr(self, 'repaint'):
            self.repaint()
    
    def show_message(self, message):
        """显示状态消息"""
        logger = get_logger('main')
        
        # 确保状态标签存在，避免在UI初始化期间出错
        if not hasattr(self, 'status_label'):
            return
        
        has_changes = (hasattr(self.pdf_processor, 'page_editor') and 
                      self.pdf_processor.page_editor and 
                      self.pdf_processor.page_editor.has_unsaved_changes())
        modified_indicator = " ● 文档已修改 | " if has_changes else ""
        self.status_label.setText(f"📢 {modified_indicator}{message}")
    
    def update_page_label(self):
        """更新页码显示 - 已移除页码显示功能"""
        # 此方法保留以兼容调用，但不执行任何操作
        pass
    
    def update_zoom_label(self):
        """更新缩放显示 - 已移除缩放显示功能"""
        # 此方法保留以兼容调用，但不执行任何操作
        pass
    
    def _on_page_changed(self):
        """页面变化时的处理"""
        self.update_save_actions_state()
        # 状态栏总页数显示已移除，仅更新工具栏总页数显示
        
        # 更新工具栏的总页码标签
        if hasattr(self, 'toolbar_total_pages_label') and self.pdf_processor:
            try:
                total_pages = self.pdf_processor.get_total_pages()
                self.toolbar_total_pages_label.setText(f"/ {total_pages}")
            except Exception as e:
                logger = get_logger('main')
                logger.error(f"页面变化时更新工具栏总页数显示失败: {e}")
                self.toolbar_total_pages_label.setText("/ 0")
    
    def _on_zoom_changed(self):
        """缩放变化时的处理"""
        self.update_zoom_label()
        # 更新所有页面的OCR文本层缩放
        if hasattr(self, 'virtual_scroll_area') and self.virtual_scroll_area:
            self.virtual_scroll_area.update_all_pages_scale()
    
    def _on_loading_progress(self, progress):
        """处理加载进度"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(progress)
    
    def _on_page_rendered(self, page_num):
        """页面渲染完成处理"""
        # 页面渲染完成处理，无需更新页码标签（已移除页码显示）
        pass
    
    def _on_thumbnail_ready(self, page_num, thumbnail):
        """缩略图准备完成处理"""
        if hasattr(self, 'thumbnail_list') and self.thumbnail_list:
            self.thumbnail_list.update_thumbnail(page_num, thumbnail)
    
    def _on_operation_history_changed(self):
        """操作历史变化处理"""
        self.update_save_actions_state()
    
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
            logger = get_logger('main')
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
        logger = get_logger('main')

        if current_page != self.page_spinbox.value():
            logger.debug(f"页码变更: {self.page_spinbox.value()} -> {current_page}")
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setValue(current_page)
            self.page_spinbox.blockSignals(False)

            if self.pdf_processor:
                # 更新 pdf_processor.current_page（转换为0-based索引）
                self.pdf_processor.current_page = current_page - 1
                logger.debug(f"已更新 pdf_processor.current_page 为: {self.pdf_processor.current_page}")

                total_pages = self.pdf_processor.get_total_pages()
                zoom_level = int(self.pdf_processor.get_zoom() * 100)
                self.show_message(f"⚡ 虚拟滚动模式 | 共 {total_pages} 页 | 缩放: {zoom_level}%")
                
                # 更新工具栏的总页数标签
                if hasattr(self, 'toolbar_total_pages_label'):
                    self.toolbar_total_pages_label.setText(f"/ {total_pages}")

            self.view_controller.update_thumbnail_selection(current_page)
    
    def resizeEvent(self, a0):
        """窗口大小变化事件"""
        super().resizeEvent(a0)
        # 使用防抖定时器，避免频繁触发
        if hasattr(self, 'resize_timer') and not self.resize_timer.isActive():
            self.resize_timer.start(100)
    
    def changeEvent(self, a0):
        """窗口状态变化事件"""
        super().changeEvent(a0)
        if a0.type() == a0.WindowStateChange:
            # 使用防抖定时器，避免频繁触发
            if hasattr(self, 'resize_timer') and not self.resize_timer.isActive():
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
    
    def contextMenuEvent(self, event):
        """处理右键菜单事件"""
        if hasattr(self, 'context_menu_manager'):
            self.context_menu_manager.show_context_menu(event)
        else:
            super().contextMenuEvent(event)
    
    def closeEvent(self, a0):
        """处理窗口关闭事件"""
        event = a0  # 保持向后兼容
        logger = get_logger('main')
        
        logger.debug("开始处理窗口关闭事件")

        if hasattr(self, 'update_actions_timer'):
            self.update_actions_timer.stop()

        has_unsaved_changes = False
        is_temp_document = False
        page_editor = None

        # 检查是否是临时文档（从图片打开或多文件合并）
        if hasattr(self.pdf_processor, 'is_temp_merge') and self.pdf_processor.is_temp_merge:
            is_temp_document = True
            logger.debug("检测到临时合并文档，需要提示保存")
        elif hasattr(self.pdf_processor, 'is_from_image') and self.pdf_processor.is_from_image:
            is_temp_document = True
            logger.debug("检测到从图片打开的文档，需要提示保存")

        # 检查是否有未保存的编辑
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

        # 如果有未保存的编辑或者是临时文档，都需要提示
        if has_unsaved_changes or is_temp_document:
            # 如果只是临时文档没有编辑，提示信息不同
            if is_temp_document and not has_unsaved_changes:
                logger.debug("临时文档无编辑，显示保存提示")
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("保存文档")
                msg_box.setText("当前文档尚未保存，是否保存？")
                msg_box.setIcon(QMessageBox.Question)

                save_btn = msg_box.addButton("保存", QMessageBox.AcceptRole)
                discard_btn = msg_box.addButton("不保存", QMessageBox.DestructiveRole)
                cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
                msg_box.setDefaultButton(save_btn)

                reply = msg_box.exec_()

                if msg_box.clickedButton() == save_btn:
                    logger.debug("用户选择保存")
                    success, message = self.file_manager.save_as_file()
                    if not success:
                        logger.error(f"保存失败: {message}")
                        QMessageBox.critical(self, "保存失败", message)
                        event.ignore()
                        return
                elif msg_box.clickedButton() == discard_btn:
                    logger.debug("用户选择不保存")
                    pass
                elif msg_box.clickedButton() == cancel_btn:
                    logger.debug("用户取消关闭")
                    event.ignore()
                    return
            else:
                logger.debug("检测到未保存的更改，显示确认对话框")
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("保存更改")
                msg_box.setText("文档已被修改，是否保存更改？")
                msg_box.setIcon(QMessageBox.Question)

                save_btn = msg_box.addButton("保存", QMessageBox.AcceptRole)
                discard_btn = msg_box.addButton("不保存", QMessageBox.DestructiveRole)
                cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
                msg_box.setDefaultButton(save_btn)

                reply = msg_box.exec_()

                if msg_box.clickedButton() == save_btn:
                    logger.debug("用户选择保存更改")
                    success, message = page_editor.save_changes()
                    if not success:
                        logger.error(f"保存失败: {message}")
                        QMessageBox.critical(self, "保存失败", message)
                        event.ignore()
                        return
                elif msg_box.clickedButton() == discard_btn:
                    logger.debug("用户选择不保存")
                    pass
                elif msg_box.clickedButton() == cancel_btn:
                    logger.debug("用户取消关闭")
                    event.ignore()
                    return
        else:
            logger.debug("没有未保存的更改")

        logger.debug("正常关闭程序")
        # 从全局窗口列表中移除当前窗口
        if 'app.main' in sys.modules:
            from app.main import open_windows
            if self in open_windows:
                open_windows.remove(self)
                logger.debug(f"窗口已从列表中移除，剩余窗口数: {len(open_windows)}")

        # 强制清理PDF处理器资源，避免fitz.Document.__del__报错
        if hasattr(self, 'pdf_processor'):
            self.pdf_processor.force_cleanup()
        event.accept()
    
    def _on_page_visible(self, page_num):
        """页面变为可见"""
        if hasattr(self.pdf_processor, 'render_pages_async'):
            self.pdf_processor.render_pages_async([page_num], self.render_width, self.render_height)
            
    def _on_page_hidden(self, page_num):
        """页面变为隐藏"""
        pass