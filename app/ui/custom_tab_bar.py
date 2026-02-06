"""自定义标签栏组件，支持在左右两侧添加控件"""

from PyQt5.QtWidgets import (QTabBar, QPushButton, QHBoxLayout,
                             QWidget, QLabel, QStyle)
from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QIcon


class CustomTabBar(QTabBar):
    """自定义标签栏，支持在左右两侧添加控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._left_widget = None
        self._right_widget = None
        self._extra_widget = None

        # 设置标签样式
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setMovable(True)
        self.setTabsClosable(True)

    def add_left_widget(self, widget):
        """在左侧添加控件（如历史记录按钮）"""
        self._left_widget = widget
        widget.setParent(self)
        self.update()

    def add_right_widget(self, widget):
        """在右侧添加控件（如新建按钮）"""
        self._right_widget = widget
        widget.setParent(self)
        self.update()

    def sizeHint(self):
        """返回推荐的尺寸"""
        size = super().sizeHint()
        if self._left_widget:
            size.setWidth(size.width() + self._left_widget.width() + 10)
        if self._right_widget:
            size.setWidth(size.width() + self._right_widget.width() + 10)
        return size

    def minimumSizeHint(self):
        """返回最小尺寸"""
        size = super().minimumSizeHint()
        if self._left_widget:
            size.setWidth(size.width() + self._left_widget.width() + 10)
        if self._right_widget:
            size.setWidth(size.width() + self._right_widget.width() + 10)
        return size

    def resizeEvent(self, event):
        """调整大小时，重新定位额外控件"""
        super().resizeEvent(event)
        self._position_extra_widgets()

    def _position_extra_widgets(self):
        """定位额外的左右控件"""
        if not self._left_widget and not self._right_widget:
            return

        if self._left_widget:
            # 左侧控件位置
            left_height = self._left_widget.height()
            self._left_widget.move(5, (self.height() - left_height) // 2)

        if self._right_widget:
            # 右侧控件位置
            right_width = self._right_widget.width()
            right_height = self._right_widget.height()
            self._right_widget.move(self.width() - right_width - 5,
                                  (self.height() - right_height) // 2)

    def paintEvent(self, event):
        """绘制标签"""
        # 绘制普通标签
        super().paintEvent(event)

        # 确保额外控件在最上层
        if self._left_widget:
            self._left_widget.raise_()
        if self._right_widget:
            self._right_widget.raise_()
