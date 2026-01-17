"""条码拆分对话框"""

import os
from typing import List
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
                           QCheckBox, QLineEdit, QSpinBox, QPushButton, QFileDialog,
                           QRadioButton, QButtonGroup, QProgressDialog,  QScrollArea,
                           QWidget, QGridLayout, QMessageBox,
                           QSizePolicy, QApplication, QLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from app.utils.logger import get_logger
from app.config.barcode_split_config import (
    BarcodeSplitConfig, BarcodeSplitConfigManager, 
    BarcodeFilterConfig, BarcodeOutputConfig
)
from app.core.barcode.barcode_detector import BarcodeDetector, BarcodeInfo
from app.core.barcode.barcode_detection_thread import BarcodeDetectionThread
from app.ui.barcode_result_dialog import BarcodeResultDialog

logger = get_logger('barcode_split_dialog')


class BarcodeSplitDialog(QDialog):
    """条码拆分设置对话框"""
    
    config_changed = pyqtSignal(object)  # 配置变更信号
    
    def __init__(self, parent=None, current_file_path=None):
        super().__init__(parent)
        self.current_file_path = current_file_path
        self.config_manager = BarcodeSplitConfigManager()
        self.current_config = self.config_manager.load_last_used_config()
        
        # 设置默认输出目录为当前文件目录+文件名（不含后缀）
        if not self.current_config.output_config.output_dir and current_file_path:
            file_dir = os.path.dirname(current_file_path)
            file_name = os.path.splitext(os.path.basename(current_file_path))[0]
            default_output_dir = os.path.join(file_dir, file_name)
            self.current_config.output_config.output_dir = default_output_dir
        
        self.init_ui()
        self.load_config_to_ui()
        
        logger.debug("条码拆分对话框初始化完成")
    
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle("条码拆分设置")
        self.resize(800, 100)  # 初始尺寸，后续会根据内容调整
        self.setMinimumSize(600, 400)  # 设置最小尺寸
        self.setMaximumSize(1000, 800)  # 设置最大尺寸，防止过大
        
        # 设置窗口标志，确保对话框居中显示
        self.setWindowFlags(self.windowFlags() | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)  # 适当增加组件间距
        main_layout.setContentsMargins(15, 15, 15, 15)  # 适当增加边距
        # 允许布局根据内容调整大小
        main_layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # 条码检测配置区域
        main_layout.addWidget(self._create_detection_group())
        
        # 过滤规则配置区域
        main_layout.addWidget(self._create_filter_group())
        
        # 输出设置区域
        main_layout.addWidget(self._create_output_group())
        
        # 操作按钮区域
        main_layout.addWidget(self._create_button_group())
        
        self.setLayout(main_layout)
    
    def center_on_screen(self):
        """将窗口居中显示在屏幕中央"""
        # 获取屏幕可用区域
        screen_geo = self.screen().availableGeometry()
        
        # 计算对话框应该的位置（居中）
        dialog_x = screen_geo.center().x() - self.width() // 2
        dialog_y = screen_geo.center().y() - self.height() // 2
        
        # 确保对话框不会超出屏幕边界，特别是顶部和底部
        # 对于较大的窗口，需要更多的边距
        margin = 30
        dialog_x = max(screen_geo.left() + margin, min(dialog_x, screen_geo.right() - self.width() - margin))
        dialog_y = max(screen_geo.top() + margin, min(dialog_y, screen_geo.bottom() - self.height() - margin))
        
        self.move(dialog_x, dialog_y)
        self.setAttribute(Qt.WA_Moved, True)  # 标记已移动
    
    def showEvent(self, event):
        """窗口显示事件，用于居中显示对话框"""
        super().showEvent(event)
        
        # 调整窗口大小以适应内容，但不超过最大尺寸
        self.adjustSize()
        
        # 确保对话框在屏幕中央显示
        if not self.testAttribute(Qt.WA_Moved):
            self.center_on_screen()
    
    def _create_detection_group(self):
        """创建条码检测配置组"""
        group = QGroupBox("条码检测配置")
        layout = QVBoxLayout()
        
        # 条码类型选择
        type_label = QLabel("检测的条码类型:")
        layout.addWidget(type_label)
        
        # 使用滚动区域来容纳条码类型复选框，支持多选
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # 移除固定高度限制，让滚动区域根据内容自适应
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 创建一个容器widget来放置所有复选框
        container_widget = QWidget()
        type_layout = QGridLayout(container_widget)
        type_layout.setSpacing(5)  # 减少间距
        
        self.barcode_type_checkboxes = {}
        
        detector = BarcodeDetector()
        supported_types = detector.get_supported_types()
        
        # 首先添加"所有类型"选项
        all_types_checkbox = QCheckBox("🔍 所有类型")
        # 检查是否启用了所有类型
        is_all_types_enabled = ("ALL_TYPES" in self.current_config.filter_config.enabled_types or 
                               len(self.current_config.filter_config.enabled_types) == len(supported_types) - 1)
        all_types_checkbox.setChecked(is_all_types_enabled)
        all_types_checkbox.toggled.connect(self._on_all_types_toggled)
        self.barcode_type_checkboxes["ALL_TYPES"] = all_types_checkbox
        type_layout.addWidget(all_types_checkbox, 0, 0, 1, 4)
        
        # 然后添加具体类型复选框
        type_index = 0  # 用于布局索引的计数器
        for barcode_type in supported_types:
            if barcode_type == "ALL_TYPES":
                continue
                
            checkbox = QCheckBox(barcode_type.replace('_', ' '))
            checkbox.setChecked(barcode_type in self.current_config.filter_config.enabled_types)
            checkbox.toggled.connect(self._on_specific_type_toggled)
            self.barcode_type_checkboxes[barcode_type] = checkbox
            
            row = type_index // 4 + 1  # +1 因为第一行是"所有类型"
            col = type_index % 4
            type_layout.addWidget(checkbox, row, col)
            type_index += 1
        
        scroll_area.setWidget(container_widget)
        layout.addWidget(scroll_area)
        group.setLayout(layout)
        return group
    
    def _create_filter_group(self):
        """创建过滤规则配置组"""
        group = QGroupBox("过滤规则")
        layout = QVBoxLayout()
        layout.setSpacing(3)  # 减少过滤规则内部间距
        
        # 长度过滤
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("条码长度:"))
        
        self.min_length_spin = QSpinBox()
        self.min_length_spin.setRange(1, 1000)
        self.min_length_spin.setSuffix(" 字符")
        self.min_length_spin.setMaximumWidth(100)
        length_layout.addWidget(self.min_length_spin)
        
        length_layout.addWidget(QLabel("到"))
        
        self.max_length_spin = QSpinBox()
        self.max_length_spin.setRange(1, 1000)
        self.max_length_spin.setValue(1000)
        self.max_length_spin.setSuffix(" 字符")
        self.max_length_spin.setMaximumWidth(100)
        length_layout.addWidget(self.max_length_spin)
        
        length_layout.addStretch()
        layout.addLayout(length_layout)
        
        # 包含关键词
        include_layout = QHBoxLayout()
        include_layout.addWidget(QLabel("包含关键词:"))
        self.include_keywords_edit = QLineEdit()
        self.include_keywords_edit.setPlaceholderText("用逗号分隔多个关键词，如: ABC,123")
        include_layout.addWidget(self.include_keywords_edit)
        layout.addLayout(include_layout)
        
        # 排除关键词
        exclude_layout = QHBoxLayout()
        exclude_layout.addWidget(QLabel("排除关键词:"))
        self.exclude_keywords_edit = QLineEdit()
        self.exclude_keywords_edit.setPlaceholderText("用逗号分隔多个关键词，如: TEST,DEMO")
        exclude_layout.addWidget(self.exclude_keywords_edit)
        layout.addLayout(exclude_layout)
        
        # 包含正则表达式
        include_regex_layout = QHBoxLayout()
        include_regex_layout.addWidget(QLabel("包含正则:"))
        self.include_regex_edit = QLineEdit()
        self.include_regex_edit.setPlaceholderText("匹配条码内容的正则表达式")
        include_regex_layout.addWidget(self.include_regex_edit)
        layout.addLayout(include_regex_layout)
        
        # 排除正则表达式
        exclude_regex_layout = QHBoxLayout()
        exclude_regex_layout.addWidget(QLabel("排除正则:"))
        self.exclude_regex_edit = QLineEdit()
        self.exclude_regex_edit.setPlaceholderText("排除条码内容的正则表达式")
        exclude_regex_layout.addWidget(self.exclude_regex_edit)
        layout.addLayout(exclude_regex_layout)
        
        # 提示信息
        hint_label = QLabel("提示: 关键词匹配不区分大小写，正则表达式匹配区分大小写")
        hint_label.setStyleSheet("QLabel { color: #666; font-size: 11px; }")
        layout.addWidget(hint_label)
        
        group.setLayout(layout)
        return group
    
    def _create_output_group(self):
        """创建输出设置组"""
        group = QGroupBox("输出设置")
        layout = QVBoxLayout()
        layout.setSpacing(3)  # 减少输出设置内部间距
        
        # 输出目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("输出目录:"))
        
        self.output_dir_label = QLabel("未选择目录")
        self.output_dir_label.setStyleSheet("""
            QLabel { 
                color: #333; 
                padding: 5px; 
                background-color: #f5f5f5; 
                border: 1px solid #ddd; 
                border-radius: 3px; 
            }
        """)
        self.output_dir_label.setWordWrap(True)
        self.output_dir_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # 允许标签扩展
        dir_layout.addWidget(self.output_dir_label)
        
        self.select_dir_btn = QPushButton("选择目录")
        self.select_dir_btn.clicked.connect(self._select_output_dir)
        dir_layout.addWidget(self.select_dir_btn)
        layout.addLayout(dir_layout)
        
        # 文件命名设置
        filename_group = QGroupBox("文件命名")
        filename_layout = QVBoxLayout()
        filename_layout.setSpacing(5)
        
        # 是否使用条码命名
        self.use_barcode_name_check = QCheckBox("使用条码值作为文件名")
        self.use_barcode_name_check.setChecked(True)
        self.use_barcode_name_check.toggled.connect(self._on_filename_mode_changed)
        filename_layout.addWidget(self.use_barcode_name_check)
        
        # 文件名模板
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("文件名模板:"))
        self.filename_template_edit = QLineEdit()
        self.filename_template_edit.setText("{barcode}_{index}")
        self.filename_template_edit.setPlaceholderText("可用变量: {barcode}, {index}")
        template_layout.addWidget(self.filename_template_edit)
        filename_layout.addLayout(template_layout)
        
        filename_group.setLayout(filename_layout)
        layout.addWidget(filename_group)
        
        # 重复条码处理
        duplicate_group = QGroupBox("重复条码处理")
        duplicate_layout = QVBoxLayout()
        duplicate_layout.setSpacing(5)
        
        self.duplicate_button_group = QButtonGroup()
        
        self.merge_radio = QRadioButton("合并为同一文件")
        self.merge_radio.setChecked(True)
        self.duplicate_button_group.addButton(self.merge_radio, 0)
        duplicate_layout.addWidget(self.merge_radio)
        
        self.separate_radio = QRadioButton("创建单独文件")
        self.duplicate_button_group.addButton(self.separate_radio, 1)
        duplicate_layout.addWidget(self.separate_radio)
        
        duplicate_group.setLayout(duplicate_layout)
        layout.addWidget(duplicate_group)
        
        # 多条码处理
        multi_barcode_group = QGroupBox("多条码处理")
        multi_barcode_layout = QVBoxLayout()
        multi_barcode_layout.setSpacing(5)
        
        self.multi_barcode_button_group = QButtonGroup()
        
        self.first_radio = QRadioButton("以第一个条码为准（只使用第一个符合规则的条码）")
        self.first_radio.setChecked(True)
        self.multi_barcode_button_group.addButton(self.first_radio, 0)
        multi_barcode_layout.addWidget(self.first_radio)
        
        self.duplicate_page_radio = QRadioButton("一页属于多个文档（会将该页复制N次分别归入对应文档）")
        self.multi_barcode_button_group.addButton(self.duplicate_page_radio, 1)
        multi_barcode_layout.addWidget(self.duplicate_page_radio)
        
        multi_barcode_group.setLayout(multi_barcode_layout)
        layout.addWidget(multi_barcode_group)
        
        group.setLayout(layout)
        return group
    
    def _create_button_group(self):
        """创建操作按钮组"""
        # 创建一个容器Widget
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(5)
        
        # 配置管理按钮
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_config_btn)
        
        self.load_config_btn = QPushButton("加载配置")
        self.load_config_btn.clicked.connect(self._load_config)
        button_layout.addWidget(self.load_config_btn)
        
        self.reset_btn = QPushButton("重置为默认")
        self.reset_btn.clicked.connect(self._reset_to_default)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        # 检测条码按钮
        self.detect_barcodes_btn = QPushButton("检测条码")
        self.detect_barcodes_btn.clicked.connect(self._detect_barcodes)
        button_layout.addWidget(self.detect_barcodes_btn)
        
        # 主要操作按钮
        self.test_detection_btn = QPushButton("测试检测")
        self.test_detection_btn.clicked.connect(self._test_detection)
        button_layout.addWidget(self.test_detection_btn)
        
        self.start_split_btn = QPushButton("开始拆分")
        self.start_split_btn.clicked.connect(self._start_split)
        self.start_split_btn.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                padding: 8px 16px; 
                border: none; 
                border-radius: 4px; 
                font-weight: bold;
            }
        """)
        button_layout.addWidget(self.start_split_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        return button_widget
    
    def _select_output_dir(self):
        """选择输出目录"""
        initial_dir = self.current_config.output_config.output_dir
        if not initial_dir and self.current_file_path:
            initial_dir = os.path.dirname(self.current_file_path)
        
        directory = QFileDialog.getExistingDirectory(
            self, "选择输出目录", initial_dir
        )
        
        if directory:
            self.output_dir_label.setText(directory)
            self.output_dir_label.setStyleSheet("""
                QLabel { 
                    color: #333; 
                    padding: 5px; 
                    background-color: #f0f8ff; 
                    border: 1px solid #4CAF50; 
                    border-radius: 3px; 
                }
            """)
    
    def _detect_barcodes(self):
        """检测条码并显示结果"""
        if not self.current_file_path or not os.path.exists(self.current_file_path):
            QMessageBox.warning(self, "警告", "请先选择一个有效的PDF文件")
            return
        
        try:
            # 获取当前配置
            config = self.get_config_from_ui()
            
            # 创建条码检测器
            detector = BarcodeDetector()
            
            # 设置启用的条码类型
            enabled_types = config.filter_config.enabled_types
            # 特殊处理：如果只选择了ALL_TYPES，需要展开为所有具体类型
            if len(enabled_types) == 1 and enabled_types[0] == "ALL_TYPES":
                enabled_types = list(detector.BARCODE_TYPES.keys())
            
            # 显示进度对话框
            self.progress_dialog = QProgressDialog("正在检测条码...", "取消", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setAutoReset(False)
            self.progress_dialog.setAutoClose(False)
            self.progress_dialog.show()
            
            # 创建并启动检测线程
            self.detection_thread = BarcodeDetectionThread(
                self.current_file_path,
                enabled_types,
                method="both"
            )
            
            # 连接信号
            self.detection_thread.progress_updated.connect(self._on_detection_progress)
            self.detection_thread.detection_completed.connect(lambda barcodes: self._on_detection_completed(barcodes, config, detector))
            self.detection_thread.detection_error.connect(self._on_detection_error)
            
            # 连接取消按钮
            self.progress_dialog.canceled.connect(self.detection_thread.request_cancel)
            
            # 启动线程
            self.detection_thread.start()
            
        except Exception as e:
            logger.error(f"启动条码检测时出错: {e}")
            QMessageBox.critical(self, "错误", f"启动条码检测时出错: {str(e)}")
    
    def _on_detection_progress(self, current: int, total: int, message: str):
        """检测进度更新"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            # 计算百分比
            if total > 0:
                percent = int((current / total) * 100)
                self.progress_dialog.setValue(percent)
            self.progress_dialog.setLabelText(message)
            QApplication.processEvents()
    
    def _on_detection_completed(self, barcodes: List[BarcodeInfo], config, detector):
        """检测完成"""
        try:
            # 关闭进度对话框
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            # 应用过滤规则
            filtered_barcodes = detector.filter_barcodes(
                barcodes,
                min_length=config.filter_config.min_length,
                max_length=config.filter_config.max_length,
                include_keywords=config.filter_config.include_keywords,
                exclude_keywords=config.filter_config.exclude_keywords,
                include_regex=config.filter_config.include_regex,
                exclude_regex=config.filter_config.exclude_regex
            )
            
            # 保存检测结果到主窗口缓存
            if hasattr(self.parent(), 'last_barcode_detection_result'):
                self.parent().last_barcode_detection_result = {
                    'file_path': self.current_file_path,
                    'config': config,
                    'barcodes': filtered_barcodes,
                    'timestamp': QDateTime.currentDateTime()
                }
            
            # 显示结果
            self._display_barcodes(filtered_barcodes)
            
        except Exception as e:
            logger.error(f"处理检测结果时出错: {e}")
            QMessageBox.critical(self, "错误", f"处理检测结果时出错: {str(e)}")
    
    def _on_detection_error(self, error_msg: str):
        """检测出错"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        logger.error(f"条码检测出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"条码检测出错: {error_msg}")

    
    def _on_filename_mode_changed(self, checked):
        """文件名模式改变事件"""
        self.filename_template_edit.setEnabled(checked)
    
    def _display_barcodes(self, barcodes):
        """显示检测到的条码"""
        # 创建并显示结果对话框
        result_dialog = BarcodeResultDialog(barcodes, self)
        result_dialog.exec_()
    
    def load_config_to_ui(self):
        """将配置加载到UI"""
        try:
            filter_config = self.current_config.filter_config
            output_config = self.current_config.output_config
            
            # 条码类型
            # 特殊处理：如果启用了所有类型
            detector = BarcodeDetector()
            supported_types = detector.get_supported_types()
            is_all_types_enabled = ("ALL_TYPES" in filter_config.enabled_types or 
                                  len(filter_config.enabled_types) == len(supported_types) - 1)  # -1 because ALL_TYPES is also in the dict
            
            for barcode_type, checkbox in self.barcode_type_checkboxes.items():
                if barcode_type == "ALL_TYPES":
                    checkbox.setChecked(is_all_types_enabled)
                    # 如果启用了所有类型，禁用其他复选框
                    if is_all_types_enabled:
                        for bt, cb in self.barcode_type_checkboxes.items():
                            if bt != "ALL_TYPES":
                                cb.setEnabled(False)
                else:
                    # 只有在未启用所有类型时才设置具体类型的选中状态
                    if not is_all_types_enabled:
                        checkbox.setChecked(barcode_type in filter_config.enabled_types)
            
            # 过滤规则
            self.min_length_spin.setValue(filter_config.min_length)
            self.max_length_spin.setValue(filter_config.max_length)
            self.include_keywords_edit.setText(', '.join(filter_config.include_keywords))
            self.exclude_keywords_edit.setText(', '.join(filter_config.exclude_keywords))
            self.include_regex_edit.setText(filter_config.include_regex)
            self.exclude_regex_edit.setText(filter_config.exclude_regex)
            
            # 输出设置
            if output_config.output_dir:
                self.output_dir_label.setText(output_config.output_dir)
                self.output_dir_label.setStyleSheet("""
                    QLabel { 
                        color: #333; 
                        padding: 5px; 
                        background-color: #f0f8ff; 
                        border: 1px solid #4CAF50; 
                        border-radius: 3px; 
                    }
                """)
            else:
                # 如果没有保存的输出目录，使用默认目录
                if self.current_file_path:
                    file_dir = os.path.dirname(self.current_file_path)
                    file_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
                    default_output_dir = os.path.join(file_dir, file_name)
                    self.output_dir_label.setText(default_output_dir)
                    self.output_dir_label.setStyleSheet("""
                        QLabel { 
                            color: #333; 
                            padding: 5px; 
                            background-color: #f0f8ff; 
                            border: 1px solid #4CAF50; 
                            border-radius: 3px; 
                        }
                    """)
            
            self.use_barcode_name_check.setChecked(output_config.use_barcode_filename)
            self.filename_template_edit.setText(output_config.filename_template)
            
            if output_config.duplicate_handling == "merge":
                self.merge_radio.setChecked(True)
            else:
                self.separate_radio.setChecked(True)
            
            # 多条码处理设置
            if hasattr(self, 'first_radio') and hasattr(self, 'duplicate_page_radio'):
                if output_config.multi_barcode_handling == "duplicate_page":
                    self.duplicate_page_radio.setChecked(True)
                else:
                    self.first_radio.setChecked(True)
            
            logger.debug("配置加载到UI完成")
            
        except Exception as e:
            logger.error(f"加载配置到UI失败: {e}")
    
    def get_config_from_ui(self):
        """从UI获取配置"""
        try:
            # 条码类型
            enabled_types = []
            all_types_checked = self.barcode_type_checkboxes.get("ALL_TYPES", 
                                                            QCheckBox()).isChecked()
            
            logger.debug(f"ALL_TYPES复选框状态: {all_types_checked}")
            
            if all_types_checked:
                # 如果选择了"所有类型"，则包含所有类型
                enabled_types = ["ALL_TYPES"]
                logger.debug("选择了所有类型")
            else:
                # 否则只包含选中的具体类型
                enabled_types = [
                    barcode_type for barcode_type, checkbox in self.barcode_type_checkboxes.items()
                    if barcode_type != "ALL_TYPES" and checkbox.isChecked()
                ]
                logger.debug(f"选择了具体类型: {enabled_types}")
            
            # 过滤规则
            include_keywords = []
            if self.include_keywords_edit.text().strip():
                include_keywords = [
                    keyword.strip() for keyword in self.include_keywords_edit.text().split(',')
                    if keyword.strip()
                ]
            
            exclude_keywords = []
            if self.exclude_keywords_edit.text().strip():
                exclude_keywords = [
                    keyword.strip() for keyword in self.exclude_keywords_edit.text().split(',')
                    if keyword.strip()
                ]
            
            filter_config = BarcodeFilterConfig(
                enabled_types=enabled_types,
                min_length=self.min_length_spin.value(),
                max_length=self.max_length_spin.value(),
                include_keywords=include_keywords,
                exclude_keywords=exclude_keywords,
                include_regex=self.include_regex_edit.text().strip(),
                exclude_regex=self.exclude_regex_edit.text().strip()
            )
            
            # 输出设置
            output_dir = self.output_dir_label.text()
            if output_dir == "未选择目录":
                output_dir = ""
            
            # 确定多条码处理模式
            multi_barcode_handling = "first"
            if hasattr(self, 'duplicate_page_radio') and self.duplicate_page_radio.isChecked():
                multi_barcode_handling = "duplicate_page"
            
            output_config = BarcodeOutputConfig(
                output_dir=output_dir,
                use_barcode_filename=self.use_barcode_name_check.isChecked(),
                filename_template=self.filename_template_edit.text(),
                duplicate_handling="merge" if self.merge_radio.isChecked() else "separate",
                multi_barcode_handling=multi_barcode_handling
            )
            
            config = BarcodeSplitConfig(
                filter_config=filter_config,
                output_config=output_config
            )
            
            logger.debug(f"从UI获取配置完成，启用的条码类型: {enabled_types}")
            return config
            
        except Exception as e:
            logger.error(f"从UI获取配置失败: {e}")
            return self.current_config
    
    def _save_config(self):
        """保存配置"""
        try:
            config = self.get_config_from_ui()
            self.current_config = config
            
            if self.config_manager.save_config(config):
                QMessageBox.information(self, "成功", "配置保存成功！")
                self.config_changed.emit(config)
            else:
                QMessageBox.warning(self, "失败", "配置保存失败！")
                
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存配置时发生错误: {e}")
    
    def _load_config(self):
        """加载配置"""
        # 这里可以实现配置选择对话框，暂时加载最后使用的配置
        try:
            config = self.config_manager.load_last_used_config()
            self.current_config = config
            self.load_config_to_ui()
            QMessageBox.information(self, "成功", "配置加载成功！")
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            QMessageBox.critical(self, "错误", f"加载配置时发生错误: {e}")
    
    def _reset_to_default(self):
        """重置为默认配置"""
        try:
            self.current_config = BarcodeSplitConfig()
            self.load_config_to_ui()
            QMessageBox.information(self, "成功", "已重置为默认配置！")
            
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            QMessageBox.critical(self, "错误", f"重置配置时发生错误: {e}")
    
    def _test_detection(self):
        """测试条码检测"""
        self._detect_barcodes()
    
    def _start_split(self):
        """开始拆分"""
        # 验证配置
        config = self.get_config_from_ui()
        
        if not config.output_config.output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return
        
        # 检查是否有效选择了条码类型
        # "ALL_TYPES" 或任何非空类型列表都是有效选择
        enabled_types = config.filter_config.enabled_types
        logger.debug(f"验证条码类型: {enabled_types}")
        if not enabled_types or len(enabled_types) == 0:
            logger.warning(f"条码类型验证失败: {enabled_types}")
            QMessageBox.warning(self, "警告", "请至少选择一种条码类型")
            return
        
        # 特殊处理：如果选择了ALL_TYPES但具体类型为空，也需要通过验证
        if len(enabled_types) == 1 and enabled_types[0] == "ALL_TYPES":
            # 这是有效的选择
            logger.debug("选择了所有类型，验证通过")
            pass
        elif len(enabled_types) == 0:
            logger.warning("未选择任何条码类型")
            QMessageBox.warning(self, "警告", "请至少选择一种条码类型")
            return
        else:
            logger.debug(f"选择了 {len(enabled_types)} 种条码类型，验证通过")
        
        if not self.current_file_path:
            QMessageBox.warning(self, "警告", "请先打开PDF文件")
            return
        
        # 保存配置并接受对话框
        self.current_config = config
        self.config_manager.save_config(config)
        self.accept()
    
    def get_config(self):
        """获取当前配置"""
        return self.current_config
    
    def _on_all_types_toggled(self, checked):
        """当"所有类型"复选框状态改变时"""
        logger.debug(f"所有类型复选框状态改变: {checked}")
        
        # 如果选中了"所有类型"，禁用其他复选框
        if checked:
            for barcode_type, checkbox in self.barcode_type_checkboxes.items():
                if barcode_type != "ALL_TYPES":
                    checkbox.setEnabled(False)
                    checkbox.setChecked(False)  # 取消选中其他类型
        else:
            # 如果取消选中"所有类型"，启用其他复选框
            for barcode_type, checkbox in self.barcode_type_checkboxes.items():
                if barcode_type != "ALL_TYPES":
                    checkbox.setEnabled(True)
    
    def _on_specific_type_toggled(self, checked):
        """当具体类型复选框状态改变时"""
        logger.debug(f"具体类型复选框状态改变: {checked}")
        
        # 如果选中了某个具体类型，取消选中"所有类型"
        if checked:
            all_types_checkbox = self.barcode_type_checkboxes.get("ALL_TYPES")
            if all_types_checkbox and all_types_checkbox.isChecked():
                all_types_checkbox.setChecked(False)
        
        # 检查是否没有任何类型被选中
        any_selected = any(
            checkbox.isChecked() 
            for barcode_type, checkbox in self.barcode_type_checkboxes.items()
            if barcode_type != "ALL_TYPES"
        )
        
        # 如果没有任何具体类型被选中，自动选中"所有类型"
        if not any_selected and not self.barcode_type_checkboxes.get("ALL_TYPES", QCheckBox()).isChecked():
            all_types_checkbox = self.barcode_type_checkboxes.get("ALL_TYPES")
            if all_types_checkbox:
                all_types_checkbox.setChecked(True)