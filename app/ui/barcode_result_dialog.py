"""条码检测结果对话框"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                           QPushButton, QLabel, QGroupBox, QApplication)
from PyQt5.QtCore import Qt
from app.utils.logger import get_logger
from collections import defaultdict

logger = get_logger('barcode_result_dialog')


class BarcodeResultDialog(QDialog):
    """条码检测结果对话框"""
    
    def __init__(self, barcodes, parent=None):
        super().__init__(parent)
        self.barcodes = barcodes
        self.init_ui()
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle("条码检测结果")
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout()
        
        # 获取去重后的条码
        unique_barcodes = self._get_unique_barcodes()
        
        total_label = QLabel(f"总条码数: {len(unique_barcodes)} (原始: {len(self.barcodes)})")
        total_label.setStyleSheet("QLabel { font-weight: bold; color: #2196F3; }")
        stats_layout.addWidget(total_label)
        
        # 按类型统计
        type_count = {}
        for barcode in unique_barcodes:
            type_count[barcode.type] = type_count.get(barcode.type, 0) + 1
        
        type_info = ", ".join([f"{k}: {v}" for k, v in type_count.items()])
        type_label = QLabel(f"类型分布: {type_info}")
        type_label.setStyleSheet("QLabel { color: #666; }")
        stats_layout.addWidget(type_label)
        
        stats_layout.addStretch()
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 结果显示区域
        result_group = QGroupBox("详细结果")
        result_layout = QVBoxLayout()
        
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        self._display_barcodes()
        
        result_layout.addWidget(self.result_display)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        copy_btn = QPushButton("复制结果")
        copy_btn.clicked.connect(self._copy_results)
        button_layout.addWidget(copy_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def _display_barcodes(self):
        """显示条码结果"""
        if not self.barcodes:
            self.result_display.setPlainText("未检测到任何条码")
            return
        
        # 获取去重后的条码
        unique_barcodes = self._get_unique_barcodes()
        
        # 按页码分组条码
        page_barcodes = defaultdict(list)
        for barcode in unique_barcodes:
            page_barcodes[barcode.page_num].append(barcode)
        
        # 构建显示文本
        display_text = f"共检测到 {len(unique_barcodes)} 个条码:\n\n"
        
        # 按页码排序显示
        for page_num in sorted(page_barcodes.keys()):
            display_text += f"第 {page_num + 1} 页:\n"
            for barcode in page_barcodes[page_num]:
                display_text += f"  • {barcode.data} ({barcode.type})\n"
            display_text += "\n"
        
        self.result_display.setPlainText(display_text)
        
    def _get_unique_barcodes(self):
        """获取去重后的条码列表"""
        # 去除重复条码（页码、类型、值都相同的条码）
        unique_barcodes = []
        seen_barcodes = set()
        
        for barcode in self.barcodes:
            # 创建唯一标识符：页码+类型+值
            identifier = (barcode.page_num, barcode.type, barcode.data)
            if identifier not in seen_barcodes:
                seen_barcodes.add(identifier)
                unique_barcodes.append(barcode)
        
        return unique_barcodes
    
    def _copy_results(self):
        """复制结果到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.result_display.toPlainText())
        # 简单提示用户已复制（实际项目中可能需要更好的提示方式）