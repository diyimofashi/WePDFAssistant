"""PDF拆分管理器模块 - 统一界面版本"""

import os
import re
from typing import List, Dict, Tuple, Optional
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSpinBox, QCheckBox, QRadioButton,
                            QButtonGroup, QTextEdit, QProgressBar, QMessageBox,
                            QGroupBox, QGridLayout, QComboBox, QLineEdit,
                            QListWidget, QListWidgetItem, QSplitter, QWidget,
                            QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont, QPixmap
from app.utils.logger import get_logger
from app.config.settings import AppSettings

logger = get_logger('split_manager')


class SplitWorker(QThread):
    """拆分工作线程"""
    
    progress_updated = pyqtSignal(int, str)  # 进度和状态
    split_finished = pyqtSignal(bool, str, list)  # 完成、消息、输出文件列表
    error_occurred = pyqtSignal(str)  # 错误
    
    def __init__(self, pdf_processor, split_config, output_dir):
        super().__init__()
        self.pdf_processor = pdf_processor
        self.split_config = split_config
        self.output_dir = output_dir
        self.output_files = []
        
    def run(self):
        """执行拆分操作"""
        try:
            if not self.pdf_processor or not self.pdf_processor.pdf_document:
                self.error_occurred.emit("没有打开的PDF文件")
                return
                
            self.progress_updated.emit(0, "准备拆分...")
            
            split_mode = self.split_config['mode']
            base_name = self.split_config['base_name']
            
            if split_mode == 0:  # 单页拆分
                self._split_single_pages(base_name)
            elif split_mode == 1:  # 范围拆分
                self._split_by_ranges(base_name, self.split_config['ranges'])
            elif split_mode == 2:  # 分组拆分
                self._split_by_groups(base_name, self.split_config['group_size'])
            elif split_mode == 3:  # 章节拆分
                self._split_by_bookmarks(base_name)
            
            self.split_finished.emit(True, f"拆分完成！共生成 {len(self.output_files)} 个文件", self.output_files)
            
        except Exception as e:
            logger.error(f"拆分过程中出错: {e}")
            self.error_occurred.emit(f"拆分失败: {str(e)}")
    
    def _split_single_pages(self, base_name: str):
        """单页拆分"""
        total_pages = len(self.pdf_processor.pdf_document.pages)
        
        for i in range(total_pages):
            progress = int((i / total_pages) * 100)
            self.progress_updated.emit(progress, f"正在拆分第 {i+1}/{total_pages} 页...")
            
            # 创建新的PDF文档
            from PyPDF2 import PdfWriter
            writer = PdfWriter()
            writer.add_page(self.pdf_processor.pdf_document.pages[i])
            
            # 保存文件
            output_path = os.path.join(self.output_dir, f"{base_name}_page_{i+1:04d}.pdf")
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            self.output_files.append(output_path)
    
    def _split_by_ranges(self, base_name: str, ranges: List[str]):
        """按范围拆分"""
        for idx, range_str in enumerate(ranges):
            progress = int((idx / len(ranges)) * 100)
            self.progress_updated.emit(progress, f"正在拆分范围: {range_str}")
            
            # 解析页面范围
            pages = self._parse_page_range(range_str)
            if not pages:
                continue
            
            # 创建新的PDF文档
            from PyPDF2 import PdfWriter
            writer = PdfWriter()
            
            for page_num in pages:
                if 0 <= page_num < len(self.pdf_processor.pdf_document.pages):
                    writer.add_page(self.pdf_processor.pdf_document.pages[page_num])
            
            # 保存文件
            output_path = os.path.join(self.output_dir, f"{base_name}_range_{idx+1:02d}_({range_str}).pdf")
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            self.output_files.append(output_path)
    
    def _split_by_groups(self, base_name: str, group_size: int):
        """按分组拆分"""
        total_pages = len(self.pdf_processor.pdf_document.pages)
        group_count = (total_pages + group_size - 1) // group_size
        
        for group_idx in range(group_count):
            progress = int((group_idx / group_count) * 100)
            self.progress_updated.emit(progress, f"正在拆分第 {group_idx+1}/{group_count} 组...")
            
            start_page = group_idx * group_size
            end_page = min(start_page + group_size, total_pages)
            
            # 创建新的PDF文档
            from PyPDF2 import PdfWriter
            writer = PdfWriter()
            
            for page_num in range(start_page, end_page):
                writer.add_page(self.pdf_processor.pdf_document.pages[page_num])
            
            # 保存文件
            output_path = os.path.join(self.output_dir, f"{base_name}_group_{group_idx+1:02d}_({start_page+1}-{end_page}).pdf")
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            self.output_files.append(output_path)
    
    def _split_by_bookmarks(self, base_name: str):
        """按书签拆分"""
        if not self.pdf_processor.fitz_document:
            self.error_occurred.emit("需要PyMuPDF支持才能按书签拆分")
            return
        
        # 获取书签信息
        bookmarks = self.pdf_processor.fitz_document.get_toc()
        if not bookmarks:
            self.error_occurred.emit("PDF中没有找到书签")
            return
        
        total_sections = len(bookmarks)
        
        for idx, bookmark in enumerate(bookmarks):
            progress = int((idx / total_sections) * 100)
            title = bookmark[1]  # 书签标题
            start_page = bookmark[2] - 1  # 书签所在页码（转换为0-based）
            
            # 确定结束页码
            if idx < total_sections - 1:
                end_page = bookmarks[idx + 1][2] - 2  # 下一个书签前一页
            else:
                end_page = len(self.pdf_processor.pdf_document.pages) - 1
            
            self.progress_updated.emit(progress, f"正在拆分章节: {title}")
            
            # 创建新的PDF文档
            from PyPDF2 import PdfWriter
            writer = PdfWriter()
            
            for page_num in range(start_page, end_page + 1):
                if 0 <= page_num < len(self.pdf_processor.pdf_document.pages):
                    writer.add_page(self.pdf_processor.pdf_document.pages[page_num])
            
            # 清理文件名中的特殊字符
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
            output_path = os.path.join(self.output_dir, f"{base_name}_{safe_title}.pdf")
            
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            self.output_files.append(output_path)
    
    def _parse_page_range(self, range_str: str) -> List[int]:
        """解析页面范围字符串，如 '1-5,8,10-12'"""
        pages = []
        try:
            parts = range_str.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    pages.extend(range(start-1, end))  # 转换为0-based
                else:
                    pages.append(int(part)-1)  # 转换为0-based
        except Exception as e:
            logger.error(f"解析页面范围失败: {range_str}, 错误: {e}")
        return pages


