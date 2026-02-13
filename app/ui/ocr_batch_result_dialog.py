"""OCR批量处理结果对话框"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QTextEdit, QPushButton, QTabWidget, QWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QApplication, QSplitter, QProgressBar)
from PyQt5.QtCore import Qt, QTimer
from app.utils.logger import get_logger

logger = get_logger('ocr_batch_result_dialog')


class OCRBatchResultDialog(QDialog):
    """OCR批量处理结果对话框"""

    def __init__(self, batch_result, parent=None):
        """初始化对话框

        Args:
            batch_result: 批量处理结果字典
            parent: 父窗口
        """
        super().__init__(parent)
        self.batch_result = batch_result
        self._init_ui()
        self._populate_data()

    def add_page_result(self, page_num, result):
        """实时添加页面识别结果

        Args:
            page_num: 页码
            result: OCR结果字典
        """
        # 更新统计数据
        success_pages = self.success_table.rowCount() + 1
        total_pages = self.batch_result.get('total_pages', 0)
        failed_pages = self.failed_table.rowCount()

        # 更新统计标签
        self.stats_label.setText(
            f"总页数: <b>{total_pages}</b> | "
            f"成功: <span style='color: green;'>{success_pages}</span> | "
            f"失败: <span style='color: red;'>{failed_pages}</span>"
        )

        # 添加到成功表格
        row = self.success_table.rowCount()
        self.success_table.insertRow(row)

        # 页码
        page_item = QTableWidgetItem(f"第 {page_num + 1} 页")
        page_item.setTextAlignment(Qt.AlignCenter)
        self.success_table.setItem(row, 0, page_item)

        # 文本预览（前100个字符）
        text = result.get('text', '')
        preview = text[:100] + '...' if len(text) > 100 else text
        preview_item = QTableWidgetItem(preview)
        self.success_table.setItem(row, 1, preview_item)

        # 查看按钮
        view_btn = QPushButton("查看")
        view_btn.clicked.connect(lambda checked, p=page_num, t=text: self._show_text_detail(p, t))
        self.success_table.setCellWidget(row, 2, view_btn)

        # 添加到完整文本区域
        self._add_to_full_text(page_num, text)

        # 更新标签页标题
        self.tab_widget.setTabText(0, f"成功页面 ({self.success_table.rowCount()})")

        # 滚动到最新添加的行
        self.success_table.scrollToBottom()

        # 刷新界面
        QApplication.processEvents()

    def update_progress(self, current_page, total_pages, message):
        """更新进度

        Args:
            current_page: 当前页码
            total_pages: 总页数
            message: 状态消息
        """
        # 更新进度条
        self.progress_bar.setValue(current_page)

        # 更新状态文本
        progress_percent = int((current_page / total_pages) * 100) if total_pages > 0 else 0
        self.status_label.setText(f"{message} ({progress_percent}%)")

        # 刷新界面
        QApplication.processEvents()

    def set_pause_callback(self, pause_callback):
        """设置暂停回调函数

        Args:
            pause_callback: 暂停时的回调函数
        """
        self.pause_callback = pause_callback

    def set_resume_callback(self, resume_callback):
        """设置继续回调函数

        Args:
            resume_callback: 继续时的回调函数
        """
        self.resume_callback = resume_callback

    def _on_pause_clicked(self):
        """暂停按钮点击"""
        if self.pause_callback:
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)
            self.status_label.setText("已暂停")
            self.pause_callback()

    def _on_resume_clicked(self):
        """继续按钮点击"""
        if self.resume_callback:
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)
            self.resume_callback()

    def set_processing_complete(self):
        """设置处理完成"""
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.status_label.setText("识别完成！")
        self.progress_bar.setValue(self.progress_bar.maximum())

    def set_paused(self):
        """设置为暂停状态"""
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(True)
        self.status_label.setText("已暂停")

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("OCR批量识别结果")
        self.setMinimumSize(1000, 700)

        layout = QVBoxLayout(self)

        # 统计信息
        stats_layout = QHBoxLayout()
        total_pages = self.batch_result.get('total_pages', 0)
        success_pages = self.batch_result.get('success_pages', 0)
        failed_pages = self.batch_result.get('failed_pages', 0)

        self.stats_label = QLabel(
            f"总页数: <b>{total_pages}</b> | "
            f"成功: <span style='color: green;'>{success_pages}</span> | "
            f"失败: <span style='color: red;'>{failed_pages}</span>"
        )
        self.stats_label.setStyleSheet("font-size: 14px; padding: 10px;")
        stats_layout.addWidget(self.stats_label)
        layout.addLayout(stats_layout)

        # 进度区域（包含进度条和状态文本）
        progress_group_layout = QVBoxLayout()
        progress_group_layout.setContentsMargins(5, 5, 5, 5)

        # 状态标签
        self.status_label = QLabel("准备开始识别...")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        progress_group_layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(total_pages)
        self.progress_bar.setValue(0)
        progress_group_layout.addWidget(self.progress_bar)

        # 控制按钮
        control_btn_layout = QHBoxLayout()
        control_btn_layout.addStretch()
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        control_btn_layout.addWidget(self.pause_btn)

        self.resume_btn = QPushButton("继续")
        self.resume_btn.clicked.connect(self._on_resume_clicked)
        self.resume_btn.setEnabled(False)
        control_btn_layout.addWidget(self.resume_btn)
        progress_group_layout.addLayout(control_btn_layout)

        # 进度容器
        progress_container = QWidget()
        progress_container.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        progress_container.setLayout(progress_group_layout)
        layout.addWidget(progress_container)

        # 分割器：上方表格，下方完整文本
        self.splitter = QSplitter(Qt.Vertical)

        # 上部：标签页
        self.tab_widget = QTabWidget()
        self.splitter.addWidget(self.tab_widget)

        # 下部：完整文本显示
        self.full_text_label = QLabel("完整识别文本:")
        self.full_text_edit = QTextEdit()
        self.full_text_edit.setReadOnly(True)
        self.full_text_edit.setFontPointSize(10)

        # 创建下部容器
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.addWidget(self.full_text_label)
        bottom_layout.addWidget(self.full_text_edit)
        self.splitter.addWidget(bottom_widget)

        # 设置分割比例（表格占60%，文本占40%）
        self.splitter.setStretchFactor(0, 6)
        self.splitter.setStretchFactor(1, 4)
        self.splitter.setSizes([420, 280])

        layout.addWidget(self.splitter)

        # 成功页面标签页
        self.success_tab = QWidget()
        self._init_success_tab()
        self.tab_widget.addTab(self.success_tab, f"成功页面 ({success_pages})")

        # 失败页面标签页
        self.failed_tab = QWidget()
        self._init_failed_tab()
        self.tab_widget.addTab(self.failed_tab, f"失败页面 ({failed_pages})")

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 导出按钮
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self._export_results)
        button_layout.addWidget(self.export_btn)

        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # 控制信号回调
        self.pause_callback = None
        self.resume_callback = None

    def _init_success_tab(self):
        """初始化成功页面标签页"""
        layout = QVBoxLayout(self.success_tab)

        # 创建表格
        self.success_table = QTableWidget()
        self.success_table.setColumnCount(3)
        self.success_table.setHorizontalHeaderLabels(["页码", "识别文本预览", "操作"])

        # 设置表格属性
        self.success_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.success_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.success_table.horizontalHeader().setStretchLastSection(True)

        # 调整列宽
        header = self.success_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 页码
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 文本预览
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 操作

        layout.addWidget(self.success_table)

    def _init_failed_tab(self):
        """初始化失败页面标签页"""
        layout = QVBoxLayout(self.failed_tab)

        # 创建表格
        self.failed_table = QTableWidget()
        self.failed_table.setColumnCount(2)
        self.failed_table.setHorizontalHeaderLabels(["页码", "错误信息"])

        # 设置表格属性
        self.failed_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.failed_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.failed_table.horizontalHeader().setStretchLastSection(True)

        # 调整列宽
        header = self.failed_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 页码
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 错误信息

        layout.addWidget(self.failed_table)

    def _populate_data(self):
        """填充数据（批量完成后调用）"""
        # 填充成功页面（如果对话框在批量过程中未打开）
        success_results = self.batch_result.get('results', {})
        for page_num, result in success_results.items():
            # 检查表格中是否已存在此页
            found = False
            for row in range(self.success_table.rowCount()):
                item = self.success_table.item(row, 0)
                if item and item.text() == f"第 {page_num + 1} 页":
                    found = True
                    break

            # 如果不存在，添加
            if not found:
                self._add_page_to_success_table(page_num, result)

        # 填充失败页面
        failed_results = self.batch_result.get('errors', {})
        self.failed_table.setRowCount(len(failed_results))

        for row, (page_num, error) in enumerate(failed_results.items()):
            # 页码
            page_item = QTableWidgetItem(f"第 {page_num + 1} 页")
            page_item.setTextAlignment(Qt.AlignCenter)
            self.failed_table.setItem(row, 0, page_item)

            # 错误信息
            error_item = QTableWidgetItem(error)
            error_item.setForeground(Qt.red)
            self.failed_table.setItem(row, 1, error_item)

        # 根据数据选择显示的标签页
        if success_results:
            self.tab_widget.setCurrentIndex(0)
        elif failed_results:
            self.tab_widget.setCurrentIndex(1)

    def _add_page_to_success_table(self, page_num, result):
        """添加页面到成功表格

        Args:
            page_num: 页码
            result: OCR结果字典
        """
        row = self.success_table.rowCount()
        self.success_table.insertRow(row)

        # 页码
        page_item = QTableWidgetItem(f"第 {page_num + 1} 页")
        page_item.setTextAlignment(Qt.AlignCenter)
        self.success_table.setItem(row, 0, page_item)

        # 文本预览（前100个字符）
        text = result.get('text', '')
        preview = text[:100] + '...' if len(text) > 100 else text
        preview_item = QTableWidgetItem(preview)
        self.success_table.setItem(row, 1, preview_item)

        # 查看按钮
        view_btn = QPushButton("查看")
        view_btn.clicked.connect(lambda checked, p=page_num, t=text: self._show_text_detail(p, t))
        self.success_table.setCellWidget(row, 2, view_btn)

    def _add_to_full_text(self, page_num, text):
        """添加文本到完整文本区域

        Args:
            page_num: 页码
            text: 识别文本
        """
        current_text = self.full_text_edit.toPlainText()
        separator = "\n" if current_text else ""
        new_content = f"{current_text}{separator}{'=' * 80}\n第 {page_num + 1} 页\n{'=' * 80}\n{text}"
        self.full_text_edit.setPlainText(new_content)

        # 滚动到底部
        scrollbar = self.full_text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _show_text_detail(self, page_num, text):
        """显示文本详情

        Args:
            page_num: 页码
            text: 完整文本
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(f"第 {page_num + 1} 页 - OCR识别结果")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        # 文本显示区域
        text_edit = QTextEdit()
        text_edit.setPlainText(text)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        # 复制按钮
        copy_btn = QPushButton("复制到剪贴板")
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(text))
        layout.addWidget(copy_btn)

        dialog.exec_()

    def _copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "成功", "文本已复制到剪贴板")

    def _export_results(self):
        """导出结果"""
        from PyQt5.QtWidgets import QFileDialog

        # 选择保存路径
        file_path, file_filter = QFileDialog.getSaveFileName(
            self,
            "导出OCR结果",
            "ocr_result.json",
            "JSON文件 (*.json);;文本文件 (*.txt);;所有文件 (*.*)"
        )

        if not file_path:
            return

        try:
            # 根据文件扩展名选择导出格式
            if file_path.lower().endswith('.json'):
                self._export_json(file_path)
            else:
                self._export_txt(file_path)

        except Exception as e:
            error_msg = f"导出失败: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def _export_txt(self, file_path):
        """导出为文本格式

        Args:
            file_path: 保存路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("OCR批量识别结果\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"总页数: {self.batch_result['total_pages']}\n")
            f.write(f"成功: {self.batch_result['success_pages']}\n")
            f.write(f"失败: {self.batch_result['failed_pages']}\n\n")

            # 写入成功页面
            if self.batch_result['success_pages'] > 0:
                f.write("=" * 80 + "\n")
                f.write("成功页面\n")
                f.write("=" * 80 + "\n\n")

                for page_num in sorted(self.batch_result['results'].keys()):
                    result = self.batch_result['results'][page_num]
                    text = result.get('text', '')
                    f.write(f"\n{'=' * 80}\n")
                    f.write(f"第 {page_num + 1} 页\n")
                    f.write(f"{'=' * 80}\n")
                    f.write(f"{text}\n")

            # 写入失败页面
            if self.batch_result['failed_pages'] > 0:
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("失败页面\n")
                f.write("=" * 80 + "\n\n")

                for page_num in sorted(self.batch_result['errors'].keys()):
                    error = self.batch_result['errors'][page_num]
                    f.write(f"第 {page_num + 1} 页: {error}\n")

        QMessageBox.information(self, "成功", f"结果已导出到: {file_path}")
        logger.info(f"OCR结果已导出到: {file_path}")

    def _export_json(self, file_path):
        """导出为JSON格式

        Args:
            file_path: 保存路径
        """
        import json

        # 构建JSON数据结构
        export_data = {
            "summary": {
                "total_pages": self.batch_result['total_pages'],
                "success_pages": self.batch_result['success_pages'],
                "failed_pages": self.batch_result['failed_pages']
            },
            "pages": []
        }

        # 添加成功页面
        for page_num in sorted(self.batch_result['results'].keys()):
            result = self.batch_result['results'][page_num]
            page_data = {
                "page_number": page_num + 1,
                "status": "success",
                "full_text": result.get('text', ''),
                "ocr_blocks": []
            }

            # 构建OCR块数据
            bboxes = result.get('bboxes', [])
            confidences = result.get('confidence', [])
            text_lines = result.get('text', '').split('\n')

            # 按行组织数据
            for i, line_text in enumerate(text_lines):
                block = {
                    "line_index": i,
                    "text": line_text
                }
                # 添加bbox(如果有)
                if i < len(bboxes):
                    block['bbox'] = bboxes[i]
                # 添加置信度(如果有)
                if i < len(confidences):
                    block['confidence'] = confidences[i]

                page_data['ocr_blocks'].append(block)

            # 添加原始bbox数据(如果有)
            if bboxes:
                page_data['bboxes'] = bboxes

            # 添加原始置信度数据(如果有)
            if confidences:
                page_data['confidences'] = confidences

            export_data["pages"].append(page_data)

        # 添加失败页面
        for page_num in sorted(self.batch_result['errors'].keys()):
            error = self.batch_result['errors'][page_num]
            export_data["pages"].append({
                "page_number": page_num + 1,
                "status": "failed",
                "error": error
            })

        # 写入JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        QMessageBox.information(self, "成功", f"结果已导出到: {file_path}")
        logger.info(f"OCR结果已导出到: {file_path}")
