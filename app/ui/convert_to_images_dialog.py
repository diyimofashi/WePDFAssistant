"""PDF转图片对话框"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QLineEdit, QRadioButton,
                             QGroupBox, QProgressBar, QMessageBox, QFileDialog)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import os
import platform
import subprocess

from app.utils.logger import get_logger

logger = get_logger('convert_to_images_dialog')


class ConvertToImagesDialog(QDialog):
    """PDF转图片对话框"""

    def __init__(self, parent, pdf_processor):
        super().__init__(parent)
        self.pdf_processor = pdf_processor

        if self.pdf_processor.current_file:
            file_dir = os.path.dirname(self.pdf_processor.current_file)
            file_name = os.path.basename(self.pdf_processor.current_file)
            file_name_without_ext = os.path.splitext(file_name)[0]
            self.output_dir = os.path.join(file_dir, file_name_without_ext)
        else:
            self.output_dir = ""

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PDF转图片")
        self.setFixedSize(500, 550)
        layout = QVBoxLayout()

        # 输出目录设置
        dir_group = QGroupBox("输出目录")
        dir_layout = QVBoxLayout()

        dir_btn_layout = QHBoxLayout()
        if self.output_dir:
            self.dir_label = QLabel(self.output_dir)
            self.dir_label.setStyleSheet("QLabel { color: #333; padding: 5px; background-color: #f0f8ff; border: 1px solid #4CAF50; border-radius: 3px; }")
        else:
            self.dir_label = QLabel("未选择目录")
            self.dir_label.setStyleSheet("QLabel { color: #666; padding: 5px; background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 3px; }")
        dir_btn_layout.addWidget(self.dir_label)

        select_dir_btn = QPushButton("选择目录")
        select_dir_btn.clicked.connect(self.select_output_dir)
        dir_btn_layout.addWidget(select_dir_btn)

        dir_layout.addLayout(dir_btn_layout)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        # 页面选择设置
        page_group = QGroupBox("页面选择")
        page_layout = QVBoxLayout()

        page_range_layout = QHBoxLayout()
        page_range_layout.addWidget(QLabel("转换页面:"))

        self.all_pages_radio = QRadioButton("全部页面")
        self.all_pages_radio.setChecked(True)
        self.all_pages_radio.toggled.connect(self.on_page_range_changed)
        page_range_layout.addWidget(self.all_pages_radio)

        self.custom_pages_radio = QRadioButton("指定页面:")
        self.custom_pages_radio.toggled.connect(self.on_page_range_changed)
        page_range_layout.addWidget(self.custom_pages_radio)

        self.page_range_edit = QLineEdit()
        self.page_range_edit.setPlaceholderText("如: 1,3,5-9,11-14")
        self.page_range_edit.setEnabled(False)
        page_range_layout.addWidget(self.page_range_edit)

        page_layout.addLayout(page_range_layout)

        total_pages = self.pdf_processor.get_total_pages()
        page_hint = QLabel(f"提示: 总页数 {total_pages} 页，支持格式: 单个页码(1,3,5)，连续范围(1-5)，混合(1,3,5-9)")
        page_hint.setStyleSheet("QLabel { color: #555; font-size: 11px; }")
        page_layout.addWidget(page_hint)

        page_group.setLayout(page_layout)
        layout.addWidget(page_group)

        # 图片格式设置
        format_group = QGroupBox("图片设置")
        format_layout = QVBoxLayout()

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("图片格式:"))
        self.format_combo = QComboBox()
        formats = self.pdf_processor.get_supported_image_formats()
        self.format_combo.addItems(formats)
        # 默认选择 JPEG（查找大写或小写的 JPEG）
        jpeg_index = self.format_combo.findText("JPEG", Qt.MatchFixedString)
        if jpeg_index < 0:
            jpeg_index = self.format_combo.findText("jpeg")
        if jpeg_index < 0:
            jpeg_index = self.format_combo.findText("jpg")
        if jpeg_index >= 0:
            self.format_combo.setCurrentIndex(jpeg_index)
        format_row.addWidget(self.format_combo)
        format_row.addStretch()
        format_layout.addLayout(format_row)

        dpi_row = QHBoxLayout()
        dpi_row.addWidget(QLabel("分辨率 (DPI):"))
        self.dpi_combo = QComboBox()
        recommended_dpi = self.pdf_processor.get_recommended_dpi()
        for quality, dpi in recommended_dpi.items():
            self.dpi_combo.addItem(f"{quality} ({dpi} DPI)", dpi)
        self.dpi_combo.setCurrentIndex(1)
        dpi_row.addWidget(self.dpi_combo)
        dpi_row.addStretch()
        format_layout.addLayout(dpi_row)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # 转换信息
        info_group = QGroupBox("转换信息")
        info_layout = QVBoxLayout()
        self.info_label = QLabel(f"总页数: {total_pages} 页")
        info_layout.addWidget(self.info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 按钮
        button_layout = QHBoxLayout()
        convert_btn = QPushButton("开始转换")
        convert_btn.clicked.connect(self.start_conversion)
        convert_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px; }")

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(convert_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _set_ui_enabled(self, enabled: bool):
        """设置界面控件启用状态"""
        for btn in self.findChildren(QPushButton):
            if btn.text() in ["开始转换", "选择目录", "取消"]:
                btn.setEnabled(enabled)

        self.format_combo.setEnabled(enabled)
        self.dpi_combo.setEnabled(enabled)
        self.all_pages_radio.setEnabled(enabled)
        self.custom_pages_radio.setEnabled(enabled)
        self.page_range_edit.setEnabled(enabled and self.custom_pages_radio.isChecked())
        self.dir_label.setEnabled(enabled)

    def on_page_range_changed(self):
        """页面范围选择改变事件"""
        self.page_range_edit.setEnabled(self.custom_pages_radio.isChecked())

    def select_output_dir(self):
        """选择输出目录"""
        start_dir = self.output_dir if self.output_dir and os.path.exists(self.output_dir) else ""
        directory = QFileDialog.getExistingDirectory(self, "选择图片保存目录", start_dir)
        if directory:
            self.output_dir = directory
            self.dir_label.setText(directory)
            self.dir_label.setStyleSheet("QLabel { color: #333; padding: 5px; background-color: #f0f8ff; border: 1px solid #4CAF50; border-radius: 3px; }")

    def start_conversion(self):
        """开始转换"""
        if not self.output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return

        if self.all_pages_radio.isChecked():
            page_range = "all"
        else:
            page_range = self.page_range_edit.text().strip()
            if not page_range:
                QMessageBox.warning(self, "警告", "请输入要转换的页面范围")
                return

        image_format = self.format_combo.currentText()
        dpi = self.dpi_combo.currentData()

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self._set_ui_enabled(False)

        self.conversion_thread = ConversionThread(
            self.pdf_processor, self.output_dir, dpi, image_format, page_range
        )
        self.conversion_thread.finished.connect(self.on_conversion_finished)
        self.conversion_thread.start()

    def on_conversion_finished(self, success, message):
        """转换完成回调"""
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)

        if success:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("转换成功")
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Information)

            open_dir_btn = msg_box.addButton("📂 打开目录", QMessageBox.ActionRole)
            msg_box.addButton("确定", QMessageBox.AcceptRole)

            msg_box.exec_()

            if msg_box.clickedButton() == open_dir_btn:
                try:
                    system = platform.system()
                    if system == "Windows":
                        if os.path.exists(self.output_dir):
                            os.startfile(self.output_dir)
                        else:
                            subprocess.Popen(['explorer', self.output_dir], shell=True)
                    elif system == "Darwin":
                        subprocess.Popen(['open', self.output_dir])
                    else:
                        subprocess.Popen(['xdg-open', self.output_dir])
                except Exception as e:
                    logger.error(f"打开目录失败: {e}")
                    QMessageBox.warning(self, "警告", f"无法打开目录: {str(e)}")

            self.accept()
        else:
            QMessageBox.critical(self, "转换失败", message)


class ConversionThread(QThread):
    """转换线程"""
    finished = pyqtSignal(bool, str)

    def __init__(self, pdf_processor, output_dir, dpi, image_format, page_range):
        super().__init__()
        self.pdf_processor = pdf_processor
        self.output_dir = output_dir
        self.dpi = dpi
        self.image_format = image_format
        self.page_range = page_range

    def run(self):
        try:
            success, message = self.pdf_processor.convert_pdf_to_images(
                self.output_dir, self.dpi, self.image_format, self.page_range
            )
            self.finished.emit(success, message)
        except Exception as e:
            logger.error(f"转换过程中发生错误: {e}")
            self.finished.emit(False, f"转换过程中发生错误: {str(e)}")
