"""
文件选择组件
用于工具参数中的文件路径输入
"""
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
)
from PyQt5.QtCore import pyqtSignal
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileChooserWidget(QWidget):
    """文件选择组件"""

    value_changed = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        file_filter: str = "All Files (*.*)",
        mode: str = "open",  # "open" or "save"
        default_dir: Optional[str] = None
    ):
        """
        初始化文件选择组件

        Args:
            parent: 父窗口
            file_filter: 文件过滤器
            mode: 模式 ("open" 或 "save")
            default_dir: 默认目录
        """
        super().__init__(parent)
        self._file_filter = file_filter
        self._mode = mode
        self._default_dir = default_dir
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 文件路径输入框
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("选择文件...")
        self._path_edit.textChanged.connect(self._on_path_changed)
        layout.addWidget(self._path_edit)

        # 浏览按钮
        self._browse_button = QPushButton("浏览...")
        self._browse_button.clicked.connect(self._on_browse_clicked)
        layout.addWidget(self._browse_button)

    def _on_path_changed(self, path: str):
        """路径改变事件"""
        self.value_changed.emit(path)

    def _on_browse_clicked(self):
        """浏览按钮点击事件"""
        if self._mode == "open":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择文件",
                self._default_dir or "",
                self._file_filter
            )
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存文件",
                self._default_dir or "",
                self._file_filter
            )

        if file_path:
            self._path_edit.setText(file_path)

    def set_value(self, value: str) -> None:
        """设置值"""
        self._path_edit.setText(value)

    def get_value(self) -> str:
        """获取值"""
        return self._path_edit.text().strip()

    def set_placeholder(self, text: str) -> None:
        """设置占位符文本"""
        self._path_edit.setPlaceholderText(text)

    def set_file_filter(self, file_filter: str) -> None:
        """设置文件过滤器"""
        self._file_filter = file_filter

    def set_mode(self, mode: str) -> None:
        """设置模式"""
        self._mode = mode
