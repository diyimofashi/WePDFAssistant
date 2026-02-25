"""批量PDF加解密处理对话框"""

import os
import shutil
import tempfile
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QProgressBar, QFileDialog, QGroupBox,
                             QLabel, QLineEdit, QCheckBox, QFormLayout, QFrame, QMessageBox,
                             QToolButton)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import fitz  # PyMuPDF
from app.utils.logger import get_logger

logger = get_logger('batch_crypto_dialog')


class BatchCryptoWorker(QThread):
    """批量加解密工作线程"""
    progress_updated = pyqtSignal(int, str, str)  # 进度, 文件名, 状态
    batch_finished = pyqtSignal(bool, str)  # 是否成功, 消息
    file_processed = pyqtSignal(str, str)  # 文件路径, 结果状态

    def __init__(self, file_list, operation_type, password, output_dir=None, overwrite=False, delete_original=False):
        super().__init__()
        self.file_list = file_list
        self.operation_type = operation_type  # 'encrypt' 或 'decrypt'
        self.password = password
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.delete_original = delete_original  # 是否删除原文件
        self.is_cancelled = False

    def run(self):
        """执行批量加解密操作"""
        success_count = 0
        total_files = len(self.file_list)
        
        for i, file_path in enumerate(self.file_list):
            if self.is_cancelled:
                self.batch_finished.emit(False, "操作已取消")
                return
            
            try:
                # 更新进度
                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress, os.path.basename(file_path), "处理中...")
                
                # 执行加解密操作
                if self.operation_type == 'encrypt':
                    result = self._encrypt_file(file_path)
                elif self.operation_type == 'decrypt':
                    result = self._decrypt_file(file_path)
                else:
                    result = False, "未知操作类型"
                
                # 更新文件状态
                status = "成功" if result[0] else f"失败: {result[1]}"
                self.file_processed.emit(file_path, status)
                
                if result[0]:
                    success_count += 1
                
                # 发送进度更新
                progress = int(((i + 1) / total_files) * 100)
                self.progress_updated.emit(progress, os.path.basename(file_path), status)
                
            except Exception as e:
                error_msg = str(e)
                self.file_processed.emit(file_path, f"错误: {error_msg}")
                logger.error(f"处理文件 {file_path} 时出错: {e}")
        
        # 完成
        self.batch_finished.emit(True, f"处理完成: {success_count}/{total_files} 个文件成功")

    def _encrypt_file(self, file_path):
        """加密单个文件"""
        try:
            # 读取原文件
            doc = fitz.open(file_path)

            # 检查是否已加密
            is_encrypted = doc.needs_pass

            # 确定输出路径
            if self.overwrite:
                # 覆盖模式：增量保存不适用于加密状态变更，使用临时文件替换
                temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                output_path = temp_path
            else:
                if self.output_dir:
                    filename = os.path.basename(file_path)
                    name, ext = os.path.splitext(filename)
                    output_path = os.path.join(self.output_dir, f"{name}_encrypted{ext}")
                else:
                    output_path = file_path.replace('.pdf', '_encrypted.pdf')

            # 设置密码并保存加密文件
            if self.password:
                doc.save(
                    output_path,
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    user_pw=self.password,
                    incremental=(not self.overwrite and not is_encrypted)  # 仅在非覆盖且未加密时使用增量保存
                )
            else:
                doc.save(
                    output_path,
                    incremental=(not self.overwrite and not is_encrypted)
                )
            doc.close()

            # 如果是覆盖模式，用临时文件替换原文件
            if self.overwrite:
                try:
                    # 尝试原子替换（同盘操作）
                    os.replace(output_path, file_path)
                except OSError:
                    # 跨盘操作，使用复制+删除
                    shutil.copy2(output_path, file_path)
                    os.remove(output_path)
                output_path = file_path

            # 如果需要删除原文件
            if self.delete_original and not self.overwrite and file_path != output_path:
                os.remove(file_path)

            return True, output_path
        except Exception as e:
            return False, str(e)

    def _decrypt_file(self, file_path):
        """解密单个文件"""
        try:
            # 读取加密文件
            doc = fitz.open(file_path)

            # 检查是否加密
            if not doc.needs_pass:
                doc.close()
                return False, "文件未加密"

            # 尝试解密
            if not doc.authenticate(self.password):
                doc.close()
                return False, "密码错误"

            # 确定输出路径
            if self.overwrite:
                # 覆盖模式：增量保存不适用于加密状态变更，使用临时文件替换
                temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                output_path = temp_path
            else:
                if self.output_dir:
                    filename = os.path.basename(file_path)
                    name, ext = os.path.splitext(filename)
                    output_path = os.path.join(self.output_dir, f"{name}_decrypted{ext}")
                else:
                    output_path = file_path.replace('.pdf', '_decrypted.pdf')

            # 保存解密文件
            doc.save(
                output_path,
                incremental=not self.overwrite  # 仅在非覆盖时使用增量保存
            )
            doc.close()

            # 如果是覆盖模式，用临时文件替换原文件
            if self.overwrite:
                try:
                    # 尝试原子替换（同盘操作）
                    os.replace(output_path, file_path)
                except OSError:
                    # 跨盘操作，使用复制+删除
                    shutil.copy2(output_path, file_path)
                    os.remove(output_path)
                output_path = file_path

            # 如果需要删除原文件
            if self.delete_original and not self.overwrite and file_path != output_path:
                os.remove(file_path)

            return True, output_path
        except Exception as e:
            return False, str(e)

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


