"""截图OCR选区组件
支持在PDF页面上通过鼠标拖拽绘制选区，用于截图OCR
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.logger import get_logger
logger = get_logger('screenshot_ocr_widget')

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont


class ScreenshotOCRWidget(QWidget):
    """截图OCR选区组件 - 在PDF页面上绘制选区"""

    # 信号定义
    selection_finished = pyqtSignal(QRect)  # 选区完成信号，传递选区矩形
    selection_canceled = pyqtSignal()  # 选区取消信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = None  # 父级PDF页面组件

        # 选区相关属性
        self.is_selecting = False  # 是否正在选择
        self.start_pos = QPoint()  # 选择起始点
        self.current_pos = QPoint()  # 当前鼠标位置
        self.selection_rect = QRect()  # 选区矩形
        self.page_index = -1  # 当前页面索引

        # UI样式配置
        self.selection_color = QColor(255, 0, 0, 30)  # 选区填充色（半透明红色）
        self.selection_border_color = QColor(255, 0, 0)  # 选区边框色（红色）
        self.selection_border_width = 2  # 边框宽度

        # 初始化UI
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 尺寸提示标签（动态显示）
        self.size_label = QLabel(self)
        self.size_label.setVisible(False)
        self.size_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        self.main_layout.addWidget(self.size_label)

    def start_selection(self, page_index, parent_widget):
        """
        开始选区模式

        Args:
            page_index: 当前页面索引
            parent_widget: 父级PDF页面组件
        """
        logger.debug(f"[start_selection] 开始选区模式，页面索引: {page_index}")

        self.page_index = page_index
        self.parent_widget = parent_widget

        # 重置选区状态
        self.is_selecting = True
        self.start_pos = QPoint()
        self.current_pos = QPoint()
        self.selection_rect = QRect()

        # 隐藏尺寸提示
        self.size_label.setVisible(False)

        # 设置鼠标样式
        self.setCursor(Qt.CrossCursor)

        # 强制重绘以显示蒙层
        self.update()

        logger.debug("[start_selection] 选区模式已激活")

    def cancel_selection(self):
        """取消选区"""
        logger.debug("[cancel_selection] 取消选区")

        self.is_selecting = False
        self.selection_rect = QRect()
        self.size_label.setVisible(False)

        # 恢复鼠标样式
        self.setCursor(Qt.ArrowCursor)

        # 触发取消信号
        self.selection_canceled.emit()

        # 重绘
        self.update()

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if not self.is_selecting:
            return

        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.selection_rect = QRect()
            logger.debug(f"[mousePressEvent] 选区起始点: ({self.start_pos.x()}, {self.start_pos.y()})")

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not self.is_selecting:
            return

        if event.buttons() & Qt.LeftButton:
            self.current_pos = event.pos()

            # 计算选区矩形（支持反向拖拽）
            self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()

            # 更新尺寸标签位置和内容
            self._update_size_label()

            # 重绘选区
            self.update()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if not self.is_selecting:
            return

        if event.button() == Qt.LeftButton:
            # 检查选区是否有效（面积大于0）
            if self.selection_rect.isValid() and self.selection_rect.width() > 5 and self.selection_rect.height() > 5:
                logger.debug(f"[mouseReleaseEvent] 选区完成: {self.selection_rect}")

                # 隐藏尺寸标签
                self.size_label.setVisible(False)

                # 结束选区
                self.is_selecting = False
                self.setCursor(Qt.ArrowCursor)

                # 触发选区完成信号
                self.selection_finished.emit(self.selection_rect)

                # 重绘（清除选区）
                self.update()
            else:
                # 选区太小，忽略
                logger.debug("[mouseReleaseEvent] 选区太小，忽略")
                self.cancel_selection()

    def keyPressEvent(self, event):
        """键盘事件"""
        if not self.is_selecting:
            super().keyPressEvent(event)
            return

        # ESC键取消选区
        if event.key() == Qt.Key_Escape:
            self.cancel_selection()

    def _update_size_label(self):
        """更新尺寸标签的位置和内容"""
        if not self.selection_rect.isValid():
            return

        # 获取选区尺寸
        width = self.selection_rect.width()
        height = self.selection_rect.height()

        # 设置标签文本
        self.size_label.setText(f"{width} × {height}")
        self.size_label.adjustSize()

        # 计算标签位置（显示在选区右下角外部）
        label_x = self.selection_rect.right() + 5
        label_y = self.selection_rect.bottom() + 5

        # 确保标签不超出窗口边界
        if label_x + self.size_label.width() > self.width():
            label_x = self.selection_rect.left() - self.size_label.width() - 5

        if label_y + self.size_label.height() > self.height():
            label_y = self.selection_rect.top() - self.size_label.height() - 5

        # 设置标签位置
        self.size_label.move(label_x, label_y)
        self.size_label.setVisible(True)

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 如果正在选区模式，绘制半透明蒙层
        if self.is_selecting:
            # 绘制整个区域的半透明蒙层（灰色）
            painter.setBrush(QBrush(QColor(128, 128, 128, 100)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())

            # 绘制选区（红色边框，半透明红色填充）
            if self.selection_rect.isValid():
                # 绘制选区填充（半透明红色）
                painter.setBrush(QBrush(self.selection_color))
                painter.setPen(QPen(self.selection_border_color, self.selection_border_width))
                painter.drawRect(self.selection_rect)

                # 绘制选区尺寸提示（在选区中心）
                text = f"{self.selection_rect.width()}×{self.selection_rect.height()}"
                font = QFont()
                font.setPointSize(10)
                painter.setFont(font)

                # 绘制文字背景
                text_rect = painter.fontMetrics().boundingRect(text)
                text_bg_rect = QRect(
                    self.selection_rect.center().x() - text_rect.width() // 2 - 5,
                    self.selection_rect.center().y() - text_rect.height() // 2 - 5,
                    text_rect.width() + 10,
                    text_rect.height() + 10
                )
                painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(text_bg_rect, 3, 3)

                # 绘制文字
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(text_bg_rect, Qt.AlignCenter, text)

        painter.end()
