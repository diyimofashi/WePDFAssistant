"""
输入组件
处理用户输入消息
"""
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QKeyEvent


class InputTextEdit(QTextEdit):
    """支持Enter键发送的文本输入框"""
    send_signal = pyqtSignal()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() & Qt.ControlModifier:
                # Ctrl+Enter 插入换行
                cursor = self.textCursor()
                cursor.insertText("\n")
            else:
                # 直接Enter发送消息
                event.accept()
                self.send_signal.emit()
        else:
            super().keyPressEvent(event)