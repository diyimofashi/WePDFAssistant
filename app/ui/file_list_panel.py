"""
文件列表面板 - 用于显示远程文件列表
支持在右侧停靠，可隐藏和显示
"""

import os
import traceback
import uuid
from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
                             QProgressBar, QComboBox, QDialog, QTreeWidget, QTreeWidgetItem,
                             QFileDialog, QCheckBox, QStyle, QStyleOptionButton,
                             QStyledItemDelegate, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QFont, QPainter, QPalette, QColor
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger('file_list_panel')


class CenterItemDelegate(QStyledItemDelegate):
    """单元格内容居中委托"""

    def paint(self, painter, option, index):
        """重写绘制方法，使单元格内容居中"""
        column = index.column()
        logger.debug(f"CenterItemDelegate.paint() 被调用, 列={column}, 行={index.row()}")
        # 设置文本居中对齐
        option.displayAlignment = Qt.AlignCenter
        logger.debug(f"已设置 displayAlignment = Qt.AlignCenter, 列={column}")
        # 绘制单元格内容
        super().paint(painter, option, index)


class CheckBoxHeaderView(QHeaderView):
    """带复选框的表头"""

    stateChanged = pyqtSignal(int)

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._checkbox = QCheckBox()
        self._checkbox.setTristate(True)
        self._checkbox.stateChanged.connect(self._on_checkbox_state_changed)
        self._checkbox.setStyleSheet("QCheckBox { margin: 4px; }")
        self._checkbox.setParent(self)  # checkbox的parent应该是header_view自身
        self._checkbox.hide()  # 初始隐藏
        self._is_programmatic_change = False  # 标记是否是程序化设置状态

        # 监听列宽变化
        self.sectionResized.connect(self._on_section_resized)

    def checkState(self):
        """获取复选框状态"""
        return self._checkbox.checkState()

    def setCheckState(self, state):
        """设置复选框状态"""
        self._is_programmatic_change = True
        self._checkbox.setCheckState(state)
        self._is_programmatic_change = False

    def _on_checkbox_state_changed(self, state):
        """复选框状态改变事件"""
        if not self._is_programmatic_change:
            # 如果不是程序化改变，则是用户点击
            # 将部分选中转换为全选
            if state == Qt.PartiallyChecked:
                self._checkbox.blockSignals(True)
                self._checkbox.setCheckState(Qt.Checked)
                self._checkbox.blockSignals(False)
                state = Qt.Checked
            self.stateChanged.emit(state)

    def _on_section_resized(self, logicalIndex, oldSize, newSize):
        """列宽改变时更新checkbox位置"""
        if logicalIndex == 0:
            self._update_checkbox_position()

    def resizeEvent(self, event):
        """调整大小时重新定位checkbox"""
        super().resizeEvent(event)
        self._update_checkbox_position()

    def showEvent(self, event):
        """显示时定位checkbox"""
        super().showEvent(event)
        self._update_checkbox_position()

    def _update_checkbox_position(self):
        """更新checkbox位置 - checkbox在第1列（logicalIndex=0）"""
        if self.count() > 1:
            # 获取第1列的位置和大小
            # sectionViewportPosition返回的是视口中的位置，已经考虑了滚动偏移
            x_pos = self.sectionViewportPosition(0)
            width = self.sectionSize(0)
            height = self.height()

            # 计算checkbox的中心位置
            center_x = x_pos + width // 2
            center_y = height // 2

            # 获取checkbox的实际尺寸
            checkbox_width = self._checkbox.width()
            checkbox_height = self._checkbox.height()

            logger.debug(f"列1位置: sectionViewportPosition(0)={x_pos}")
            logger.debug(f"列2位置: sectionViewportPosition(1)={self.sectionViewportPosition(1)}")
            logger.debug(f"Checkbox最终位置: x={center_x - checkbox_width // 2}, y={center_y - checkbox_height // 2}")

            # 移动checkbox到中心位置
            self._checkbox.move(
                center_x - checkbox_width // 2,
                center_y - checkbox_height // 2
            )
            self._checkbox.raise_()
            self._checkbox.show()
        else:
            self._checkbox.hide()

    def paintSection(self, painter, rect, logicalIndex):
        """重写绘制表头的方法"""
        if logicalIndex == 0:
            # 第1列不绘制文本（因为有checkbox控件）
            # 样式表会自动处理边框，这里只跳过文本
            return
        else:
            # 其他列正常绘制
            super().paintSection(painter, rect, logicalIndex)


class LoadFilesThread(QThread):
    """加载文件列表的线程"""
    finished = pyqtSignal(object)

    def __init__(self, plugin, remote_path: str = "", page: int = 1, page_size: int = 50):
        super().__init__()
        self.plugin = plugin
        self.remote_path = remote_path
        self.page = page
        self.page_size = page_size

    def run(self):
        """执行加载文件列表"""
        logger.info(f"LoadFilesThread run() 被调用，remote_path={self.remote_path!r}, type={type(self.remote_path)}, page={self.page}, page_size={self.page_size}")

        # 检查插件是否支持分页
        supports_pagination = hasattr(self.plugin, 'supports_pagination') and self.plugin.supports_pagination()

        if supports_pagination:
            # 使用分页参数调用
            result = self.plugin.list_files(self.remote_path, page=self.page, page_size=self.page_size)
        else:
            # 不使用分页
            result = self.plugin.list_files(self.remote_path)

        self.finished.emit(result)


