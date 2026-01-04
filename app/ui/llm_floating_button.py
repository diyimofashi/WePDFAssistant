"""
LLM浮动按钮组件
在主窗口右下角显示AI助手按钮
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QRadialGradient, QBrush


class LLMFloatingButton(QWidget):
    """LLM浮动按钮"""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setFixedSize(60, 60)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        """绘制圆形按钮"""
        painter = QPainter(self)
        painter.setRenderHint(painter.Antialiasing)

        # 绘制渐变圆形背景
        gradient = QRadialGradient(30, 30, 30)
        gradient.setColorAt(0, QColor(102, 126, 234))  # #667eea
        gradient.setColorAt(1, QColor(118, 75, 162))  # #764ba2
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(Qt.NoPen))
        painter.drawEllipse(2, 2, 56, 56)

        # 绘制AI图标
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, "AI")

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """鼠标进入事件"""
        self.setCursor(Qt.PointingHandCursor)
        super().enterEvent(event)