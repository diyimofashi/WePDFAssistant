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
        
        # 打开多张图片
        open_multiple_images_action = QAction("🖼️ 打开多张图片", self.parent)
        open_multiple_images_action.setShortcut("Ctrl+Shift+O")
        open_multiple_images_action.triggered.connect(self.parent.open_multiple_images)
        file_menu.addAction(open_multiple_images_action)
        
        # 打开图片目录
        open_image_dir_action = QAction("📁 打开图片目录", self.parent)
        open_image_dir_action.setShortcut("Ctrl+D")
        open_image_dir_action.triggered.connect(self.parent.open_image_directory)
        file_menu.addAction(open_image_dir_action)

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

        # 加密保存
        encrypt_save_action = QAction("🔒 加密保存", self.parent)
        encrypt_save_action.triggered.connect(self.parent.encrypt_save_file)
        file_menu.addAction(encrypt_save_action)

        # 加密另存为
        encrypt_save_as_action = QAction("🔒 加密另存为", self.parent)
        encrypt_save_as_action.triggered.connect(self.parent.encrypt_save_as_file)
        file_menu.addAction(encrypt_save_as_action)

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
        
        file_menu.addSeparator()
        
        # 打开远程文件
        remote_open_action = QAction("🌐 打开远程文件", self.parent)
        remote_open_action.triggered.connect(self.parent.open_remote_file)
        file_menu.addAction(remote_open_action)
    
    def _create_view_menu(self, menubar):
        """创建视图菜单"""
        view_menu = menubar.addMenu("👀 视图")
        
        # 缩略图
        self.parent.thumbnail_action = QAction("🖼️ 缩略图", self.parent)
        self.parent.thumbnail_action.setCheckable(True)
        self.parent.thumbnail_action.setChecked(True)
        self.parent.thumbnail_action.triggered.connect(self.parent.toggle_thumbnails)
        view_menu.addAction(self.parent.thumbnail_action)
        
        # 缩放子菜单
        view_menu.addSeparator()
        zoom_menu = view_menu.addMenu("🔍 缩放")
        
        # 基本缩放操作
        zoom_in_action = QAction("➕ 放大", self.parent)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.parent.zoom_in)
        zoom_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("➖ 缩小", self.parent)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.parent.zoom_out)
        zoom_menu.addAction(zoom_out_action)
        
        fit_width_action = QAction("↔️ 适应宽度", self.parent)
        fit_width_action.triggered.connect(lambda: self.parent.fit_to_width())
        zoom_menu.addAction(fit_width_action)
        
        fit_height_action = QAction("↕️ 适应高度", self.parent)
        fit_height_action.triggered.connect(lambda: self.parent.fit_to_height())
        zoom_menu.addAction(fit_height_action)
        
        actual_size_action = QAction("1:1 原始尺寸", self.parent)
        actual_size_action.triggered.connect(lambda: self.parent.set_actual_size())
        zoom_menu.addAction(actual_size_action)
        
        zoom_menu.addSeparator()
        
        # 预设缩放比例
        zoom_levels = [25, 50, 75, 100, 125, 150, 200]
        for level in zoom_levels:
            zoom_action = QAction(f"{level}%", self.parent)
            zoom_action.triggered.connect(lambda checked=False, l=level: self.parent.set_zoom_level(l))
            zoom_menu.addAction(zoom_action)
        
        # 页面布局子菜单
        view_menu.addSeparator()
        layout_menu = view_menu.addMenu("📄 页面布局")
        
        single_page_action = QAction("📖 单页显示", self.parent)
        single_page_action.setCheckable(True)
        single_page_action.setChecked(True)
        # 假设父窗口有相关方法
        layout_menu.addAction(single_page_action)
        
        double_page_action = QAction("📚 双页显示", self.parent)
        double_page_action.setCheckable(True)
        # 假设父窗口有相关方法
        layout_menu.addAction(double_page_action)
        
        continuous_action = QAction("📜 连续模式", self.parent)
        continuous_action.setCheckable(True)
        # 假设父窗口有相关方法
        layout_menu.addAction(continuous_action)
    
    def _create_tools_menu(self, menubar):
        """创建工具菜单"""
        tools_menu = menubar.addMenu("🛠️ 工具")
        
        # PDF处理子菜单
        pdf_menu = tools_menu.addMenu("📄 PDF处理")
        
        # 导入图片
        import_images_action = QAction("📷 导入图片", self.parent)
        import_images_action.setShortcut("Ctrl+Shift+I")
        import_images_action.triggered.connect(self.parent.import_images)
        pdf_menu.addAction(import_images_action)
        
        # 从目录导入图片
        import_images_dir_action = QAction("📂 从目录导入图片", self.parent)
        import_images_dir_action.triggered.connect(self.parent.open_images_from_directory)
        pdf_menu.addAction(import_images_dir_action)
        
        # 转为图片
        convert_to_image_action = QAction("🖼️ 转为图片", self.parent)
        convert_to_image_action.setShortcut("Ctrl+I")
        convert_to_image_action.triggered.connect(self.parent.convert_pdf_to_images)
        pdf_menu.addAction(convert_to_image_action)
        
        # 分割PDF
        split_action = QAction("✂️ 分割PDF", self.parent)
        split_action.triggered.connect(self.parent.split_pdf)
        pdf_menu.addAction(split_action)
        
        # OCR工具子菜单
        tools_menu.addSeparator()
        ocr_menu = tools_menu.addMenu("🔍 OCR工具")
        
        # OCR设置
        ocr_settings_action = QAction("⚙️ OCR设置", self.parent)
        ocr_settings_action.triggered.connect(self.parent.show_ocr_settings)
        ocr_menu.addAction(ocr_settings_action)
        
        # 执行OCR
        perform_ocr_action = QAction("🔤 执行OCR", self.parent)
        perform_ocr_action.triggered.connect(self.parent.perform_ocr_on_current_page)
        ocr_menu.addAction(perform_ocr_action)
        
        # 创建可搜索PDF
        searchable_pdf_action = QAction("📄 创建可搜索PDF", self.parent)
        searchable_pdf_action.triggered.connect(self.parent.create_searchable_pdf)
        ocr_menu.addAction(searchable_pdf_action)
        
        # 上传工具子菜单
        tools_menu.addSeparator()
        upload_menu = tools_menu.addMenu("📤 上传工具")
        
        # 上传设置
        upload_settings_action = QAction("⚙️ 上传设置", self.parent)
        upload_settings_action.triggered.connect(self.parent.show_upload_settings)
        upload_menu.addAction(upload_settings_action)
        
        # 上传当前文档
        upload_current_action = QAction("📄 上传当前文档", self.parent)
        upload_current_action.triggered.connect(self.parent.upload_current_document)
        upload_menu.addAction(upload_current_action)
        
        # 下载工具子菜单
        tools_menu.addSeparator()
        download_menu = tools_menu.addMenu("📥 下载工具")
        
        # 下载设置
        download_settings_action = QAction("⚙️ 下载设置", self.parent)
        download_settings_action.triggered.connect(self.parent.show_download_settings)
        download_menu.addAction(download_settings_action)
        
        # 下载远程文件
        download_remote_action = QAction("🌐 下载远程文件", self.parent)
        download_remote_action.triggered.connect(self.parent.open_remote_file)
        download_menu.addAction(download_remote_action)
        
        # 条码工具子菜单
        tools_menu.addSeparator()
        barcode_menu = tools_menu.addMenu("📟 条码工具")
        
        # 条码设置
        barcode_settings_action = QAction("⚙️ 条码设置", self.parent)
        barcode_settings_action.triggered.connect(self.parent.show_barcode_settings)
        barcode_menu.addAction(barcode_settings_action)
        
        # 条码拆分
        barcode_split_action = QAction("📟 条码拆分", self.parent)
        barcode_split_action.triggered.connect(self.parent.barcode_split_pdf)
        barcode_menu.addAction(barcode_split_action)
        
        # 检测条码
        detect_barcode_action = QAction("🔍 检测条码", self.parent)
        # 假设父窗口有相关方法
        barcode_menu.addAction(detect_barcode_action)
        
        # 批量处理工具
        tools_menu.addSeparator()
        batch_menu = tools_menu.addMenu("🔄 批量处理")
        
        # 批量加解密
        batch_crypto_action = QAction("🔐 批量加解密", self.parent)
        batch_crypto_action.triggered.connect(self.parent.show_batch_crypto_dialog)
        batch_menu.addAction(batch_crypto_action)
        
        # 其他工具
        tools_menu.addSeparator()
        other_menu = tools_menu.addMenu("⚡ 其他工具")
        
        # 搜索
        search_action = QAction("🔍 搜索", self.parent)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.parent.show_search_options)
        other_menu.addAction(search_action)
        
        # 打印
        print_action = QAction("🖨️ 打印", self.parent)
        # 假设父窗口有相关方法
        other_menu.addAction(print_action)
    
    def _create_help_menu(self, menubar):
        """创建帮助菜单"""
        help_menu = menubar.addMenu("❓ 帮助")
        
        # 关于
        about_action = QAction("ℹ️ 关于", self.parent)
        about_action.triggered.connect(self.parent.show_about)
        help_menu.addAction(about_action)
        
        # 快捷键说明
        shortcuts_action = QAction("⌨️ 快捷键说明", self.parent)
        # 假设父窗口有相关方法
        help_menu.addAction(shortcuts_action)
        
        # 检查更新
        update_action = QAction("🔄 检查更新", self.parent)
        # 假设父窗口有相关方法
        help_menu.addAction(update_action)