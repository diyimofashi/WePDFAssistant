"""
下载文件列表对话框
用于展示远程文件列表并支持打开文件
"""

import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QWidget, QProgressBar,
                             QSplitter, QAbstractItemView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from typing import List, Dict, Any
from app.managers.download_plugin_manager import download_plugin_manager
from app.config.download_plugin_config import download_config_manager
from app.utils.logger import get_logger

logger = get_logger('download_file_list_dialog')


class LoadFilesThread(QThread):
    """加载文件列表的线程"""
    finished = pyqtSignal(object, object)

    def __init__(self, plugin, remote_path: str = ""):
        super().__init__()
        self.plugin = plugin
        self.remote_path = remote_path

    def run(self):
        """执行加载文件列表"""
        result = self.plugin.list_files(self.remote_path)
        self.finished.emit(result, self.plugin_name)


class DownloadFileListDialog(QDialog):
    """下载文件列表对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("远程文件列表")
        self.resize(900, 600)
        self.setMinimumSize(700, 500)
        self.setModal(True)

        # 获取当前插件
        self.plugin_name = download_config_manager.get_current_plugin()
        self.plugin = download_plugin_manager.get_plugin(self.plugin_name)

        # 文件列表数据
        self.files_data = []

        # 加载线程
        self.load_thread = None

        self.setup_ui()
        self.load_files()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 顶部标题栏
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # 插件信息
        plugin_info = getattr(self.plugin, 'PluginInfo', {})
        local_options = plugin_info.get('local_options', {})
        plugin_title = local_options.get('title', self.plugin_name)
        title_label = QLabel(f"插件: {plugin_title}")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_label.setFont(title_font)

        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.load_files)
        self.refresh_button.setMinimumWidth(80)

        # 打开按钮
        self.open_button = QPushButton("打开")
        self.open_button.clicked.connect(self.open_selected_file)
        self.open_button.setMinimumWidth(80)
        self.open_button.setEnabled(False)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.open_button)

        layout.addWidget(header_widget)

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

        # 选中行变化
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        layout.addWidget(self.table)

        # 加载进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        # 底部按钮
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        self.close_button.setMinimumWidth(80)

        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        layout.addWidget(button_widget)

    def load_files(self):
        """加载文件列表"""
        if self.load_thread and self.load_thread.isRunning():
            return

        self.table.setRowCount(0)
        self.files_data = []
        self.open_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.refresh_button.setEnabled(False)

        # 创建加载线程
        self.load_thread = LoadFilesThread(self.plugin, "")
        self.load_thread.plugin_name = self.plugin_name
        self.load_thread.finished.connect(self.on_files_loaded)
        self.load_thread.start()

    def on_files_loaded(self, result: object, plugin_name: object):
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
        selected = self.table.selectedItems()
        self.open_button.setEnabled(len(selected) > 0)

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
            parent = self.parent()
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
                import subprocess
                import platform
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
