"""搜索功能管理器模块"""

from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QMessageBox, QLineEdit,
                             QLabel, QWidget, QFrame, QGroupBox, QCheckBox, QPushButton)
from PyQt5.QtCore import Qt
import fitz
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
        self.search_input.setPlaceholderText("请输入要搜索的关键词")
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
        self.search_btn.clicked.connect(self.search_manager.search_new_query)
        nav_layout.addWidget(self.search_btn)

        layout.addLayout(nav_layout)

        # 搜索结果信息
        self.result_label = QLabel("未搜索")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.result_label)

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
            self.search_panel.setFixedWidth(400)  # 设置固定宽度，高度自适应

        self.search_panel.show()
        self.search_panel.activateWindow()
        self.search_panel.search_input.setFocus()

    def search_text(self):
        """搜索PDF中的文本（包括OCR插入的文本）"""
        if self.search_panel:
            search_text = self.search_panel.get_search_text()
        else:
            # 如果搜索面板不存在，尝试从父窗口获取（兼容旧代码）
            search_text = self.parent.search_lineedit.text().strip() if hasattr(self.parent, 'search_lineedit') else ""
            
        # 添加调试日志，确认获取的搜索文本
        logger.debug(f"开始搜索，获取的搜索文本: '{search_text}'")
    
        if not search_text:
            logger.debug("搜索文本为空，提示用户输入关键词")
            msg_box = QMessageBox(self.parent)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("搜索")
            msg_box.setText("请输入要搜索的关键词")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
            return

        if not self.parent.pdf_processor.fitz_document:
            msg_box = QMessageBox(self.parent)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("搜索")
            msg_box.setText("请先打开PDF文件")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
            return

        # 检查是否存在OCR可搜索PDF处理器，如果是，则使用其文档
        # 不在搜索后自动切换回原始文档，保持当前文档状态
        current_doc_path = getattr(self.parent.pdf_processor, 'current_file', None)
        
        if hasattr(self.parent, 'ocr_searchable_handler') and self.parent.ocr_searchable_handler:
            # 如果启用了OCR可搜索PDF功能，确保使用正确的文档
            try:
                # 获取当前应该使用的文档路径
                searchable_doc_path = self.parent.ocr_searchable_handler.get_current_document_path()
                if searchable_doc_path:
                    # 确保当前文档是正确的OCR可搜索PDF
                    current_doc_is_searchable = self.parent.ocr_searchable_handler.is_using_searchable_pdf
                    if current_doc_is_searchable:
                        # 如果当前正在使用可搜索PDF，无需切换
                        logger.debug(f"当前正在使用OCR可搜索PDF进行搜索: {searchable_doc_path}")
                    else:
                        # 如果当前不是可搜索PDF，暂时切换
                        logger.debug(f"临时切换到OCR可搜索PDF进行搜索: {searchable_doc_path}")
                        current_page = self.parent.pdf_processor.current_page
                        current_zoom = getattr(self.parent.pdf_processor, 'zoom_factor', 1.0)
                        
                        # 关闭当前文档并打开可搜索文档
                        self.parent.pdf_processor.fitz_document.close()
                        self.parent.pdf_processor.fitz_document = fitz.open(searchable_doc_path)
                        self.parent.pdf_processor.current_page = current_page
                        setattr(self.parent.pdf_processor, 'zoom_factor', current_zoom)
            except Exception as e:
                logger.warning(f"切换到可搜索PDF文档失败，使用原始文档进行搜索: {e}")

        # 直接使用PDF原生搜索（包括OCR插入的文本）
        success, result = self.parent.pdf_processor.search_text(
            search_text,
            self.search_case_sensitive,
            self.search_whole_word
        )

        if success:
            self.search_results = result['results']
            self.last_search_text = search_text

            # 更新搜索面板的结果标签
            if self.search_panel:
                self.search_panel.update_result_label(result['message'])

            self.parent.show_message(result['message'])

            if self.search_results:
                # 设置初始索引为0（第一个匹配项）
                self.current_search_index = 0
                self._navigate_to_match()  # 跳转到第一个匹配项
            else:
                self.parent.update_preview()  # 如果没有结果，仍需更新预览
        else:
            # 更新搜索面板的结果标签
            if self.search_panel:
                self.search_panel.update_result_label("搜索失败")
            self.parent.show_message(f"搜索失败: {result}")
            msg_box = QMessageBox(self.parent)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("搜索")
            msg_box.setText(result)
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
            

    
    def search_next_match(self):
        """搜索按钮：执行搜索或跳到下一个匹配项"""
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
    
    def search_new_query(self):
        """重新执行搜索，不管之前是否有搜索结果"""
        self.search_text()

    def search_next(self):
        """搜索下一个匹配项"""
        if not self.search_results:
            msg_box = QMessageBox(self.parent)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("搜索")
            msg_box.setText("请先执行搜索")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
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
            msg_box = QMessageBox(self.parent)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("搜索")
            msg_box.setText("请先执行搜索")
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
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
        
        # 确保UI滚动到目标页面
        if hasattr(self.parent, 'virtual_scroll'):
            # 滚动到目标页面（使用1基索引）
            self.parent.virtual_scroll.scroll_to_page(result['page_index'])
    
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