"""截图OCR结果展示对话框
用于显示截图OCR识别结果，支持复制和保存
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.logger import get_logger
logger = get_logger('screenshot_result_dialog')

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,QApplication,
                             QPushButton, QLabel, QFileDialog, QMessageBox,
                             QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


class ScreenshotOCRResultDialog(QDialog):
    """截图OCR结果对话框"""

    def __init__(self, ocr_result, parent=None):
        super().__init__(parent)
        self.ocr_result = ocr_result  # OCR识别结果

        # 初始化UI
        self._init_ui()
        self._display_result()

    def _init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("OCR识别结果")
        self.setMinimumSize(600, 500)
        self.resize(800, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 结果信息
        info_layout = QHBoxLayout()
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        # 识别结果文本框
        result_group = QGroupBox("识别结果")
        result_layout = QVBoxLayout()

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Microsoft YaHei", 11))
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)

        # 选项
        options_layout = QHBoxLayout()
        self.show_details_checkbox = QCheckBox("显示详细信息（置信度、坐标等）")
        self.show_details_checkbox.stateChanged.connect(self._on_show_details_changed)
        options_layout.addWidget(self.show_details_checkbox)
        options_layout.addStretch()
        main_layout.addLayout(options_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 复制按钮
        self.copy_button = QPushButton("复制文本")
        self.copy_button.setMinimumWidth(100)
        self.copy_button.clicked.connect(self._on_copy_clicked)
        button_layout.addWidget(self.copy_button)

        # 保存按钮
        self.save_button = QPushButton("保存")
        self.save_button.setMinimumWidth(100)
        self.save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(self.save_button)

        # 关闭按钮
        self.close_button = QPushButton("关闭")
        self.close_button.setMinimumWidth(100)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

    def _display_result(self):
        """显示OCR识别结果"""
        if not self.ocr_result:
            self.result_text.setText("没有识别结果")
            self.info_label.setText("OCR识别失败")
            return

        # 检查是否成功
        if self.ocr_result.is_success():
            # 提取文本
            texts = []
            if isinstance(self.ocr_result.data, list):
                for item in self.ocr_result.data:
                    if isinstance(item, dict):
                        text = item.get("text", "")
                        if text:
                            texts.append(text)

            # 显示文本
            if texts:
                full_text = "\n".join(texts)
                self.result_text.setText(full_text)
                self.info_label.setText(f"✅ 识别成功，共 {len(texts)} 个文本块")
                self.copy_button.setEnabled(True)
                self.save_button.setEnabled(True)
            else:
                self.result_text.setText("未识别到任何文本")
                self.info_label.setText("⚠️ 识别成功，但未检测到文本")
                self.copy_button.setEnabled(False)
                self.save_button.setEnabled(False)
        else:
            self.result_text.setText(f"识别失败: {self.ocr_result.message}")
            self.info_label.setText("❌ OCR识别失败")
            self.copy_button.setEnabled(False)
            self.save_button.setEnabled(False)

    def _on_show_details_changed(self, state):
        """显示详细信息"""
        if not self.ocr_result or not self.ocr_result.is_success():
            return

        if state == Qt.Checked:
            # 显示详细信息
            details = []
            if isinstance(self.ocr_result.data, list):
                for idx, item in enumerate(self.ocr_result.data, 1):
                    if isinstance(item, dict):
                        text = item.get("text", "")
                        confidence = item.get("confidence", 0)
                        bbox = item.get("bbox", []) or item.get("box", [])

                        details.append(f"--- 文本块 {idx} ---")
                        details.append(f"文本: {text}")
                        details.append(f"置信度: {confidence:.2%}")

                        if bbox:
                            details.append(f"坐标: {bbox}")

                        details.append("")

            if details:
                self.result_text.setText("\n".join(details))
        else:
            # 只显示纯文本
            self._display_result()

    def _on_copy_clicked(self):
        """复制文本到剪贴板"""
        text = self.result_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

            # 显示提示
            self.copy_button.setText("已复制")
            QTimer.singleShot(2000, lambda: self.copy_button.setText("复制文本"))
            logger.info("[_on_copy_clicked] 文本已复制到剪贴板")

    def _on_save_clicked(self):
        """保存识别结果"""
        text = self.result_text.toPlainText()
        if not text:
            return

        # 选择保存路径
        default_name = "ocr_result.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存OCR结果",
            default_name,
            "文本文件 (*.txt);;所有文件 (*.*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)

                QMessageBox.information(self, "保存成功", f"识别结果已保存到:\n{file_path}")
                logger.info(f"[_on_save_clicked] 识别结果已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存文件时出错:\n{str(e)}")
                logger.error(f"[_on_save_clicked] 保存文件失败: {e}")
