"""多标签页主窗口"""

from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QPushButton,
                             QVBoxLayout, QWidget, QMessageBox, QStatusBar)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QKeySequence
import os

from app.ui.custom_tab_bar import CustomTabBar
from app.ui.pdf_editor_widget import PDFEditorWidget
from app.utils.logger import get_logger


logger = get_logger('tabbed_window')


class TabbedMainWindow(QMainWindow):
    """多标签页主窗口，管理多个PDF编辑器"""

    def __init__(self):
        super().__init__()

        # 窗口标题
        self.setWindowTitle("PDFAssistant - 多标签页模式")
        self.resize(1400, 900)

        # 标签页容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabBarAutoHide(False)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.setAcceptDrops(True)
        self.tab_widget.dragEnterEvent = self.drag_enter_event
        self.tab_widget.dropEvent = self.drop_event

        # 自定义标签栏
        self.custom_tab_bar = CustomTabBar()
        self.tab_widget.setTabBar(self.custom_tab_bar)

        # 历史记录按钮
        self.history_button = QPushButton("📜 历史")
        self.history_button.setToolTip("显示历史记录")
        self.history_button.setFixedSize(80, 28)
        self.history_button.clicked.connect(self.toggle_history_panel)
        self.custom_tab_bar.add_left_widget(self.history_button)

        # 新建Tab按钮
        self.new_tab_button = QPushButton("+")
        self.new_tab_button.setToolTip("新建标签页")
        self.new_tab_button.setFixedSize(30, 28)
        self.new_tab_button.clicked.connect(self.new_tab)
        self.custom_tab_bar.add_right_widget(self.new_tab_button)

        # 设置中央组件
        self.setCentralWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 默认添加一个空白tab
        self.new_tab()

        logger.info("多标签页主窗口初始化完成")

    def new_tab(self, file_path=None):
        """新建标签页"""
        editor = PDFEditorWidget(file_path, self)

        # 设置标签页标题
        if file_path:
            title = os.path.basename(file_path)
        else:
            title = "未命名"

        # 添加到标签页容器
        index = self.tab_widget.addTab(editor, title)
        self.tab_widget.setCurrentIndex(index)

        # 保存编辑器引用
        editor.tab_index = index

        # 连接标题变化信号
        editor.tab_title_changed.connect(
            lambda t, idx=index: self.update_tab_title(idx, t)
        )

        # 更新状态栏
        self.update_status_bar()

        logger.debug(f"新建标签页: {title}, 索引: {index}")

        return index

    def open_file_in_new_tab(self, file_path):
        """在新标签页打开文件"""
        if os.path.exists(file_path):
            self.new_tab(file_path)
        else:
            QMessageBox.warning(self, "文件不存在", f"文件不存在: {file_path}")

    def close_tab(self, index):
        """关闭标签页"""
        editor = self.tab_widget.widget(index)

        if not isinstance(editor, PDFEditorWidget):
            # 不是PDF编辑器，直接关闭
            self.tab_widget.removeTab(index)
            return

        # 检查未保存的更改
        if editor.has_unsaved_changes():
            file_name = os.path.basename(editor.file_path) if editor.file_path else "未命名"
            reply = QMessageBox.question(
                self,
                "保存",
                f"文件 '{file_name}' 有未保存的更改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                if not editor.save_file():
                    return  # 保存失败，不关闭
            elif reply == QMessageBox.Cancel:
                return  # 取消关闭

        # 关闭编辑器
        editor.close()

        # 移除标签页
        self.tab_widget.removeTab(index)

        # 如果所有tab都关闭了，创建一个空白tab
        if self.tab_widget.count() == 0:
            self.new_tab()

        # 更新状态栏
        self.update_status_bar()

        logger.debug(f"关闭标签页，剩余: {self.tab_widget.count()} 个")

    def close_current_tab(self):
        """关闭当前标签页"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)

    def on_tab_changed(self, index):
        """标签页切换事件"""
        if index < 0:
            return

        editor = self.tab_widget.widget(index)
        if isinstance(editor, PDFEditorWidget):
            # 更新窗口标题
            title = editor.file_path or "未命名"
            window_title = f"{os.path.basename(title)} - PDFAssistant"
            if editor.has_unsaved_changes():
                window_title = f"* {window_title}"
            self.setWindowTitle(window_title)

        # 更新状态栏
        self.update_status_bar()

        logger.debug(f"切换到标签页: {index}")

    def toggle_history_panel(self):
        """切换历史记录面板"""
        current_editor = self.tab_widget.currentWidget()
        if isinstance(current_editor, PDFEditorWidget):
            current_editor.toggle_history()

    def update_tab_title(self, index, title):
        """更新标签页标题"""
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.setTabText(index, title)

    def update_status_bar(self):
        """更新状态栏信息"""
        current_index = self.tab_widget.currentIndex()
        if current_index < 0:
            self.status_bar.showMessage("准备就绪")
            return

        editor = self.tab_widget.widget(current_index)
        if isinstance(editor, PDFEditorWidget):
            file_info = editor.file_path or "未命名"
            if editor.has_unsaved_changes():
                file_info = f"* {file_info}"
            self.status_bar.showMessage(f"当前文件: {file_info}")

    def drag_enter_event(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drop_event(self, event):
        """拖拽放下事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path and os.path.exists(file_path):
                    self.open_file_in_new_tab(file_path)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 检查所有tab是否有未保存的更改
        unsaved_tabs = []
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if isinstance(editor, PDFEditorWidget) and editor.has_unsaved_changes():
                file_name = os.path.basename(editor.file_path) if editor.file_path else "未命名"
                unsaved_tabs.append((i, file_name))

        if unsaved_tabs:
            # 有未保存的更改
            reply = QMessageBox.question(
                self,
                "退出",
                f"有 {len(unsaved_tabs)} 个文件有未保存的更改，是否保存？",
                QMessageBox.SaveAll | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.SaveAll
            )

            if reply == QMessageBox.SaveAll:
                # 保存所有
                for index, file_name in unsaved_tabs:
                    editor = self.tab_widget.widget(index)
                    if not editor.save_file():
                        event.ignore()
                        return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return

        event.accept()
