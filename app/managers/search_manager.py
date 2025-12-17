"""搜索功能管理器模块"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QGroupBox, QMessageBox
from PyQt5.QtCore import Qt
from app.utils.logger import get_logger

logger = get_logger('search_manager')


class SearchManager:
    """搜索管理器 - 负责PDF文本搜索功能"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.search_results = []
        self.current_search_index = -1
        self.last_search_text = ""
        self.search_case_sensitive = False
        self.search_whole_word = False
    
    def show_search_options(self):
        """显示搜索选项对话框"""
        dialog = SearchOptionsDialog(self.parent, self.search_case_sensitive, self.search_whole_word)
        
        if dialog.exec_() == QDialog.Accepted:
            self.search_case_sensitive = dialog.case_checkbox.isChecked()
            self.search_whole_word = dialog.whole_word_checkbox.isChecked()
            
            if self.last_search_text:
                self.search_text()
    
    def search_text(self):
        """搜索PDF中的文本"""
        search_text = self.parent.search_lineedit.text().strip() if hasattr(self.parent, 'search_lineedit') else ""
        
        if not search_text:
            QMessageBox.information(self.parent, "搜索", "请输入要搜索的关键词")
            return
            
        if not self.parent.pdf_processor.fitz_document:
            QMessageBox.information(self.parent, "搜索", "请先打开PDF文件")
            return
        
        success, result = self.parent.pdf_processor.search_text(
            search_text, 
            self.search_case_sensitive, 
            self.search_whole_word
        )
        
        if success:
            self.search_results = result['results']
            self.current_search_index = 0
            self.last_search_text = search_text
            
            self.parent.show_message(result['message'])
            
            if self.search_results:
                self.highlight_current_match()
            
            self.parent.update_preview()
        else:
            self.parent.show_message(f"搜索失败: {result}")
            QMessageBox.information(self.parent, "搜索", result)
    
    def search_next(self):
        """搜索下一个匹配项"""
        if not self.search_results:
            QMessageBox.information(self.parent, "搜索", "请先执行搜索")
            return
            
        if self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            self._navigate_to_match()
            self.parent.show_message(f"第 {self.current_search_index + 1} / {len(self.search_results)} 个匹配项")
        else:
            self.current_search_index = 0
            self._navigate_to_match()
            self.parent.show_message(f"重新开始，第 1 / {len(self.search_results)} 个匹配项")
    
    def search_previous(self):
        """搜索上一个匹配项"""
        if not self.search_results:
            QMessageBox.information(self.parent, "搜索", "请先执行搜索")
            return
            
        if self.current_search_index > 0:
            self.current_search_index -= 1
            self._navigate_to_match()
            self.parent.show_message(f"第 {self.current_search_index + 1} / {len(self.search_results)} 个匹配项")
        else:
            self.current_search_index = len(self.search_results) - 1
            self._navigate_to_match()
            self.parent.show_message(f"回到末尾，第 {len(self.search_results)} / {len(self.search_results)} 个匹配项")
    
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
        self.parent.pdf_processor.highlight_search_result(
            result['page_index'], 
            result['rect']
        )


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