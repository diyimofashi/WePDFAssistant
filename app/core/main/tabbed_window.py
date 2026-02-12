"""多标签页主窗口"""

from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QMessageBox,
                             QStatusBar, QWidget, QPushButton)
from PyQt5.QtCore import QTimer
import os

from app.ui.custom_tab_bar import CustomTabBar
from app.ui.pdf_editor_widget import PDFEditorWidget
from app.ui.welcome_widget import WelcomeWidget
from app.managers.history_manager import HistoryManager
from app.managers.shortcut_manager import ShortcutManager
from app.utils.logger import get_logger


logger = get_logger('tabbed_window')


class TabbedMainWindow(QMainWindow):
    """多标签页主窗口，管理多个PDF编辑器"""

    def __init__(self):
        super().__init__()
        logger.info("TabbedMainWindow.__init__ 开始")

        # 窗口标题
        self.setWindowTitle("PDFAssistant - 多标签页模式")
        self.resize(1400, 900)
        logger.info("窗口标题和大小设置完成")

        # 初始化快捷键管理器
        self.shortcut_manager = ShortcutManager(self)
        logger.info("快捷键管理器初始化完成")

        # 标签页容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabBarAutoHide(False)
        self.tab_widget.setTabsClosable(True)  # 使用原生关闭按钮
        self.tab_widget.tabCloseRequested.connect(self.close_tab)  # 连接关闭信号
        self.tab_widget.setMovable(True)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.setAcceptDrops(True)
        self.tab_widget.dragEnterEvent = self.drag_enter_event
        self.tab_widget.dropEvent = self.drop_event

        # 自定义标签栏
        self.custom_tab_bar = CustomTabBar()
        self.tab_widget.setTabBar(self.custom_tab_bar)

        # 连接标签栏右键菜单信号
        self.custom_tab_bar.close_tab_requested.connect(self._close_tab_by_index)
        self.custom_tab_bar.close_other_tabs_requested.connect(self._close_other_tabs)
        self.custom_tab_bar.close_tabs_to_right_requested.connect(self._close_tabs_to_right)
        self.custom_tab_bar.close_tabs_to_left_requested.connect(self._close_tabs_to_left)
        self.custom_tab_bar.close_all_requested.connect(self._close_all_tabs)

        # 标记最后一个tab为新建标签页按钮
        self._new_tab_button_index = -1
        self._is_updating = False

        # 连接tab数量变化信号
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # 历史记录tab（index 0，可关闭，显示WelcomeWidget）
        self.history_manager = HistoryManager(self)
        self.welcome_widget = WelcomeWidget(self, self.history_manager)
        self.welcome_widget.file_open_requested.connect(self.open_file_in_new_tab)
        self.tab_widget.addTab(self.welcome_widget, "📜 历史")

        # 添加新建标签页按钮tab
        self._add_new_tab_button_tab()

        # 设置中央组件
        self.setCentralWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        logger.info("状态栏设置完成")

        logger.info("多标签页主窗口初始化完成")

    def _add_new_tab_button_tab(self):
        """添加新建标签页按钮tab"""
        # 创建一个空widget作为按钮
        button_widget = QWidget()
        self._new_tab_button_index = self.tab_widget.addTab(button_widget, "+")

        # 移除按钮tab的关闭按钮
        if self.custom_tab_bar:
            left_button = self.custom_tab_bar.tabButton(self._new_tab_button_index, CustomTabBar.LeftSide)
            right_button = self.custom_tab_bar.tabButton(self._new_tab_button_index, CustomTabBar.RightSide)

            if left_button:
                self.custom_tab_bar.setTabButton(self._new_tab_button_index, CustomTabBar.LeftSide, None)

            if right_button:
                self.custom_tab_bar.setTabButton(self._new_tab_button_index, CustomTabBar.RightSide, None)

        logger.debug(f"添加新建标签页按钮tab, index={self._new_tab_button_index}")

    def _is_new_tab_button_tab(self, index):
        """判断是否是新建标签页按钮tab"""
        return index == self._new_tab_button_index

    def _on_tab_changed(self, index):
        """tab切换事件处理"""
        # 如果点击的是新建标签页按钮tab，则新建tab
        if self._is_new_tab_button_tab(index):
            self.new_tab()
            # 切换回前一个tab
            if self.tab_widget.count() > 1:
                self.tab_widget.setCurrentIndex(self.tab_widget.count() - 2)
            return

        self.on_tab_changed(index)

    def new_tab(self, file_path=None):
        """新建标签页"""
        if self._is_updating:
            return

        self._is_updating = True
        logger.debug(f"new_tab: file_path={file_path}")
        editor = PDFEditorWidget(file_path, self)

        # 设置标签页标题
        if file_path:
            title = os.path.basename(file_path)
        else:
            title = "未命名"

        # 在新建标签页按钮tab之前插入新tab
        if self._new_tab_button_index > 0:
            index = self.tab_widget.insertTab(self._new_tab_button_index, editor, title)
            # 更新新建标签页按钮tab的索引
            self._new_tab_button_index += 1
        else:
            index = self.tab_widget.addTab(editor, title)
            # 将新建标签页按钮tab移到最后
            button_widget = self.tab_widget.widget(self._new_tab_button_index)
            button_text = self.tab_widget.tabText(self._new_tab_button_index)
            self.tab_widget.removeTab(self._new_tab_button_index)
            self._new_tab_button_index = self.tab_widget.addTab(button_widget, button_text)

        logger.debug(f"  addTab返回index={index}, total_tabs={self.tab_widget.count()}")
        self.tab_widget.setCurrentIndex(index)

        # 保存编辑器引用
        editor.tab_index = index

        # 连接标题变化信号
        editor.tab_title_changed.connect(
            lambda t, idx=index: self.update_tab_title(idx, t)
        )

        # 连接文件打开和保存信号，用于更新tooltip
        editor.file_opened.connect(
            lambda path, idx=index: self.tab_widget.setTabToolTip(idx, path)
        )
        editor.file_saved.connect(
            lambda path, idx=index: self.tab_widget.setTabToolTip(idx, path)
        )

        # 设置tooltip显示文件全路径（如果已提供）
        if file_path:
            self.tab_widget.setTabToolTip(index, file_path)

        # 更新状态栏
        self.update_status_bar()

        self._is_updating = False
        logger.debug(f"新建标签页: {title}, 索引: {index}")

        return index

    def _find_tab_index_by_file_path(self, file_path):
        """根据文件路径查找标签页索引

        Args:
            file_path: 文件路径

        Returns:
            找到返回标签页索引，未找到返回 None
        """
        # 标准化文件路径（处理大小写和路径分隔符）
        file_path_normalized = os.path.normpath(os.path.abspath(file_path))
        logger.debug(f"[_find_tab_index_by_file_path] 查找文件: {file_path}")
        logger.debug(f"[_find_tab_index_by_file_path] 标准化路径: {file_path_normalized}")

        for index in range(self.tab_widget.count()):
            # 跳过新建按钮tab和历史tab
            if self._is_new_tab_button_tab(index):
                logger.debug(f"[_find_tab_index_by_file_path] 跳过新标签页按钮tab: index={index}")
                continue

            widget = self.tab_widget.widget(index)
            logger.debug(f"[_find_tab_index_by_file_path] index={index}, widget={widget}, type={type(widget)}")

            if isinstance(widget, PDFEditorWidget):
                logger.debug(f"[_find_tab_index_by_file_path] index={index}, widget.file_path={widget.file_path}")

            if isinstance(widget, PDFEditorWidget) and widget.file_path:
                # 标准化已打开文件的路径
                opened_path_normalized = os.path.normpath(os.path.abspath(widget.file_path))
                logger.debug(f"[_find_tab_index_by_file_path] 已打开文件标准化路径: {opened_path_normalized}")
                if opened_path_normalized == file_path_normalized:
                    logger.debug(f"[_find_tab_index_by_file_path] 找到已打开的文件: {file_path}, 标签页索引: {index}")
                    return index

        logger.debug(f"[_find_tab_index_by_file_path] 未找到文件: {file_path}")
        return None

    def open_file_in_new_tab(self, file_path):
        """在新标签页打开文件，如果文件已打开则切换到该标签页"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "文件不存在", f"文件不存在: {file_path}")
            return

        # 检查文件是否已经在其他标签页中打开
        existing_tab_index = self._find_tab_index_by_file_path(file_path)
        if existing_tab_index is not None:
            # 切换到已打开的标签页
            self.tab_widget.setCurrentIndex(existing_tab_index)
            logger.info(f"文件已在标签页 {existing_tab_index} 中打开，切换到该标签页: {file_path}")
        else:
            # 在新标签页中打开文件
            self.new_tab(file_path)

    def open_file(self):
        """打开文件对话框，在新标签页打开选中的文件"""
        from PyQt5.QtWidgets import QFileDialog
        from app.config.settings import AppSettings

        last_dir = AppSettings.get_last_open_dir()

        # 弹出文件选择对话框，支持多选
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", last_dir,
            "所有支持的文件 (*.pdf *.jpg *.jpeg *.png *.bmp *.gif *.tiff *.tif *.webp *.ico);;PDF文件 (*.pdf);;图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp *.ico);;所有文件 (*.*)"
        )

        # 如果用户没有选择文件，直接返回
        if not file_paths:
            logger.info("用户取消了文件选择")
            return

        # 如果选择了多个文件，只打开第一个（或者可以创建一个临时PDF）
        if len(file_paths) > 1:
            # 目前只处理第一个文件，后续可以扩展为合并打开
            file_path = file_paths[0]
            logger.info(f"选择了多个文件，只打开第一个: {file_path}")
        else:
            file_path = file_paths[0]

        # 保存最后打开的目录
        AppSettings.set_last_open_dir(file_path)

        # 在新标签页打开文件
        if os.path.exists(file_path):
            # 检查文件是否已经在其他标签页中打开
            existing_tab_index = self._find_tab_index_by_file_path(file_path)
            if existing_tab_index is not None:
                # 切换到已打开的标签页
                self.tab_widget.setCurrentIndex(existing_tab_index)
                logger.info(f"文件已在标签页 {existing_tab_index} 中打开，切换到该标签页: {file_path}")
            else:
                # 在新标签页中打开文件
                self.new_tab(file_path)
        else:
            QMessageBox.warning(self, "文件不存在", f"文件不存在: {file_path}")

    def close_tab(self, index):
        """关闭标签页"""
        # 不允许关闭新建标签页按钮tab
        if self._is_new_tab_button_tab(index):
            return

        # 记录当前是否是激活的标签页
        current_index = self.tab_widget.currentIndex()
        is_current_tab = (index == current_index)

        editor = self.tab_widget.widget(index)

        # 如果是历史记录tab（WelcomeWidget），关闭后重新创建
        if isinstance(editor, WelcomeWidget):
            self.tab_widget.removeTab(index)
            self._new_tab_button_index -= 1
            # 重新创建历史记录tab
            self._create_history_tab()
            logger.debug("关闭历史记录tab，重新创建")
            return

        if not isinstance(editor, PDFEditorWidget):
            # 不是PDF编辑器，直接关闭
            self.tab_widget.removeTab(index)
            self._new_tab_button_index -= 1
            # 如果关闭的是当前标签页，自动选择上一个标签页
            if is_current_tab:
                self._select_previous_tab(index)
            return

        # 检查未保存的更改
        if editor.has_unsaved_changes():
            file_name = os.path.basename(editor.file_path) if editor.file_path else "未命名"
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("保存")
            msg_box.setText(f"文件 '{file_name}' 有未保存的更改，是否保存？")
            msg_box.setIcon(QMessageBox.Question)
            
            save_btn = msg_box.addButton("保存", QMessageBox.AcceptRole)
            discard_btn = msg_box.addButton("不保存", QMessageBox.DestructiveRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
            msg_box.setDefaultButton(save_btn)
            
            reply = msg_box.exec_()
            
            if msg_box.clickedButton() == save_btn:
                if not editor.save_file():
                    return  # 保存失败，不关闭
            elif msg_box.clickedButton() == cancel_btn:
                return  # 取消关闭

        # 关闭编辑器
        editor.close()

        # 移除标签页
        self.tab_widget.removeTab(index)
        self._new_tab_button_index -= 1

        # 如果关闭的是当前标签页，自动选择上一个标签页
        if is_current_tab:
            self._select_previous_tab(index)

        # 更新状态栏
        self.update_status_bar()

        logger.debug(f"关闭标签页，剩余: {self.tab_widget.count()} 个")

    def close_current_tab(self):
        """关闭当前标签页"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)

    def _create_history_tab(self):
        """创建历史记录tab"""
        self.history_manager = HistoryManager(self)
        self.welcome_widget = WelcomeWidget(self, self.history_manager)
        self.welcome_widget.file_open_requested.connect(self.open_file_in_new_tab)
        self.tab_widget.insertTab(0, self.welcome_widget, "📜 历史")

    def on_tab_changed(self, index):
        """标签页切换事件"""
        if index < 0:
            return

        # index 0 是历史记录tab
        if index == 0:
            self.setWindowTitle("PDFAssistant - 多标签页模式")
            self.update_status_bar()
            logger.debug("切换到历史记录tab")
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

    def _close_tab_by_index(self, index):
        """关闭指定标签页"""
        self.close_tab(index)

    def _close_other_tabs(self, current_index):
        """关闭除当前标签页外的所有标签页"""
        if self._is_new_tab_button_tab(current_index):
            return

        # 从后往前关闭,避免索引变化
        for i in range(self.tab_widget.count() - 1, -1, -1):
            if i != current_index and not self._is_new_tab_button_tab(i):
                self.close_tab(i)

    def _close_tabs_to_right(self, current_index):
        """关闭当前标签页右侧的所有标签页"""
        if self._is_new_tab_button_tab(current_index):
            return

        # 从后往前关闭,避免索引变化
        for i in range(self.tab_widget.count() - 1, current_index, -1):
            if not self._is_new_tab_button_tab(i):
                self.close_tab(i)

    def _close_tabs_to_left(self, current_index):
        """关闭当前标签页左侧的所有标签页"""
        if self._is_new_tab_button_tab(current_index):
            return

        # 从后往前关闭,避免索引变化
        for i in range(current_index - 1, -1, -1):
            if not self._is_new_tab_button_tab(i):
                self.close_tab(i)

    def _close_all_tabs(self):
        """关闭所有标签页"""
        # 从后往前关闭,避免索引变化
        for i in range(self.tab_widget.count() - 1, -1, -1):
            if not self._is_new_tab_button_tab(i):
                self.close_tab(i)

    def _select_previous_tab(self, closed_index):
        """关闭标签页后，自动选择上一个标签页
        
        Args:
            closed_index: 被关闭的标签页索引
        """
        # 优先选择左侧（上一个）标签页
        previous_index = closed_index - 1

        # 如果左侧没有标签页，则选择右侧（下一个）标签页
        if previous_index < 0:
            previous_index = 0

        # 确保索引有效且不是新建标签页按钮
        if previous_index < self.tab_widget.count() and not self._is_new_tab_button_tab(previous_index):
            self.tab_widget.setCurrentIndex(previous_index)
            logger.debug(f"自动选择标签页: {previous_index}")
        elif self.tab_widget.count() > 0:
            # 如果上一个索引无效，尝试选择第一个有效标签页
            for i in range(self.tab_widget.count()):
                if not self._is_new_tab_button_tab(i):
                    self.tab_widget.setCurrentIndex(i)
                    logger.debug(f"自动选择第一个有效标签页: {i}")
                    break

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
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("退出")
            msg_box.setText(f"有 {len(unsaved_tabs)} 个文件有未保存的更改，是否保存？")
            msg_box.setIcon(QMessageBox.Question)
            
            save_all_btn = msg_box.addButton("保存所有", QMessageBox.AcceptRole)
            discard_btn = msg_box.addButton("不保存", QMessageBox.DestructiveRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
            msg_box.setDefaultButton(save_all_btn)
            
            reply = msg_box.exec_()
            
            if msg_box.clickedButton() == save_all_btn:
                # 保存所有
                for index, file_name in unsaved_tabs:
                    editor = self.tab_widget.widget(index)
                    if not editor.save_file():
                        event.ignore()
                        return
            elif msg_box.clickedButton() == cancel_btn:
                event.ignore()
                return

        event.accept()
