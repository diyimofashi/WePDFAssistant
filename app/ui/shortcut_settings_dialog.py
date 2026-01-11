"""快捷键设置对话框
用于配置和管理应用的所有快捷键
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.logger import get_logger
logger = get_logger('shortcut_settings_dialog')

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
                             QSplitter, QWidget, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class ShortcutInputDialog(QDialog):
    """快捷键输入对话框"""

    def __init__(self, current_shortcut, parent=None):
        super().__init__(parent)
        self.current_shortcut = current_shortcut
        self.new_shortcut = ""
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("设置快捷键")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 说明文字
        info_label = QLabel("请按下新的快捷键组合...")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("font-size: 14px; color: #666; padding: 20px;")
        layout.addWidget(info_label)

        # 快捷键显示区域
        self.shortcut_display = QLabel()
        self.shortcut_display.setAlignment(Qt.AlignCenter)
        self.shortcut_display.setMinimumHeight(80)
        self.shortcut_display.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 24px;
                font-weight: bold;
                color: #333;
                padding: 20px;
            }
        """)
        if self.current_shortcut:
            self.shortcut_display.setText(self.current_shortcut)
        else:
            self.shortcut_display.setText("无")
        layout.addWidget(self.shortcut_display)

        # 清除按钮
        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self._clear_shortcut)
        layout.addWidget(clear_btn, 0, Qt.AlignCenter)

        # 当前值显示
        current_label = QLabel(f"当前快捷键: {self.current_shortcut if self.current_shortcut else '无'}")
        current_label.setStyleSheet("color: #999; font-size: 12px;")
        current_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(current_label)

        # 冲突提示（默认隐藏）
        self.conflict_label = QLabel()
        self.conflict_label.setWordWrap(True)
        self.conflict_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffeeba;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        self.conflict_label.hide()
        layout.addWidget(self.conflict_label)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.setMinimumWidth(80)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _clear_shortcut(self):
        """清除快捷键"""
        self.new_shortcut = ""
        self.shortcut_display.setText("无")
        self.conflict_label.hide()

    def keyPressEvent(self, event):
        """处理键盘事件，捕获快捷键"""
        from PyQt5.QtGui import QKeySequence

        # 忽略某些按键
        if event.key() in [Qt.Key_Escape, Qt.Key_Enter, Qt.Key_Return]:
            return

        # 获取按键序列
        key_sequence = QKeySequence(event.modifiers() | event.key())
        shortcut = key_sequence.toString()

        # 更新显示
        self.new_shortcut = shortcut
        self.shortcut_display.setText(shortcut)

        # 检查冲突
        self._check_conflict(shortcut)

    def _check_conflict(self, shortcut):
        """检查快捷键冲突"""
        if not shortcut:
            self.conflict_label.hide()
            return

        # 获取父对话框
        parent_dialog = self.parent()
        if isinstance(parent_dialog, ShortcutSettingsDialog):
            conflict = parent_dialog.check_shortcut_conflict(shortcut)
            if conflict:
                action_name = conflict['name']
                category = conflict['category']
                self.conflict_label.setText(
                    f"⚠️  此快捷键已被「{category}/{action_name}」使用\n"
                    f"如果继续，该功能将失去快捷键。"
                )
                self.conflict_label.show()
            else:
                self.conflict_label.hide()

    def get_shortcut(self):
        """获取新设置的快捷键"""
        return self.new_shortcut


