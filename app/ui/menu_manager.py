"""菜单管理器模块"""

from PyQt5.QtWidgets import QMenuBar, QMenu, QAction
from PyQt5.QtCore import QObject
from app.utils.logger import get_logger

logger = get_logger('menu_manager')


class MenuManager(QObject):
    """菜单管理器 - 负责创建和管理应用菜单"""
    
    def __init__(self, parent_window):
        super().__init__()
        self.parent = parent_window
        
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.parent.menuBar()
        
        # 文件菜单
        self._create_file_menu(menubar)
        
        # 视图菜单
        self._create_view_menu(menubar)
        
        # 工具菜单
        self._create_tools_menu(menubar)
        
        # 帮助菜单
        self._create_help_menu(menubar)
        
        return menubar
    
    def _create_file_menu(self, menubar):
        """创建文件菜单"""
        file_menu = menubar.addMenu("📁 文件")
        
        # 打开
        open_action = QAction("📂 打开", self.parent)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.parent.open_file)
        file_menu.addAction(open_action)
        
        # 保存
        save_action = QAction("💾 保存", self.parent)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.parent.save_file)
        file_menu.addAction(save_action)
        
        # 另存为
        save_as_action = QAction("💾 另存为", self.parent)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.parent.save_as_file)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # 保存更改
        self.parent.save_changes_action = QAction("✅ 保存更改", self.parent)
        self.parent.save_changes_action.setShortcut("Ctrl+Shift+S")
        self.parent.save_changes_action.triggered.connect(self.parent.save_changes)
        self.parent.save_changes_action.setEnabled(False)
        file_menu.addAction(self.parent.save_changes_action)
        
        # 放弃更改
        self.parent.discard_changes_action = QAction("❌ 放弃更改", self.parent)
        self.parent.discard_changes_action.setShortcut("Ctrl+D")
        self.parent.discard_changes_action.triggered.connect(self.parent.discard_changes)
        self.parent.discard_changes_action.setEnabled(False)
        file_menu.addAction(self.parent.discard_changes_action)
        
        file_menu.addSeparator()
        
        # 撤销
        self.parent.undo_action = QAction("↩️ 撤销", self.parent)
        self.parent.undo_action.setShortcut("Ctrl+Z")
        self.parent.undo_action.triggered.connect(self.parent.undo_operation)
        self.parent.undo_action.setEnabled(False)
        file_menu.addAction(self.parent.undo_action)
        
        # 重做
        self.parent.redo_action = QAction("↪️ 重做", self.parent)
        self.parent.redo_action.setShortcut("Ctrl+Y")
        self.parent.redo_action.triggered.connect(self.parent.redo_operation)
        self.parent.redo_action.setEnabled(False)
        file_menu.addAction(self.parent.redo_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("🚪 退出", self.parent)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.parent.close)
        file_menu.addAction(exit_action)
    
    def _create_view_menu(self, menubar):
        """创建视图菜单"""
        view_menu = menubar.addMenu("👀 视图")
        
        # 缩略图
        self.parent.thumbnail_action = QAction("🖼️ 缩略图", self.parent)
        self.parent.thumbnail_action.setCheckable(True)
        self.parent.thumbnail_action.setChecked(True)
        self.parent.thumbnail_action.triggered.connect(self.parent.toggle_thumbnails)
        view_menu.addAction(self.parent.thumbnail_action)
    
    def _create_tools_menu(self, menubar):
        """创建工具菜单"""
        tools_menu = menubar.addMenu("🛠️ 工具")
        
        # 导入图片
        import_images_action = QAction("📷 导入图片", self.parent)
        import_images_action.setShortcut("Ctrl+Shift+I")
        import_images_action.triggered.connect(self.parent.import_images)
        tools_menu.addAction(import_images_action)
        
        # 转为图片
        convert_to_image_action = QAction("🖼️ 转为图片", self.parent)
        convert_to_image_action.setShortcut("Ctrl+I")
        convert_to_image_action.triggered.connect(self.parent.convert_pdf_to_images)
        tools_menu.addAction(convert_to_image_action)
        
        tools_menu.addSeparator()
        
        # 分割PDF
        split_action = QAction("✂️ 分割PDF", self.parent)
        split_action.triggered.connect(self.parent.split_pdf)
        tools_menu.addAction(split_action)
    
    def _create_help_menu(self, menubar):
        """创建帮助菜单"""
        help_menu = menubar.addMenu("❓ 帮助")
        
        # 关于
        about_action = QAction("ℹ️ 关于", self.parent)
        about_action.triggered.connect(self.parent.show_about)
        help_menu.addAction(about_action)