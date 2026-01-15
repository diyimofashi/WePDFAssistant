"""页面选择对话框模块"""

from typing import Dict
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QRadioButton, QButtonGroup, 
                            QLineEdit, QSpinBox, QMessageBox, QCheckBox,
                            QListWidget, QListWidgetItem, QGroupBox)
from PyQt5.QtCore import Qt

logger = None


class PageSelectionDialog(QDialog):
    """页面选择对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_pages = 0
        self.file_name = ""
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("选择页面")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 文件信息
        self.file_info_label = QLabel("文件: - | 总页数: -")
        layout.addWidget(self.file_info_label)
        
        # 选择模式
        mode_group = QGroupBox("选择模式")
        mode_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup()
        
        self.all_pages_radio = QRadioButton("全部页面")
        self.all_pages_radio.setChecked(True)
        self.mode_group.addButton(self.all_pages_radio, 0)
        mode_layout.addWidget(self.all_pages_radio)
        
        # 页面范围
        range_layout = QHBoxLayout()
        self.range_radio = QRadioButton("页面范围:")
        self.mode_group.addButton(self.range_radio, 1)
        range_layout.addWidget(self.range_radio)
        
        self.range_start = QSpinBox()
        self.range_start.setMinimum(1)
        self.range_start.setEnabled(False)
        range_layout.addWidget(self.range_start)
        
        range_layout.addWidget(QLabel("到"))
        
        self.range_end = QSpinBox()
        self.range_end.setMinimum(1)
        self.range_end.setEnabled(False)
        range_layout.addWidget(self.range_end)
        
        mode_layout.addLayout(range_layout)
        
        # 自定义范围
        custom_layout = QHBoxLayout()
        self.custom_radio = QRadioButton("自定义范围:")
        self.mode_group.addButton(self.custom_radio, 2)
        custom_layout.addWidget(self.custom_radio)
        
        self.custom_range_edit = QLineEdit()
        self.custom_range_edit.setPlaceholderText("如: 1-5, 8, 10-12")
        self.custom_range_edit.setEnabled(False)
        custom_layout.addWidget(self.custom_range_edit)
        
        custom_layout.addWidget(QLabel("(支持范围: 如1-5, 8, 10-12)"))
        mode_layout.addLayout(custom_layout)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 页面预览
        preview_group = QGroupBox("页面预览")
        preview_layout = QVBoxLayout()
        
        self.preview_list = QListWidget()
        self.preview_list.setIconSize(self.preview_list.gridSize())
        self.preview_list.setViewMode(QListWidget.IconMode)
        self.preview_list.setResizeMode(QListWidget.Adjust)
        self.preview_list.setSpacing(5)
        preview_layout.addWidget(self.preview_list)
        
        self.preview_label = QLabel("已选择: 0 页")
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        self.range_start.valueChanged.connect(self.update_range_preview)
        self.range_end.valueChanged.connect(self.update_range_preview)
        self.custom_range_edit.textChanged.connect(self.update_custom_preview)
    
    def set_file_info(self, file_info: Dict):
        """设置文件信息"""
        self.file_name = file_info['name']
        self.total_pages = file_info['pages']
        
        self.file_info_label.setText(f"文件: {self.file_name} | 总页数: {self.total_pages}")
        
        # 设置范围默认值
        self.range_start.setValue(1)
        self.range_end.setValue(self.total_pages)
        self.range_start.setMaximum(self.total_pages)
        self.range_end.setMaximum(self.total_pages)
        
        # 更新预览
        self._update_preview()
    
    def on_mode_changed(self, button):
        """模式改变"""
        mode_id = self.mode_group.checkedId()
        
        if mode_id == 0:
            self.range_start.setEnabled(False)
            self.range_end.setEnabled(False)
            self.custom_range_edit.setEnabled(False)
        elif mode_id == 1:
            self.range_start.setEnabled(True)
            self.range_end.setEnabled(True)
            self.custom_range_edit.setEnabled(False)
        elif mode_id == 2:
            self.range_start.setEnabled(False)
            self.range_end.setEnabled(False)
            self.custom_range_edit.setEnabled(True)
        
        self._update_preview()
    
    def update_range_preview(self):
        """更新范围预览"""
        if self.mode_group.checkedId() == 1:
            self._update_preview()
    
    def update_custom_preview(self):
        """更新自定义范围预览"""
        if self.mode_group.checkedId() == 2:
            self._update_preview()
    
    def _update_preview(self):
        """更新页面预览"""
        self.preview_list.clear()
        
        mode_id = self.mode_group.checkedId()
        pages = []
        
        if mode_id == 0:
            pages = list(range(1, self.total_pages + 1))
        elif mode_id == 1:
            start = self.range_start.value()
            end = self.range_end.value()
            pages = list(range(start, end + 1))
        elif mode_id == 2:
            custom = self.custom_range_edit.text().strip()
            pages = self._parse_custom_range(custom)
        
        # 添加页面到预览列表
        for page in pages:
            if 1 <= page <= self.total_pages:
                item = QListWidgetItem(f"{page}")
                item.setTextAlignment(Qt.AlignCenter)
                self.preview_list.addItem(item)
        
        self.preview_label.setText(f"已选择: {len(pages)} 页")
    
    def _parse_custom_range(self, range_str: str) -> list:
        """解析自定义范围"""
        pages = []
        
        try:
            parts = range_str.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    start, end = part.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    pages.extend(range(start, end + 1))
                elif part.isdigit():
                    pages.append(int(part))
        except Exception as e:
            pass
        
        return sorted(set(pages))
    
    def get_page_range(self) -> str:
        """获取页面范围字符串"""
        mode_id = self.mode_group.checkedId()
        
        if mode_id == 0:
            return 'all'
        elif mode_id == 1:
            start = self.range_start.value()
            end = self.range_end.value()
            return f"{start}-{end}"
        elif mode_id == 2:
            return self.custom_range_edit.text().strip()
        
        return 'all'