class SplitDialog(QDialog):
    """PDF拆分对话框 - 统一界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.pdf_processor = parent.pdf_processor if parent else None
        self.worker = None
        self.split_result = None  # 存储拆分结果
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("PDF拆分工具")
        self.setFixedSize(700, 650)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 拆分模式选择和参数
        mode_group = QGroupBox("📋 拆分设置")
        mode_layout = QVBoxLayout()
        
        self.mode_button_group = QButtonGroup()
        
        # 单页拆分
        single_layout = QVBoxLayout()
        self.single_radio = QRadioButton("📄 单页拆分 - 每页保存为单独PDF")
        self.single_radio.setChecked(True)
        single_layout.addWidget(self.single_radio)
        
        # 范围拆分
        range_layout = QVBoxLayout()
        self.range_radio = QRadioButton("📑 范围拆分 - 指定页面范围")
        range_layout.addWidget(self.range_radio)
        self.range_edit = QTextEdit()
        self.range_edit.setPlaceholderText("输入页面范围，每行一个范围，例如：\n1-5        # 第1页到第5页\n8,10,12-15 # 第8、10、12到15页\n20-        # 第20页到末尾\n-10        # 从第1页到第10页\n3,7,15-20  # 不连续的页面")
        self.range_edit.setStyleSheet("padding: 10px; font-family: monospace; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9;")
        self.range_edit.setMaximumHeight(150)
        self.range_layout = range_layout
        range_layout.addWidget(self.range_edit)
        range_layout.addSpacing(5)
        
        # 分组拆分
        group_layout = QVBoxLayout()
        self.group_radio = QRadioButton("📚 分组拆分 - 按指定页数分组")
        group_layout.addWidget(self.group_radio)
        self.group_input_widget = QWidget()
        group_input_layout = QHBoxLayout()
        group_label = QLabel("每组的页数:")
        self.group_size_spin = QSpinBox()
        self.group_size_spin.setRange(1, 100)
        self.group_size_spin.setValue(5)
        self.group_size_spin.setSuffix(" 页")
        self.group_size_spin.setStyleSheet("padding: 8px; font-size: 13px;")
        group_input_layout.addWidget(group_label)
        group_input_layout.addWidget(self.group_size_spin)
        group_input_layout.addStretch()
        self.group_input_widget.setLayout(group_input_layout)
        self.group_layout = group_layout
        group_layout.addWidget(self.group_input_widget)
        group_desc = QLabel("💡 将PDF按指定页数分组，适合大文件处理")
        group_desc.setStyleSheet("color: #666; font-style: italic; margin-left: 10px;")
        group_layout.addWidget(group_desc)
        group_layout.addSpacing(5)
        
        # 章节拆分
        bookmark_layout = QVBoxLayout()
        self.bookmark_radio = QRadioButton("📊 章节拆分 - 根据书签自动拆分")
        bookmark_layout.addWidget(self.bookmark_radio)
        self.bookmark_info = QLabel("📊 将根据PDF中的书签自动拆分为章节")
        self.bookmark_info.setStyleSheet("color: #007acc; font-weight: bold; padding: 8px;")
        self.bookmark_layout = bookmark_layout
        bookmark_layout.addWidget(self.bookmark_info)
        
        # 书签列表容器
        self.bookmark_list_widget = QWidget()
        self.bookmark_list_layout = QVBoxLayout()
        self.bookmark_list_widget.setLayout(self.bookmark_list_layout)
        bookmark_layout.addWidget(self.bookmark_list_widget)
        bookmark_layout.addSpacing(5)
        
        # 条码拆分
        barcode_layout = QVBoxLayout()
        self.barcode_radio = QRadioButton("📟 条码拆分 - 根据条码自动拆分")
        barcode_layout.addWidget(self.barcode_radio)
        self.barcode_info = QLabel("📟 根据PDF页面中的一维码、二维码等条码自动拆分")
        self.barcode_info.setStyleSheet("color: #28a745; font-weight: bold; padding: 8px;")
        self.barcode_layout = barcode_layout
        barcode_layout.addWidget(self.barcode_info)
        barcode_desc = QLabel("💡 支持多种条码类型，可配置过滤规则和命名方式")
        barcode_desc.setStyleSheet("color: #666; font-style: italic; margin-left: 10px;")
        barcode_layout.addWidget(barcode_desc)
        barcode_layout.addSpacing(5)
        
        self.mode_button_group.addButton(self.single_radio, 0)
        self.mode_button_group.addButton(self.range_radio, 1)
        self.mode_button_group.addButton(self.group_radio, 2)
        self.mode_button_group.addButton(self.bookmark_radio, 3)
        self.mode_button_group.addButton(self.barcode_radio, 4)
        
        # 将所有模式布局添加到主布局
        mode_layout.addLayout(single_layout)
        mode_layout.addLayout(self.range_layout)
        mode_layout.addLayout(self.group_layout)
        mode_layout.addLayout(self.bookmark_layout)
        mode_layout.addLayout(self.barcode_layout)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 通用设置区域
        general_group = QGroupBox("⚙️ 通用设置")
        general_layout = QVBoxLayout()
        
        # 基础文件名
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel("基础文件名:"))
        self.base_name_edit = QLineEdit("split_output")
        self.base_name_edit.setPlaceholderText("输出文件的前缀名称")
        self.base_name_edit.setStyleSheet("padding: 8px; font-size: 13px;")
        filename_layout.addWidget(self.base_name_edit)
        general_layout.addLayout(filename_layout)
        
        # 输出目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("保存目录:"))
        self.output_dir_edit = QLineEdit()
        # 设置默认目录为当前文件目录+文件名
        default_dir = self.get_default_output_dir()
        self.output_dir_edit.setText(default_dir)
        self.output_dir_edit.setStyleSheet("padding: 8px; font-size: 13px;")
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_output_directory)
        dir_layout.addWidget(self.output_dir_edit)
        dir_layout.addWidget(self.browse_btn)
        general_layout.addLayout(dir_layout)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # 进度显示区域
        self.progress_group = QGroupBox("🔄 执行进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666;")
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_group.setLayout(progress_layout)
        layout.addWidget(self.progress_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 开始拆分")
        self.start_btn.clicked.connect(self.start_split)
        self.start_btn.setStyleSheet("font-weight: bold; padding: 10px 20px;")
        
        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.start_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.mode_button_group.buttonClicked.connect(self.on_mode_changed)
        
        # 初始化显示
        self.on_mode_changed()
    
    def get_default_output_dir(self):
        """获取默认输出目录"""
        try:
            if self.pdf_processor and self.pdf_processor.current_file:
                # 获取当前文件的目录和文件名（不含扩展名）
                file_dir = os.path.dirname(self.pdf_processor.current_file)
                file_name = os.path.splitext(os.path.basename(self.pdf_processor.current_file))[0]
                default_dir = os.path.join(file_dir, file_name)
                return default_dir
            else:
                # 如果没有打开文件，使用上次的保存目录
                return os.path.join(AppSettings.get_last_save_dir(), "split_output")
        except Exception:
            # 出错时使用默认目录
            return os.path.join(AppSettings.get_last_save_dir(), "split_output")
    
    def browse_output_directory(self):
        """选择输出目录"""
        current_dir = self.output_dir_edit.text()
        if not os.path.exists(current_dir):
            current_dir = AppSettings.get_last_save_dir()
            
        dir_path = QFileDialog.getExistingDirectory(self, "选择保存目录", current_dir)
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def on_mode_changed(self):
        """模式改变时的处理"""
        mode_id = self.mode_button_group.checkedId()
        
        # 清除书签列表（如果存在）
        if hasattr(self, 'bookmark_list_layout'):
            for i in reversed(range(self.bookmark_list_layout.count())):
                child = self.bookmark_list_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
        
        # 显示/隐藏范围拆分配置
        if mode_id == 1:  # 范围拆分
            self.range_edit.setVisible(True)
        else:
            self.range_edit.setVisible(False)
        
        # 显示/隐藏分组拆分配置
        if mode_id == 2:  # 分组拆分
            self.group_input_widget.setVisible(True)
        else:
            self.group_input_widget.setVisible(False)
        
        # 显示/隐藏章节拆分配置
        if mode_id == 3:  # 章节拆分
            self.bookmark_info.setVisible(True)
            self.bookmark_list_widget.setVisible(True)
            
            # 检查书签
            if self.pdf_processor and self.pdf_processor.fitz_document:
                bookmarks = self.pdf_processor.fitz_document.get_toc()
                if bookmarks:
                    bookmark_list = QLabel(f"✅ 检测到 {len(bookmarks)} 个书签:")
                    bookmark_list.setStyleSheet("color: green; font-weight: bold; margin-bottom: 8px;")
                    self.bookmark_list_layout.addWidget(bookmark_list)
                    
                    # 显示前几个书签，确保完全可见
                    for i, bookmark in enumerate(bookmarks[:5]):  # 只显示前5个
                        level, title, page = bookmark
                        bookmark_item = QLabel(f"   • {title} (页 {page})")
                        bookmark_item.setStyleSheet("color: #666; margin-left: 15px; font-size: 12px; padding: 2px;")
                        self.bookmark_list_layout.addWidget(bookmark_item)
                        
                    if len(bookmarks) > 5:
                        more_label = QLabel(f"   ... 还有 {len(bookmarks) - 5} 个书签")
                        more_label.setStyleSheet("color: #999; margin-left: 15px; font-style: italic; font-size: 12px; padding: 2px;")
                        self.bookmark_list_layout.addWidget(more_label)
                else:
                    no_bookmark = QLabel("⚠️ 未检测到书签，此模式无法使用")
                    no_bookmark.setStyleSheet("color: orange; padding: 15px; font-weight: bold;")
                    self.bookmark_list_layout.addWidget(no_bookmark)
            else:
                no_pdf = QLabel("⚠️ 请先打开PDF文件")
                no_pdf.setStyleSheet("color: orange; padding: 15px; font-weight: bold;")
                self.bookmark_list_layout.addWidget(no_pdf)
        else:
            self.bookmark_info.setVisible(False)
            self.bookmark_list_widget.setVisible(False)
        
        # 显示/隐藏条码拆分配置
        if mode_id == 4:  # 条码拆分
            self.barcode_info.setVisible(True)
        else:
            self.barcode_info.setVisible(False)
    
    def get_split_config(self) -> Optional[dict]:
        """获取拆分配置"""
        base_name = self.base_name_edit.text().strip()
        if not base_name:
            QMessageBox.warning(self, "警告", "请输入基础文件名")
            return None
        
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择保存目录")
            return None
        
        # 创建输出目录
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建目录: {str(e)}")
            return None
        
        # 构建拆分配置
        config = {
            'mode': self.mode_button_group.checkedId(),
            'base_name': base_name,
            'output_dir': output_dir
        }
        
        # 根据模式添加特定配置
        mode_id = config['mode']
        
        if mode_id == 1:  # 范围拆分
            ranges = [line.strip() for line in self.range_edit.toPlainText().split('\n') if line.strip()]
            if not ranges:
                QMessageBox.warning(self, "警告", "请输入页面范围")
                return None
            config['ranges'] = ranges
            
        elif mode_id == 2:  # 分组拆分
            config['group_size'] = self.group_size_spin.value()
            
        elif mode_id == 3:  # 章节拆分
            if self.pdf_processor and self.pdf_processor.fitz_document:
                bookmarks = self.pdf_processor.fitz_document.get_toc()
                if not bookmarks:
                    QMessageBox.warning(self, "警告", "PDF中没有找到书签，无法进行章节拆分")
                    return None
        elif mode_id == 4:  # 条码拆分
            # 条码拆分使用单独的对话框
            return None  # 不返回配置，使用特殊处理
        
        return config
    
    def start_split(self):
        """开始拆分"""
        if not self.pdf_processor or not self.pdf_processor.pdf_document:
            QMessageBox.warning(self, "警告", "请先打开PDF文件")
            return
        
        # 检查是否是条码拆分模式
        mode_id = self.mode_button_group.checkedId()
        if mode_id == 4:  # 条码拆分
            self.start_barcode_split()
            return
        
        split_config = self.get_split_config()
        if not split_config:
            return
        
        # 显示进度
        self.progress_group.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("准备拆分...")
        self.start_btn.setEnabled(False)
        
        # 创建工作线程
        self.worker = SplitWorker(self.pdf_processor, split_config, split_config['output_dir'])
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.split_finished.connect(self.on_split_finished)
        self.worker.error_occurred.connect(self.on_error_occurred)
        
        # 开始工作
        self.worker.start()
    
    def start_barcode_split(self):
        """启动条码拆分"""
        try:
            from app.ui.barcode_split_dialog import BarcodeSplitDialog
            from app.core.barcode.barcode_split_processor import BarcodeSplitThread
            
            current_file_path = self.pdf_processor.current_file
            if not current_file_path:
                QMessageBox.warning(self, "警告", "请先打开PDF文件")
                return
            
            # 显示条码拆分配置对话框
            barcode_dialog = BarcodeSplitDialog(self, current_file_path)
            if barcode_dialog.exec_() != QDialog.Accepted:
                return
            
            config = barcode_dialog.get_config()
            
            # 显示进度
            self.progress_group.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("准备条码拆分...")
            self.start_btn.setEnabled(False)
            
            # 创建条码拆分工作线程
            self.barcode_worker = BarcodeSplitThread(current_file_path, config)
            self.barcode_worker.progress_updated.connect(self.on_progress_updated)
            self.barcode_worker.finished.connect(self.on_barcode_split_finished)
            self.barcode_worker.error_occurred.connect(self.on_error_occurred)
            
            # 开始拆分
            self.barcode_worker.start()
            
        except Exception as e:
            logger.error(f"启动条码拆分失败: {e}")
            QMessageBox.critical(self, "错误", f"启动条码拆分失败: {str(e)}")
            self.start_btn.setEnabled(True)
    
    def on_progress_updated(self, progress: int, status: str):
        """进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
    
    def on_split_finished(self, success: bool, message: str, output_files: List[str]):
        """拆分完成"""
        self.start_btn.setEnabled(True)

        if success:
            output_dir = self.output_dir_edit.text().strip()

            # 保存拆分结果
            self.split_result = {
                'success': True,
                'message': message,
                'output_dir': output_dir,
                'output_files': output_files,
                'file_count': len(output_files)
            }

            QMessageBox.information(self, "拆分完成", f"✅ {message}\n\n共生成 {len(output_files)} 个文件")

            # 询问是否打开输出目录
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("打开输出目录")
            msg_box.setText("是否打开输出目录查看拆分结果？")
            yes_btn = msg_box.addButton("是", QMessageBox.YesRole)
            no_btn = msg_box.addButton("否", QMessageBox.NoRole)
            msg_box.setDefaultButton(no_btn)  # 默认选择"否"
            msg_box.exec_()

            if msg_box.clickedButton() == yes_btn:
                try:
                    # 标准化路径，确保使用正确的路径分隔符
                    if output_dir:
                        # 替换正斜杠为反斜杠，处理混合路径
                        normalized_dir = output_dir.replace('/', os.sep)
                        # 移除多余的路径分隔符
                        normalized_dir = os.path.normpath(normalized_dir)

                        logger.info(f"尝试打开目录: {normalized_dir}")

                        if os.path.exists(normalized_dir):
                            import subprocess
                            subprocess.Popen(['explorer', normalized_dir])
                        else:
                            QMessageBox.warning(self, "目录不存在", f"指定的输出目录不存在：\n{normalized_dir}")
                    else:
                        QMessageBox.warning(self, "目录为空", "输出目录路径为空")
                except Exception as e:
                    logger.error(f"打开输出目录失败: {e}")
                    QMessageBox.warning(self, "打开失败", f"无法打开输出目录：\n{str(e)}")

            self.accept()
        else:
            self.split_result = {
                'success': False,
                'message': message,
                'output_dir': None,
                'output_files': [],
                'file_count': 0
            }
            QMessageBox.critical(self, "拆分失败", f"❌ {message}")
    
    def on_barcode_split_finished(self, result):
        """条码拆分完成处理"""
        self.start_btn.setEnabled(True)

        if result.success:
            output_dir = None
            # 从配置中获取输出目录
            if hasattr(self, 'barcode_worker') and self.barcode_worker:
                output_dir = self.barcode_worker.config.output_config.output_dir
            else:
                output_dir = self.output_dir_edit.text().strip()

            # 保存条码拆分结果
            self.split_result = {
                'success': True,
                'message': result.message,
                'output_dir': output_dir,
                'output_files': result.files_created,
                'file_count': len(result.files_created),
                'is_barcode_split': True
            }

            QMessageBox.information(self, "拆分完成", f"✅ {result.message}\n\n共生成 {len(result.files_created)} 个文件")

            # 询问是否打开输出目录
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("打开输出目录")
            msg_box.setText("是否打开输出目录查看拆分结果？")
            yes_btn = msg_box.addButton("是", QMessageBox.YesRole)
            no_btn = msg_box.addButton("否", QMessageBox.NoRole)
            msg_box.setDefaultButton(no_btn)
            msg_box.exec_()

            if msg_box.clickedButton() == yes_btn:
                try:
                    if output_dir:
                        normalized_dir = output_dir.replace('/', os.sep)
                        normalized_dir = os.path.normpath(normalized_dir)

                        logger.info(f"尝试打开目录: {normalized_dir}")

                        if os.path.exists(normalized_dir):
                            import subprocess
                            subprocess.Popen(['explorer', normalized_dir])
                        else:
                            QMessageBox.warning(self, "目录不存在", f"指定的输出目录不存在：\n{normalized_dir}")
                    else:
                        QMessageBox.warning(self, "目录为空", "输出目录路径为空")
                except Exception as e:
                    logger.error(f"打开输出目录失败: {e}")
                    QMessageBox.warning(self, "打开失败", f"无法打开输出目录：\n{str(e)}")

            self.accept()
        else:
            self.split_result = {
                'success': False,
                'message': result.message,
                'output_dir': None,
                'output_files': [],
                'file_count': 0
            }
            QMessageBox.critical(self, "拆分失败", f"❌ {result.message}")
    
    def on_error_occurred(self, error_msg: str):
        """错误处理"""
        self.start_btn.setEnabled(True)
        QMessageBox.critical(self, "错误", f"❌ {error_msg}")


class SplitManager:
    """PDF拆分管理器"""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.last_split_result = None

    def show_split_dialog(self):
        """显示拆分对话框

        Returns:
            dict: 拆分结果字典，包含:
                - success: 是否成功
                - message: 消息
                - output_dir: 输出目录
                - output_files: 输出文件列表
                - file_count: 文件数量
                - is_barcode_split: 是否为条码拆分
        """
        if not self.parent.pdf_processor or not self.parent.pdf_processor.pdf_document:
            QMessageBox.warning(self.parent, "警告", "请先打开PDF文件")
            return None

        dialog = SplitDialog(self.parent)
        dialog.exec_()

        # 保存并返回拆分结果
        self.last_split_result = dialog.split_result
        return self.last_split_result