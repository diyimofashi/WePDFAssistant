"""跳转页面对话框模块"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QSpinBox, QMessageBox)
from PyQt5.QtCore import Qt

from app.utils.logger import get_logger

logger = get_logger('jump_page_dialog')


class JumpPageDialog(QDialog):
    """跳转页面对话框"""

    def __init__(self, current_page: int, total_pages: int, parent=None):
        """
        初始化对话框

        Args:
            current_page: 当前页码（1基索引）
            total_pages: 总页数
            parent: 父窗口
        """
        super().__init__(parent)
        self.current_page = current_page
        self.total_pages = total_pages
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("跳转页面")
        self.setModal(True)
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)

        # 标签
        info_label = QLabel(f"总页数: {self.total_pages}")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("QLabel { color: #666; font-size: 12px; margin: 5px 0; }")
        layout.addWidget(info_label)

        # 页码输入
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("跳转到第"))

        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(self.total_pages)
        self.page_spinbox.setValue(self.current_page)
        self.page_spinbox.setAlignment(Qt.AlignCenter)
        self.page_spinbox.setFixedWidth(80)
        self.page_spinbox.setStyleSheet("QSpinBox { font-size: 14px; padding: 5px; }")
        input_layout.addWidget(self.page_spinbox)

        input_layout.addWidget(QLabel("页"))
        layout.addLayout(input_layout)

        # 快捷按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        first_btn = QPushButton("首页")
        first_btn.clicked.connect(lambda: self.page_spinbox.setValue(1))
        button_layout.addWidget(first_btn)

        last_btn = QPushButton("末页")
        last_btn.clicked.connect(lambda: self.page_spinbox.setValue(self.total_pages))
        button_layout.addWidget(last_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addSpacing(10)

        # 确定/取消按钮
        ok_cancel_layout = QHBoxLayout()
        ok_cancel_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        ok_cancel_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        ok_cancel_layout.addWidget(cancel_btn)

        ok_cancel_layout.addStretch()
        layout.addLayout(ok_cancel_layout)

    def get_target_page(self) -> int:
        """
        获取目标页码

        Returns:
            int: 目标页码（1基索引）
        """
        return self.page_spinbox.value()

    def accept(self):
        """确定按钮点击"""
        page = self.get_target_page()

        if not (1 <= page <= self.total_pages):
            QMessageBox.warning(self, "错误", f"页码必须在 1 到 {self.total_pages} 之间")
            return

        super().accept()
