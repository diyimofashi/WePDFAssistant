"""文件历史记录分类管理对话框模块"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
    QGroupBox, QFormLayout, QSplitter, QMessageBox, QTreeWidget,
    QTreeWidgetItem, QAbstractItemView, QHeaderView
)
from PyQt5.QtCore import Qt
import os
from app.utils.logger import get_logger

logger = get_logger('history_dialog')


class HistoryDialog(QDialog):
    """文件历史记录分类管理对话框"""

    def __init__(self, parent_window, history_manager):
        super().__init__(parent_window)
        self.parent = parent_window
        self.history_manager = history_manager
        self.category_mapping = history_manager.get_category_mapping().copy()

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("管理历史记录分类")
        self.setModal(True)
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：目录映射
        left_panel = self._create_mapping_panel()
        splitter.addWidget(left_panel)

        # 右侧：分类统计
        right_panel = self._create_stats_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_mapping_panel(self):
        """创建目录映射面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标题
        title_label = QLabel("目录到分类的映射")
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title_label)

        # 添加新映射
        add_group = QGroupBox("添加新映射")
        add_layout = QFormLayout()

        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("输入目录路径（如：D:/工作/）")
        add_layout.addRow("目录路径:", self.dir_input)

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        add_layout.addRow("分类名称:", self.category_combo)

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_mapping)
        add_layout.addRow("", add_btn)

        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        # 映射列表
        list_label = QLabel("现有映射:")
        layout.addWidget(list_label)

        self.mapping_tree = QTreeWidget()
        self.mapping_tree.setHeaderLabels(["目录路径", "分类名称"])
        self.mapping_tree.setAlternatingRowColors(True)
        self.mapping_tree.setRootIsDecorated(False)
        self.mapping_tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mapping_tree.setColumnWidth(0, 400)
        self.mapping_tree.setColumnWidth(1, 200)
        layout.addWidget(self.mapping_tree)

        # 映射操作按钮
        mapping_btn_layout = QHBoxLayout()

        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_mapping)
        mapping_btn_layout.addWidget(edit_btn)

        remove_btn = QPushButton("删除")
        remove_btn.clicked.connect(self.remove_mapping)
        mapping_btn_layout.addWidget(remove_btn)

        layout.addLayout(mapping_btn_layout)

        return widget

    def _create_stats_panel(self):
        """创建统计面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标题
        title_label = QLabel("分类统计")
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title_label)

        # 分类列表
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(["分类名称", "文件数量"])
        self.category_tree.setAlternatingRowColors(True)
        self.category_tree.setRootIsDecorated(False)
        self.category_tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.category_tree.setColumnWidth(0, 250)
        self.category_tree.setColumnWidth(1, 150)
        layout.addWidget(self.category_tree)

        # 分类操作
        category_btn_layout = QHBoxLayout()

        clear_btn = QPushButton("清空分类")
        clear_btn.clicked.connect(self.clear_category)
        category_btn_layout.addWidget(clear_btn)

        category_btn_layout.addStretch()

        layout.addLayout(category_btn_layout)

        # 统计信息
        stats_group = QGroupBox("总体统计")
        stats_layout = QFormLayout()

        self.recent_count_label = QLabel("0")
        stats_layout.addRow("最近文件数:", self.recent_count_label)

        self.category_count_label = QLabel("0")
        stats_layout.addRow("分类数量:", self.category_count_label)

        self.total_files_label = QLabel("0")
        stats_layout.addRow("分类文件总数:", self.total_files_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        layout.addStretch()

        return widget

    def load_data(self):
        """加载数据"""
        # 加载映射
        self.mapping_tree.clear()
        for dir_path, category in self.category_mapping.items():
            item = QTreeWidgetItem([dir_path, category])
            self.mapping_tree.addTopLevelItem(item)

        # 加载分类
        self.category_tree.clear()
        categories = self.history_manager.get_categories()
        for category_name, files in categories.items():
            item = QTreeWidgetItem([category_name, str(len(files))])
            item.setData(0, Qt.UserRole, category_name)
            self.category_tree.addTopLevelItem(item)

        # 更新分类下拉框
        current_text = self.category_combo.currentText()
        self.category_combo.clear()
        for category in sorted(categories.keys()):
            self.category_combo.addItem(category)
        if current_text:
            self.category_combo.setCurrentText(current_text)

        # 更新统计信息
        stats = self.history_manager.get_statistics()
        self.recent_count_label.setText(str(stats['total_recent']))
        self.category_count_label.setText(str(stats['total_categories']))
        self.total_files_label.setText(str(stats['total_category_files']))

    def add_mapping(self):
        """添加新映射"""
        dir_path = self.dir_input.text().strip()
        category_name = self.category_combo.currentText().strip()

        if not dir_path:
            QMessageBox.warning(self, "警告", "请输入目录路径")
            return

        if not category_name:
            QMessageBox.warning(self, "警告", "请输入分类名称")
            return

        # 规范化路径
        dir_path = os.path.normpath(dir_path)
        if not dir_path.endswith(os.sep):
            dir_path += os.sep

        # 检查是否已存在
        if dir_path in self.category_mapping:
            QMessageBox.warning(self, "警告", "该目录的映射已存在")
            return

        # 添加映射
        self.category_mapping[dir_path] = category_name

        # 保存
        self.history_manager.get_category_mapping()

        # 更新界面
        self.load_data()

        # 清空输入
        self.dir_input.clear()

        self.parent.show_message("✅ 映射已添加")

    def edit_mapping(self):
        """编辑映射"""
        selected_items = self.mapping_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要编辑的映射")
            return

        item = selected_items[0]
        dir_path = item.text(0)
        current_category = item.text(1)

        # 弹出编辑对话框
        from PyQt5.QtWidgets import QInputDialog
        new_category, ok = QInputDialog.getText(
            self,
            "编辑映射",
            "请输入新的分类名称:",
            text=current_category
        )

        if ok and new_category.strip():
            # 更新映射
            self.category_mapping[dir_path] = new_category.strip()
            self.history_manager.set_category_mapping(self.category_mapping)

            # 更新界面
            self.load_data()

            self.parent.show_message("✅ 映射已更新")

    def remove_mapping(self):
        """删除映射"""
        selected_items = self.mapping_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要删除的映射")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_items)} 个映射吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for item in selected_items:
                dir_path = item.text(0)
                if dir_path in self.category_mapping:
                    del self.category_mapping[dir_path]

            # 保存
            self.history_manager.set_category_mapping(self.category_mapping)

            # 更新界面
            self.load_data()

            self.parent.show_message("✅ 映射已删除")

    def clear_category(self):
        """清空分类"""
        selected_items = self.category_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要清空的分类")
            return

        item = selected_items[0]
        category_name = item.data(0, Qt.UserRole)
        if not category_name:
            return

        reply = QMessageBox.question(
            self,
            "确认清空",
            f"确定要清空分类 '{category_name}' 的所有文件记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.history_manager.clear_category(category_name)
            self.load_data()
            self.parent.show_message("✅ 分类已清空")
