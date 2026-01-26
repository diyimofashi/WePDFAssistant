"""
文件列表面板 - 用于显示远程文件列表
支持在右侧停靠，可隐藏和显示
"""

from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
                             QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger('file_list_panel')


class LoadFilesThread(QThread):
    """加载文件列表的线程"""
    finished = pyqtSignal(object)

    def __init__(self, plugin, remote_path: str = ""):
        super().__init__()
        self.plugin = plugin
        self.remote_path = remote_path

    def run(self):
        """执行加载文件列表"""
        logger.info(f"LoadFilesThread run() 被调用，remote_path={self.remote_path!r}, type={type(self.remote_path)}")
        result = self.plugin.list_files(self.remote_path)
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
        self.refresh_button.clicked.connect(lambda: self.load_files())
        button_layout.addWidget(self.refresh_button)
        layout.addLayout(button_layout)

        # 文件列表表格
        self.table = QTableWidget()
        # 默认表头，将在load_current_plugin_info中更新
        self.default_headers = ["文件名", "文件大小", "修改时间", "文件类型", "路径"]
        self.update_table_headers(self.default_headers)
        
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

        self.setWidget(container)

    def update_table_headers(self, headers):
        """更新表格头部"""
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # 根据列数重新设置列宽调整模式
        for col_idx in range(len(headers)):
            if col_idx == 0:  # 第一列拉伸
                self.table.horizontalHeader().setSectionResizeMode(col_idx, QHeaderView.Stretch)
            else:  # 其他列根据内容调整
                self.table.horizontalHeader().setSectionResizeMode(col_idx, QHeaderView.ResizeToContents)

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
            
            # 获取插件特定的表头信息
            headers = self.get_headers_for_plugin(plugin)
            self.update_table_headers(headers)
            
            logger.info(f"成功加载下载插件: {plugin_name}")
        except Exception as e:
            logger.error(f"加载当前插件失败: {e}")

    def get_headers_for_plugin(self, plugin):
        """根据插件获取对应的表头信息，优先检查插件是否提供自定义表头"""
        # 检查插件是否提供自定义表头方法
        if hasattr(plugin, 'get_column_headers') and callable(getattr(plugin, 'get_column_headers')):
            try:
                return plugin.get_column_headers()
            except Exception as e:
                logger.warning(f"插件 {plugin.plugin_name} 的 get_column_headers 方法调用失败: {e}")
        
        # 检查插件是否定义了 COLUMN_HEADERS 属性
        if hasattr(plugin, 'COLUMN_HEADERS'):
            return plugin.COLUMN_HEADERS
        
        # 根据插件名称返回不同的默认表头
        if hasattr(plugin, 'plugin_name'):
            plugin_name = plugin.plugin_name.lower()
            if 'qcloud' in plugin_name or 'oss' in plugin_name or 'cos' in plugin_name:
                ***REMOVED***OSS插件的表头
                return ["文件名", "文件大小", "修改时间", "文件类型"]
        
        # 默认表头
        return self.default_headers

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
            
            # 更新表头
            headers = self.get_headers_for_plugin(plugin)
            self.update_table_headers(headers)
            
            logger.info(f"成功加载下载插件: {plugin_name}")

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
        
        # 更新表头
        headers = self.get_headers_for_plugin(plugin)
        self.update_table_headers(headers)

    def load_files(self, remote_path: str = ""):
        """加载文件列表"""
        logger.info(f"load_files() 被调用，remote_path={remote_path!r}, type={type(remote_path)}")
        if not self.plugin:
            QMessageBox.warning(self, "提示", "请先在下载设置中选择插件")
            return

        if self.load_thread and self.load_thread.isRunning():
            logger.warning("加载线程正在运行，忽略新的请求")
            return

        self.table.setRowCount(0)
        self.files_data = []
        self.progress_bar.setVisible(True)
        self.refresh_button.setEnabled(False)

        # 创建加载线程
        self.load_thread = LoadFilesThread(self.plugin, remote_path)
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
        self.populate_table()

    def populate_table(self):
        """填充表格数据"""
        # 确保表格列数与数据匹配
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        
        self.table.setRowCount(len(self.files_data))

        for row, file_info in enumerate(self.files_data):
            # 根据表头动态填充列
            for col_idx, header in enumerate(headers):
                if header == "文件名":
                    value = file_info.get('name', '')
                    name_item = QTableWidgetItem(value)
                    name_item.setData(Qt.UserRole, file_info)
                    self.table.setItem(row, col_idx, name_item)
                elif header == "文件大小":
                    size = file_info.get('size', 0)
                    # 确保大小是整数类型
                    try:
                        size = int(size)
                    except (ValueError, TypeError):
                        size = 0
                    size_text = self.format_size(size)
                    self.table.setItem(row, col_idx, QTableWidgetItem(size_text))
                elif header == "修改时间":
                    modified_time = file_info.get('modified_time', '')
                    self.table.setItem(row, col_idx, QTableWidgetItem(modified_time))
                elif header == "文件类型":
                    file_type = file_info.get('type', 'file')
                    type_text = '文件夹' if file_type == 'dir' else '文件'
                    self.table.setItem(row, col_idx, QTableWidgetItem(type_text))
                elif header == "路径":
                    path = file_info.get('path', '')
                    self.table.setItem(row, col_idx, QTableWidgetItem(path))
                else:
                    # 对于未知的表头，尝试从file_info中获取对应字段
                    field_name = self.convert_header_to_field(header)
                    value = file_info.get(field_name, '')
                    self.table.setItem(row, col_idx, QTableWidgetItem(str(value)))

    def convert_header_to_field(self, header: str) -> str:
        """将表头转换为对应的字段名"""
        header_map = {
            "文件名": "name",
            "文件大小": "size",
            "修改时间": "modified_time",
            "文件类型": "type",
            "路径": "path"
        }
        return header_map.get(header, header.lower())

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