"""自定义标签栏组件"""

from PyQt5.QtWidgets import QTabBar, QMenu, QAction
from PyQt5.QtCore import QTimer, pyqtSignal
from app.utils.logger import get_logger

logger = get_logger('custom_tab_bar')


class CustomTabBar(QTabBar):
    """自定义标签栏"""

    # 定义右键菜单动作的信号
    close_tab_requested = pyqtSignal(int)  # 关闭标签页
    close_other_tabs_requested = pyqtSignal(int)  # 关闭其他标签页
    close_tabs_to_right_requested = pyqtSignal(int)  # 关闭右侧标签页
    close_tabs_to_left_requested = pyqtSignal(int)  # 关闭左侧标签页
    close_all_requested = pyqtSignal()  # 关闭所有标签页

    def __init__(self, parent=None):
        super().__init__(parent)
        self._context_menu_index = -1  # 记录右键点击的标签页索引

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

    def contextMenuEvent(self, event):
        """处理右键菜单事件"""
        # 获取右键点击的标签页索引
        self._context_menu_index = self.tabAt(event.pos())

        # 如果点击的不是有效标签页,不显示菜单
        if self._context_menu_index == -1:
            return

        # 创建右键菜单
        menu = QMenu(self)

        # 关闭
        close_action = QAction("关闭", self)
        close_action.triggered.connect(lambda: self.close_tab_requested.emit(self._context_menu_index))
        menu.addAction(close_action)

        # 关闭其他
        close_other_action = QAction("关闭其他", self)
        close_other_action.triggered.connect(lambda: self.close_other_tabs_requested.emit(self._context_menu_index))
        menu.addAction(close_other_action)

        # 关闭右侧
        close_right_action = QAction("关闭右侧", self)
        close_right_action.triggered.connect(lambda: self.close_tabs_to_right_requested.emit(self._context_menu_index))
        menu.addAction(close_right_action)

        # 关闭左侧
        close_left_action = QAction("关闭左侧", self)
        close_left_action.triggered.connect(lambda: self.close_tabs_to_left_requested.emit(self._context_menu_index))
        menu.addAction(close_left_action)

        # 添加分隔符
        menu.addSeparator()

        # 关闭所有
        close_all_action = QAction("关闭所有", self)
        close_all_action.triggered.connect(lambda: self.close_all_requested.emit())
        menu.addAction(close_all_action)

        # 显示菜单
        menu.exec_(self.mapToGlobal(event.pos()))

        super().contextMenuEvent(event)