class ShortcutSettingsDialog(QDialog):
    """快捷键设置对话框"""

    shortcut_updated = pyqtSignal(str, str)  # action_id, new_shortcut

    def __init__(self, shortcut_manager, parent=None):
        super().__init__(parent)
        self.shortcut_manager = shortcut_manager
        self.all_shortcuts = {}
        self.current_category = "全部"
        self.search_keyword = ""

        self._init_ui()
        self._load_shortcuts()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("快捷键设置")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_layout.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索快捷键或功能名称...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)

        layout.addLayout(search_layout)

        # 分类筛选
        category_layout = QHBoxLayout()
        category_label = QLabel("分类:")
        category_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(200)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        category_layout.addWidget(self.category_combo)

        category_layout.addStretch()
        layout.addLayout(category_layout)

        # 快捷键表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["功能名称", "快捷键", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        # 设置样式
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                gridline-color: #eee;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #ddd;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.table)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self._on_reset_clicked)
        button_layout.addWidget(reset_btn)

        ok_btn = QPushButton("确定")
        ok_btn.setMinimumWidth(80)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _load_shortcuts(self):
        """加载快捷键数据"""
        # 获取所有快捷键
        from app.config.shortcut_config import ShortcutConfig
        self.all_shortcuts = ShortcutConfig.get_all_shortcuts()

        # 填充分类下拉框
        categories = ShortcutConfig.get_categories()
        self.category_combo.clear()
        self.category_combo.addItem("全部")
        for category in categories:
            self.category_combo.addItem(category)

        # 显示快捷键列表
        self._update_table()

    def _update_table(self):
        """更新快捷键表格"""
        # 清空表格
        self.table.setRowCount(0)

        # 过滤数据
        filtered_shortcuts = {}
        for action_id, info in self.all_shortcuts.items():
            # 分类过滤
            if self.current_category != "全部":
                if info['category'] != self.current_category:
                    continue

            # 搜索过滤
            if self.search_keyword:
                keyword_lower = self.search_keyword.lower()
                if (keyword_lower not in info['name'].lower() and
                    keyword_lower not in info['current'].lower()):
                    continue

            filtered_shortcuts[action_id] = info

        # 填充表格
        for action_id, info in filtered_shortcuts.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 功能名称
            name_item = QTableWidgetItem(info['name'])
            name_item.setData(Qt.UserRole, action_id)
            self.table.setItem(row, 0, name_item)

            # 快捷键
            shortcut_item = QTableWidgetItem(info['current'])
            self.table.setItem(row, 1, shortcut_item)

            # 操作按钮
            modify_btn = QPushButton("修改")
            modify_btn.clicked.connect(lambda checked, aid=action_id: self._on_modify_clicked(aid))
            self.table.setCellWidget(row, 2, modify_btn)

        logger.debug(f"已加载 {len(filtered_shortcuts)} 个快捷键")

    def _on_category_changed(self, category):
        """分类改变事件"""
        self.current_category = category
        self._update_table()

    def _on_search_changed(self, text):
        """搜索文本改变事件"""
        self.search_keyword = text
        self._update_table()

    def _on_modify_clicked(self, action_id):
        """修改按钮点击事件"""
        from app.config.shortcut_config import ShortcutConfig

        # 获取当前快捷键
        current_shortcut = ShortcutConfig.get_shortcut(action_id)

        # 显示输入对话框
        dialog = ShortcutInputDialog(current_shortcut, self)
        if dialog.exec_() == QDialog.Accepted:
            new_shortcut = dialog.get_shortcut()

            # 检查是否需要更新
            if new_shortcut == current_shortcut:
                return

            # 检查冲突
            conflict = self.check_shortcut_conflict(new_shortcut, exclude_action_id=action_id)
            if conflict:
                reply = QMessageBox.question(
                    self,
                    "快捷键冲突",
                    f"快捷键「{new_shortcut}」已被「{conflict['category']}/{conflict['name']}」使用。\n"
                    f"是否继续？继续后将覆盖该功能的快捷键。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.No:
                    return

            # 更新快捷键
            success, message = self.shortcut_manager.update_shortcut(action_id, new_shortcut)

            if success:
                # 更新表格
                self.all_shortcuts = ShortcutConfig.get_all_shortcuts()
                self._update_table()

                # 发送信号
                self.shortcut_updated.emit(action_id, new_shortcut)

                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.warning(self, "失败", message)

    def _on_reset_clicked(self):
        """恢复默认按钮点击事件"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要将所有快捷键恢复为默认值吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 重置所有快捷键
            self.shortcut_manager.reset_to_default()

            # 重新加载数据
            self._load_shortcuts()

            QMessageBox.information(self, "成功", "所有快捷键已恢复为默认值")

    def check_shortcut_conflict(self, shortcut, exclude_action_id=None):
        """
        检查快捷键冲突

        Args:
            shortcut: 要检查的快捷键
            exclude_action_id: 要排除的动作ID

        Returns:
            dict or None: 如果冲突，返回冲突信息；否则返回None
        """
        return self.shortcut_manager.check_conflict(shortcut, exclude_action_id)
