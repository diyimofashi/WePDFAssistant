"""
操作气泡组件
处理用户需要执行的操作界面
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QFrame, QFileDialog, QProgressBar, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from typing import Dict, Any


class ActionBubble(QFrame):
    """用户操作气泡组件"""
    action_completed = pyqtSignal(str, dict)
    
    def __init__(self, action_type: str, params: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._action_type = action_type
        self._params = params
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        
        # 创建操作区域
        action_widget = QFrame()
        action_widget.setObjectName("actionBubble")
        action_widget.setStyleSheet("""
            #actionBubble {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #fff3e0, stop:1 #ffe0b2);
                border: 2px solid #ffcc80;
                border-radius: 15px;
                padding: 2px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff9800, stop:1 #f57c00);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 14px;
                min-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ffa726, stop:1 #ff9800);
            }
            QPushButton:pressed {
                background: #ef6c00;
            }
            QLineEdit {
                border: 2px solid #ffcc80;
                border-radius: 8px;
                padding: 8px;
                background: white;
                font-size: 14px;
            }
            QTextEdit {
                border: 2px solid #ffcc80;
                border-radius: 8px;
                padding: 8px;
                background: white;
                font-size: 14px;
            }
            QProgressBar {
                border: 1px solid #ffcc80;
                border-radius: 5px;
                text-align: center;
                min-height: 20px;
                background: #fff3e0;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff9800, stop:1 #f57c00);
                border-radius: 4px;
            }
        """)
        
        action_layout = QVBoxLayout(action_widget)
        action_layout.setContentsMargins(15, 12, 15, 12)
        action_layout.setSpacing(12)
        
        # 标题
        title = QLabel(self._get_action_title())
        title.setStyleSheet("""
            QLabel {
                color: #e65100;
                font-weight: bold;
                font-size: 15px;
                padding-bottom: 5px;
            }
        """)
        action_layout.addWidget(title)
        
        # 根据操作类型创建相应的UI
        if self._action_type == "file_chooser":
            self._create_file_chooser_ui(action_layout)
        elif self._action_type == "confirm":
            self._create_confirm_ui(action_layout)
        elif self._action_type == "input":
            self._create_input_ui(action_layout)
        elif self._action_type == "select_option":
            self._create_select_option_ui(action_layout)
        elif self._action_type == "progress":
            self._create_progress_ui(action_layout)
        elif self._action_type == "password":
            self._create_password_ui(action_layout)
        else:
            self._create_generic_ui(action_layout)
        
        layout.addWidget(action_widget)
        self._add_shadow_effect()
    
    def _add_shadow_effect(self):
        """添加阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
    
    def _get_action_title(self) -> str:
        """获取操作标题"""
        titles = {
            "file_chooser": "📁 请选择文件",
            "confirm": "❓ 请确认",
            "input": "✏️ 请输入",
            "select_option": "📋 请选择选项",
            "progress": "⏳ 进度显示",
            "password": "🔐 请输入密码",
            "number": "🔢 请输入数字",
            "color": "🎨 请选择颜色",
        }
        return titles.get(self._action_type, "⚙️ 需要操作")
    
    def _create_file_chooser_ui(self, layout: QVBoxLayout):
        """创建文件选择UI"""
        purpose = self._params.get("purpose", "选择文件")
        file_filter = self._params.get("file_filter", "所有文件 (*.*)")
        save_mode = self._params.get("save_mode", False)
        
        desc = QLabel(f"用途: {purpose}")
        desc.setStyleSheet("color: #5d4037; font-size: 12px;")
        layout.addWidget(desc)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if save_mode:
            choose_button = QPushButton("💾 选择保存位置")
        else:
            choose_button = QPushButton("📂 选择文件")
        choose_button.clicked.connect(self._choose_file)
        button_layout.addWidget(choose_button)
        
        layout.addLayout(button_layout)
    
    def _choose_file(self):
        """选择文件"""
        purpose = self._params.get("purpose", "选择文件")
        file_filter = self._params.get("file_filter", "所有文件 (*.*)")
        save_mode = self._params.get("save_mode", False)
        default_path = self._params.get("default_path", "")
        
        if save_mode:
            # 保存模式：使用保存对话框
            file_path, _ = QFileDialog.getSaveFileName(self, purpose, default_path, file_filter)
        else:
            # 打开模式：使用打开对话框
            file_path, _ = QFileDialog.getOpenFileName(self, purpose, default_path, file_filter)
        
        if file_path:
            result = {
                "file_path": file_path,
                "message": f"已选择文件: {file_path}",
                "save_mode": save_mode  # 返回保存模式信息
            }
            self.action_completed.emit("file_chooser", result)
    
    def _create_confirm_ui(self, layout: QVBoxLayout):
        """创建确认UI"""
        message = self._params.get("message", "请确认操作")
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #5d4037; font-size: 13px;")
        layout.addWidget(msg_label)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("❌ 取消")
        cancel_button.clicked.connect(lambda: self.action_completed.emit("confirm", {"confirmed": False}))
        button_layout.addWidget(cancel_button)
        
        confirm_button = QPushButton("✅ 确认")
        confirm_button.clicked.connect(lambda: self.action_completed.emit("confirm", {"confirmed": True}))
        button_layout.addWidget(confirm_button)
        
        layout.addLayout(button_layout)
    
    def _create_input_ui(self, layout: QVBoxLayout):
        """创建输入UI"""
        placeholder = self._params.get("placeholder", "请输入内容")
        
        input_edit = QTextEdit()
        input_edit.setMaximumHeight(60)
        input_edit.setPlaceholderText(placeholder)
        input_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #bdbdbd;
                border-radius: 6px;
                padding: 8px;
                background: white;
                font-size: 13px;
            }
        """)
        layout.addWidget(input_edit)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        submit_button = QPushButton("✓ 提交")
        submit_button.clicked.connect(
            lambda: self.action_completed.emit("input", {"value": input_edit.toPlainText()})
        )
        button_layout.addWidget(submit_button)
        
        layout.addLayout(button_layout)
    
    def _create_generic_ui(self, layout: QVBoxLayout):
        """创建通用UI"""
        message = self._params.get("message", "需要执行操作")
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #5d4037; font-size: 13px;")
        layout.addWidget(msg_label)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("✓ 确定")
        ok_button.clicked.connect(lambda: self.action_completed.emit("generic", {}))
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
    
    def _create_select_option_ui(self, layout: QVBoxLayout):
        """创建选项选择UI"""
        message = self._params.get("message", "请选择一个选项")
        options = self._params.get("options", [])
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #5d4037; font-size: 13px;")
        layout.addWidget(msg_label)
        
        # 创建选项按钮
        options_layout = QHBoxLayout()
        for option in options:
            if isinstance(option, dict):
                label = option.get("label", option.get("value", str(option)))
                value = option.get("value", label)
            else:
                label = str(option)
                value = option
            
            option_button = QPushButton(label)
            option_button.clicked.connect(
                lambda checked, val=value: self.action_completed.emit("select_option", {"value": val, "label": label})
            )
            options_layout.addWidget(option_button)
        
        layout.addLayout(options_layout)
    
    def _create_progress_ui(self, layout: QVBoxLayout):
        """创建进度显示UI"""
        message = self._params.get("message", "处理中...")
        progress = self._params.get("progress", 0)
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #5d4037; font-size: 13px;")
        layout.addWidget(msg_label)
        
        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setValue(progress)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdbdbd;
                border-radius: 5px;
                text-align: center;
                min-height: 20px;
                background: #fafafa;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 3px;
            }
        """)
        layout.addWidget(progress_bar)
    
    def _create_password_ui(self, layout: QVBoxLayout):
        """创建密码输入UI"""
        message = self._params.get("message", "请输入密码")
        placeholder = self._params.get("placeholder", "密码")
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #5d4037; font-size: 13px;")
        layout.addWidget(msg_label)
        
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        password_edit.setPlaceholderText(placeholder)
        password_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #bdbdbd;
                border-radius: 6px;
                padding: 8px;
                background: white;
                font-size: 13px;
            }
        """)
        layout.addWidget(password_edit)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        submit_button = QPushButton("✓ 提交")
        submit_button.clicked.connect(
            lambda: self.action_completed.emit("password", {"value": password_edit.text()})
        )
        button_layout.addWidget(submit_button)
        
        layout.addLayout(button_layout)