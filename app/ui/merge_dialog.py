"""PDF合并对话框模块"""

import os
from typing import List, Dict
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QListWidget, QListWidgetItem, 
                            QCheckBox, QRadioButton, QButtonGroup, QLineEdit,
                            QFileDialog, QGroupBox, QProgressBar, QMessageBox,
                            QSplitter, QWidget, QGridLayout, QSpinBox, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from app.utils.logger import get_logger
from app.config.settings import AppSettings
from app.core.processing.pdf_merger import PDFMerger
from app.ui.page_selection_dialog import PageSelectionDialog

logger = get_logger('merge_dialog')


class MergeWorker(QThread):
    """合并工作线程"""

    progress_updated = pyqtSignal(int, str)
    merge_finished = pyqtSignal(bool, str, str)

    def __init__(self, merger, file_list, merge_config):
        super().__init__()
        self.merger = merger
        self.file_list = file_list
        self.merge_config = merge_config

    def run(self):
        """执行合并操作"""
        try:
            self.progress_updated.emit(0, "准备合并...")

            mode = self.merge_config.get('mode', 0)

            if mode == 2:  # 分组合并
                success, message, output_path = self.merger.merge_in_groups(
                    self.file_list,
                    self.merge_config.get('group_size', 5),
                    self.merge_config.get('output_dir', ''),
                    self.merge_config.get('output_name', 'merged.pdf').replace('.pdf', '')
                )
                if success:
                    self.progress_updated.emit(100, "合并完成!")
                self.merge_finished.emit(success, message, output_path if success else None)
            else:
                success, message, output_path = self.merger.merge_files(
                    self.file_list,
                    self.merge_config,
                    self.progress_updated
                )

                if success:
                    self.progress_updated.emit(100, "合并完成!")
                self.merge_finished.emit(True, message, output_path)

        except Exception as e:
            logger.error(f"合并线程出错: {e}")
            self.merge_finished.emit(False, f"合并失败: {str(e)}", None)


