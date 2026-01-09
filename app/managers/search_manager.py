"""搜索功能管理器模块"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QPushButton, QGroupBox, QMessageBox, QLineEdit,
                             QLabel, QWidget, QFrame)
from PyQt5.QtCore import Qt
from app.utils.logger import get_logger

logger = get_logger('search_manager')


class SearchPanel(QWidget):
    """搜索面板"""

    def __init__(self, search_manager):
        super().__init__()
        self.search_manager = search_manager
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 搜索输入框
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        input_layout.addWidget(QLabel("🔍 搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词...")
        self.search_input.returnPressed.connect(self.search_manager.search_text)
        input_layout.addWidget(self.search_input, 1)  # stretch=1，占据更多空间
        layout.addLayout(input_layout)

        # 搜索选项
        options_group = QGroupBox("搜索选项")
        options_layout = QVBoxLayout()

        self.case_checkbox = QCheckBox("区分大小写")
        self.case_checkbox.stateChanged.connect(self._on_options_changed)
        options_layout.addWidget(self.case_checkbox)

        self.whole_word_checkbox = QCheckBox("全词匹配")
        self.whole_word_checkbox.stateChanged.connect(self._on_options_changed)
        options_layout.addWidget(self.whole_word_checkbox)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 导航按钮
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)

        self.prev_btn = QPushButton("⬆️ 上一个")
        self.prev_btn.clicked.connect(self.search_manager.search_previous)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("⬇️ 下一个")
        self.next_btn.clicked.connect(self.search_manager.search_next)
        nav_layout.addWidget(self.next_btn)

        nav_layout.addStretch()  # 添加弹簧，将搜索按钮推到最右侧

        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.clicked.connect(self.search_manager.search_next_match)
        nav_layout.addWidget(self.search_btn)

        layout.addLayout(nav_layout)

        # 搜索结果信息
        self.result_label = QLabel("未搜索")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.result_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        layout.addStretch()
        self.setLayout(layout)

    def _on_options_changed(self):
        """选项改变时更新搜索管理器"""
        self.search_manager.search_case_sensitive = self.case_checkbox.isChecked()
        self.search_manager.search_whole_word = self.whole_word_checkbox.isChecked()

    def get_search_text(self):
        """获取搜索文本"""
        return self.search_input.text().strip()

    def update_result_label(self, text):
        """更新结果标签"""
        self.result_label.setText(text)


class SearchManager:
    """搜索管理器 - 负责PDF文本搜索功能"""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.search_results = []
        self.current_search_index = -1
        self.last_search_text = ""
        self.search_case_sensitive = False
        self.search_whole_word = False
        self.search_panel = None

    def show_search_panel(self):
        """显示搜索面板"""
        if not self.search_panel:
            self.search_panel = SearchPanel(self)
            self.search_panel.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
            self.search_panel.setWindowTitle("搜索")
            self.search_panel.setFixedSize(400, 320)  # 增加宽度到400

        self.search_panel.show()
        self.search_panel.activateWindow()
        self.search_panel.search_input.setFocus()

    def show_search_options(self):
        """显示搜索选项对话框"""
        dialog = SearchOptionsDialog(self.parent, self.search_case_sensitive, self.search_whole_word)
        
        if dialog.exec_() == QDialog.Accepted:
            self.search_case_sensitive = dialog.case_checkbox.isChecked()
            self.search_whole_word = dialog.whole_word_checkbox.isChecked()
            
            if self.last_search_text:
                self.search_text()
    
    def search_text(self):
        """搜索PDF中的文本（包括OCR插入的文本）"""
        if self.search_panel:
            search_text = self.search_panel.get_search_text()
        else:
            # 如果搜索面板不存在，尝试从父窗口获取（兼容旧代码）
            search_text = self.parent.search_lineedit.text().strip() if hasattr(self.parent, 'search_lineedit') else ""

        if not search_text:
            QMessageBox.information(self.parent, "搜索", "请输入要搜索的关键词")
            return

        if not self.parent.pdf_processor.fitz_document:
            QMessageBox.information(self.parent, "搜索", "请先打开PDF文件")
            return

        # 直接使用PDF原生搜索（包括OCR插入的文本）
        success, result = self.parent.pdf_processor.search_text(
            search_text,
            self.search_case_sensitive,
            self.search_whole_word
        )

        if success:
            self.search_results = result['results']
            self.current_search_index = 0
            self.last_search_text = search_text

            # 更新搜索面板的结果标签
            if self.search_panel:
                self.search_panel.update_result_label(result['message'])

            self.parent.show_message(result['message'])

            if self.search_results:
                self.highlight_current_match()

            self.parent.update_preview()
        else:
            # 更新搜索面板的结果标签
            if self.search_panel:
                self.search_panel.update_result_label("搜索失败")
            self.parent.show_message(f"搜索失败: {result}")
            QMessageBox.information(self.parent, "搜索", result)
    
    def search_next_match(self):
        """搜索按钮：第一次执行搜索，之后跳到下一个匹配项"""
        # 如果没有搜索结果，执行搜索
        if not self.search_results:
            self.search_text()
        else:
            # 跳到下一个匹配项，循环
            if self.current_search_index < len(self.search_results) - 1:
                self.current_search_index += 1
            else:
                self.current_search_index = 0

            self._navigate_to_match()
            message = f"第 {self.current_search_index + 1} / {len(self.search_results)} 个匹配项"
            self.parent.show_message(message)
            if self.search_panel:
                self.search_panel.update_result_label(message)

    def search_next(self):
        """搜索下一个匹配项"""
        if not self.search_results:
            QMessageBox.information(self.parent, "搜索", "请先执行搜索")
            return

        if self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            self._navigate_to_match()
            message = f"第 {self.current_search_index + 1} / {len(self.search_results)} 个匹配项"
            self.parent.show_message(message)
            if self.search_panel:
                self.search_panel.update_result_label(message)
        else:
            self.current_search_index = 0
            self._navigate_to_match()
            message = f"重新开始，第 1 / {len(self.search_results)} 个匹配项"
            self.parent.show_message(message)
            if self.search_panel:
                self.search_panel.update_result_label(message)

    def search_previous(self):
        """搜索上一个匹配项"""
        if not self.search_results:
            QMessageBox.information(self.parent, "搜索", "请先执行搜索")
            return

        if self.current_search_index > 0:
            self.current_search_index -= 1
            self._navigate_to_match()
            message = f"第 {self.current_search_index + 1} / {len(self.search_results)} 个匹配项"
            self.parent.show_message(message)
            if self.search_panel:
                self.search_panel.update_result_label(message)
        else:
            self.current_search_index = len(self.search_results) - 1
            self._navigate_to_match()
            message = f"回到末尾，第 {len(self.search_results)} / {len(self.search_results)} 个匹配项"
            self.parent.show_message(message)
            if self.search_panel:
                self.search_panel.update_result_label(message)
    
    def _navigate_to_match(self):
        """导航到匹配项"""
        result = self.search_results[self.current_search_index]
        self.parent.pdf_processor.current_page = result['page_index']
        self.highlight_current_match()
        self.parent.update_preview()
    
    def highlight_current_match(self):
        """高亮当前匹配项"""
        if not self.search_results or self.current_search_index < 0:
            return

        self.parent.pdf_processor.clear_highlights()

        result = self.search_results[self.current_search_index]
        success = self.parent.pdf_processor.highlight_search_result(
            result['page_index'],
            result['rect']
        )

        if success:
            # 强制刷新页面以显示高亮
            logger.debug(f"刷新页面{result['page_index']+1}以显示高亮")
            # 清除渲染缓存
            if hasattr(self.parent.pdf_processor, 'clear_render_cache'):
                self.parent.pdf_processor.clear_render_cache()
            # 更新预览
            self.parent.update_preview()


class SearchOptionsDialog(QDialog):
    """搜索选项对话框"""
    
    def __init__(self, parent, case_sensitive, whole_word):
        super().__init__(parent)
        self.case_sensitive = case_sensitive
        self.whole_word = whole_word
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("搜索选项")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout()
        
        options_group = QGroupBox("搜索选项")
        options_layout = QVBoxLayout()
        
        self.case_checkbox = QCheckBox("区分大小写")
        self.case_checkbox.setChecked(self.case_sensitive)
        options_layout.addWidget(self.case_checkbox)
        
        self.whole_word_checkbox = QCheckBox("全词匹配")
        self.whole_word_checkbox.setChecked(self.whole_word)
        options_layout.addWidget(self.whole_word_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)