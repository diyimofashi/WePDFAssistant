"""
文件列表面板 - 用于显示远程文件列表
支持在右侧停靠，可隐藏和显示
支持分页和不分页两种模式
"""

from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
                             QProgressBar, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger('file_list_panel')


class LoadFilesThread(QThread):
    """加载文件列表的线程"""
    finished = pyqtSignal(object)

    def __init__(self, plugin, remote_path: str = "", page: int = 1, page_size: int = 50, supports_pagination: bool = False):
        super().__init__()
        self.plugin = plugin
        self.remote_path = remote_path
        self.page = page
        self.page_size = page_size
        self.supports_pagination = supports_pagination

    def run(self):
        """执行加载文件列表"""
        kwargs = {}
        if self.supports_pagination:
            kwargs['page'] = self.page
            kwargs['page_size'] = self.page_size

        result = self.plugin.list_files(self.remote_path, **kwargs)
        self.finished.emit(result)


class FileListPanel(QDockWidget):
    """文件列表面板"""

    def __init__(self, parent=None):
        super().__init__("文件列表", parent)
        self.parent_window = parent
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)

        # 设置面板宽度为默认宽度的1倍（600像素）
        self.setMinimumWidth(600)

        # 文件列表数据
        self.files_data = []
        self.plugin = None
        self.load_thread = None
        self.plugin_name = ""  # 添加插件名称属性

        # 分页相关
        self.current_page = 1
        self.page_size = 50
        self.total_count = 0
        self.total_pages = 0
        self.supports_pagination = False  # 插件是否支持分页

        self.setup_ui()
        self.load_current_plugin_info()

    def setup_ui(self):
        """设置UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 刷新按钮（靠右对齐）
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setMaximumWidth(80)
        self.refresh_button.clicked.connect(self.load_files)
        button_layout.addWidget(self.refresh_button)
        layout.addLayout(button_layout)

        # 文件列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["文件名", "文件大小", "修改时间", "文件类型", "路径"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # 双击打开文件
        self.table.itemDoubleClicked.connect(self.open_file_at_index)

        layout.addWidget(self.table)

        # 加载进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        # 分页控件
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(self.pagination_widget)
        pagination_layout.setContentsMargins(0, 0, 0, 0)

        # 每页数量标签和下拉框
        pagination_layout.addWidget(QLabel("每页:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "20", "30", "50", "100", "200", "500"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        pagination_layout.addWidget(self.page_size_combo)

        pagination_layout.addStretch()

        # 上一页按钮
        self.prev_button = QPushButton("上一页")
        self.prev_button.clicked.connect(self.on_prev_page)
        self.prev_button.setEnabled(False)
        pagination_layout.addWidget(self.prev_button)

        # 页码标签
        self.page_label = QLabel("第 1 页")
        pagination_layout.addWidget(self.page_label)

        # 下一页按钮
        self.next_button = QPushButton("下一页")
        self.next_button.clicked.connect(self.on_next_page)
        self.next_button.setEnabled(False)
        pagination_layout.addWidget(self.next_button)

        self.pagination_widget.setVisible(False)
        layout.addWidget(self.pagination_widget)

        self.setWidget(container)

    def load_current_plugin_info(self):
        """加载当前应用的下载插件信息（不加载文件列表）"""
        try:
            from app.config.download_plugin_config import download_config_manager
            from app.managers.download_plugin_manager import download_plugin_manager

            plugin_name = download_config_manager.get_current_plugin()
            if not plugin_name:
                return

            plugin = download_plugin_manager.get_plugin(plugin_name)
            if not plugin:
                return

            # 检查插件是否已初始化，如果没有则初始化
            if not plugin.is_initialized:
                config = download_config_manager.get_plugin_config(plugin_name)
                init_result = download_plugin_manager.initialize_plugin(plugin_name, config)
                if not init_result.is_success():
                    logger.error(f"下载插件 {plugin_name} 初始化失败: {init_result.message}")
                    return

            # 使用插件实例
            self.plugin = plugin
            self.plugin_name = plugin_name

            if hasattr(plugin, 'PluginInfo'):
                plugin_info = plugin.PluginInfo
                local_options = plugin_info.get('local_options', {})
                plugin_title = local_options.get('title', plugin_name)
            else:
                plugin_title = plugin_name

            # 更新面板标题
            self.setWindowTitle(f"文件列表 - {plugin_title}")
            logger.info(f"成功加载下载插件: {plugin_name}")

            # 检查插件是否支持分页
            self.supports_pagination = getattr(plugin, 'supports_pagination', lambda: False)()

            # 如果插件支持分页，显示分页控件
            if self.supports_pagination:
                self.pagination_widget.setVisible(True)
            else:
                self.pagination_widget.setVisible(False)
        except Exception as e:
            logger.error(f"加载当前插件失败: {e}")

    def load_current_plugin(self):
        """加载当前应用的下载插件并加载文件列表"""
        try:
            from app.config.download_plugin_config import download_config_manager
            from app.managers.download_plugin_manager import download_plugin_manager

            plugin_name = download_config_manager.get_current_plugin()
            if not plugin_name:
                return

            plugin = download_plugin_manager.get_plugin(plugin_name)
            if not plugin:
                return

            # 检查插件是否已初始化，如果没有则初始化
            if not plugin.is_initialized:
                config = download_config_manager.get_plugin_config(plugin_name)
                init_result = download_plugin_manager.initialize_plugin(plugin_name, config)
                if not init_result.is_success():
                    logger.error(f"下载插件 {plugin_name} 初始化失败: {init_result.message}")
                    return

            # 使用插件实例
            self.plugin = plugin
            self.plugin_name = plugin_name

            if hasattr(plugin, 'PluginInfo'):
                plugin_info = plugin.PluginInfo
                local_options = plugin_info.get('local_options', {})
                plugin_title = local_options.get('title', plugin_name)
            else:
                plugin_title = plugin_name

            # 更新面板标题
            self.setWindowTitle(f"文件列表 - {plugin_title}")
            logger.info(f"成功加载下载插件: {plugin_name}")

            # 检查插件是否支持分页
            self.supports_pagination = getattr(plugin, 'supports_pagination', lambda: False)()

            # 如果插件支持分页，显示分页控件
            if self.supports_pagination:
                self.pagination_widget.setVisible(True)
            else:
                self.pagination_widget.setVisible(False)

            # 自动加载文件列表
            self.load_files()
        except Exception as e:
            logger.error(f"加载当前插件失败: {e}")

    def set_plugin(self, plugin):
        """设置插件（保留用于手动设置的场景）"""
        self.plugin = plugin
        plugin_name = getattr(plugin, 'plugin_name', '')
        if hasattr(plugin, 'PluginInfo'):
            plugin_info = plugin.PluginInfo
            local_options = plugin_info.get('local_options', {})
            plugin_title = local_options.get('title', plugin_name)
        else:
            plugin_title = plugin_name

            # 更新面板标题
            self.setWindowTitle(f"文件列表 - {plugin_title}")

            # 检查插件是否支持分页
            self.supports_pagination = getattr(plugin, 'supports_pagination', lambda: False)()

            # 如果插件支持分页，显示分页控件
            if self.supports_pagination:
                self.pagination_widget.setVisible(True)
            else:
                self.pagination_widget.setVisible(False)

    def load_files(self, remote_path: str = ""):
        """加载文件列表"""
        if not self.plugin:
            QMessageBox.warning(self, "提示", "请先在下载设置中选择插件")
            return

        if self.load_thread and self.load_thread.isRunning():
            return

        self.table.setRowCount(0)
        self.files_data = []
        self.progress_bar.setVisible(True)
        self.refresh_button.setEnabled(False)

        # 创建加载线程
        self.load_thread = LoadFilesThread(
            self.plugin,
            remote_path,
            self.current_page,
            self.page_size,
            self.supports_pagination
        )
        self.load_thread.finished.connect(self.on_files_loaded)
        self.load_thread.start()

    def on_files_loaded(self, result: object):
        """文件列表加载完成"""
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)

        if not result.is_success():
            QMessageBox.warning(self, "加载失败",
                            f"加载文件列表失败: {result.message}")
            logger.error(f"加载文件列表失败: {result.message}")
            return

        self.files_data = result.data.get('files', [])

        # 更新分页信息
        if self.supports_pagination:
            self.total_count = result.data.get('total', len(self.files_data))
            self.total_pages = result.data.get('total_pages', 1)
            self.update_pagination_controls()
        else:
            self.total_count = len(self.files_data)
            self.total_pages = 1

        self.populate_table()

    def populate_table(self):
        """填充表格数据"""
        self.table.setRowCount(len(self.files_data))

        for row, file_info in enumerate(self.files_data):
            # 文件名
            name_item = QTableWidgetItem(file_info.get('name', ''))
            name_item.setData(Qt.UserRole, file_info)
            self.table.setItem(row, 0, name_item)

            # 文件大小
            size = file_info.get('size', 0)
            # 确保大小是整数类型
            try:
                size = int(size)
            except (ValueError, TypeError):
                size = 0
            size_text = self.format_size(size)
            self.table.setItem(row, 1, QTableWidgetItem(size_text))

            # 修改时间
            modified_time = file_info.get('modified_time', '')
            self.table.setItem(row, 2, QTableWidgetItem(modified_time))

            # 文件类型
            file_type = file_info.get('type', 'file')
            type_text = '文件夹' if file_type == 'dir' else '文件'
            self.table.setItem(row, 3, QTableWidgetItem(type_text))

            # 路径
            path = file_info.get('path', '')
            self.table.setItem(row, 4, QTableWidgetItem(path))

    def format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"

    def on_selection_changed(self):
        """选中行变化"""
        pass

    def open_file_at_index(self, item):
        """双击打开文件"""
        row = item.row()
        file_info = self.table.item(row, 0).data(Qt.UserRole)

        # 只能打开文件，不能打开文件夹
        if file_info.get('type') == 'dir':
            QMessageBox.information(self, "提示", "请选择文件而不是文件夹")
            return

        self.open_file(file_info)

    def open_selected_file(self):
        """打开选中的文件"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        file_info = self.table.item(row, 0).data(Qt.UserRole)

        # 只能打开文件，不能打开文件夹
        if file_info.get('type') == 'dir':
            QMessageBox.information(self, "提示", "请选择文件而不是文件夹")
            return

        self.open_file(file_info)

    def open_file(self, file_info: Dict[str, Any]):
        """打开文件"""
        import os
        import subprocess
        import platform

        # 下载文件到临时目录
        temp_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp', 'PDF')
        os.makedirs(temp_dir, exist_ok=True)

        filename = file_info.get('name', '')
        local_path = os.path.join(temp_dir, filename)

        # 下载文件
        result = self.plugin.download_file(file_info.get('path', ''), local_path)

        if not result.is_success():
            QMessageBox.warning(self, "下载失败", f"下载文件失败: {result.message}")
            logger.error(f"下载文件失败: {result.message}")
            return

        # 获取主窗口并打开文件
        try:
            parent = self.parent_window
            while parent and not hasattr(parent, 'pdf_processor'):
                parent = parent.parent()

            if parent and hasattr(parent, 'pdf_processor'):
                success, message = parent.pdf_processor.open_pdf(local_path)
                if not success:
                    QMessageBox.warning(self, "打开失败", f"打开文件失败: {message}")
                    logger.error(f"打开文件失败: {message}")
                else:
                    logger.info(f"已打开文件: {local_path}")
            else:
                # 如果找不到主窗口，使用系统默认程序打开
                try:
                    if platform.system() == 'Windows':
                        os.startfile(local_path)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.call(['open', local_path])
                    else:  # Linux
                        subprocess.call(['xdg-open', local_path])
                    logger.info(f"已使用系统程序打开文件: {local_path}")
                except Exception as e:
                    QMessageBox.warning(self, "打开失败", f"打开文件失败: {str(e)}")
                    logger.error(f"打开文件失败: {e}")
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"打开文件失败: {str(e)}")
            logger.error(f"打开文件失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.terminate()
        super().closeEvent(event)

    def on_page_size_changed(self, value: str):
        """每页数量改变"""
        self.page_size = int(value)
        self.current_page = 1
        self.load_files()

    def on_prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_files()

    def on_next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_files()

    def update_pagination_controls(self):
        """更新分页控件状态"""
        if self.total_pages > 0:
            self.page_label.setText(f"第 {self.current_page} / {self.total_pages} 页 (共 {self.total_count} 条)")
        else:
            self.page_label.setText("第 0 页")

        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