class BatchCryptoDialog(QDialog):
    """批量PDF加解密对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量PDF加解密处理")
        self.setGeometry(200, 200, 800, 600)
        self.setModal(False)  # 非模态对话框，允许用户继续操作其他窗口
        
        self.parent = parent
        self.worker = None
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 选项卡控件
        self.tab_widget = QTabWidget()
        
        # 设置标签页样式，改善选中标签的背景色
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C0C0C0;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #F0F0F0;
                border: 1px solid #C0C0C0;
                padding: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                border-bottom-color: #FFFFFF;
            }
            QTabBar::tab:hover {
                background-color: #E6F3FF;
            }
        """)
        
        # 批量加密选项卡
        self.encrypt_tab = self.create_encrypt_tab()
        self.tab_widget.addTab(self.encrypt_tab, "批量加密")
        
        # 批量解密选项卡
        self.decrypt_tab = self.create_decrypt_tab()
        self.tab_widget.addTab(self.decrypt_tab, "批量解密")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.add_files_btn = QPushButton("添加文件")
        self.add_files_btn.clicked.connect(self.add_files)
        
        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)
        
        self.remove_selected_btn = QPushButton("移除选中")
        self.remove_selected_btn.clicked.connect(self.remove_selected)
        
        self.clear_all_btn = QPushButton("清空列表")
        self.clear_all_btn.clicked.connect(self.clear_file_list)
        
        self.process_btn = QPushButton("开始处理")
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        
        self.cancel_btn = QPushButton("取消处理")
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        
        button_layout.addWidget(self.add_files_btn)
        button_layout.addWidget(self.add_folder_btn)
        button_layout.addWidget(self.remove_selected_btn)
        button_layout.addWidget(self.clear_all_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 注意：移除了底部的状态标签，将状态信息显示在窗口标题中
        
        self.setLayout(layout)
    
    def create_encrypt_tab(self):
        """创建加密选项卡"""
        tab = QFrame()
        layout = QVBoxLayout()
        
        # 密码输入区域
        password_group = QGroupBox("加密设置")
        password_layout = QFormLayout()
        
        # 创建密码输入框和显示按钮的水平布局
        encrypt_password_layout = QHBoxLayout()
        self.encrypt_password_input = QLineEdit()
        self.encrypt_password_input.setEchoMode(QLineEdit.Password)
        encrypt_password_layout.addWidget(self.encrypt_password_input)
        
        # 创建显示/隐藏密码按钮
        self.show_encrypt_password_btn = QToolButton()
        self.show_encrypt_password_btn.setText("👁")  # 眼睛图标
        self.show_encrypt_password_btn.setCheckable(True)
        self.show_encrypt_password_btn.clicked.connect(
            lambda checked: self.encrypt_password_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        encrypt_password_layout.addWidget(self.show_encrypt_password_btn)
        password_layout.addRow("加密密码:", encrypt_password_layout)
        
        # 覆盖选项
        self.encrypt_overwrite_checkbox = QCheckBox("覆盖源文件")
        self.encrypt_overwrite_checkbox.setChecked(True)  # 默认勾选覆盖源文件
        password_layout.addRow("", self.encrypt_overwrite_checkbox)
        
        # 输出目录选择
        output_layout = QHBoxLayout()
        self.encrypt_output_path_input = QLineEdit()
        self.encrypt_output_path_input.setPlaceholderText("选择输出目录（仅在不覆盖源文件时有效）")
        self.encrypt_output_path_input.setEnabled(False)  # 默认禁用，仅在不覆盖源文件时启用
        output_layout.addWidget(self.encrypt_output_path_input)
        
        self.encrypt_browse_output_btn = QPushButton("浏览")
        self.encrypt_browse_output_btn.clicked.connect(lambda: self.browse_output_directory('encrypt'))
        output_layout.addWidget(self.encrypt_browse_output_btn)
        
        password_layout.addRow("输出目录:", output_layout)
        
        # 删除原文件选项
        self.encrypt_delete_original_checkbox = QCheckBox("处理成功后删除原文件")
        self.encrypt_delete_original_checkbox.setEnabled(False)  # 默认禁用
        password_layout.addRow("", self.encrypt_delete_original_checkbox)
        
        # 连接复选框状态变化信号
        self.encrypt_overwrite_checkbox.stateChanged.connect(lambda state: self.toggle_output_options('encrypt', state))
        
        password_group.setLayout(password_layout)
        layout.addWidget(password_group)
        
        # 文件列表
        self.encrypt_file_table = QTableWidget()
        self.encrypt_file_table.setColumnCount(3)
        self.encrypt_file_table.setHorizontalHeaderLabels(["文件名", "路径", "状态"])
        header = self.encrypt_file_table.horizontalHeader()
        # 设置为拉伸模式，使列宽更紧凑
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        layout.addWidget(QLabel("待加密文件列表:"))
        layout.addWidget(self.encrypt_file_table)
        
        tab.setLayout(layout)
        return tab
    
    def create_decrypt_tab(self):
        """创建解密选项卡"""
        tab = QFrame()
        layout = QVBoxLayout()
        
        # 密码输入区域
        password_group = QGroupBox("解密设置")
        password_layout = QFormLayout()
        
        # 创建密码输入框和显示按钮的水平布局
        decrypt_password_layout = QHBoxLayout()
        self.decrypt_password_input = QLineEdit()
        self.decrypt_password_input.setEchoMode(QLineEdit.Password)
        decrypt_password_layout.addWidget(self.decrypt_password_input)
        
        # 创建显示/隐藏密码按钮
        self.show_decrypt_password_btn = QToolButton()
        self.show_decrypt_password_btn.setText("👁")  # 眼睛图标
        self.show_decrypt_password_btn.setCheckable(True)
        self.show_decrypt_password_btn.clicked.connect(
            lambda checked: self.decrypt_password_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        decrypt_password_layout.addWidget(self.show_decrypt_password_btn)
        password_layout.addRow("解密密码:", decrypt_password_layout)
        
        # 覆盖选项
        self.decrypt_overwrite_checkbox = QCheckBox("覆盖源文件")
        self.decrypt_overwrite_checkbox.setChecked(True)  # 默认勾选覆盖源文件
        password_layout.addRow("", self.decrypt_overwrite_checkbox)
        
        # 输出目录选择
        output_layout = QHBoxLayout()
        self.decrypt_output_path_input = QLineEdit()
        self.decrypt_output_path_input.setPlaceholderText("选择输出目录（仅在不覆盖源文件时有效）")
        self.decrypt_output_path_input.setEnabled(False)  # 默认禁用，仅在不覆盖源文件时启用
        output_layout.addWidget(self.decrypt_output_path_input)
        
        self.decrypt_browse_output_btn = QPushButton("浏览")
        self.decrypt_browse_output_btn.clicked.connect(lambda: self.browse_output_directory('decrypt'))
        output_layout.addWidget(self.decrypt_browse_output_btn)
        
        password_layout.addRow("输出目录:", output_layout)
        
        # 删除原文件选项
        self.decrypt_delete_original_checkbox = QCheckBox("处理成功后删除原文件")
        self.decrypt_delete_original_checkbox.setEnabled(False)  # 默认禁用
        password_layout.addRow("", self.decrypt_delete_original_checkbox)
        
        # 连接复选框状态变化信号
        self.decrypt_overwrite_checkbox.stateChanged.connect(lambda state: self.toggle_output_options('decrypt', state))
        
        password_group.setLayout(password_layout)
        layout.addWidget(password_group)
        
        # 文件列表
        self.decrypt_file_table = QTableWidget()
        self.decrypt_file_table.setColumnCount(3)
        self.decrypt_file_table.setHorizontalHeaderLabels(["文件名", "路径", "状态"])
        header = self.decrypt_file_table.horizontalHeader()
        # 设置为拉伸模式，使列宽更紧凑
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        layout.addWidget(QLabel("待解密文件列表:"))
        layout.addWidget(self.decrypt_file_table)
        
        tab.setLayout(layout)
        return tab
    
    def add_files(self):
        """添加文件"""
        current_table = self.get_current_file_table()
        if not current_table:
            return
            
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择PDF文件", "", "PDF文件 (*.pdf)"
        )
        
        for file_path in file_paths:
            self.add_file_to_table(current_table, file_path)
    
    def add_folder(self):
        """添加文件夹中的所有PDF文件"""
        current_table = self.get_current_file_table()
        if not current_table:
            return
            
        folder_path = QFileDialog.getExistingDirectory(self, "选择包含PDF的文件夹")
        if not folder_path:
            return
            
        # 查找文件夹中的所有PDF文件
        for filename in os.listdir(folder_path):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(folder_path, filename)
                self.add_file_to_table(current_table, file_path)
    
    def add_file_to_table(self, table, file_path):
        """向表格添加文件"""
        # 检查文件是否已存在
        for row in range(table.rowCount()):
            if table.item(row, 1).text() == file_path:
                return  # 文件已存在，不重复添加
        
        row = table.rowCount()
        table.insertRow(row)
        
        filename = os.path.basename(file_path)
        table.setItem(row, 0, QTableWidgetItem(filename))
        table.setItem(row, 1, QTableWidgetItem(file_path))
        table.setItem(row, 2, QTableWidgetItem("待处理"))
    
    def get_current_file_table(self):
        """获取当前活动的文件表格"""
        current_index = self.tab_widget.currentIndex()
        if current_index == 0:  # 加密选项卡
            return self.encrypt_file_table
        elif current_index == 1:  # 解密选项卡
            return self.decrypt_file_table
        return None
    
    def remove_selected(self):
        """移除选中文件"""
        current_table = self.get_current_file_table()
        if not current_table:
            return
            
        selected_rows = []
        for item in current_table.selectedItems():
            if item.row() not in selected_rows:
                selected_rows.append(item.row())
        
        # 从后往前删除，避免索引变化问题
        for row in sorted(selected_rows, reverse=True):
            current_table.removeRow(row)
    
    def clear_file_list(self):
        """清空文件列表"""
        current_table = self.get_current_file_table()
        if current_table:
            current_table.setRowCount(0)
    
    def browse_output_directory(self, operation_type):
        """浏览输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            if operation_type == 'encrypt':
                self.encrypt_output_path_input.setText(directory)
            else:  # decrypt
                self.decrypt_output_path_input.setText(directory)
    
    def toggle_output_options(self, operation_type, state):
        """切换输出选项的启用状态"""
        checked = state == Qt.Checked
        
        if operation_type == 'encrypt':
            self.encrypt_output_path_input.setEnabled(not checked)
            self.encrypt_browse_output_btn.setEnabled(not checked)
            # 当覆盖源文件时，禁用并取消选中"删除原文件"选项
            self.encrypt_delete_original_checkbox.setEnabled(not checked)
            if checked:
                self.encrypt_delete_original_checkbox.setChecked(False)
        else:  # decrypt
            self.decrypt_output_path_input.setEnabled(not checked)
            self.decrypt_browse_output_btn.setEnabled(not checked)
            # 当覆盖源文件时，禁用并取消选中"删除原文件"选项
            self.decrypt_delete_original_checkbox.setEnabled(not checked)
            if checked:
                self.decrypt_delete_original_checkbox.setChecked(False)

    def start_processing(self):
        """开始处理"""
        current_table = self.get_current_file_table()
        if not current_table:
            return
            
        if current_table.rowCount() == 0:
            # 使用警告对话框而不是状态标签
            QMessageBox.warning(self, "警告", "请先添加需要处理的文件")
            return
        
        # 获取当前选项卡类型
        current_index = self.tab_widget.currentIndex()
        operation_type = 'encrypt' if current_index == 0 else 'decrypt'
        
        # 获取密码
        if operation_type == 'encrypt':
            password = self.encrypt_password_input.text()
        else:
            password = self.decrypt_password_input.text()
        
        if not password:
            QMessageBox.warning(self, "警告", "请输入密码")
            return
        
        # 获取覆盖选项
        if operation_type == 'encrypt':
            overwrite = self.encrypt_overwrite_checkbox.isChecked()
            output_dir = self.encrypt_output_path_input.text() if not overwrite else None
            delete_original = self.encrypt_delete_original_checkbox.isChecked()
        else:
            overwrite = self.decrypt_overwrite_checkbox.isChecked()
            output_dir = self.decrypt_output_path_input.text() if not overwrite else None
            delete_original = self.decrypt_delete_original_checkbox.isChecked()
        
        # 如果不覆盖原文件但没有指定输出目录，提示用户选择
        if not overwrite and not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录或勾选覆盖源文件选项")
            return
        
        # 获取文件列表
        file_list = []
        for row in range(current_table.rowCount()):
            file_path = current_table.item(row, 1).text()
            if os.path.exists(file_path):
                file_list.append(file_path)
        
        if not file_list:
            QMessageBox.warning(self, "警告", "没有有效的文件")
            return
        
        # 设置界面状态
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 将状态信息显示在窗口标题中
        operation_name = "加密" if operation_type == 'encrypt' else "解密"
        self.setWindowTitle(f"批量PDF{operation_name}处理 - 正在处理...")
        
        # 创建并启动工作线程
        self.worker = BatchCryptoWorker(
            file_list=file_list,
            operation_type=operation_type,
            password=password,
            output_dir=output_dir,
            overwrite=overwrite,
            delete_original=delete_original  # 传递删除原文件选项
        )
        
        # 连接信号
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.batch_finished.connect(self.on_batch_finished)
        self.worker.file_processed.connect(self.update_file_status)
        
        self.worker.start()
    
    def cancel_processing(self):
        """取消处理"""
        if self.worker:
            self.worker.cancel()
            # 将取消信息显示在窗口标题中
            current_index = self.tab_widget.currentIndex()
            operation_name = "加密" if current_index == 0 else "解密"
            self.setWindowTitle(f"批量PDF{operation_name}处理 - 正在取消处理...")
    
    def update_progress(self, progress, filename, status):
        """更新进度"""
        self.progress_bar.setValue(progress)
        # 将进度信息显示在窗口标题中
        current_index = self.tab_widget.currentIndex()
        operation_name = "加密" if current_index == 0 else "解密"
        self.setWindowTitle(f"批量PDF{operation_name}处理 - {filename} | {status} ({progress}%)")
    
    def update_file_status(self, file_path, status):
        """更新文件状态"""
        current_table = self.get_current_file_table()
        if not current_table:
            return
            
        # 查找对应文件并更新状态
        for row in range(current_table.rowCount()):
            if current_table.item(row, 1).text() == file_path:
                current_table.setItem(row, 2, QTableWidgetItem(status))
                break
    
    def on_batch_finished(self, success, message):
        """处理完成回调"""
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        if success:
            # 将完成信息显示在窗口标题中
            current_index = self.tab_widget.currentIndex()
            operation_name = "加密" if current_index == 0 else "解密"
            self.setWindowTitle(f"批量PDF{operation_name}处理 - 完成: {message}")
        else:
            # 将错误信息显示在窗口标题中
            current_index = self.tab_widget.currentIndex()
            operation_name = "加密" if current_index == 0 else "解密"
            self.setWindowTitle(f"批量PDF{operation_name}处理 - 错误: {message}")
        
        # 清理工作线程
        if self.worker:
            self.worker.wait()
            self.worker = None