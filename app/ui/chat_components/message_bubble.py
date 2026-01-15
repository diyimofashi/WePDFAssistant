"""
消息气泡组件
处理用户和助手的消息显示
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QFrame, 
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(5)
        
        # 创建消息内容区域
        content_widget = QFrame()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(0)
        
        # 消息文本框
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlainText(self._content)
        self._text_edit.setFrameStyle(QFrame.NoFrame)
        self._text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._text_edit.setMinimumHeight(30)
        self._text_edit.setMaximumHeight(16777215)  # 设置为最大值，允许自适应
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 根据内容自适应高度
        self._adjust_height()
        
        # 设置样式
        if self._role == "user":
            content_widget.setObjectName("userBubble")
            content_widget.setStyleSheet("""
                #userBubble {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e3f2fd, stop:1 #bbdefb);
                    border: 1px solid #90caf9;
                    border-radius: 12px;
                }
                QTextEdit {
                    background: transparent;
                    border: none;
                    padding: 0;
                    color: #1565c0;
                    font-size: 14px;
                }
            """)
        else:  # assistant
            content_widget.setObjectName("assistantBubble")
            content_widget.setStyleSheet("""
                #assistantBubble {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #fafafa, stop:1 #f5f5f5);
                    border: 1px solid #e0e0e0;
                    border-radius: 12px;
                }
                QTextEdit {
                    background: transparent;
                    border: none;
                    padding: 0;
                    color: #424242;
                    font-size: 14px;
                }
            """)
        
        content_layout.addWidget(self._text_edit)
        layout.addWidget(content_widget)
        
        # 添加阴影效果
        self._add_shadow_effect()
    
    def _adjust_height(self):
        """根据内容自适应高度"""
        # 保存当前光标位置
        cursor_pos = self._text_edit.textCursor().position()
        
        # 设置一个临时的固定宽度来计算内容高度
        doc = self._text_edit.document()
        doc_width = self._text_edit.width() - 30  # 减去边距和滚动条空间
        if doc_width <= 0:  # 如果控件还未显示，使用默认宽度
            doc_width = 400
        
        doc.setTextWidth(doc_width)
        
        # 获取文档的实际内容高度
        content_height = doc.size().height()
        
        # 设置最小高度和最大高度限制
        min_height = 40
        max_height = 300  # 可根据需要调整
        
        # 计算最终高度，添加额外空间以确保文本完全显示
        final_height = max(min_height, min(int(content_height) + 25, max_height))
        
        self._text_edit.setMaximumHeight(final_height)
        
        # 重置文档宽度为自动
        doc.setTextWidth(-1)
        
        # 恢复光标位置
        cursor = self._text_edit.textCursor()
        cursor.setPosition(cursor_pos)
        self._text_edit.setTextCursor(cursor)
    
    def update_content(self, content: str):
        """更新消息内容"""
        self._content = content
        self._text_edit.setPlainText(content)
        self._adjust_height()
    
    def _add_shadow_effect(self):
        """添加阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)