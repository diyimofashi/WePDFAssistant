"""密码输入对话框"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel)
from PyQt5.QtCore import Qt
from app.utils.logger import get_logger

logger = get_logger('password_dialog')


class PasswordDialog(QDialog):
    """密码输入对话框"""

    def __init__(self, parent=None, title="", max_attempts=5):
        super().__init__(parent)
        self.password = ""
        self.title = title
        self.max_attempts = max_attempts
        self.attempts = 0
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle(self.title)
        self.setFixedWidth(350)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 密码输入框
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(35)
        self.password_input.textChanged.connect(self._on_password_changed)

        layout.addWidget(self.password_input)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.ok_button = QPushButton("确定")
        self.ok_button.setMinimumHeight(35)
        self.ok_button.setMinimumWidth(100)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setEnabled(False)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 回车键提交
        self.password_input.returnPressed.connect(self._on_ok_clicked)

    def _on_password_changed(self, text):
        """密码输入变化时更新按钮状态"""
        self.ok_button.setEnabled(bool(text.strip()))

    def _on_ok_clicked(self):
        """点击确定按钮"""
        self.accept()

    def get_password(self):
        """获取输入的密码"""
        return self.password_input.text().strip()

    def clear_password(self):
        """清除密码输入框"""
        self.password_input.clear()
        self.password_input.setFocus()

    @classmethod
    def get_user_password(cls, parent=None, title="", max_attempts=5):
        """静态方法：弹出对话框并获取用户输入的密码，支持多次尝试"""
        for attempt in range(max_attempts):
            dialog = cls(parent, title, max_attempts)
            if dialog.exec_() == QDialog.Accepted:
                password = dialog.get_password()
                logger.debug(f"用户第{attempt + 1}次输入了密码")
                return password
            else:
                logger.debug("用户取消了密码输入")
                return None
        logger.debug(f"密码尝试次数已达{max_attempts}次")
        return None
