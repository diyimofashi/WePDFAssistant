"""
参数配置对话框
用于收集工具参数
"""
from typing import Optional, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QComboBox, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ParameterConfigDialog(QDialog):
    """参数配置对话框"""

    def __init__(
        self,
        custom_widget: Optional[Any],
        param_name: str,
        parent: Optional[Any] = None,
        description: Optional[str] = None,
        param_type: str = "string"
    ):
        """
        初始化对话框

        Args:
            custom_widget: 自定义UI组件
            param_name: 参数名称
            parent: 父窗口
            description: 参数描述
            param_type: 参数类型
        """
        super().__init__(parent)
        self._custom_widget = custom_widget
        self._param_name = param_name
        self._description = description or f"请输入 {param_name}"
        self._param_type = param_type
        self._value_widget = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("参数配置")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 参数名称和描述
        title_label = QLabel(f"<b>{self._param_name}</b>")
        layout.addWidget(title_label)

        desc_label = QLabel(self._description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666;")
        layout.addWidget(desc_label)

        # 值输入区域
        if self._custom_widget:
            # 使用自定义组件
            layout.addWidget(self._custom_widget)
            self._value_widget = self._custom_widget
        else:
            # 使用通用输入组件
            value_layout = QHBoxLayout()

            if self._param_type == "string":
                self._value_widget = QLineEdit()
            elif self._param_type == "integer":
                self._value_widget = QSpinBox()
                self._value_widget.setMinimum(0)
                self._value_widget.setMaximum(999999)
            elif self._param_type == "number":
                from PyQt5.QtWidgets import QDoubleSpinBox
                self._value_widget = QDoubleSpinBox()
                self._value_widget.setMinimum(0)
                self._value_widget.setMaximum(999999.99)
            else:
                # 默认使用文本框
                self._value_widget = QLineEdit()

            value_layout.addWidget(self._value_widget)
            layout.addLayout(value_layout)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

    def _on_ok_clicked(self):
        """确定按钮点击"""
        value = self.get_value()

        if not value:
            reply = QMessageBox.question(
                self,
                "确认",
                "参数值为空，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.No:
                return

        self.accept()

    def get_value(self) -> Any:
        """获取参数值"""
        if hasattr(self._value_widget, "get_value"):
            # 自定义组件有get_value方法
            return self._value_widget.get_value()
        else:
            # PyQt标准组件
            return self._value_widget.text() if hasattr(self._value_widget, "text") else self._value_widget.value()

    def set_value(self, value: Any) -> None:
        """设置参数值"""
        if hasattr(self._value_widget, "set_value"):
            # 自定义组件有set_value方法
            self._value_widget.set_value(value)
        elif hasattr(self._value_widget, "setText"):
            # 文本输入组件
            self._value_widget.setText(str(value))
        elif hasattr(self._value_widget, "setValue"):
            # 数值输入组件
            self._value_widget.setValue(int(value) if isinstance(value, str) else value)
