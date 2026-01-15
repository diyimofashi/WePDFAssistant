"""
消息气泡组件
处理用户和助手的消息显示
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFontMetrics
from typing import Optional


class MessageBubble(QFrame):
    """消息气泡组件"""

    def __init__(self, role: str, content: str, parent=None):
        super().__init__(parent)
        self._role = role
        self._content = content
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        # 使用水平布局来控制左右对齐
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)
        main_layout.setSpacing(10)

        # 根据角色设置对齐方式
        if self._role == "user":
            # 用户消息靠右，添加左侧弹性空间
            main_layout.addStretch(1)

        # 消息文本框（直接作为气泡）
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlainText(self._content)
        self._text_edit.setFrameStyle(QFrame.NoFrame)
        self._text_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._text_edit.setWordWrapMode(1)  # 启用自动换行
        self._text_edit.setObjectName("messageTextEdit")

        # 设置气泡的最大宽度
        self._text_edit.setMaximumWidth(600)

        # 设置样式
        if self._role == "user":
            self._text_edit.setStyleSheet("""
                QTextEdit#messageTextEdit {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e3f2fd, stop:1 #bbdefb);
                    border: 1px solid #90caf9;
                    border-radius: 12px;
                    padding: 12px 10px;
                    color: #1565c0;
                    font-size: 14px;
                }
            """)
        else:  # assistant
            self._text_edit.setStyleSheet("""
                QTextEdit#messageTextEdit {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #fafafa, stop:1 #f5f5f5);
                    border: 1px solid #e0e0e0;
                    border-radius: 12px;
                    padding: 12px 10px;
                    color: #424242;
                    font-size: 14px;
                }
            """)

        # 将文本框添加到主布局
        main_layout.addWidget(self._text_edit)

        if self._role == "assistant":
            # 助手消息靠左，添加右侧弹性空间
            main_layout.addStretch(1)

        # 计算并设置高度
        self._adjust_height()

    def _adjust_height(self):
        """根据内容自适应高度"""
        # 延迟调整，等待控件显示
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._calculate_and_set_height)

    def _calculate_and_set_height(self):
        """计算并设置高度"""
        from PyQt5.QtCore import QTimer

        # 获取文本框的实际宽度
        widget_width = self._text_edit.width()

        if widget_width <= 0:
            # 如果控件还未显示，等待后重试
            QTimer.singleShot(100, self._calculate_and_set_height)
            return

        # 计算文本内容
        doc = self._text_edit.document()

        # 创建临时文本框来计算文本尺寸
        temp_edit = QTextEdit()
        temp_edit.setReadOnly(True)
        temp_edit.setPlainText(self._content)
        temp_edit.setFont(self._text_edit.font())
        temp_edit.setFrameStyle(QFrame.NoFrame)
        temp_edit.setMaximumWidth(widget_width - 26)  # 减去padding
        temp_edit.setWordWrapMode(1)
        temp_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        temp_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 获取文档
        temp_doc = temp_edit.document()
        temp_doc.setTextWidth(widget_width - 26)

        # 获取内容高度
        content_height = temp_doc.size().height()

        # 删除临时控件
        temp_edit.deleteLater()

        # 计算最终高度：内容高度 + padding (上下各12px) + 边框 (2px)
        final_height = int(content_height) + 26

        # 设置最小高度
        if final_height < 44:
            final_height = 44

        # 设置固定高度
        self._text_edit.setFixedHeight(final_height)

        # 显示当前宽度用于调试
        print(f"MessageBubble: widget_width={widget_width}, content_height={content_height}, final_height={final_height}")

    def update_content(self, content: str):
        """更新消息内容"""
        self._content = content
        self._text_edit.setPlainText(content)
        self._adjust_height()
