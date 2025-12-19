"""工具栏管理器模块"""

from PyQt5.QtWidgets import QToolBar, QAction, QSpinBox, QLabel
from PyQt5.QtCore import QObject, QSize, Qt
from PyQt5.QtGui import QIcon
from app.utils.logger import get_logger

logger = get_logger('toolbar_manager')


class ToolbarManager(QObject):
    """工具栏管理器 - 负责创建和管理应用工具栏"""
    
    def __init__(self, parent_window):
        super().__init__()
        self.parent = parent_window
        
    def create_main_toolbar(self):
        """创建主工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        # 文件操作组
        self._add_file_actions(toolbar)
        toolbar.addSeparator()
        
        # 编辑操作组
        self._add_edit_actions(toolbar)
        toolbar.addSeparator()
        
        # 视图控制组
        self._add_view_actions(toolbar)
        toolbar.addSeparator()
        
        # 导航组
        self._add_navigation_actions(toolbar)
        toolbar.addSeparator()
        
        # 模式切换组
        self._add_mode_actions(toolbar)
        toolbar.addSeparator()
        
        # 转换工具组
        self._add_convert_actions(toolbar)
        
        self.parent.addToolBar(toolbar)
        return toolbar
    
    def _add_file_actions(self, toolbar):
        """添加文件操作按钮"""
        # 打开
        open_btn = QAction("📂 打开", self.parent)
        open_btn.setToolTip("打开PDF文件 (Ctrl+O)")
        open_btn.setShortcut("Ctrl+O")
        open_btn.triggered.connect(self.parent.open_file)
        toolbar.addAction(open_btn)
        
        # 保存
        save_btn = QAction("💾 保存", self.parent)
        save_btn.setToolTip("保存PDF文件 (Ctrl+S)")
        save_btn.setShortcut("Ctrl+S")
        save_btn.triggered.connect(self.parent.save_file)
        toolbar.addAction(save_btn)
        
        # 另存为
        save_as_btn = QAction("💾 另存为", self.parent)
        save_as_btn.setToolTip("另存为PDF文件 (Ctrl+Shift+S)")
        save_as_btn.setShortcut("Ctrl+Shift+S")
        save_as_btn.triggered.connect(self.parent.save_as_file)
        toolbar.addAction(save_as_btn)
    
    def _add_edit_actions(self, toolbar):
        """添加编辑操作按钮"""
        # 撤销
        self.parent.undo_btn = QAction("↩️ 撤销", self.parent)
        self.parent.undo_btn.setToolTip("撤销上一步操作 (Ctrl+Z)")
        self.parent.undo_btn.setShortcut("Ctrl+Z")
        self.parent.undo_btn.triggered.connect(self.parent.undo_operation)
        self.parent.undo_btn.setEnabled(False)
        toolbar.addAction(self.parent.undo_btn)
        
        # 重做
        self.parent.redo_btn = QAction("↪️ 重做", self.parent)
        self.parent.redo_btn.setToolTip("重做上一步操作 (Ctrl+Y)")
        self.parent.redo_btn.setShortcut("Ctrl+Y")
        self.parent.redo_btn.triggered.connect(self.parent.redo_operation)
        self.parent.redo_btn.setEnabled(False)
        toolbar.addAction(self.parent.redo_btn)
    
    def _add_view_actions(self, toolbar):
        """添加视图控制按钮"""
        # 放大
        zoom_in_btn = QAction("➕ 放大", self.parent)
        zoom_in_btn.setToolTip("放大页面 (Ctrl++)")
        zoom_in_btn.setShortcut("Ctrl++")
        zoom_in_btn.triggered.connect(self.parent.zoom_in)
        toolbar.addAction(zoom_in_btn)
        
        # 缩小
        zoom_out_btn = QAction("➖ 缩小", self.parent)
        zoom_out_btn.setToolTip("缩小页面 (Ctrl+-)")
        zoom_out_btn.setShortcut("Ctrl+-")
        zoom_out_btn.triggered.connect(self.parent.zoom_out)
        toolbar.addAction(zoom_out_btn)
        
        # 适应宽度
        fit_width_btn = QAction("↔️ 适应宽度", self.parent)
        fit_width_btn.setToolTip("适应页面宽度")
        fit_width_btn.triggered.connect(lambda: self.parent.fit_to_width())
        toolbar.addAction(fit_width_btn)
        
        # 适应高度
        fit_height_btn = QAction("↕️ 适应高度", self.parent)
        fit_height_btn.setToolTip("适应页面高度")
        fit_height_btn.triggered.connect(lambda: self.parent.fit_to_height())
        toolbar.addAction(fit_height_btn)
        
        # 原始尺寸
        actual_size_btn = QAction("1:1 原始尺寸", self.parent)
        actual_size_btn.setToolTip("显示原始尺寸")
        actual_size_btn.triggered.connect(lambda: self.parent.set_actual_size())
        toolbar.addAction(actual_size_btn)
    
    def _add_navigation_actions(self, toolbar):
        """添加导航按钮"""
        # 上一页
        prev_page_btn = QAction("⬅️ 上一页", self.parent)
        prev_page_btn.setToolTip("上一页 (PgUp)")
        prev_page_btn.setShortcut("PgUp")
        prev_page_btn.triggered.connect(self.parent.previous_page)
        toolbar.addAction(prev_page_btn)
        
        # 下一页
        next_page_btn = QAction("➡️ 下一页", self.parent)
        next_page_btn.setToolTip("下一页 (PgDown)")
        next_page_btn.setShortcut("PgDown")
        next_page_btn.triggered.connect(self.parent.next_page)
        toolbar.addAction(next_page_btn)
        
        # 页码输入框
        self.parent.page_spinbox = QSpinBox()
        self.parent.page_spinbox.setFixedWidth(60)
        self.parent.page_spinbox.setAlignment(Qt.AlignCenter)
        self.parent.page_spinbox.setMinimum(1)
        self.parent.page_spinbox.setValue(1)
        self.parent.page_spinbox.setToolTip("当前页码")
        self.parent.page_spinbox.valueChanged.connect(self.parent._on_page_spinbox_changed)
        self.parent.page_spinbox.editingFinished.connect(self.parent.go_to_page)
        toolbar.addWidget(self.parent.page_spinbox)
        
        # 总页数标签
        self.parent.total_pages_label = QLabel()
        toolbar.addWidget(self.parent.total_pages_label)
    
    def _add_mode_actions(self, toolbar):
        """添加模式切换按钮"""
        # 搜索
        search_btn = QAction("🔍 搜索", self.parent)
        search_btn.setToolTip("搜索文本 (Ctrl+F)")
        search_btn.setShortcut("Ctrl+F")
        search_btn.triggered.connect(self.parent.show_search_options)
        toolbar.addAction(search_btn)
        
        # 缩略图
        self.parent.thumbnail_btn = QAction("📋 缩略图", self.parent)
        self.parent.thumbnail_btn.setCheckable(True)
        self.parent.thumbnail_btn.setChecked(False)
        self.parent.thumbnail_btn.setToolTip("显示/隐藏缩略图")
        self.parent.thumbnail_btn.triggered.connect(self.parent.toggle_thumbnails)
        toolbar.addAction(self.parent.thumbnail_btn)
    
    def _add_convert_actions(self, toolbar):
        """添加转换工具按钮"""
        # 导入图片
        import_images_btn = QAction("📷 导入图片", self.parent)
        import_images_btn.setToolTip("导入图片到PDF (Ctrl+Shift+I)")
        import_images_btn.triggered.connect(self.parent.import_images)
        toolbar.addAction(import_images_btn)
        
        # 拆分PDF
        split_btn = QAction("✂️ 拆分", self.parent)
        split_btn.setToolTip("拆分PDF文档")
        split_btn.triggered.connect(self.parent.split_pdf)
        toolbar.addAction(split_btn)
        
        # 条码拆分
        barcode_split_btn = QAction("📟 条码拆分", self.parent)
        barcode_split_btn.setToolTip("根据条码拆分PDF文档")
        barcode_split_btn.triggered.connect(self.parent.barcode_split_pdf)
        toolbar.addAction(barcode_split_btn)
        
        # OCR设置
        ocr_settings_btn = QAction("🔍 OCR设置", self.parent)
        ocr_settings_btn.setToolTip("配置OCR引擎参数")
        ocr_settings_btn.triggered.connect(self.parent.show_ocr_settings)
        toolbar.addAction(ocr_settings_btn)
        
        # 执行OCR
        perform_ocr_btn = QAction("🔤 执行OCR", self.parent)
        perform_ocr_btn.setToolTip("对当前页面执行OCR识别")
        perform_ocr_btn.triggered.connect(self.parent.perform_ocr_on_current_page)
        toolbar.addAction(perform_ocr_btn)