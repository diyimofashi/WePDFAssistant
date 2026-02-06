"""文件历史记录停靠面板模块"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QMenu, QFrame, QSplitter, QAbstractItemView,
    QToolBar, QToolButton, QStyle, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSize, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QImage, QFont
import os
import fitz  # PyMuPDF用于生成缩略图
from datetime import datetime
from app.utils.logger import get_logger
from app.core.performance.cache_manager import DiskCache

logger = get_logger('history_panel')


class ThumbnailGenerator(QThread):
    """缩略图生成线程"""

    thumbnail_ready = pyqtSignal(str, QPixmap)  # file_path, thumbnail
    finished = pyqtSignal()  # 生成完成

    def __init__(self, file_paths, disk_cache):
        super().__init__()
        self.file_paths = file_paths
        self.disk_cache = disk_cache
        self._is_running = True

    def run(self):
        """在后台生成缩略图"""
        import time
        total_start = time.time()
        logger.info(f"缩略图生成线程开始，共 {len(self.file_paths)} 个文件")

        for idx, file_path in enumerate(self.file_paths):
            if not self._is_running:
                break

            file_start = time.time()
            logger.debug(f"[{idx+1}/{len(self.file_paths)}] 开始处理文件: {file_path}")

            # 先检查磁盘缓存
            cache_key = f"history_thumb_{file_path}"
            cache_start = time.time()
            cached_thumbnail = self.disk_cache.get(cache_key)
            cache_elapsed = (time.time() - cache_start) * 1000

            if cached_thumbnail:
                logger.debug(f"从缓存加载缩略图: {file_path}, 耗时 {cache_elapsed:.0f}ms")
                self.thumbnail_ready.emit(file_path, cached_thumbnail)
                continue

            logger.debug(f"缓存未命中，需要生成缩略图: {file_path}")
            if os.path.exists(file_path):
                try:
                    # 生成第一页缩略图
                    gen_start = time.time()
                    pixmap = self._generate_thumbnail(file_path)
                    gen_elapsed = (time.time() - gen_start) * 1000

                    if pixmap:
                        # 保存到磁盘缓存
                        save_start = time.time()
                        self.disk_cache.put(cache_key, pixmap)
                        save_elapsed = (time.time() - save_start) * 1000
                        logger.debug(f"生成缩略图完成: {file_path}, 生成耗时 {gen_elapsed:.0f}ms, 保存耗时 {save_elapsed:.0f}ms")
                        self.thumbnail_ready.emit(file_path, pixmap)
                except Exception as e:
                    logger.error(f"生成缩略图失败 {file_path}: {e}")

            file_elapsed = (time.time() - file_start) * 1000
            logger.debug(f"[{idx+1}/{len(self.file_paths)}] 文件处理完成: {file_path}, 总耗时 {file_elapsed:.0f}ms")

        total_elapsed = time.time() - total_start
        logger.info(f"缩略图生成线程完成，总耗时 {total_elapsed:.2f}秒")

        # 发送完成信号
        self.finished.emit()

    def _generate_thumbnail(self, file_path):
        """生成PDF文件第一页缩略图"""
        import time
        step_times = {}
        start = time.time()

        try:
            step_times['open'] = (time.time() - start) * 1000
            doc = fitz.open(file_path)
            step_times['after_open'] = (time.time() - start) * 1000

            if len(doc) > 0:
                step_times['get_page'] = (time.time() - start) * 1000
                page = doc[0]
                # 缩放因子，使缩略图清晰
                zoom = 2.0
                matrix = fitz.Matrix(zoom, zoom)
                step_times['before_pixmap'] = (time.time() - start) * 1000
                pix = page.get_pixmap(matrix=matrix)
                step_times['after_pixmap'] = (time.time() - start) * 1000

                # 转换为QPixmap
                step_times['before_qimage'] = (time.time() - start) * 1000
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(img)
                step_times['after_qimage'] = (time.time() - start) * 1000

                # 缩放到目标尺寸
                target_size = QSize(180, 240)
                step_times['before_scale'] = (time.time() - start) * 1000
                scaled = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                step_times['after_scale'] = (time.time() - start) * 1000

                logger.debug(f"生成缩略图步骤耗时: open={step_times['open']:.0f}ms, get_page={step_times.get('get_page', 0):.0f}ms, before_pixmap={step_times.get('before_pixmap', 0):.0f}ms, after_pixmap={step_times.get('after_pixmap', 0):.0f}ms, before_qimage={step_times.get('before_qimage', 0):.0f}ms, after_qimage={step_times.get('after_qimage', 0):.0f}ms, before_scale={step_times.get('before_scale', 0):.0f}ms, after_scale={step_times.get('after_scale', 0):.0f}ms")
                return scaled
            else:
                logger.warning(f"PDF文件为空: {file_path}")
        except Exception as e:
            logger.error(f"生成缩略图异常 {file_path}: {e}")
        return None

    def stop(self):
        """停止生成（非阻塞）"""
        logger.debug("ThumbnailGenerator.stop: 设置停止标志")
        self._is_running = False
        # 不调用 wait()，避免阻塞主线程
        # 线程会在下一次迭代时检测到 _is_running 为 False 并退出


class HistoryPanel(QDockWidget):
    """文件历史记录停靠面板 - 左右分栏布局"""

    # 自定义信号
    file_opened = pyqtSignal(str)  # 文件被打开时发出信号
    refresh_needed = pyqtSignal()  # 需要刷新时发出信号

    def __init__(self, parent_window, history_manager):
        logger.debug("HistoryPanel.__init__ 开始执行")
        super().__init__("历史记录", parent_window)
        self.parent = parent_window
        self.history_manager = history_manager
        self.thumbnail_cache = {}
        self.thumbnail_thread = None
        self.current_category = None
        self._is_generating = False  # 缩略图生成标志

        # 初始化磁盘缓存
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(project_root, "cache", "history_thumbnails")
        self.disk_cache = DiskCache(cache_dir, max_size_mb=100)
        logger.debug(f"历史缩略图磁盘缓存目录: {cache_dir}")

        # 缓存样式表，避免重复创建
        self._thumbnail_style = """
            QLabel {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
        """
        self._name_label_style = "font-size: 11px;"
        self._info_label_style = "font-size: 9px; color: #666;"

        logger.debug("HistoryPanel.__init__ 准备调用 init_ui...")
        self.init_ui()
        logger.debug("HistoryPanel.__init__ 完成")

    def init_ui(self):
        """初始化UI"""
        logger.debug("HistoryPanel.init_ui 开始执行")

        # 创建主控件
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 创建分割器（左右分栏）
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：目录树
        logger.debug("HistoryPanel.init_ui 准备创建目录树...")
        left_widget = self._create_directory_tree()
        splitter.addWidget(left_widget)

        # 右侧：文件列表
        logger.debug("HistoryPanel.init_ui 准备创建文件列表...")
        right_widget = self._create_file_list()
        splitter.addWidget(right_widget)

        # 设置分割器比例（左侧30%，右侧70%）
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setSizes([250, 550])

        layout.addWidget(splitter)

        # 添加按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_history)
        button_layout.addWidget(refresh_btn)

        clear_recent_btn = QPushButton("🗑️ 清除最近")
        clear_recent_btn.clicked.connect(self.clear_recent_files)
        button_layout.addWidget(clear_recent_btn)

        manage_btn = QPushButton("⚙️ 管理分类")
        manage_btn.clicked.connect(self.show_category_management)
        button_layout.addWidget(manage_btn)

        layout.addLayout(button_layout)

        # 设置停靠面板内容
        self.setWidget(main_widget)

        # 设置允许停靠位置
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        logger.debug("HistoryPanel.init_ui 完成")

    def _create_directory_tree(self):
        """创建左侧目录树"""
        logger.debug("HistoryPanel._create_directory_tree 开始执行")
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 5, 0)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel("📁 目录分类")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(title_label)

        # 创建树形控件
        self.directory_tree = QTreeWidget()
        self.directory_tree.setHeaderHidden(True)
        self.directory_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.directory_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        self.directory_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.directory_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
            QTreeWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #eee;
            }
            QTreeWidget::item:hover {
                background-color: #e8f4fc;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)

        layout.addWidget(self.directory_tree)

        # 延迟加载目录树，避免阻塞UI初始化
        QTimer.singleShot(100, self._load_directory_tree)

        logger.debug("HistoryPanel._create_directory_tree 完成")
        return widget

    def _create_file_list(self):
        """创建右侧文件列表"""
        logger.debug("HistoryPanel._create_file_list 开始执行")
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(5)

        # 标题
        self.file_list_title = QLabel("📄 文件列表")
        self.file_list_title.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(self.file_list_title)

        # 创建列表控件（使用Icon模式显示缩略图）
        self.file_list = QListWidget()
        self.file_list.setViewMode(QListWidget.IconMode)  # 使用图标模式显示缩略图
        self.file_list.setResizeMode(QListWidget.Adjust)  # 自动调整
        self.file_list.setSpacing(10)  # 增加间距
        self.file_list.setMovement(QListWidget.Static)  # 禁止拖动
        self.file_list.setWordWrap(True)  # 文字换行
        self.file_list.setTextElideMode(Qt.ElideRight)  # 文字过长时省略
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._show_file_context_menu)
        self.file_list.itemDoubleClicked.connect(self._on_file_item_double_clicked)
        self.file_list.setIconSize(QSize(180, 240))
        self.file_list.setGridSize(QSize(210, 310))  # 增加单元格大小，给item留出空间

        # 监听滚动事件，实现懒加载缩略图
        self.file_list.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._scroll_throttle_timer = None
        self._visible_range = (0, 10)  # 跟踪可见范围

        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                text-align: center;
            }
            QListWidget::item:hover {
                border: 2px solid #0078d4;
                background-color: #f0f8ff;
            }
            QListWidget::item:selected {
                border: 2px solid #0078d4;
                background-color: #e8f4fc;
            }
        """)

        layout.addWidget(self.file_list)

        # 延迟加载最近项目，避免阻塞UI初始化
        QTimer.singleShot(100, self._load_recent_files_to_list)

        logger.debug("HistoryPanel._create_file_list 完成")
        return widget

    def _load_directory_tree(self):
        """加载目录树结构"""
        logger.debug("HistoryPanel._load_directory_tree 开始执行")
        self.directory_tree.clear()

        # 1. 最近项目（根节点）
        logger.debug("_load_directory_tree: 创建最近项目节点")
        recent_item = QTreeWidgetItem(self.directory_tree)
        recent_item.setText(0, "⏰ 最近项目")
        recent_item.setData(0, Qt.UserRole, {'type': 'recent'})
        recent_item.setExpanded(True)

        # 2. 所有目录（按目录名称分组）
        logger.debug("_load_directory_tree: 开始获取分类...")
        categories = self.history_manager.get_categories()
        logger.debug(f"_load_directory_tree: 获取到 {len(categories) if categories else 0} 个分类")
        if categories:
            directories_item = QTreeWidgetItem(self.directory_tree)
            directories_item.setText(0, "📂 所有目录")
            directories_item.setData(0, Qt.UserRole, {'type': 'all_categories'})

            # 按分类名称排序
            sorted_categories = sorted(categories.keys(), key=str.lower)
            for category_key in sorted_categories:
                category_info = categories[category_key]
                # 兼容新旧格式
                if isinstance(category_info, dict) and 'name' in category_info:
                    category_name = category_info['name']
                    category_path = category_info.get('path', '')
                    files = category_info.get('files', [])
                else:
                    # 旧格式，只有文件列表
                    category_name = category_key.split('|||')[0] if '|||' in category_key else category_key
                    category_path = category_key.split('|||')[1] if '|||' in category_key else ''
                    files = category_info

                category_item = QTreeWidgetItem(directories_item)
                file_count = len(files)
                category_item.setText(0, f"📁 {category_name} ({file_count})")
                category_item.setData(0, Qt.UserRole, {
                    'type': 'category',
                    'name': category_name,
                    'path': category_path,
                    'key': category_key
                })
                # 设置悬停提示（显示完整路径）
                if category_path:
                    category_item.setToolTip(0, f"{category_path}")

        # 3. 按月份归档
        logger.debug("_load_directory_tree: 开始按月份归档...")
        monthly_item = QTreeWidgetItem(self.directory_tree)
        monthly_item.setText(0, "📅 按月份归档")
        monthly_item.setData(0, Qt.UserRole, {'type': 'monthly'})

        # 按月份分类所有文件
        monthly_groups = self._group_files_by_month()
        logger.debug(f"_load_directory_tree: 按月份分组完成，共 {len(monthly_groups)} 个月份")
        sorted_months = sorted(monthly_groups.keys(), reverse=True)
        for month in sorted_months:
            month_item = QTreeWidgetItem(monthly_item)
            file_count = len(monthly_groups[month])
            month_item.setText(0, f"📅 {month} ({file_count})")
            month_item.setData(0, Qt.UserRole, {
                'type': 'month',
                'month': month
            })

        # 默认展开所有节点
        self.directory_tree.expandAll()

        logger.debug("HistoryPanel._load_directory_tree 完成")

    def _group_files_by_month(self):
        """按月份分组文件"""
        logger.debug("HistoryPanel._group_files_by_month 开始执行")
        monthly_groups = {}
        recent_files = self.history_manager.get_recent_files()

        for record in recent_files:
            open_time = record.get('open_time', 0)
            if open_time:
                dt = datetime.fromtimestamp(open_time)
                month_key = dt.strftime("%Y-%m")
                if month_key not in monthly_groups:
                    monthly_groups[month_key] = []
                monthly_groups[month_key].append(record)

        return monthly_groups

    def _load_recent_files_to_list(self):
        """加载最近文件到右侧列表"""
        import time
        start = time.time()
        logger.debug("HistoryPanel._load_recent_files_to_list 开始执行")
        self.current_category = 'recent'
        self.file_list_title.setText("📄 最近项目")
        self.file_list.clear()
        self.thumbnail_cache = {}

        logger.debug(f"_load_recent_files_to_list: 清空完成，耗时 {(time.time() - start) * 1000:.0f}ms")

        logger.debug("_load_recent_files_to_list: 开始获取最近文件...")
        recent_files = self.history_manager.get_recent_files()
        logger.debug(f"_load_recent_files_to_list: 获取到 {len(recent_files) if recent_files else 0} 个最近文件，耗时 {(time.time() - start) * 1000:.0f}ms")

        if not recent_files:
            item = QListWidgetItem("暂无最近打开的文件")
            item.setFlags(Qt.NoItemFlags)
            self.file_list.addItem(item)
            logger.debug(f"_load_recent_files_to_list: 无最近文件，完成，总耗时 {(time.time() - start) * 1000:.0f}ms")
            return

        # 先添加文件项，不生成缩略图
        logger.debug("_load_recent_files_to_list: 准备异步添加文件项...")
        self._add_file_items_async(recent_files)
        logger.debug(f"_load_recent_files_to_list: 异步添加已调度，耗时 {(time.time() - start) * 1000:.0f}ms")

        # 延迟启动缩略图生成（在文件项添加完成后）
        QTimer.singleShot(2000, lambda: self._start_thumbnail_generation(recent_files))

        logger.debug(f"HistoryPanel._load_recent_files_to_list 完成，总耗时 {(time.time() - start) * 1000:.0f}ms")

    def _add_file_items_async(self, files):
        """异步分批添加文件项，避免阻塞UI"""
        logger.debug(f"_add_file_items_async 开始执行，文件数: {len(files)}")
        try:
            self._current_files = files
            self._current_batch_index = 0
            self._total_files_count = len(files)
            self._files_to_add = files.copy()

            logger.debug(f"_add_file_items_async: 准备分批添加 {self._total_files_count} 个文件")

            # 使用定时器分批添加
            QTimer.singleShot(0, self._add_next_batch)
            logger.debug("_add_file_items_async: 定时器已设置")
        except Exception as e:
            logger.error(f"_add_file_items_async 异常: {e}")
            import traceback
            traceback.print_exc()

    def _add_next_batch(self):
        """添加下一批文件项"""
        if self._current_batch_index >= len(self._current_files):
            logger.debug(f"_add_next_batch: 所有文件项添加完成，共 {len(self._current_files)} 个文件")
            return

        # 获取当前批次（每批1个，减少单批次工作量）
        end_index = min(self._current_batch_index + 1, len(self._current_files))
        batch = self._current_files[self._current_batch_index:end_index]

        # 添加当前批次的文件
        for record in batch:
            self._add_file_item(record)

        # 只在最后一批时记录日志，减少日志输出
        if end_index >= len(self._current_files):
            logger.debug(f"_add_next_batch: 所有文件项添加完成，共 {len(self._current_files)} 个文件")

        # 更新索引
        self._current_batch_index = end_index

        # 继续添加下一批，使用50ms间隔让UI有更多时间刷新
        QTimer.singleShot(50, self._add_next_batch)

    def _load_category_files_to_list(self, category_name, category_key=None):
        """加载指定分类的文件到右侧列表"""
        self.current_category = category_key or category_name
        self.file_list_title.setText(f"📄 {category_name}")
        self.file_list.clear()
        self.thumbnail_cache = {}  # 清空缩略图缓存

        categories = self.history_manager.get_categories()
        # 查找对应的分类数据
        files = []
        if category_key and category_key in categories:
            category_info = categories[category_key]
            files = category_info.get('files', []) if isinstance(category_info, dict) else category_info
        else:
            # 兼容旧格式，直接用分类名查找
            for key, value in categories.items():
                if isinstance(value, dict) and value.get('name') == category_name:
                    files = value.get('files', [])
                    break
                elif not isinstance(value, dict) and key == category_name:
                    files = value
                    break

        if not files:
            item = QListWidgetItem(f"分类 '{category_name}' 下暂无文件")
            item.setFlags(Qt.NoItemFlags)
            self.file_list.addItem(item)
            return

        # 启动缩略图生成
        self._start_thumbnail_generation(files)

        # 异步分批添加文件项
        self._add_file_items_async(files)

    def _load_month_files_to_list(self, month):
        """加载指定月份的文件到右侧列表"""
        self.current_category = f'month_{month}'
        self.file_list_title.setText(f"📄 {month}")
        self.file_list.clear()
        self.thumbnail_cache = {}  # 清空缩略图缓存

        monthly_groups = self._group_files_by_month()
        files = monthly_groups.get(month, [])

        if not files:
            item = QListWidgetItem(f"{month} 暂无文件记录")
            item.setFlags(Qt.NoItemFlags)
            self.file_list.addItem(item)
            return

        # 启动缩略图生成
        self._start_thumbnail_generation(files)

        # 异步分批添加文件项
        self._add_file_items_async(files)

    def _add_file_item(self, record):
        """添加文件项到列表 - 优化版，先用简单项，后续更新"""
        import time
        start_time = time.time()

        file_path = record.get('path', '')
        filename = record.get('filename', '')
        open_time = record.get('open_time', 0)
        page_count = record.get('page_count', 0)

        # 移除同步的文件存在性检查，让缩略图线程在后台处理
        # 文件不存在时，缩略图生成失败不会影响UI显示

        # 格式化显示
        time_str = self.history_manager.format_open_time(open_time)

        # 创建列表项
        item = QListWidgetItem()
        item.setData(Qt.UserRole, record)  # 存储完整记录
        item.setSizeHint(QSize(210, 310))  # 设置固定大小，与 gridSize 匹配

        # 添加tooltip显示完整路径
        item.setToolTip(file_path)

        # 添加到列表
        self.file_list.addItem(item)

        # 缓存记录以便后续创建widget更新缩略图
        self.thumbnail_cache[file_path] = {
            'type': 'pending',
            'record': record,
            'index': self.file_list.count() - 1
        }

        elapsed = (time.time() - start_time) * 1000
        if elapsed > 100:  # 超过100ms记录
            logger.warning(f"_add_file_item 耗时 {elapsed:.0f}ms, 文件: {filename}")

    def _start_thumbnail_generation(self, files):
        """启动缩略图生成线程"""
        logger.debug("HistoryPanel._start_thumbnail_generation 开始执行")

        # 检查是否正在生成缩略图
        if self._is_generating:
            logger.debug("_start_thumbnail_generation: 已有缩略图生成任务，跳过")
            return

        # 不停止之前的线程，让它自然结束（避免阻塞）
        if self.thumbnail_thread and self.thumbnail_thread.isRunning():
            logger.debug("_start_thumbnail_generation: 之前线程仍在运行，设置停止标志")
            self.thumbnail_thread._is_running = False

        # 直接传递所有文件路径，存在性检查移到后台线程中
        file_paths = [f.get('path') for f in files if f.get('path')]
        logger.debug(f"_start_thumbnail_generation: 准备为 {len(file_paths)} 个文件生成缩略图")

        if file_paths:
            self._is_generating = True
            self.thumbnail_thread = ThumbnailGenerator(file_paths, self.disk_cache)
            self.thumbnail_thread.thumbnail_ready.connect(self._on_thumbnail_ready)
            self.thumbnail_thread.finished.connect(self._on_thumbnail_finished)
            self.thumbnail_thread.start()
            logger.debug("_start_thumbnail_generation: 缩略图生成线程已启动")

        logger.debug("HistoryPanel._start_thumbnail_generation 完成")

    def _on_thumbnail_finished(self):
        """缩略图生成完成回调"""
        logger.debug("_on_thumbnail_finished: 缩略图生成线程完成")
        self._is_generating = False
        if self.thumbnail_thread:
            self.thumbnail_thread = None

    def _on_thumbnail_ready(self, file_path, thumbnail):
        """缩略图生成完成的回调 - 只缓存，不更新UI"""
        # 只缓存缩略图，不立即更新UI
        self.thumbnail_cache[file_path] = thumbnail
        # 缩略图将在滚动到可见区域时才更新到UI

    def _process_pending_thumbnails(self):
        """批量处理所有待更新的缩略图"""
        import time
        start = time.time()

        if not hasattr(self, '_pending_thumbnails') or not self._pending_thumbnails:
            return

        # 只处理前3个，避免一次性处理太多
        pending_count = len(self._pending_thumbnails)
        batch_size = min(3, pending_count)
        batch_items = list(self._pending_thumbnails.items())[:batch_size]

        # 从待处理队列中移除这批
        for file_path, _ in batch_items:
            del self._pending_thumbnails[file_path]

        logger.debug(f"开始批量处理 {batch_size}/{pending_count} 个缩略图")

        for file_path, thumbnail in batch_items:
            try:
                self._update_thumbnail_item(file_path, thumbnail)
            except Exception as e:
                logger.error(f"更新缩略图失败 {file_path}: {e}")

        elapsed = (time.time() - start) * 1000
        logger.debug(f"批量处理 {batch_size} 个缩略图完成，耗时 {elapsed:.0f}ms")

        # 如果还有待处理的，继续处理
        if self._pending_thumbnails:
            QTimer.singleShot(100, self._process_pending_thumbnails)

    def _update_thumbnail_item(self, file_path, thumbnail):
        """实际更新缩略图项的方法（在主线程的事件循环中执行）"""
        import time
        start = time.time()

        if file_path in self.thumbnail_cache:
            cache_entry = self.thumbnail_cache[file_path]

            # 如果是简单的文本项，升级为带缩略图的widget
            if isinstance(cache_entry, dict) and cache_entry.get('type') == 'pending':
                record = cache_entry['record']
                item_index = cache_entry['index']

                # 获取原始项
                widget_start = time.time()
                item = self.file_list.item(item_index)
                if item:
                    # 创建带缩略图的widget
                    widget = self._create_thumbnail_widget(record, thumbnail)
                    set_widget_start = time.time()
                    self.file_list.setItemWidget(item, widget)
                    set_widget_elapsed = (time.time() - set_widget_start) * 1000

                    # 更新缓存
                    self.thumbnail_cache[file_path] = thumbnail
                    logger.debug(f"更新缩略图widget: {file_path}, setItemWidget耗时 {set_widget_elapsed:.0f}ms")

            elif isinstance(cache_entry, QLabel):
                # 如果已经是widget中的label，直接更新
                cache_entry.setPixmap(thumbnail)
                cache_entry.setText("")
                self.thumbnail_cache[file_path] = thumbnail

        elapsed = (time.time() - start) * 1000
        if elapsed > 50:  # 超过50ms记录
            logger.debug(f"_update_thumbnail_item {file_path} 耗时 {elapsed:.0f}ms")

    def _create_thumbnail_widget(self, record, thumbnail):
        """创建带缩略图的widget"""
        filename = record.get('filename', '')
        file_path = record.get('path', '')
        open_time = record.get('open_time', 0)
        page_count = record.get('page_count', 0)

        # 格式化显示
        time_str = self.history_manager.format_open_time(open_time)

        # 创建widget
        widget = QWidget()
        widget.setFixedSize(210, 310)
        widget.setToolTip(file_path)  # 设置 tooltip 显示完整路径
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)  # 垂直和水平都居中
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)  # 无边距

        # 文件类型标签（红色加粗）
        file_ext = os.path.splitext(filename)[1].upper().lstrip('.')
        if not file_ext:
            file_ext = 'FILE'
        type_label = QLabel(file_ext)
        type_label.setStyleSheet("""
            QLabel {
                color: #dc3545;
                font-weight: bold;
                font-size: 14px;
                padding: 2px 6px;
            }
        """)
        type_label.setFixedSize(50, 24)
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setToolTip(file_path)  # 设置 tooltip 显示完整路径

        # 缩略图
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(180, 240)  # 与 iconSize 一致
        thumbnail_label.setPixmap(thumbnail)
        thumbnail_label.setToolTip(file_path)  # 设置 tooltip 显示完整路径
        thumbnail_label.setStyleSheet(self._thumbnail_style)
        thumbnail_label.setAlignment(Qt.AlignCenter)

        # 将类型标签作为子控件放在缩略图左上角
        type_label.setParent(thumbnail_label)
        type_label.move(5, 5)
        type_label.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        layout.addWidget(thumbnail_label)

        # 文件名
        name_label = QLabel(filename[:20] + "..." if len(filename) > 20 else filename)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setMaximumWidth(180)  # 与缩略图宽度一致
        name_label.setToolTip(file_path)  # 设置 tooltip 显示完整路径
        name_label.setStyleSheet(self._name_label_style)
        layout.addWidget(name_label)

        # 时间
        info_label = QLabel(f"{time_str}")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(info_label)

        return widget

    def _on_tree_item_clicked(self, item, column):
        """目录树项点击事件"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        type_ = data.get('type')

        if type_ == 'recent':
            self._load_recent_files_to_list()
        elif type_ == 'category':
            category_name = data.get('name')
            category_key = data.get('key')
            self._load_category_files_to_list(category_name, category_key)
        elif type_ == 'month':
            month = data.get('month')
            self._load_month_files_to_list(month)
        elif type_ == 'all_categories':
            # 点击"所有目录"时，显示所有分类下的文件
            self._load_all_categories_files()

    def _on_scroll(self, value):
        """滚动事件处理，实现懒加载缩略图"""
        # 取消之前的定时器
        if self._scroll_throttle_timer:
            self._scroll_throttle_timer.stop()

        # 设置新的定时器，200ms后才更新
        self._scroll_throttle_timer = QTimer()
        self._scroll_throttle_timer.setSingleShot(True)
        self._scroll_throttle_timer.timeout.connect(self._update_visible_thumbnails)
        self._scroll_throttle_timer.start(200)

    def _update_visible_thumbnails(self):
        """更新可见区域的缩略图"""
        if not self.isVisible():
            return

        # 获取可见区域的项目索引
        top_item = self.file_list.itemAt(0, 0)
        bottom_y = self.file_list.height()
        bottom_item = self.file_list.itemAt(0, bottom_y - 10)

        if not top_item:
            return

        top_index = self.file_list.row(top_item)
        bottom_index = self.file_list.row(bottom_item) if bottom_item else top_index + 10

        # 扩大可见范围，预加载上下各5个
        visible_start = max(0, top_index - 5)
        visible_end = min(self.file_list.count(), bottom_index + 5)

        # 如果可见范围没有变化，不需要更新
        if (visible_start, visible_end) == self._visible_range:
            return

        self._visible_range = (visible_start, visible_end)
        logger.debug(f"更新可见缩略图: {visible_start}-{visible_end}")

        # 只更新可见范围内的缩略图
        for i in range(visible_start, visible_end):
            item = self.file_list.item(i)
            if item:
                record = item.data(Qt.UserRole)
                if record:
                    file_path = record.get('path', '')
                    if file_path and file_path in self.thumbnail_cache:
                        thumbnail = self.thumbnail_cache[file_path]
                        if isinstance(thumbnail, QPixmap):
                            # 检查是否已经有widget
                            if not self.file_list.itemWidget(item):
                                # 创建带缩略图的widget
                                widget = self._create_thumbnail_widget(record, thumbnail)
                                self.file_list.setItemWidget(item, widget)

    def _on_file_item_double_clicked(self, item):
        """双击文件项"""
        record = item.data(Qt.UserRole)
        if record:
            file_path = record.get('path', '')
            self._open_file(file_path)

    def _show_tree_context_menu(self, pos):
        """显示目录树右键菜单"""
        item = self.directory_tree.itemAt(pos)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        type_ = data.get('type')
        menu = QMenu(self)

        if type_ == 'recent':
            refresh_action = menu.addAction("🔄 刷新最近")
            refresh_action.triggered.connect(self._load_recent_files_to_list)

            menu.addSeparator()

            clear_action = menu.addAction("🗑️ 清除最近")
            clear_action.triggered.connect(self.clear_recent_files)

        elif type_ == 'category':
            category_name = data.get('name')
            category_key = data.get('key')
            refresh_action = menu.addAction("🔄 刷新")
            refresh_action.triggered.connect(lambda: self._load_category_files_to_list(category_name, category_key))

            menu.addSeparator()

            clear_action = menu.addAction("🗑️ 清除此分类")
            clear_action.triggered.connect(lambda: self._clear_category(category_key or category_name))

        elif type_ == 'month':
            month = data.get('month')
            refresh_action = menu.addAction("🔄 刷新")
            refresh_action.triggered.connect(lambda: self._load_month_files_to_list(month))

        elif type_ == 'all_categories':
            refresh_action = menu.addAction("🔄 刷新")
            refresh_action.triggered.connect(self._load_all_categories_files)

        menu.exec_(self.directory_tree.mapToGlobal(pos))

    def _show_file_context_menu(self, pos):
        """显示文件右键菜单"""
        item = self.file_list.itemAt(pos)
        if not item:
            return

        record = item.data(Qt.UserRole)
        if not record:
            return

        file_path = record.get('path', '')
        if not file_path:
            return

        menu = QMenu(self)

        # 打开
        open_action = menu.addAction("📂 打开文件")
        open_action.triggered.connect(lambda: self._open_file(file_path))

        # 在资源管理器中显示
        show_action = menu.addAction("🔍 在资源管理器中显示")
        show_action.triggered.connect(lambda: self._show_in_explorer(file_path))

        menu.addSeparator()

        # 从历史中移除
        remove_action = menu.addAction("🗑️ 从历史中移除")
        remove_action.triggered.connect(lambda: self._remove_from_history(file_path))

        menu.exec_(self.file_list.mapToGlobal(pos))

    def _open_file(self, file_path):
        """打开文件"""
        if os.path.exists(file_path):
            self.file_opened.emit(file_path)
        else:
            self.parent.show_message("❌ 文件不存在")

    def _show_in_explorer(self, file_path):
        """在资源管理器中显示文件"""
        import subprocess
        if os.path.exists(file_path):
            subprocess.Popen(['explorer', '/select,', file_path])
        else:
            self.parent.show_message("❌ 文件不存在")

    def _remove_from_history(self, file_path):
        """从历史中移除文件"""
        self.history_manager.remove_file_from_recent(file_path)
        self.refresh_history()
        self.parent.show_message("✅ 已从历史中移除")

    def _clear_category(self, category_name):
        """清空分类"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认清除",
            f"确定要清空分类 '{category_name}' 的所有文件记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history_manager.clear_category(category_name)
            self._load_directory_tree()
            self.refresh_needed.emit()
            self.parent.show_message(f"✅ 已清空分类 '{category_name}'")

    def refresh_history(self):
        """刷新历史记录"""
        self._load_directory_tree()
        if self.current_category == 'recent':
            self._load_recent_files_to_list()
        elif self.current_category == 'all_categories':
            self._load_all_categories_files()
        elif isinstance(self.current_category, str) and self.current_category.startswith('month_'):
            month = self.current_category.replace('month_', '')
            self._load_month_files_to_list(month)
        else:
            self._load_category_files_to_list(self.current_category)
        self.refresh_needed.emit()
        self.parent.show_message("✅ 历史记录已刷新")

    def clear_recent_files(self):
        """清除最近文件"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认清除",
            "确定要清除所有最近文件记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history_manager.clear_recent_files()
            self._load_directory_tree()
            self._load_recent_files_to_list()
            self.refresh_needed.emit()
            self.parent.show_message("✅ 已清除最近文件")

    def show_category_management(self):
        """显示分类管理对话框"""
        from app.ui.history_dialog import HistoryDialog
        dialog = HistoryDialog(self.parent, self.history_manager)
        if dialog.exec_() == HistoryDialog.Accepted:
            self.refresh_history()

    def closeEvent(self, event):
        """关闭事件处理"""
        logger.debug("HistoryPanel.closeEvent 开始执行")

        # 设置停止标志
        if self.thumbnail_thread and self.thumbnail_thread.isRunning():
            logger.debug("closeEvent: 设置缩略图线程停止标志")
            self.thumbnail_thread._is_running = False

            # 给线程一点时间自然退出，但不阻塞
            # 使用定时器延迟执行实际关闭
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._cleanup_thread())

        # 立即接受关闭事件
        event.accept()

    def _cleanup_thread(self):
        """清理线程资源"""
        if self.thumbnail_thread and not self.thumbnail_thread.isRunning():
            logger.debug("_cleanup_thread: 线程已停止，可以清理")
            self.thumbnail_thread = None
        elif self.thumbnail_thread and self.thumbnail_thread.isRunning():
            logger.debug("_cleanup_thread: 线程仍在运行，等待其自然结束")
            # 再次检查，最多等待3次（300ms）
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._cleanup_thread)
