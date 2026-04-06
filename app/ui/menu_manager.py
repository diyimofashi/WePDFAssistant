"""菜单管理器模块"""

from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import QObject
from app.utils.logger import get_logger
from app.config.settings import AppSettings

logger = get_logger('menu_manager')


class MenuManager(QObject):
    """菜单管理器 - 负责创建和管理应用菜单"""

    def __init__(self, parent_window):
        super().__init__()
        self.parent = parent_window
        self.shortcuts_registered = False  # 标记是否已注册快捷键

    def register_shortcuts(self):
        """注册所有菜单动作的快捷键到快捷键管理器"""
        if self.shortcuts_registered:
            return

        # 尝试获取快捷键管理器
        shortcut_manager = None
        if hasattr(self.parent, 'shortcut_manager'):
            shortcut_manager = self.parent.shortcut_manager
        elif self.parent.parent() and hasattr(self.parent.parent(), 'shortcut_manager'):
            shortcut_manager = self.parent.parent().shortcut_manager
        elif self.parent.window() and hasattr(self.parent.window(), 'shortcut_manager'):
            shortcut_manager = self.parent.window().shortcut_manager

        if not shortcut_manager:
            logger.warning("快捷键管理器未找到，跳过快捷键注册")
            return

        # 注册跳转页面动作
        if hasattr(self.parent, 'jump_to_page'):
            jump_action = QAction("🔢 跳转页面", self.parent)
            jump_action.triggered.connect(self.parent.jump_to_page)
            shortcut_manager.register_action("nav.jump_page", jump_action)
            logger.debug("已注册快捷键: nav.jump_page")

        self.shortcuts_registered = True
        logger.info("菜单快捷键注册完成")

        
    def create_menubar(self, menubar=None):
        """创建菜单栏

        Args:
            menubar: 可选的菜单栏对象。如果不提供，则从 parent.menuBar() 获取
        """
        if menubar is None:
            menubar = self.parent.menuBar()

        # 文件菜单
        self._create_file_menu(menubar)

        # 视图菜单
        self._create_view_menu(menubar)

        # 设置菜单
        self._create_settings_menu(menubar)

        # 工具菜单
        self._create_tools_menu(menubar)

        # 帮助菜单
        self._create_help_menu(menubar)

        # 注册快捷键
        self.register_shortcuts()

        return menubar
    
    def _create_file_menu(self, menubar):
        """创建文件菜单"""
        file_menu = menubar.addMenu("📁 文件")

        # 打开（支持文件、多张图片、图片目录）
        open_action = QAction("📂 打开", self.parent)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.parent.open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

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
        # 读取设置:打开新文件时是否默认显示缩略图
        is_checked = AppSettings.get_show_thumbnails_default()
        self.parent.thumbnail_action.setChecked(is_checked)
        self.parent.thumbnail_action.triggered.connect(self.toggle_thumbnails_default)
        view_menu.addAction(self.parent.thumbnail_action)

        # 文件列表面板
        from app.utils.plugin_checker import check_storage_plugin
        if check_storage_plugin():
            self.parent.file_list_panel_visible_action = QAction("📂 文件列表面板", self.parent)
            self.parent.file_list_panel_visible_action.setCheckable(True)
            # 读取设置
            is_visible = AppSettings.get_file_list_panel_visible()
            self.parent.file_list_panel_visible_action.setChecked(is_visible)
            self.parent.file_list_panel_visible_action.triggered.connect(self.toggle_file_list_panel_visible)
            view_menu.addAction(self.parent.file_list_panel_visible_action)

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

        # 实际大小选项
        view_menu.addSeparator()
        actual_size_action = QAction("📏 实际大小", self.parent)
        actual_size_action.setCheckable(True)
        actual_size_action.setChecked(not AppSettings.get_use_a4_scaling())
        actual_size_action.triggered.connect(self.parent.toggle_actual_size)
        view_menu.addAction(actual_size_action)
        self.parent.actual_size_action = actual_size_action

        # 导航操作
        view_menu.addSeparator()

        # 上一页
        prev_page_action = QAction("⬅️ 上一页", self.parent)
        prev_page_action.setShortcut("PgUp")
        prev_page_action.triggered.connect(self.parent.previous_page)
        view_menu.addAction(prev_page_action)

        # 下一页
        next_page_action = QAction("➡️ 下一页", self.parent)
        next_page_action.setShortcut("PgDown")
        next_page_action.triggered.connect(self.parent.next_page)
        view_menu.addAction(next_page_action)

        # 跳转页面
        jump_page_action = QAction("🔢 跳转页面", self.parent)
        jump_page_action.setShortcut("Ctrl+G")
        jump_page_action.triggered.connect(self.parent.go_to_page)
        view_menu.addAction(jump_page_action)

        
    def _create_settings_menu(self, menubar):
        """创建设置菜单"""
        settings_menu = menubar.addMenu("⚙️ 设置")

        # 界面设置
        ui_settings_action = QAction("🎨 界面设置", self.parent)
        ui_settings_action.triggered.connect(self.parent.show_ui_settings)
        settings_menu.addAction(ui_settings_action)

        # 快捷键设置
        shortcut_settings_action = QAction("⌨️ 快捷键设置", self.parent)
        shortcut_settings_action.setShortcut("Ctrl+K")
        shortcut_settings_action.triggered.connect(self.parent.show_shortcut_settings)
        settings_menu.addAction(shortcut_settings_action)
    
    def _create_tools_menu(self, menubar):
        tools_menu = menubar.addMenu("🛠️ 工具")
        
        # PDF处理子菜单
        pdf_menu = tools_menu.addMenu("📄 PDF处理")

        # 导入图片
        import_images_action = QAction("📷 导入图片", self.parent)
        import_images_action.setShortcut("Ctrl+Shift+I")
        import_images_action.triggered.connect(self.parent.import_images)
        pdf_menu.addAction(import_images_action)

        # 转为图片
        convert_to_image_action = QAction("🖼️ 转为图片", self.parent)
        convert_to_image_action.setShortcut("Ctrl+I")
        convert_to_image_action.triggered.connect(self.parent.convert_pdf_to_images)
        pdf_menu.addAction(convert_to_image_action)
        
        # 分割PDF
        split_action = QAction("✂️ 分割PDF", self.parent)
        split_action.triggered.connect(self.parent.split_pdf)
        pdf_menu.addAction(split_action)

        # 合并PDF
        merge_action = QAction("📑 合并PDF", self.parent)
        merge_action.triggered.connect(self.parent.merge_pdf)
        pdf_menu.addAction(merge_action)
        
        # OCR工具子菜单
        tools_menu.addSeparator()
        ocr_menu = tools_menu.addMenu("🔍 OCR工具")

        # OCR设置
        ocr_settings_action = QAction("⚙️ OCR设置", self.parent)
        ocr_settings_action.triggered.connect(self.parent.show_ocr_settings)
        ocr_menu.addAction(ocr_settings_action)

        # 截图OCR
        screenshot_ocr_action = QAction("📷 截图OCR", self.parent)
        screenshot_ocr_action.setShortcut("Alt+S")
        screenshot_ocr_action.triggered.connect(self.parent.start_screenshot_ocr_mode)
        ocr_menu.addAction(screenshot_ocr_action)

        # 对当前页执行OCR
        perform_ocr_action = QAction("🔤 对当前页执行OCR", self.parent)
        perform_ocr_action.triggered.connect(self.parent.perform_ocr_on_current_page)
        ocr_menu.addAction(perform_ocr_action)

        # 对全部页面执行OCR
        perform_all_pages_ocr_action = QAction("📚 对全部页面执行OCR", self.parent)
        perform_all_pages_ocr_action.triggered.connect(self.parent.perform_ocr_on_all_pages)
        ocr_menu.addAction(perform_all_pages_ocr_action)

        # 创建可搜索PDF
        searchable_pdf_action = QAction("📄 创建可搜索PDF", self.parent)
        searchable_pdf_action.triggered.connect(self.parent.create_searchable_pdf)
        ocr_menu.addAction(searchable_pdf_action)

        # OCR文本层高亮模式
        ocr_menu.addSeparator()
        self.parent.ocr_debug_mode_action = QAction("🔍 OCR文本层高亮模式", self.parent)
        self.parent.ocr_debug_mode_action.setCheckable(True)
        self.parent.ocr_debug_mode_action.setChecked(False)
        self.parent.ocr_debug_mode_action.triggered.connect(self.parent.toggle_ocr_debug_mode)
        ocr_menu.addAction(self.parent.ocr_debug_mode_action)

        # 云存储插件子菜单
        tools_menu.addSeparator()
        storage_menu = tools_menu.addMenu("☁️ 云存储插件")

        # 云存储插件设置
        storage_settings_action = QAction("⚙️ 云存储插件设置", self.parent)
        storage_settings_action.triggered.connect(self.parent.show_storage_settings)
        storage_menu.addAction(storage_settings_action)

        # 条码工具子菜单
        tools_menu.addSeparator()
        barcode_menu = tools_menu.addMenu("📟 条码工具")
        
        # 条码插件设置
        barcode_settings_action = QAction("⚙️ 条码拆分", self.parent)
        barcode_settings_action.triggered.connect(self.parent.show_barcode_settings)
        barcode_menu.addAction(barcode_settings_action)
        
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
        search_action.triggered.connect(self.parent.show_search_panel)
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
        
        # 检查更新
        update_action = QAction("🔄 检查更新", self.parent)
        # 假设父窗口有相关方法
        help_menu.addAction(update_action)

    def toggle_file_list_panel_visible(self):
        """切换文件列表面板的可见性设置"""
        current = AppSettings.get_file_list_panel_visible()
        new_value = not current
        AppSettings.set_file_list_panel_visible(new_value)

        # 更新菜单项状态
        self.parent.file_list_panel_visible_action.setChecked(new_value)

        # 如果设置为显示且面板当前不可见，则显示它
        if new_value and self.parent.file_list_dock and not self.parent.file_list_dock.isVisible():
            self.parent.file_list_dock.show()
            self.parent.file_list_panel.load_current_plugin()
        # 如果设置为隐藏且面板当前可见，则隐藏它
        elif not new_value and self.parent.file_list_dock and self.parent.file_list_dock.isVisible():
            self.parent.file_list_dock.hide()

        logger = get_logger('menu_manager')
        logger.info(f"文件列表面板可见性设置已更改为: {'显示' if new_value else '隐藏'}")

    def toggle_thumbnails_default(self):
        """切换打开新文件时是否默认显示缩略图"""
        current = AppSettings.get_show_thumbnails_default()
        new_value = not current
        AppSettings.set_show_thumbnails_default(new_value)

        # 更新菜单项状态
        self.parent.thumbnail_action.setChecked(new_value)

        logger = get_logger('menu_manager')
        logger.info(f"缩略图默认显示设置已更改为: {'显示' if new_value else '隐藏'}")