class UploadProgressDialog(QDialog):
    """上传进度对话框"""
    cancelled = pyqtSignal()

    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle("上传文件")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        self.setFixedSize(400, 120)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 文件名标签
        self.filename_label = QLabel(f"正在上传: {filename}")
        self.filename_label.setWordWrap(True)
        layout.addWidget(self.filename_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(20)
        layout.addWidget(self.progress_bar)

        # 取消按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def cancel(self):
        """取消上传"""
        self.cancelled.emit()
        self.reject()

    def set_progress(self, value, maximum):
        """设置进度"""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
        self.progress_bar.setTextVisible(True)


class UploadThread(QThread):
    """上传文件的线程"""
    finished_signal = pyqtSignal(object, bool, str, str)
    error_signal = pyqtSignal(str, bool, str)

    def __init__(self, plugin, local_path, filename, remote_path, is_temp_file):
        super().__init__()
        self.plugin = plugin
        self.local_path = local_path
        self.filename = filename
        self.remote_path = remote_path
        self.is_temp_file = is_temp_file

    def run(self):
        try:
            logger.debug(f"上传线程开始，文件: {self.local_path}, 远程路径: {self.remote_path}")
            result = self.plugin.upload_file(self.local_path, self.remote_path, filename=self.filename)
            logger.debug(f"上传线程完成，结果: {result.is_success()}")
            self.finished_signal.emit(result, self.is_temp_file, self.local_path, self.filename)
        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            logger.error(traceback.format_exc())
            self.error_signal.emit(str(e), self.is_temp_file, self.local_path)


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
        self.upload_thread = None
        self.plugin_name = ""  # 添加插件名称属性

        # 列配置（支持对象字典格式）
        self._column_configs = []

        # 分页相关
        self.current_page = 1
        self.page_size = 50
        self.total_files = 0
        self.total_pages = 1

        # 目录相关
        self.current_remote_path = ""  # 当前所在远程路径
        self.path_history = []  # 路径历史，用于返回上一级

        self.setup_ui()
        self.load_current_plugin_info()

        # 初始化路径标签（在setup_ui之后调用）
        self.update_path_label()

    def setup_ui(self):
        """设置UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 按钮和路径区域（同一行）
        top_layout = QHBoxLayout()
        top_layout.setSpacing(2)  # 设置控件间距，减小间距

        # 目录选择按钮
        self.dir_button = QPushButton("📁 选择目录")
        self.dir_button.setMinimumWidth(90)  # 设置最小宽度
        self.dir_button.setMaximumWidth(100)  # 设置最大宽度
        self.dir_button.clicked.connect(self.show_directory_dialog)
        top_layout.addWidget(self.dir_button)

        # 当前路径标签容器
        self.path_container = QWidget()
        self.path_layout = QHBoxLayout(self.path_container)
        self.path_layout.setContentsMargins(8, 0, 8, 0)  # 左右各8px padding
        self.path_layout.setSpacing(2)
        self.path_layout.setAlignment(Qt.AlignLeft)  # 路径标签靠左对齐
        top_layout.addWidget(self.path_container)

        # 添加弹性空间，将右侧按钮推到右边
        top_layout.addStretch()

        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setMaximumWidth(80)
        self.refresh_button.clicked.connect(lambda: self.load_files())
        top_layout.addWidget(self.refresh_button)

        # 删除按钮（根据插件配置显示）
        self.delete_button = QPushButton("删除")
        self.delete_button.setMaximumWidth(80)
        self.delete_button.clicked.connect(self.delete_selected_file)
        self.delete_button.setVisible(False)
        top_layout.addWidget(self.delete_button)

        # 移动按钮
        self.move_button = QPushButton("移动")
        self.move_button.setMaximumWidth(80)
        self.move_button.clicked.connect(self.move_selected_files)
        top_layout.addWidget(self.move_button)

        # 复制按钮
        self.copy_button = QPushButton("复制")
        self.copy_button.setMaximumWidth(80)
        self.copy_button.clicked.connect(self.copy_selected_files)
        top_layout.addWidget(self.copy_button)

        # 下载按钮
        self.download_button = QPushButton("下载")
        self.download_button.setMaximumWidth(80)
        self.download_button.clicked.connect(self.download_selected_files)
        top_layout.addWidget(self.download_button)

        # 上传按钮（根据插件配置显示）
        self.upload_button = QPushButton("上传当前文档")
        self.upload_button.setMaximumWidth(120)
        self.upload_button.clicked.connect(self.upload_current_document)
        self.upload_button.setVisible(False)
        top_layout.addWidget(self.upload_button)

        # 添加顶部布局
        layout.addLayout(top_layout)

        # 文件列表表格
        self.table = QTableWidget()
        # 初始表头，将在load_current_plugin_info中从插件获取
        self.table.setColumnCount(0)
        self.table.setHorizontalHeaderLabels([])

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 允许多选
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁用编辑

        # 使用自定义表头（带复选框）
        self.header_view = CheckBoxHeaderView(Qt.Horizontal, self.table)
        self.table.setHorizontalHeader(self.header_view)
        self.header_view.stateChanged.connect(self.on_header_state_changed)
        self.header_view.setSectionsMovable(True)
        self.header_view.setDragEnabled(True)
        self.header_view.setDragDropMode(QAbstractItemView.InternalMove)
        self.header_view.setSectionsClickable(True)  # 允许点击表头
        self.header_view.setHighlightSections(True)  # 高亮点击的列

        # 隐藏垂直表头（默认的行号列）
        self.table.verticalHeader().setVisible(False)

        # 使用Qt样式表设置表格样式，第一行显示上边框
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 4px;
                border-top: 1px solid #a0a0a0;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QHeaderView::section {
                border-left: 1px solid transparent;
                padding: 4px;
                font-weight: bold;
            }
            /* 第一列（checkbox列）标题背景透明 */
            QHeaderView::section:first {
                background: transparent;
            }
        """)

        # 添加复选框列
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels([""])
        self.header_view.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 40)

        # 为第一列（checkbox列）设置居中委托
        self.table.setItemDelegateForColumn(0, CenterItemDelegate(self.table))

        # 双击打开文件
        self.table.itemDoubleClicked.connect(self.open_file_at_index)

        # 复选框状态改变
        self.table.itemChanged.connect(self.on_item_changed)

        layout.addWidget(self.table)

        # 分页控制区域
        self.pagination_layout = QHBoxLayout()
        self.pagination_label = QLabel("第 1 页 / 共 1 页")
        self.pagination_label.setStyleSheet("QLabel { padding: 4px; }")
        self.pagination_layout.addWidget(self.pagination_label)

        # 每页显示数量
        self.page_size_label = QLabel("每页:")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "20", "30", "50", "100", "200", "500"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.setFixedWidth(70)
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        self.pagination_layout.addWidget(self.page_size_label)
        self.pagination_layout.addWidget(self.page_size_combo)

        # 分页按钮
        self.pagination_layout.addStretch()

        self.first_page_btn = QPushButton("<<")
        self.first_page_btn.setToolTip("第一页")
        self.first_page_btn.setFixedSize(40, 25)
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        self.pagination_layout.addWidget(self.first_page_btn)

        self.prev_page_btn = QPushButton("<")
        self.prev_page_btn.setToolTip("上一页")
        self.prev_page_btn.setFixedSize(40, 25)
        self.prev_page_btn.clicked.connect(self.go_to_previous_page)
        self.pagination_layout.addWidget(self.prev_page_btn)

        self.next_page_btn = QPushButton(">")
        self.next_page_btn.setToolTip("下一页")
        self.next_page_btn.setFixedSize(40, 25)
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.pagination_layout.addWidget(self.next_page_btn)

        self.last_page_btn = QPushButton(">>")
        self.last_page_btn.setToolTip("最后一页")
        self.last_page_btn.setFixedSize(40, 25)
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        self.pagination_layout.addWidget(self.last_page_btn)

        layout.addLayout(self.pagination_layout)

        # 初始化时隐藏分页控件，根据插件是否支持分页来决定是否显示
        self.pagination_widgets = [
            self.pagination_label,
            self.page_size_label,
            self.page_size_combo,
            self.first_page_btn,
            self.prev_page_btn,
            self.next_page_btn,
            self.last_page_btn
        ]
        self.set_pagination_visible(False)

        # 加载进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.setWidget(container)

    def update_table_headers(self, headers):
        """更新表格头部，支持对象字典格式"""
        # 存储列配置信息
        self._column_configs = []

        # 第1列是复选框列，第2列是SN列
        full_headers = ["", "SN"]
        col_configs = []

        # 处理接口返回的列配置（支持字符串列表或对象字典列表）
        for header_config in headers:
            if isinstance(header_config, dict):
                # 对象字典格式
                title = header_config.get("title", "")
                full_headers.append(title)
                col_configs.append(header_config)
            else:
                # 简单字符串格式（向后兼容）
                full_headers.append(header_config)
                col_configs.append({
                    "title": str(header_config),
                    "field": self.convert_header_to_field(str(header_config))
                })

        self.table.setColumnCount(len(full_headers))
        self.table.setHorizontalHeaderLabels(full_headers)

        # 为第一、二列（checkbox和SN列）设置居中委托
        logger.debug(f"为第0列设置居中委托")
        self.table.setItemDelegateForColumn(0, CenterItemDelegate(self.table))
        logger.debug(f"为第1列设置居中委托")
        self.table.setItemDelegateForColumn(1, CenterItemDelegate(self.table))
        logger.debug(f"委托设置完成，第0列委托: {self.table.itemDelegateForColumn(0)}, 第1列委托: {self.table.itemDelegateForColumn(1)}")

        # 设置复选框列和SN列的表头居中对齐
        for col_idx in [0, 1]:
            header_item = self.table.horizontalHeaderItem(col_idx)
            if header_item:
                header_item.setTextAlignment(Qt.AlignCenter)
                logger.debug(f"第{col_idx}列表头设置居中对齐: {header_item.text()}")

        # 调整模式映射
        mode_map = {
            "fixed": QHeaderView.Fixed,
            "interactive": QHeaderView.Interactive,
            "stretch": QHeaderView.Stretch,
            "resize_to_contents": QHeaderView.ResizeToContents
        }

        # 根据列数重新设置列宽调整模式
        for col_idx in range(len(full_headers)):
            if col_idx == 0:
                # 第1列是复选框列，固定宽度40px
                self.header_view.setSectionResizeMode(col_idx, QHeaderView.Fixed)
                self.table.setColumnWidth(col_idx, 40)
                logger.debug(f"第0列（checkbox列）设置宽度=40px，模式=Fixed，实际宽度={self.table.columnWidth(col_idx)}")
            elif col_idx == 1:
                # 第2列SN列，固定宽度40px
                self.header_view.setSectionResizeMode(col_idx, QHeaderView.Fixed)
                self.table.setColumnWidth(col_idx, 40)
                logger.debug(f"第1列（SN列）设置宽度=40px，模式=Fixed，实际宽度={self.table.columnWidth(col_idx)}")
            elif col_idx >= 2:
                # 处理插件返回的列配置
                config_idx = col_idx - 2
                if config_idx < len(col_configs):
                    config = col_configs[config_idx]

                    # 设置列宽
                    if "width" in config:
                        self.table.setColumnWidth(col_idx, config["width"])

                    # 设置调整模式
                    resize_mode = config.get("resize_mode", "interactive")
                    self.header_view.setSectionResizeMode(col_idx, mode_map.get(resize_mode, QHeaderView.Interactive))

                    # 存储配置供后续使用
                    self._column_configs.append(config)

    def on_header_state_changed(self, state):
        """表头复选框状态改变"""
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(state)

    def on_item_changed(self, item):
        """表格项改变事件"""
        if item.column() == 0:  # 第1列是复选框列
            # 更新表头状态
            has_checked = False
            has_unchecked = False
            for row in range(self.table.rowCount()):
                checkbox_item = self.table.item(row, 0)
                if checkbox_item:
                    if checkbox_item.checkState() == Qt.Checked:
                        has_checked = True
                    else:
                        has_unchecked = True

            if has_checked and not has_unchecked:
                self.header_view.setCheckState(Qt.Checked)
            elif has_unchecked and not has_checked:
                self.header_view.setCheckState(Qt.Unchecked)
            else:
                self.header_view.setCheckState(Qt.PartiallyChecked)

    def load_current_plugin_info(self):
        """加载当前应用的下载插件信息（不加载文件列表）"""
        logger.info("load_current_plugin_info 开始执行")
        try:
            from app.config.storage_plugin_config import storage_config_manager
            from app.managers.storage_plugin_manager import storage_plugin_manager

            logger.info("获取当前插件名称...")
            plugin_name = storage_config_manager.get_current_plugin()
            if not plugin_name:
                logger.info("没有配置当前插件")
                return

            logger.info(f"当前插件名称: {plugin_name}")
            logger.info("获取插件实例...")
            plugin = storage_plugin_manager.get_plugin(plugin_name)
            if not plugin:
                logger.warning(f"插件实例不存在: {plugin_name}")
                return

            logger.info(f"插件实例获取成功: {plugin}")
            # 检查插件是否已初始化，如果没有则初始化
            if not plugin.is_initialized:
                logger.info("插件未初始化，开始初始化...")
                config = storage_config_manager.get_plugin_config(plugin_name)
                logger.info(f"插件配置: {config}")
                init_result = storage_plugin_manager.initialize_plugin(plugin_name, config)
                if not init_result.is_success():
                    logger.error(f"存储插件 {plugin_name} 初始化失败: {init_result.message}")
                    return
                logger.info("插件初始化成功")

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

            logger.info("准备获取表头信息...")
            # 获取插件特定的表头信息
            headers = self.get_headers_for_plugin(plugin)
            logger.info(f"获取到的表头: {headers}")
            logger.info("更新表格表头...")
            self.update_table_headers(headers)

            logger.info(f"成功加载下载插件: {plugin_name}")
        except Exception as e:
            logger.error(f"加载当前插件失败: {e}", exc_info=True)
            import traceback
            traceback.print_exc()

    def get_headers_for_plugin(self, plugin):
        """根据插件获取对应的表头信息"""
        logger.info(f"get_headers_for_plugin 被调用，plugin={plugin}")
        # 优先调用插件接口的 get_file_list_columns 方法
        if hasattr(plugin, 'get_file_list_columns') and callable(getattr(plugin, 'get_file_list_columns')):
            logger.info("插件有 get_file_list_columns 方法，准备调用")
            try:
                headers = plugin.get_file_list_columns()
                logger.info(f"成功获取表头: {headers}")
                return headers
            except Exception as e:
                logger.error(f"插件 {plugin.plugin_name} 的 get_file_list_columns 方法调用失败: {e}", exc_info=True)
                import traceback
                traceback.print_exc()

        # 默认表头
        logger.warning("使用默认表头")
        return ["文件名", "文件大小", "修改时间", "文件类型", "路径"]

    def load_current_plugin(self):
        """加载当前应用的下载插件并加载文件列表"""
        try:
            from app.config.storage_plugin_config import storage_config_manager
            from app.managers.storage_plugin_manager import storage_plugin_manager

            plugin_name = storage_config_manager.get_current_plugin()
            if not plugin_name:
                return

            plugin = storage_plugin_manager.get_plugin(plugin_name)
            if not plugin:
                return

            # 检查插件是否已初始化，如果没有则初始化
            if not plugin.is_initialized:
                config = storage_config_manager.get_plugin_config(plugin_name)
                init_result = storage_plugin_manager.initialize_plugin(plugin_name, config)
                if not init_result.is_success():
                    logger.error(f"存储插件 {plugin_name} 初始化失败: {init_result.message}")
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

            # 更新功能按钮的可见性
            self.update_feature_buttons()

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

    def set_pagination_visible(self, visible: bool):
        """设置分页控件的可见性"""
        # 设置所有子控件的可见性
        for widget in self.pagination_widgets:
            widget.setVisible(visible)

    def load_files(self, remote_path: str = None, page: int = None):
        """加载文件列表"""
        # 如果没有指定remote_path，使用当前路径
        if remote_path is None:
            remote_path = self.current_remote_path

        logger.info(f"load_files() 被调用，remote_path={remote_path!r}, type={type(remote_path)}, page={page}")

        if not self.plugin:
            QMessageBox.warning(self, "提示", "请先在云存储插件设置中选择插件")
            return

        if self.load_thread and self.load_thread.isRunning():
            logger.warning("加载线程正在运行，忽略新的请求")
            return

        self.table.setRowCount(0)
        self.files_data = []

        # 更新当前路径
        self.current_remote_path = remote_path
        self.update_path_label()

        # 确定当前页码
        if page is not None:
            self.current_page = page

        self.progress_bar.setVisible(True)
        self.refresh_button.setEnabled(False)

        # 检查插件是否支持分页
        supports_pagination = hasattr(self.plugin, 'supports_pagination') and self.plugin.supports_pagination()
        if supports_pagination:
            self.set_pagination_visible(True)
        else:
            self.set_pagination_visible(False)

        # 创建加载线程
        self.load_thread = LoadFilesThread(self.plugin, remote_path, self.current_page, self.page_size)
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

        # 获取文件列表数据
        self.files_data = result.data.get('files', [])

        # 获取分页信息（如果有）
        if 'total' in result.data:
            self.total_files = result.data.get('total', 0)
            self.total_pages = result.data.get('total_pages', 1)
            self.current_page = result.data.get('page', 1)
            self.page_size = result.data.get('page_size', self.page_size)

            # 更新分页标签
            self.update_pagination_label()
            self.update_pagination_buttons()
        else:
            # 没有分页信息，禁用分页控件
            self.set_pagination_visible(False)

        self.populate_table()

    def populate_table(self):
        """填充表格数据，支持对象字典格式的列配置"""
        self.table.setRowCount(len(self.files_data))

        for row, file_info in enumerate(self.files_data):
            # 第1列是复选框
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox.setCheckState(Qt.Unchecked)
            checkbox.setData(Qt.UserRole, file_info)  # 存储文件信息
            checkbox.setTextAlignment(Qt.AlignCenter)  # 居中对齐
            self.table.setItem(row, 0, checkbox)
            logger.debug(f"第{row}行，第0列（checkbox列）设置完成，检查状态: {checkbox.checkState()}")

            # 第2列是SN序号
            sn_item = QTableWidgetItem(str(row + 1))
            sn_item.setFlags(Qt.ItemIsEnabled)
            sn_item.setTextAlignment(Qt.AlignCenter)  # 居中对齐
            self.table.setItem(row, 1, sn_item)
            logger.debug(f"第{row}行，第1列（SN列）设置完成，文本: {sn_item.text()}, 对齐: {sn_item.textAlignment()}")

            # 从第3列开始填充数据（使用列配置）
            if hasattr(self, '_column_configs'):
                for config_idx, config in enumerate(self._column_configs):
                    col_idx = config_idx + 2  # 跳过复选框和SN列
                    field_name = config.get('field', '')

                    # 根据字段名获取值
                    if field_name == 'name':
                        value = file_info.get('name', '')
                        item = QTableWidgetItem(value)
                        item.setData(Qt.UserRole, file_info)
                        item.setToolTip(value)
                        self.table.setItem(row, col_idx, item)
                    elif field_name == 'size':
                        size = file_info.get('size', 0)
                        try:
                            size = int(size)
                        except (ValueError, TypeError):
                            size = 0
                        size_text = self.format_size(size)
                        item = QTableWidgetItem(size_text)
                        item.setToolTip(size_text)
                        self.table.setItem(row, col_idx, item)
                    elif field_name == 'modified_time':
                        value = file_info.get('modified_time', '')
                        item = QTableWidgetItem(value)
                        item.setToolTip(value)
                        self.table.setItem(row, col_idx, item)
                    elif field_name == 'type':
                        file_type = file_info.get('type', 'file')
                        type_text = '文件夹' if file_type == 'dir' else '文件'
                        item = QTableWidgetItem(type_text)
                        item.setToolTip(type_text)
                        self.table.setItem(row, col_idx, item)
                    elif field_name == 'path':
                        value = file_info.get('path', '')
                        item = QTableWidgetItem(value)
                        item.setToolTip(value)
                        self.table.setItem(row, col_idx, item)
                    else:
                        # 其他字段直接取值
                        value = file_info.get(field_name, '')
                        value_str = str(value)
                        item = QTableWidgetItem(value_str)
                        item.setToolTip(value_str)
                        self.table.setItem(row, col_idx, item)
            else:
                # 向后兼容：如果没有列配置，使用表头标题
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                for col_idx, header in enumerate(headers[2:], start=2):
                    field_name = self.convert_header_to_field(header)
                    value = file_info.get(field_name, '')

                    if header == "文件名":
                        item = QTableWidgetItem(value)
                        item.setData(Qt.UserRole, file_info)
                        item.setToolTip(value)
                        self.table.setItem(row, col_idx, item)
                    elif header == "文件大小":
                        size = file_info.get('size', 0)
                        try:
                            size = int(size)
                        except (ValueError, TypeError):
                            size = 0
                        size_text = self.format_size(size)
                        item = QTableWidgetItem(size_text)
                        item.setToolTip(size_text)
                        self.table.setItem(row, col_idx, item)
                    elif header == "修改时间":
                        item = QTableWidgetItem(value)
                        item.setToolTip(value)
                        self.table.setItem(row, col_idx, item)
                    elif header == "文件类型":
                        file_type = file_info.get('type', 'file')
                        type_text = '文件夹' if file_type == 'dir' else '文件'
                        item = QTableWidgetItem(type_text)
                        item.setToolTip(type_text)
                        self.table.setItem(row, col_idx, item)
                    elif header == "路径":
                        item = QTableWidgetItem(value)
                        item.setToolTip(value)
                        self.table.setItem(row, col_idx, item)
                    else:
                        value_str = str(value)
                        item = QTableWidgetItem(value_str)
                        item.setToolTip(value_str)
                        self.table.setItem(row, col_idx, item)

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
        """双击打开文件或进入目录"""
        row = item.row()
        # 文件信息在复选框列（第0列）存储
        checkbox_item = self.table.item(row, 0)
        if not checkbox_item:
            return
        file_info = checkbox_item.data(Qt.UserRole)

        # 如果是文件夹，进入该目录
        if file_info.get('type') == 'dir':
            dir_path = file_info.get('path', '')
            self.current_remote_path = dir_path
            self.update_path_label()
            self.load_files(self.current_remote_path)
            return

        self.open_file(file_info)

    def open_selected_file(self):
        """打开选中的文件"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        # 文件信息在复选框列（第0列）存储
        checkbox_item = self.table.item(row, 0)
        if not checkbox_item:
            return
        file_info = checkbox_item.data(Qt.UserRole)

        # 只能打开文件，不能打开文件夹
        if file_info.get('type') == 'dir':
            QMessageBox.information(self, "提示", "请选择文件而不是文件夹")
            return

        self.open_file(file_info)

    def open_file(self, file_info: Dict[str, Any]):
        """打开文件"""
        import os

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
                QMessageBox.warning(self, "打开失败", "未找到主窗口，无法打开文件")
                logger.error("未找到主窗口，无法打开文件")
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"打开文件失败: {str(e)}")
            logger.error(f"打开文件失败: {e}")

    def get_selected_files(self):
        """获取所有勾选的文件信息"""
        files = []
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.Checked:
                file_info = checkbox_item.data(Qt.UserRole)
                if file_info:
                    files.append(file_info)
        return files

    def move_selected_files(self):
        """移动选中的文件"""
        files = self.get_selected_files()
        if not files:
            QMessageBox.information(self, "提示", "请先选择要移动的文件")
            return

        # 显示目录选择对话框
        dialog = DirectoryDialog(self.plugin, self.current_remote_path, self)
        if dialog.exec_() == QDialog.Accepted:
            target_path = dialog.selected_path
            if target_path == self.current_remote_path:
                QMessageBox.information(self, "提示", "目标目录与当前目录相同")
                return

            # 确认移动
            file_names = "\n".join([f.get('name', '') for f in files[:5]])
            if len(files) > 5:
                file_names += f"\n... 还有 {len(files) - 5} 个文件"

            reply = QMessageBox.question(
                self,
                "确认移动",
                f"确定要移动 {len(files)} 个文件到 '{target_path}' 吗？\n\n{file_names}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    success_count = 0
                    failed_files = []

                    for file_info in files:
                        # 复制到目标目录
                        old_path = file_info.get('path', '')
                        new_filename = file_info.get('name', '')
                        if target_path:
                            new_path = f"{target_path.rstrip('/')}/{new_filename}"
                        else:
                            new_path = new_filename

                        # 先复制
                        copy_result = self.plugin.copy_file(old_path, new_path)
                        if copy_result.is_success():
                            # 复制成功后删除原文件
                            delete_result = self.plugin.delete_file(old_path)
                            if delete_result.is_success():
                                success_count += 1
                            else:
                                failed_files.append(file_info.get('name', ''))
                                # 复制成功但删除失败，需要回滚
                                self.plugin.delete_file(new_path)
                        else:
                            failed_files.append(file_info.get('name', ''))

                    if success_count > 0:
                        QMessageBox.information(self, "移动成功", f"成功移动 {success_count} 个文件")
                        self.load_files()
                    if failed_files:
                        QMessageBox.warning(self, "部分失败", f"以下文件移动失败:\n" + "\n".join(failed_files[:10]))

                except Exception as e:
                    QMessageBox.warning(self, "移动失败", f"移动文件时发生错误: {str(e)}")
                    logger.error(f"移动文件失败: {e}")

    def copy_selected_files(self):
        """复制选中的文件"""
        files = self.get_selected_files()
        if not files:
            QMessageBox.information(self, "提示", "请先选择要复制的文件")
            return

        # 显示目录选择对话框
        dialog = DirectoryDialog(self.plugin, self.current_remote_path, self)
        if dialog.exec_() == QDialog.Accepted:
            target_path = dialog.selected_path

            try:
                success_count = 0
                failed_files = []

                for file_info in files:
                    old_path = file_info.get('path', '')
                    new_filename = file_info.get('name', '')
                    if target_path:
                        new_path = f"{target_path.rstrip('/')}/{new_filename}"
                    else:
                        new_path = new_filename

                    result = self.plugin.copy_file(old_path, new_path)
                    if result.is_success():
                        success_count += 1
                    else:
                        failed_files.append(file_info.get('name', ''))

                if success_count > 0:
                    QMessageBox.information(self, "复制成功", f"成功复制 {success_count} 个文件")
                    if target_path != self.current_remote_path:
                        self.load_files()
                if failed_files:
                    QMessageBox.warning(self, "部分失败", f"以下文件复制失败:\n" + "\n".join(failed_files[:10]))

            except Exception as e:
                QMessageBox.warning(self, "复制失败", f"复制文件时发生错误: {str(e)}")
                logger.error(f"复制文件失败: {e}")

    def download_selected_files(self):
        """下载选中的文件"""
        files = self.get_selected_files()
        if not files:
            QMessageBox.information(self, "提示", "请先选择要下载的文件")
            return

        # 选择保存目录
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not save_dir:
            return

        try:
            success_count = 0
            failed_files = []

            for file_info in files:
                remote_path = file_info.get('path', '')
                filename = file_info.get('name', '')
                local_path = os.path.join(save_dir, filename)

                result = self.plugin.download_file(remote_path, local_path)
                if result.is_success():
                    success_count += 1
                else:
                    failed_files.append(filename)

            if success_count > 0:
                QMessageBox.information(self, "下载成功", f"成功下载 {success_count} 个文件")
            if failed_files:
                QMessageBox.warning(self, "部分失败", f"以下文件下载失败:\n" + "\n".join(failed_files[:10]))

        except Exception as e:
            QMessageBox.warning(self, "下载失败", f"下载文件时发生错误: {str(e)}")
            logger.error(f"下载文件失败: {e}")

    def delete_selected_file(self):
        """删除选中的文件"""
        files = self.get_selected_files()
        if not files:
            QMessageBox.information(self, "提示", "请先选择要删除的文件")
            return

        # 检查是否包含目录
        has_dir = any(f.get('type') == 'dir' for f in files)

        # 确认删除
        file_names = "\n".join([f.get('name', '') for f in files[:5]])
        if len(files) > 5:
            file_names += f"\n... 还有 {len(files) - 5} 个文件"

        if has_dir:
            message = f"确定要删除 {len(files)} 个文件或目录吗？\n\n{file_names}\n\n此操作不可恢复！"
        else:
            message = f"确定要删除 {len(files)} 个文件吗？\n\n{file_names}\n\n此操作不可恢复！"

        reply = QMessageBox.question(
            self,
            "确认删除",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                success_count = 0
                failed_files = []

                for file_info in files:
                    file_path = file_info.get('path', '')
                    file_type = file_info.get('type', 'unknown')
                    logger.info(f"准备删除: {file_path} (类型: {file_type})")

                    # 根据类型调用不同的删除方法
                    if file_type == 'dir':
                        if hasattr(self.plugin, 'delete_directory'):
                            result = self.plugin.delete_directory(file_path)
                        else:
                            result = self.plugin.delete_file(file_path)
                    else:
                        result = self.plugin.delete_file(file_path)

                    if result.is_success():
                        success_count += 1
                        logger.info(f"删除成功: {file_path}")
                    else:
                        failed_files.append(file_info.get('name', ''))
                        logger.error(f"删除失败: {file_path}, 原因: {result.message}")

                if success_count > 0:
                    QMessageBox.information(self, "删除成功", f"成功删除 {success_count} 个文件")
                    self.load_files()
                if failed_files:
                    QMessageBox.warning(self, "部分失败", f"以下文件删除失败:\n" + "\n".join(failed_files[:10]))

            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"删除文件时发生错误: {str(e)}")
                logger.error(f"删除文件失败: {e}", exc_info=True)

    def upload_current_document(self):
        """上传当前打开的文档"""
        import tempfile

        # 获取主窗口
        parent = self.parent_window
        while parent and not hasattr(parent, 'pdf_processor'):
            parent = parent.parent()

        if not parent or not hasattr(parent, 'pdf_processor'):
            QMessageBox.warning(self, "提示", "无法获取当前文档信息")
            return

        # 获取当前文档路径
        pdf_processor = parent.pdf_processor
        local_path = None
        filename = None
        is_temp_file = False

        # 检查是否有打开的文档（PDF或图片）
        if not hasattr(pdf_processor, 'fitz_document') or not pdf_processor.fitz_document:
            QMessageBox.warning(self, "提示", "当前没有打开的文档")
            return

        # 获取文件路径
        if hasattr(pdf_processor, 'current_file') and pdf_processor.current_file:
            # PDF文件或已保存的文件
            local_path = pdf_processor.current_file
            filename = os.path.basename(local_path)
        elif hasattr(pdf_processor, 'current_doc_path') and pdf_processor.current_doc_path:
            # 当前文档路径（临时保存的文件）
            local_path = pdf_processor.current_doc_path
            filename = os.path.basename(local_path)
        else:
            # 图片文件，创建临时文件并保存
            try:
                # 生成临时文件名
                temp_dir = tempfile.gettempdir()
                if hasattr(pdf_processor, 'original_image_path') and pdf_processor.original_image_path:
                    base_name = os.path.splitext(os.path.basename(pdf_processor.original_image_path))[0]
                else:
                    base_name = f"image_{uuid.uuid4().hex[:8]}"
                
                temp_filename = f"{base_name}.pdf"
                temp_path = os.path.join(temp_dir, temp_filename)
                
                # 保存到临时文件
                pdf_processor.fitz_document.save(temp_path)
                local_path = temp_path
                filename = temp_filename
                is_temp_file = True
                
                logger.debug(f"创建临时文件: {temp_path}")
                logger.debug("准备调用进度条显示")
            except Exception as e:
                QMessageBox.warning(self, "提示", f"创建临时文件失败: {str(e)}")
                logger.error(f"创建临时文件失败: {e}")
                return

        # 再次检查是否有文件路径
        if not local_path or not filename:
            QMessageBox.warning(self, "提示", "当前没有打开的文档")
            return

        # 显示上传进度对话框
        logger.debug("显示上传进度对话框")
        self.upload_dialog = UploadProgressDialog(filename, self)
        self.upload_dialog.show()

        # 在后台线程中执行上传，构建完整的目标路径
        logger.debug("准备启动上传线程")
        current_dir = self.current_remote_path or ""
        if current_dir:
            remote_path = f"{current_dir.rstrip('/')}/{filename}"
        else:
            remote_path = filename

        self.upload_thread = UploadThread(self.plugin, local_path, filename, remote_path, is_temp_file)
        self.upload_thread.finished_signal.connect(lambda result, is_tf, lp, fn: self._on_upload_complete(result, is_tf, lp, fn))
        self.upload_thread.error_signal.connect(lambda err_msg, is_tf, lp: self._on_upload_error(err_msg, is_tf, lp))
        self.upload_thread.start()
        logger.debug(f"上传线程已启动，完整远程路径: {remote_path}")

    def _on_upload_complete(self, result, is_temp_file, local_path, filename):
        """上传完成回调"""
        logger.info(f"_on_upload_complete 被调用，result.is_success()={result.is_success()}, filename={filename}")

        # 关闭进度对话框
        if hasattr(self, 'upload_dialog') and self.upload_dialog:
            self.upload_dialog.close()

        # 删除临时文件（先删除，避免影响后续操作）
        if is_temp_file and local_path and os.path.exists(local_path):
            try:
                os.unlink(local_path)
                logger.debug(f"已删除临时文件: {local_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {e}")

        if result.is_success():
            logger.info(f"上传成功: {result.message}")
            # 显示成功消息
            QMessageBox.information(self, "上传成功", f"✅ 文件上传成功: {filename}")
            # 重新加载文件列表
            self.load_files()
        else:
            logger.error(f"上传失败: {result.message}")
            QMessageBox.warning(self, "上传失败", result.message)

    def _on_upload_error(self, error_message, is_temp_file, local_path):
        """上传错误回调"""
        # 删除临时文件
        if is_temp_file and local_path and os.path.exists(local_path):
            try:
                os.unlink(local_path)
                logger.debug(f"已删除临时文件: {local_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {e}")

        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)

        QMessageBox.warning(self, "上传失败", f"上传文件时发生错误: {error_message}")

    def _show_upload_success_message(self, filename):
        """显示上传成功消息"""
        logger.debug(f"显示上传成功消息: {filename}")
        QMessageBox.information(self, "上传成功", f"✅ 文件上传成功: {filename}")

    def update_feature_buttons(self):
        """根据插件配置更新功能按钮的可见性"""
        if not self.plugin:
            return

        # 获取插件配置
        plugin_config = {}
        if hasattr(self.plugin, 'config'):
            plugin_config = self.plugin.config

        # 检查是否启用删除功能
        enable_delete = plugin_config.get('enable_delete', False)
        self.delete_button.setVisible(enable_delete)
        if enable_delete:
            logger.info("删除功能已启用")
        else:
            logger.info("删除功能已禁用")

        # 检查是否启用上传功能
        enable_upload = plugin_config.get('enable_upload', False)
        self.upload_button.setVisible(enable_upload)
        if enable_upload:
            logger.info("上传功能已启用")
        else:
            logger.info("上传功能已禁用")

        # 移动、复制、下载功能默认启用
        logger.info("移动、复制、下载功能已启用")

    def update_pagination_label(self):
        """更新分页标签"""
        self.pagination_label.setText(f"第 {self.current_page} 页 / 共 {self.total_pages} 页 (总计 {self.total_files} 个文件)")

    def update_pagination_buttons(self):
        """更新分页按钮状态"""
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)

    def go_to_first_page(self):
        """跳转到第一页"""
        if self.current_page != 1:
            self.load_files(page=1)

    def go_to_previous_page(self):
        """跳转到上一页"""
        if self.current_page > 1:
            self.load_files(page=self.current_page - 1)

    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_page < self.total_pages:
            self.load_files(page=self.current_page + 1)

    def go_to_last_page(self):
        """跳转到最后一页"""
        if self.current_page != self.total_pages:
            self.load_files(page=self.total_pages)

    def on_page_size_changed(self, size_text: str):
        """每页显示数量改变"""
        try:
            new_page_size = int(size_text)
            if new_page_size != self.page_size:
                self.page_size = new_page_size
                # 重新计算总页数
                self.total_pages = (self.total_files + self.page_size - 1) // self.page_size if self.total_files > 0 else 1
                # 跳转到第一页
                self.load_files(page=1)
        except ValueError:
            logger.error(f"无效的页大小: {size_text}")

    def closeEvent(self, event):
        """关闭事件"""
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.terminate()
        super().closeEvent(event)

    def show_directory_dialog(self):
        """显示目录选择对话框"""
        if not self.plugin:
            QMessageBox.warning(self, "提示", "请先在云存储插件设置中选择插件")
            return

        dialog = DirectoryDialog(self.plugin, self.current_remote_path, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_path = dialog.get_selected_path()
            if selected_path != self.current_remote_path:
                self.current_remote_path = selected_path
                self.update_path_label()
                self.load_files(self.current_remote_path)

    def update_path_label(self):
        """更新路径标签，创建可点击的路径段"""
        # 清空旧的路径标签（包括所有 item）
        for i in reversed(range(self.path_layout.count())):
            item = self.path_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                # 移除 spacer item
                self.path_layout.removeItem(item)

        # 添加根目录 "./"
        root_label = QLabel("./")
        root_label.setStyleSheet("color: #1890ff; font-size: 12px; text-decoration: underline; cursor: pointer;")
        root_label.mousePressEvent = lambda e: self.navigate_to_path("")
        root_label.setToolTip("点击返回根目录")
        self.path_layout.addWidget(root_label)

        if self.current_remote_path:
            # 分割路径并添加每个路径段
            parts = self.current_remote_path.split('/')
            path_so_far = ""

            for part in parts:
                if not part:
                    continue

                # 添加斜杠分隔符（除了第一个路径段）
                if path_so_far:
                    sep_label = QLabel("/")
                    sep_label.setStyleSheet("color: #666; font-size: 12px;")
                    self.path_layout.addWidget(sep_label)

                # 构建完整路径
                path_so_far = f"{path_so_far}/{part}" if path_so_far else part

                # 创建可点击的路径段
                path_label = QLabel(part)
                path_label.setStyleSheet("color: #1890ff; font-size: 12px; text-decoration: underline; cursor: pointer;")
                path_label.mousePressEvent = lambda e, path=path_so_far: self.navigate_to_path(path)
                path_label.setToolTip(f"点击进入: {part}")
                self.path_layout.addWidget(path_label)

    def navigate_to_path(self, path):
        """导航到指定路径"""
        if path != self.current_remote_path:
            self.current_remote_path = path
            self.update_path_label()
            self.load_files(self.current_remote_path)


class DirectoryDialog(QDialog):
    """目录选择对话框"""

    def __init__(self, plugin, current_path, parent=None):
        super().__init__(parent)

        self.plugin = plugin
        self.current_path = current_path
        self.selected_path = current_path
        self.setWindowTitle("选择目录")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        self.setFixedSize(600, 500)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 当前路径显示容器
        self.path_container = QWidget()
        self.path_layout = QHBoxLayout(self.path_container)
        self.path_layout.setContentsMargins(0, 0, 0, 0)
        self.path_layout.setSpacing(2)

        # 添加标题
        title_label = QLabel("当前路径: ")
        title_label.setStyleSheet("color: #333; font-weight: bold; padding: 5px;")
        self.path_layout.addWidget(title_label)

        # 更新路径标签
        self.update_path_label()

        # 添加弹性空间
        self.path_layout.addStretch()
        layout.addWidget(self.path_container)

        # 目录树
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["目录名称"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree)

        # 按钮
        button_layout = QHBoxLayout()

        self.back_button = QPushButton("返回上一级")
        self.back_button.clicked.connect(self.go_back)
        button_layout.addWidget(self.back_button)

        button_layout.addStretch()

        self.ok_button = QPushButton("确定")
        self.ok_button.setMinimumWidth(100)
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 加载目录树
        self.load_directory_tree()

    def load_directory_tree(self):
        """加载目录树"""
        try:
            # 使用插件的 list_directories 方法获取目录列表
            result = self.plugin.list_directories(self.current_path)
            if not result.is_success():
                QMessageBox.warning(self, "错误", f"加载目录失败: {result.message}")
                return

            dirs = result.data.get('directories', [])
            self.tree.clear()

            for dir_info in dirs:
                item = QTreeWidgetItem([dir_info.get('name', '')])
                item.setData(0, Qt.UserRole, dir_info)
                item.setIcon(0, self.style().standardIcon(self.style().SP_DirIcon))
                self.tree.addTopLevelItem(item)

            # 如果有子目录，添加展开标记
            self.tree.expandAll()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载目录时发生错误: {str(e)}")

    def on_item_clicked(self, item, column):
        """点击目录项"""
        dir_info = item.data(0, Qt.UserRole)
        if dir_info:
            path = dir_info.get('path', '')
            self.selected_path = path

    def on_item_double_clicked(self, item, column):
        """双击进入目录"""
        dir_info = item.data(0, Qt.UserRole)
        if dir_info:
            path = dir_info.get('path', '')
            self.navigate_to_path(path)

    def go_back(self):
        """返回上一级目录"""
        if self.current_path:
            # 获取父目录
            parts = self.current_path.split('/')
            parent_path = '/'.join(parts[:-1]) if len(parts) > 1 else ''
            self.navigate_to_path(parent_path)

    def update_path_label(self):
        """更新路径标签，创建可点击的路径段"""
        # 清空旧的路径标签（保留第一个标题标签）
        for i in reversed(range(self.path_layout.count())):
            item = self.path_layout.itemAt(i)
            widget = item.widget()
            if widget:
                # 保留标题标签
                if hasattr(widget, 'text') and widget.text() == "当前路径: ":
                    continue
                widget.deleteLater()

        # 添加根目录 "/"
        root_label = QLabel("/")
        root_label.setStyleSheet("color: #1890ff; font-size: 12px; text-decoration: underline; cursor: pointer;")
        root_label.mousePressEvent = lambda e: self.navigate_to_path("")
        root_label.setToolTip("点击返回根目录")
        self.path_layout.addWidget(root_label)

        if self.current_path:
            # 分割路径并添加每个路径段
            parts = self.current_path.split('/')
            path_so_far = ""

            for part in parts:
                if not part:
                    continue

                # 添加分隔符
                sep_label = QLabel("/")
                sep_label.setStyleSheet("color: #666; font-size: 12px;")
                self.path_layout.addWidget(sep_label)

                # 构建完整路径
                path_so_far = f"{path_so_far}/{part}" if path_so_far else part

                # 创建可点击的路径段
                path_label = QLabel(part)
                path_label.setStyleSheet("color: #1890ff; font-size: 12px; text-decoration: underline; cursor: pointer;")
                path_label.mousePressEvent = lambda e, path=path_so_far: self.navigate_to_path(path)
                path_label.setToolTip(f"点击进入: {part}")
                self.path_layout.addWidget(path_label)

    def navigate_to_path(self, path):
        """导航到指定路径"""
        if path != self.current_path:
            self.current_path = path
            self.selected_path = path
            self.update_path_label()
            self.load_directory_tree()

    def get_selected_path(self):
        """获取选中的路径"""
        return self.selected_path