"""
消息气泡组件
处理用户和助手的消息显示
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFontMetrics, QTextOption
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

        # 关键：使用正确的尺寸策略
        # 水平方向：最小，根据内容扩展，但不超过最大宽度
        # 垂直方向：最小，根据内容扩展
        self._text_edit.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self._text_edit.setWordWrapMode(QTextOption.WordWrap)
        self._text_edit.setObjectName("messageTextEdit")

        # 设置气泡的最大宽度和最小宽度
        self._text_edit.setMaximumWidth(600)
        self._text_edit.setMinimumWidth(100)

        # 设置样式
        if self._role == "user":
            self._text_edit.setStyleSheet("""
                QTextEdit#messageTextEdit {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e3f2fd, stop:1 #bbdefb);
                    border: 1px solid #90caf9;
                    border-radius: 12px;
                    padding: 5px 5px;
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
                    padding: 5px 5px;
                    color: #424242;
                    font-size: 14px;
                }
            """)

        # 将文本框添加到主布局
        main_layout.addWidget(self._text_edit)

        if self._role == "assistant":
            # 助手消息靠左，添加右侧弹性空间
            main_layout.addStretch(1)

        # 延迟调整高度，确保控件已经显示并有了正确的宽度
        QTimer.singleShot(100, self._adjust_height)

    def _adjust_height(self):
        """根据内容自适应高度和宽度"""
        # 获取文档
        doc = self._text_edit.document()

        # 获取控件的实际宽度
        widget_width = self._text_edit.width()

        # 如果宽度还是0或太小，延迟重试
        if widget_width < 100:
            QTimer.singleShot(100, self._adjust_height)
            return

        # 重置文档宽度，让文档自然换行
        doc.setTextWidth(-1)

        # 获取自然尺寸（文档理想的最小尺寸）
        doc_size = doc.size()

        # 计算理想的宽度（让文本尽量少换行）
        ideal_width = int(doc_size.width()) + 24  # 加上padding

        # 限制在合理范围内
        min_width = 100
        max_width = 600
        ideal_width = max(min_width, min(ideal_width, max_width))

        # 设置文档宽度，让文档按这个宽度重新排版
        doc.setTextWidth(ideal_width - 24)

        # 重新获取文档大小
        doc_size = doc.size()
        content_height = doc_size.height()

        # 计算最终高度：内容高度 + 上下padding（24px）
        min_height = 44  # 单行文本的最小高度
        final_height = max(min_height, int(content_height))

        # 设置宽度和高度
        self._text_edit.setMinimumWidth(ideal_width)
        self._text_edit.setMaximumWidth(ideal_width)
        self._text_edit.setFixedHeight(final_height)

    def update_content(self, content: str):
        """更新消息内容"""
        self._content = content
        self._text_edit.setPlainText(content)
        # 延迟调整高度
        QTimer.singleShot(100, self._adjust_height)

