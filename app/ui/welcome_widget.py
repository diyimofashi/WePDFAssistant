"""欢迎界面组件模块"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea,
    QSplitter, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QToolButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread, QSettings
from PyQt5.QtGui import QFont, QPixmap, QImage
import os
import hashlib
import fitz
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger('welcome_widget')


class ThumbnailCache:
    """缩略图持久化缓存管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._cache = {}
            self._initialized = True
            self._load_from_disk()

    def _get_cache_path(self, file_path):
        """获取缓存的路径"""
        cache_dir = os.path.join(os.path.expanduser('~'), '.pypdf_cache', 'thumbnails')
        os.makedirs(cache_dir, exist_ok=True)

        # 使用文件路径的哈希作为缓存文件名
        file_hash = hashlib.md5(file_path.encode('utf-8')).hexdigest()
        cache_file = os.path.join(cache_dir, f"{file_hash}.png")
        return cache_file

    def _get_file_hash(self, file_path):
        """获取文件的哈希值（用于检测文件是否修改）"""
        try:
            stat = os.stat(file_path)
            return f"{file_path}_{stat.st_mtime}_{stat.st_size}"
        except Exception:
            return file_path

    def get(self, file_path):
        """从缓存获取缩略图"""
        cache_path = self._get_cache_path(file_path)
        file_key = self._get_file_hash(file_path)

        if file_key in self._cache:
            return self._cache[file_key]

        # 尝试从磁盘加载
        if os.path.exists(cache_path):
            try:
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    self._cache[file_key] = pixmap
                    return pixmap
            except Exception as e:
                logger.debug(f"从磁盘加载缓存失败: {e}")

        return None

    def set(self, file_path, pixmap):
        """保存缩略图到缓存"""
        cache_path = self._get_cache_path(file_path)
        file_key = self._get_file_hash(file_path)

        self._cache[file_key] = pixmap

        # 异步保存到磁盘
        try:
            pixmap.save(cache_path, "PNG")
        except Exception as e:
            logger.debug(f"保存缩略图缓存失败: {e}")

    def _load_from_disk(self):
        """预加载磁盘缓存（可选）"""
        pass

    def clear(self):
        """清空内存缓存"""
        self._cache.clear()

    def clear_disk_cache(self):
        """清空磁盘缓存"""
        cache_dir = os.path.join(os.path.expanduser('~'), '.pypdf_cache', 'thumbnails')
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            self._cache.clear()
            logger.info("磁盘缓存已清空")


class ThumbnailGenerator(QThread):
    """缩略图生成线程"""

    thumbnail_ready = pyqtSignal(str, QPixmap)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self._is_running = True

    def run(self):
        for file_path in self.file_paths:
            if not self._is_running:
                break

            if os.path.exists(file_path):
                try:
                    pixmap = self._generate_thumbnail(file_path)
                    if pixmap:
                        self.thumbnail_ready.emit(file_path, pixmap)
                except Exception as e:
                    logger.error(f"生成缩略图失败 {file_path}: {e}")

    def _generate_thumbnail(self, file_path):
        try:
            doc = fitz.open(file_path)
            if len(doc) > 0:
                page = doc[0]
                # 降低缩放比例以提高性能，目标尺寸是180x240
                # 180/缩放 = 原始宽度，所以缩放约0.5-0.8足够
                zoom = 0.5
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix)

                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(img)

                target_size = QSize(180, 240)
                return pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.FastTransformation)  # 使用快速缩放
        except Exception as e:
            logger.error(f"生成缩略图异常 {file_path}: {e}")
        return None

    def stop(self):
        """停止生成（非阻塞）"""
        logger.debug("ThumbnailGenerator.stop: 设置停止标志")
        self._is_running = False
        # 不调用 wait()，避免阻塞主线程
        # 线程会在下一次迭代时检测到 _is_running 为 False 并退出