class MergeDialog(QDialog):
    """PDF合并对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.merger = None
        self.files_info = []
        self.file_list = []
        self.merge_worker = None
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("PDF文件合并")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 文件选择区域
        file_group = self._create_file_selection_group()
        layout.addWidget(file_group)
        
        # 合并选项区域
        options_group = self._create_options_group()
        layout.addWidget(options_group)
        
        # 输出选项区域
        output_group = self._create_output_group()
        layout.addWidget(output_group)
        
        # 进度区域
        progress_group = self._create_progress_group()
        layout.addWidget(progress_group)
        
        # 按钮区域
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)
        
    def _create_file_selection_group(self) -> QGroupBox:
        """创建文件选择区域"""
        group = QGroupBox("文件选择")
        layout = QVBoxLayout()
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        add_file_btn = QPushButton("📂 添加文件")
        add_file_btn.clicked.connect(self.add_files)
        btn_layout.addWidget(add_file_btn)
        
        add_dir_btn = QPushButton("📁 添加文件夹")
        add_dir_btn.clicked.connect(self.add_directory)
        btn_layout.addWidget(add_dir_btn)
        
        clear_btn = QPushButton("🗑️ 清除所有")
        clear_btn.clicked.connect(self.clear_files)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 文件列表
        self.file_list_widget = QListWidget()
        self.file_list_widget.setDragDropMode(QListWidget.InternalMove)
        self.file_list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list_widget.itemDoubleClicked.connect(self.select_pages_for_item)
        layout.addWidget(self.file_list_widget)
        
        # 操作按钮行
        op_btn_layout = QHBoxLayout()
        
        move_up_btn = QPushButton("⬆️ 上移")
        move_up_btn.clicked.connect(self.move_up)
        op_btn_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("⬇️ 下移")
        move_down_btn.clicked.connect(self.move_down)
        op_btn_layout.addWidget(move_down_btn)
        
        remove_btn = QPushButton("🗑️ 删除")
        remove_btn.clicked.connect(self.remove_file)
        op_btn_layout.addWidget(remove_btn)
        
        select_pages_btn = QPushButton("📄 选择页面...")
        select_pages_btn.clicked.connect(self.select_pages)
        op_btn_layout.addWidget(select_pages_btn)
        
        op_btn_layout.addStretch()
        layout.addLayout(op_btn_layout)
        
        # 统计信息
        self.stats_label = QLabel("文件: 0 | 页数: 0 | 大小: 0 MB")
        layout.addWidget(self.stats_label)
        
        group.setLayout(layout)
        return group
    
    def _create_options_group(self) -> QGroupBox:
        """创建选项区域"""
        group = QGroupBox("合并选项")
        layout = QVBoxLayout()
        
        # 合并模式
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("合并模式:"))
        
        self.mode_group = QButtonGroup()
        
        self.merge_all_radio = QRadioButton("全部合并")
        self.merge_all_radio.setChecked(True)
        self.merge_all_radio.setToolTip("将所有选中的PDF文件按顺序合并为一个文件")
        self.mode_group.addButton(self.merge_all_radio, 0)
        mode_layout.addWidget(self.merge_all_radio)

        self.merge_range_radio = QRadioButton("合并勾选的文件")
        self.merge_range_radio.setToolTip("只合并文件列表中勾选的文件")
        self.mode_group.addButton(self.merge_range_radio, 1)
        mode_layout.addWidget(self.merge_range_radio)

        self.merge_group_radio = QRadioButton("分组合并")
        self.merge_group_radio.setToolTip("将文件按指定数量分组合并,生成多个文件")
        self.mode_group.addButton(self.merge_group_radio, 2)
        mode_layout.addWidget(self.merge_group_radio)
        
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 分组合并选项容器(初始隐藏)
        self.group_options_widget = QWidget()
        group_layout = QHBoxLayout(self.group_options_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(QLabel("每组文件数:"))
        self.group_size_spin = QSpinBox()
        self.group_size_spin.setMinimum(2)
        self.group_size_spin.setMaximum(100)
        self.group_size_spin.setValue(5)
        self.group_size_spin.setToolTip("分组合并时,每多少个PDF合并为一个文件")
        group_layout.addWidget(self.group_size_spin)
        group_layout.addStretch()
        self.group_options_widget.setVisible(False)
        layout.addWidget(self.group_options_widget)

        # 复选框选项
        self.preserve_pages_check = QCheckBox("保留原页码")
        self.preserve_pages_check.setToolTip("保留每个文件的原有页码,不重新编号")
        layout.addWidget(self.preserve_pages_check)

        # 连接信号
        self.merge_all_radio.toggled.connect(self.on_merge_mode_changed)
        self.merge_range_radio.toggled.connect(self.on_merge_mode_changed)
        self.merge_group_radio.toggled.connect(self.on_merge_mode_changed)

        
        group.setLayout(layout)
        return group
    
    def _create_output_group(self) -> QGroupBox:
        """创建输出区域"""
        group = QGroupBox("输出选项")
        layout = QGridLayout()
        
        # 输出文件名
        layout.addWidget(QLabel("文件名:"), 0, 0)
        self.output_name_edit = QLineEdit("merged.pdf")
        layout.addWidget(self.output_name_edit, 0, 1)
        
        # 输出目录
        layout.addWidget(QLabel("保存位置:"), 1, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText(os.path.expanduser("~"))
        layout.addWidget(self.output_dir_edit, 1, 1)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_output_dir)
        layout.addWidget(browse_btn, 1, 2)
        
        # 加密选项
        self.encrypt_check = QCheckBox("合并后加密")
        layout.addWidget(self.encrypt_check, 2, 0)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setEnabled(False)
        layout.addWidget(self.password_edit, 2, 1)

        # 连接信号
        self.encrypt_check.toggled.connect(self.on_encrypt_toggled)
        
        group.setLayout(layout)
        return group
    
    def _create_progress_group(self) -> QGroupBox:
        """创建进度区域"""
        group = QGroupBox("合并进度")
        layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备就绪")
        layout.addWidget(self.status_label)
        
        group.setLayout(layout)
        return group

    def on_merge_mode_changed(self, checked: bool):
        """合并模式改变槽函数"""
        # 只在选中分组合并时显示分组选项
        self.group_options_widget.setVisible(self.merge_group_radio.isChecked())
        if self.merge_group_radio.isChecked():
            self.group_size_spin.setEnabled(True)
        else:
            self.group_size_spin.setEnabled(False)

    def on_encrypt_toggled(self, checked: bool):
        """加密选项改变槽函数"""
        self.password_edit.setEnabled(checked)
        if checked:
            self.password_edit.setFocus()

    def _create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        
        layout.addStretch()
        
        self.start_btn = QPushButton("🚀 开始合并")
        self.start_btn.clicked.connect(self.start_merge)
        layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)
        
        return layout
    
    def add_files(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "选择PDF文件",
            AppSettings.get_last_open_dir(),
            "PDF文件 (*.pdf)"
        )
        
        if files:
            self._add_files_to_list(files)
            AppSettings.set_last_open_dir(os.path.dirname(files[0]))
    
    def add_directory(self):
        """添加文件夹"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择文件夹",
            AppSettings.get_last_open_dir()
        )
        
        if dir_path:
            files = []
            for file in os.listdir(dir_path):
                if file.lower().endswith('.pdf'):
                    files.append(os.path.join(dir_path, file))
            
            if files:
                self._add_files_to_list(files)
                AppSettings.set_last_open_dir(dir_path)
            else:
                QMessageBox.warning(self, "提示", "该文件夹中没有PDF文件")
    
    def _add_files_to_list(self, files: List[str]):
        """添加文件到列表"""
        if not self.merger:
            self.merger = PDFMerger()
            
        for file_path in files:
            if file_path not in self.file_list:
                info = self.merger.get_file_info(file_path)
                if info:
                    self.file_list.append(file_path)
                    self.files_info.append(info)
                    
                    # 创建列表项
                    item = QListWidgetItem()
                    item.setText(f"☑ {info['name']} ({info['pages']}页, {info['size_mb']:.2f}MB)")
                    item.setData(Qt.UserRole, len(self.files_info) - 1)
                    self.file_list_widget.addItem(item)
        
        self._update_stats()
    
    def remove_file(self):
        """删除选中文件"""
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要删除的文件")
            return
            
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认删除")
        msg_box.setText(f"确定要删除选中的 {len(selected_items)} 个文件吗?")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮文本为中文
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        reply = msg_box.exec_()
        
        if reply == QMessageBox.Yes:
            # 从后往前删除,避免索引错乱
            for item in reversed(selected_items):
                index = item.data(Qt.UserRole)
                self.file_list_widget.takeItem(self.file_list_widget.row(item))
                del self.file_list[index]
                del self.files_info[index]
            
            self._update_file_list_display()
            self._update_stats()
    
    def clear_files(self):
        """清除所有文件"""
        if not self.file_list:
            return
            
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认清除")
        msg_box.setText("确定要清除所有文件吗?")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮文本为中文
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        reply = msg_box.exec_()
        
        if reply == QMessageBox.Yes:
            self.file_list_widget.clear()
            self.file_list.clear()
            self.files_info.clear()
            self._update_stats()
    
    def move_up(self):
        """上移选中项"""
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            row = self.file_list_widget.row(item)
            if row > 0:
                # 交换文件列表中的顺序
                self.file_list[row], self.file_list[row-1] = self.file_list[row-1], self.file_list[row]
                self.files_info[row], self.files_info[row-1] = self.files_info[row-1], self.files_info[row]
        
        self._update_file_list_display()
    
    def move_down(self):
        """下移选中项"""
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            return
            
        for item in reversed(selected_items):
            row = self.file_list_widget.row(item)
            if row < self.file_list_widget.count() - 1:
                # 交换文件列表中的顺序
                self.file_list[row], self.file_list[row+1] = self.file_list[row+1], self.file_list[row]
                self.files_info[row], self.files_info[row+1] = self.files_info[row+1], self.files_info[row]
        
        self._update_file_list_display()
    
    def select_pages(self):
        """选择选中文件的页面"""
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要设置页面的文件")
            return
            
        dialog = PageSelectionDialog(self)
        
        for item in selected_items:
            index = item.data(Qt.UserRole)
            info = self.files_info[index]
            dialog.set_file_info(info)
            
            if dialog.exec_() == QDialog.Accepted:
                page_range = dialog.get_page_range()
                info['selected_pages'] = page_range
                
                # 更新显示
                range_text = "全部" if page_range == 'all' else page_range
                item.setText(f"☑ {info['name']} ({info['pages']}页, {range_text}, {info['size_mb']:.2f}MB)")
    
    def select_pages_for_item(self, item: QListWidgetItem):
        """双击文件项选择页面"""
        index = item.data(Qt.UserRole)
        info = self.files_info[index]
        
        dialog = PageSelectionDialog(self)
        dialog.set_file_info(info)
        
        if dialog.exec_() == QDialog.Accepted:
            page_range = dialog.get_page_range()
            info['selected_pages'] = page_range
            
            range_text = "全部" if page_range == 'all' else page_range
            item.setText(f"☑ {info['name']} ({info['pages']}页, {range_text}, {info['size_mb']:.2f}MB)")
    
    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            self.output_dir_edit.text()
        )
        
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def start_merge(self):
        """开始合并"""
        if not self.file_list:
            QMessageBox.warning(self, "提示", "请先添加要合并的PDF文件")
            return
            
        output_name = self.output_name_edit.text().strip()
        if not output_name:
            QMessageBox.warning(self, "提示", "请输入输出文件名")
            self.output_name_edit.setFocus()
            return
            
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir or not os.path.exists(output_dir):
            QMessageBox.warning(self, "提示", "请选择有效的输出目录")
            return
            
        # 构建合并配置
        page_ranges = {}
        for idx, info in enumerate(self.files_info):
            selected_pages = info.get('selected_pages', 'all')
            page_ranges[self.file_list[idx]] = selected_pages
            
        merge_config = {
            'output_name': output_name,
            'output_dir': output_dir,
            'mode': self.mode_group.checkedId(),
            'page_ranges': page_ranges,
            'group_size': self.group_size_spin.value(),
            'preserve_page_numbers': self.preserve_pages_check.isChecked(),
            'encrypt': self.encrypt_check.isChecked(),
            'password': self.password_edit.text()
        }
        
        # 禁用UI
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        
        # 启动合并线程
        self.merger = PDFMerger()
        self.merge_worker = MergeWorker(self.merger, self.file_list, merge_config)
        self.merge_worker.progress_updated.connect(self.update_progress)
        self.merge_worker.merge_finished.connect(self.on_merge_finished)
        self.merge_worker.start()
    
    def update_progress(self, value: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def on_merge_finished(self, success: bool, message: str, output_path: str):
        """合并完成"""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(
                self,
                "合并成功",
                message + f"\n\n输出文件:\n{output_path}"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "合并失败",
                message
            )
    
    def _update_file_list_display(self):
        """更新文件列表显示"""
        self.file_list_widget.clear()
        for idx, info in enumerate(self.files_info):
            item = QListWidgetItem()
            range_text = info.get('selected_pages', 'all')
            range_display = "全部" if range_text == 'all' else range_text
            item.setText(f"☑ {info['name']} ({info['pages']}页, {range_display}, {info['size_mb']:.2f}MB)")
            item.setData(Qt.UserRole, idx)
            self.file_list_widget.addItem(item)
    
    def _update_stats(self):
        """更新统计信息"""
        total_pages = sum(info['pages'] for info in self.files_info)
        total_size = sum(info['size'] for info in self.files_info)
        
        self.stats_label.setText(
            f"文件: {len(self.files_info)} | "
            f"页数: {total_pages} | "
            f"大小: {total_size / (1024*1024):.2f} MB"
        )
