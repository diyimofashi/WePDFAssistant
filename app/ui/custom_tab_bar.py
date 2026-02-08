"""自定义标签栏组件"""

from PyQt5.QtWidgets import QTabBar
from PyQt5.QtCore import QTimer
from app.utils.logger import get_logger

logger = get_logger('custom_tab_bar')


class CustomTabBar(QTabBar):
    """自定义标签栏"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置标签样式
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setMovable(True)
        self.setUsesScrollButtons(True)  # 使用滚动按钮
        self.setTabsClosable(True)  # 使用原生关闭按钮

        # 设置TabBar样式表
        self.setStyleSheet("""
            QTabBar {
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                text-align: center;
                padding: 5px 10px;
                border: none;
                background: #f0f0f0;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
                min-width: 40px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-bottom: 2px solid #0078d4;
            }
            QTabBar::tab:hover:!selected {
                background: #e0e0e0;
            }
            QTabBar::close-button {
                subcontrol-position: right;
                padding: 2px;
            }
            QTabBar::close-button:hover {
                background: #ff6b6b;
                border-radius: 4px;
            }
        """)

    def _ensure_history_tab_no_close_button(self):
        """确保历史记录tab（index 0）不显示关闭按钮"""
        if self.count() == 0:
            return

        # 移除历史记录tab的关闭按钮
        left_button = self.tabButton(0, QTabBar.LeftSide)
        right_button = self.tabButton(0, QTabBar.RightSide)

        if left_button:
            self.setTabButton(0, QTabBar.LeftSide, None)
            logger.debug("已移除历史记录tab左侧关闭按钮")

        if right_button:
            self.setTabButton(0, QTabBar.RightSide, None)
            logger.debug("已移除历史记录tab右侧关闭按钮")

    def tabInserted(self, index):
        """tab插入时调用"""
        logger.debug(f"tabInserted: index={index}, tabText={self.tabText(index)}, total_tabs={self.count()}")
        super().tabInserted(index)
        # 延迟检查关闭按钮状态，确保Qt已完成自动创建
        QTimer.singleShot(0, self._ensure_history_tab_no_close_button)

    def tabRemoved(self, index):
        """tab移除时调用"""
        super().tabRemoved(index)
        # 确保历史记录tab没有关闭按钮
        QTimer.singleShot(0, self._ensure_history_tab_no_close_button)