class WelcomeWidget(QWidget):
    """欢迎界面 - 显示在没有文件打开时，占满整个容器，与历史记录面板布局一致"""

    # 信号定义
    file_open_requested = pyqtSignal(str)  # 文件打开请求信号
    new_file_requested = pyqtSignal()  # 新建文件请求信号
    close_requested = pyqtSignal()  # 关闭欢迎界面请求信号

    def __init__(self, parent=None, history_manager=None):
        super().__init__(parent)
        self.history_manager = history_manager or (HistoryManager(parent) if parent else None)
        self.thumbnail_cache = {}  # 内存缓存：file_path -> QLabel
        self.persistent_cache = ThumbnailCache()  # 持久化缓存
        self.thumbnail_thread = None
        self.current_category = 'recent'
        self._is_initialized = False  # 初始化标志
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部标题栏（带关闭按钮）
        title_bar = self._create_title_bar()
        layout.addWidget(title_bar)

        # 内容区域（左右布局）
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 左侧：目录树（固定宽度）
        left_widget = self._create_directory_tree()
        left_widget.setFixedWidth(300)
        content_layout.addWidget(left_widget)

        # 右侧：文件列表（填充剩余空间）
        right_widget = self._create_file_list()
        content_layout.addWidget(right_widget, stretch=1)

        layout.addWidget(content_widget, stretch=1)

        # 首次加载数据（延迟加载，避免阻塞UI）
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(200, self._initialize_data)

    def _initialize_data(self):
        """初始化数据（延迟加载）"""
        if not self._is_initialized:
            self._load_directory_tree()
            self._load_recent_files_to_list(delay_thumbnails=True)
            self._is_initialized = True
            logger.debug("欢迎界面数据初始化完成")

    def _create_title_bar(self):
        """创建顶部标题栏"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-bottom: 1px solid #ccc;
            }
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel("📜 历史记录")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        layout.addWidget(title_label, stretch=1)

        # 关闭按钮
        close_btn = QToolButton()
        close_btn.setText("✕")
        close_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                font-size: 18px;
                color: #666;
                min-width: 24px;
                min-height: 24px;
                padding: 0px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
                color: #333;
            }
            QToolButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        close_btn.setToolTip("返回文档")
        close_btn.clicked.connect(self.close_requested)
        layout.addWidget(close_btn)

        return widget

    def _create_directory_tree(self):
        """创建左侧目录树"""
        widget = QWidget()
        widget.setFixedWidth(300)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 5, 0)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel("📁 目录分类")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(title_label)

        # 创建树形控件
        self.directory_tree = QTreeWidget()
        self.directory_tree.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.directory_tree.setHeaderHidden(True)
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

        layout.addWidget(self.directory_tree, stretch=1)

        return widget

    def _create_file_list(self):
        """创建右侧文件列表"""
        logger.debug("创建右侧文件列表...")
        widget = QWidget()
        widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(5)

        # 标题
        self.file_list_title = QLabel("📄 文件列表")
        self.file_list_title.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(self.file_list_title)

        # 创建列表控件（使用大图标模式显示缩略图）
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(200)
        self.file_list.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.file_list.setViewMode(QListWidget.IconMode)
        self.file_list.setIconSize(QSize(180, 240))
        self.file_list.setGridSize(QSize(210, 310))  # 增加单元格大小，给item留出空间
        self.file_list.setResizeMode(QListWidget.Adjust)
        self.file_list.setSpacing(10)
        self.file_list.setMovement(QListWidget.Static)
        self.file_list.setWordWrap(True)
        self.file_list.setTextElideMode(Qt.ElideRight)
        self.file_list.itemDoubleClicked.connect(self._on_file_item_double_clicked)
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

        layout.addWidget(self.file_list, stretch=1)

        logger.debug("右侧文件列表创建完成")

        return widget

    def _load_directory_tree(self):
        """加载目录树结构"""
        self.directory_tree.clear()

        # 1. 最近项目
        recent_item = QTreeWidgetItem(self.directory_tree)
        recent_item.setText(0, "⏰ 最近项目")
        recent_item.setData(0, Qt.UserRole, {'type': 'recent'})
        recent_item.setSelected(True)  # 默认选中

        # 2. 所有目录
        categories = self.history_manager.get_categories()
        if categories:
            directories_item = QTreeWidgetItem(self.directory_tree)
            directories_item.setText(0, "📂 所有目录")
            directories_item.setData(0, Qt.UserRole, {'type': 'all_categories'})

            sorted_categories = sorted(categories.keys(), key=str.lower)
            for category_key in sorted_categories:
                category_info = categories[category_key]
                # 兼容新旧格式
                if isinstance(category_info, dict):
                    category_name = category_info.get('name', category_key.split('|||')[0] if '|||' in category_key else category_key)
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
        monthly_item = QTreeWidgetItem(self.directory_tree)
        monthly_item.setText(0, "📅 按月份归档")
        monthly_item.setData(0, Qt.UserRole, {'type': 'monthly'})

        monthly_groups = self._group_files_by_month()
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

    def _group_files_by_month(self):
        """按月份分组文件"""
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

    def _load_recent_files_to_list(self, delay_thumbnails=False):
        """加载最近文件到右侧列表"""
        logger.debug("加载最近文件到右侧列表...")
        self.current_category = 'recent'
        self.file_list_title.setText("📄 最近项目")

        recent_files = self.history_manager.get_recent_files()
        logger.debug(f"获取到最近文件数量: {len(recent_files)}")

        self.file_list.clear()
        self.thumbnail_cache.clear()  # 只清空内存缓存，不清空持久化缓存

        if not recent_files:
            item = QListWidgetItem("暂无最近打开的文件")
            item.setFlags(Qt.NoItemFlags)
            self.file_list.addItem(item)
            return

        # 先添加文件项，不立即生成缩略图
        for record in recent_files:
            self._add_file_item(record)

        logger.debug(f"文件列表加载完成，当前列表项数量: {self.file_list.count()}")

        # 延迟启动缩略图生成（只为未缓存的文件生成）
        if delay_thumbnails:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, lambda: self._start_thumbnail_generation(recent_files))
        else:
            self._start_thumbnail_generation(recent_files)

    def _load_category_files_to_list(self, category_name, category_key=None):
        """加载指定分类的文件到右侧列表"""
        self.current_category = category_key or category_name
        self.file_list_title.setText(f"📄 {category_name}")
        self.file_list.clear()
        self.thumbnail_cache.clear()  # 只清空内存缓存

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

        # 先添加文件项
        for record in files:
            self._add_file_item(record)

        # 延迟启动缩略图生成
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._start_thumbnail_generation(files))

    def _load_month_files_to_list(self, month):
        """加载指定月份的文件到右侧列表"""
        self.current_category = f'month_{month}'
        self.file_list_title.setText(f"📄 {month}")
        self.file_list.clear()
        self.thumbnail_cache.clear()  # 只清空内存缓存

        monthly_groups = self._group_files_by_month()
        files = monthly_groups.get(month, [])

        if not files:
            item = QListWidgetItem(f"{month} 暂无文件记录")
            item.setFlags(Qt.NoItemFlags)
            self.file_list.addItem(item)
            return

        # 先添加文件项
        for record in files:
            self._add_file_item(record)

        # 延迟启动缩略图生成
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._start_thumbnail_generation(files))

    def _load_all_categories_files(self):
        """加载所有分类下的文件"""
        self.current_category = 'all_categories'
        self.file_list_title.setText("📄 所有分类文件")
        self.file_list.clear()
        self.thumbnail_cache = {}

        categories = self.history_manager.get_categories()
        all_files = []
        for category_info in categories.values():
            # 兼容新旧格式
            if isinstance(category_info, dict):
                all_files.extend(category_info.get('files', []))
            else:
                all_files.extend(category_info)

        if not all_files:
            item = QListWidgetItem("暂无分类文件")
            item.setFlags(Qt.NoItemFlags)
            self.file_list.addItem(item)
            return

        all_files.sort(key=lambda x: x.get('open_time', 0), reverse=True)

        # 先添加文件项
        for record in all_files:
            self._add_file_item(record)

        # 延迟启动缩略图生成
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._start_thumbnail_generation(all_files))

    def _add_file_item(self, record):
        """添加文件项到列表"""
        file_path = record.get('path', '')
        filename = record.get('filename', '')
        open_time = record.get('open_time', 0)
        page_count = record.get('page_count', 0)

        if not os.path.exists(file_path):
            logger.debug(f"文件不存在，跳过: {file_path}")
            return

        from datetime import datetime
        time_str = self.history_manager.format_open_time(open_time)
        logger.debug(f"添加文件项: {filename}, 时间: {time_str}")

        item = QListWidgetItem()
        item.setData(Qt.UserRole, record)
        item.setSizeHint(QSize(210, 310))  # 设置固定大小，与 gridSize 匹配

        item_widget = QWidget()
        item_widget.setFixedSize(210, 310)
        item_widget.setToolTip(file_path)  # 设置 tooltip 显示完整路径

        item_layout = QVBoxLayout(item_widget)
        item_layout.setAlignment(Qt.AlignCenter)  # 垂直和水平都居中
        item_layout.setSpacing(5)
        item_layout.setContentsMargins(0, 0, 0, 0)  # 无边距

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

        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(180, 240)  # 与 iconSize 一致
        thumbnail_label.setToolTip(file_path)  # 设置 tooltip 显示完整路径
        thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
        """)
        thumbnail_label.setAlignment(Qt.AlignCenter)

        # 尝试从持久化缓存加载缩略图
        cached_thumbnail = self.persistent_cache.get(file_path)
        if cached_thumbnail:
            thumbnail_label.setPixmap(cached_thumbnail)
        else:
            thumbnail_label.setText("加载中...")

        # 使用QLabel自带的父级布局，将类型标签移到左上角
        thumbnail_label.setProperty("thumbnail", True)
        type_label.setParent(thumbnail_label)
        type_label.move(5, 5)
        type_label.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        item_layout.addWidget(thumbnail_label)

        name_label = QLabel(filename[:20] + "..." if len(filename) > 20 else filename)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setMaximumWidth(180)  # 与缩略图宽度一致
        name_label.setToolTip(file_path)  # 设置 tooltip 显示完整路径
        name_label.setStyleSheet("font-size: 12px;")
        item_layout.addWidget(name_label)

        info_label = QLabel(f"{time_str}")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("font-size: 12px; color: #666;")
        item_layout.addWidget(info_label)

        self.file_list.addItem(item)
        self.file_list.setItemWidget(item, item_widget)
        logger.debug(f"文件项已添加到列表，当前列表项数量: {self.file_list.count()}")

        # 缓存QLabel引用
        self.thumbnail_cache[file_path] = thumbnail_label

    def _start_thumbnail_generation(self, files):
        """启动缩略图生成线程"""
        if self.thumbnail_thread and self.thumbnail_thread.isRunning():
            self.thumbnail_thread.stop()

        # 只为没有缓存的文件生成缩略图
        uncached_files = []
        for f in files:
            file_path = f.get('path')
            if file_path and os.path.exists(file_path):
                cached = self.persistent_cache.get(file_path)
                if not cached:
                    uncached_files.append(f)

        if uncached_files:
            logger.debug(f"需要生成缩略图的文件数量: {len(uncached_files)}")
            self.thumbnail_thread = ThumbnailGenerator([f.get('path') for f in uncached_files])
            self.thumbnail_thread.thumbnail_ready.connect(self._on_thumbnail_ready)
            self.thumbnail_thread.start()
        else:
            logger.debug("所有文件都有缓存，无需生成缩略图")

    def _on_thumbnail_ready(self, file_path, thumbnail):
        """缩略图生成完成的回调"""
        # 保存到持久化缓存
        self.persistent_cache.set(file_path, thumbnail)

        # 更新UI显示
        if file_path in self.thumbnail_cache:
            label = self.thumbnail_cache[file_path]
            if isinstance(label, QLabel):
                label.setPixmap(thumbnail)
                label.setText("")

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
            self._load_all_categories_files()

    def _on_file_item_double_clicked(self, item):
        """双击文件项"""
        record = item.data(Qt.UserRole)
        if record:
            file_path = record.get('path', '')
            self.file_open_requested.emit(file_path)

    def refresh_history(self):
        """刷新历史记录显示"""
        if not self._is_initialized:
            return

        logger.debug("刷新历史记录显示...")
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

    def _stop_thumbnail_generation(self):
        """停止缩略图生成线程"""
        if self.thumbnail_thread and self.thumbnail_thread.isRunning():
            self.thumbnail_thread.stop()
            logger.debug("缩略图生成线程已停止")

    def closeEvent(self, event):
        """关闭事件处理"""
        logger.debug("WelcomeWidget.closeEvent 开始执行")

        # 设置停止标志，但不等待线程结束（避免阻塞）
        if self.thumbnail_thread and self.thumbnail_thread.isRunning():
            logger.debug("closeEvent: 设置缩略图线程停止标志")
            self.thumbnail_thread._is_running = False

        # 立即接受关闭事件
        event.accept()
