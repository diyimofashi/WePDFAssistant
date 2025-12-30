"""
条码插件设置对话框
提供GUI界面来配置条码插件的各种设置，模仿OCR设置对话框的结构
"""

import json
import fitz  # PyMuPDF
from typing import Dict, Any
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QPushButton, QLineEdit, QTextEdit, QCheckBox,
                            QSpinBox, QDoubleSpinBox, QGroupBox, QTabWidget,
                            QMessageBox, QLabel, QComboBox, QScrollArea, QButtonGroup, QRadioButton,
                            QSizePolicy, QWidget, QLayout, QGridLayout, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.managers.barcode_plugin_manager import barcode_plugin_manager
from app.config.barcode_plugin_config import barcode_config_manager


class BarcodeSettingsDialog(QDialog):
    """条码插件设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("条码插件设置")
        self.resize(800, 600)
        self.setModal(False)  # 设置为非模态对话框
        
        # 初始化配置管理器
        self.plugin_manager = barcode_plugin_manager
        self.config_manager = barcode_config_manager
        
        # 存储控件引用
        self.plugin_widgets = {}
        
        # 自动加载插件
        try:
            self.plugin_manager.load_all_plugins()
        except Exception as e:
            print(f"加载条码插件时出错: {e}")
        
        self.setup_ui()
        self.create_plugin_settings_tabs()
        self.load_settings()
    
    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # 适当增加组件间距
        layout.setContentsMargins(15, 15, 15, 15)  # 适当增加边距
        # 允许布局根据内容调整大小
        layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        # 设置标签页位置为北（顶部），并设置标签对齐方式为左对齐
        self.tab_widget.setTabPosition(QTabWidget.North)
        # 设置标签页的样式，使其左对齐，去掉选中背景色
        self.tab_widget.setStyleSheet("""
            QTabWidget::tab-bar { alignment: left; }
            QTabBar::tab {
                min-width: 80px;
                padding: 8px 12px;
                background: transparent;
                border: none;
            }
            QTabBar::tab:selected {
                background: transparent;
                color: #0078d4;
                font-weight: bold;
            }
        """)
        
        # 添加插件设置标签页
        layout.addWidget(self.tab_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 保存设置")
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        # 测试检测按钮
        self.test_detection_btn = QPushButton("🔍 测试检测")
        self.test_detection_btn.clicked.connect(self.test_detection)
        button_layout.addWidget(self.test_detection_btn)
        
        # 开始拆分按钮
        self.start_split_btn = QPushButton("✂️ 开始拆分")
        self.start_split_btn.setStyleSheet('''
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                padding: 8px 16px; 
                border: none; 
                border-radius: 4px; 
                font-weight: bold;
            }
        ''')
        self.start_split_btn.clicked.connect(self.start_split)
        button_layout.addWidget(self.start_split_btn)
        
        self.close_btn = QPushButton("❌ 关闭")
        self.close_btn.clicked.connect(self.accept)  # 使用accept而不是close
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def accept(self):
        """点击确定按钮时保存设置"""
        try:
            # 保存每个插件的配置
            for plugin_name, widgets in self.plugin_widgets.items():
                config = {}
                
                # 收集配置值
                for option_key, widget in widgets.items():
                    if option_key.endswith('_options') or option_key == 'barcode_type_checkboxes':
                        continue  # 跳过选项映射和复选框组
                    value = self.get_widget_value(widget)
                    if value is not None:
                        config[option_key] = value
                
                # 处理条码类型复选框组
                if 'barcode_type_checkboxes' in widgets:
                    barcode_type_checkboxes = widgets['barcode_type_checkboxes']
                    enabled_types = []
                    all_types_checked = barcode_type_checkboxes.get("ALL_TYPES", QCheckBox()).isChecked()
                    
                    if all_types_checked:
                        enabled_types = ["ALL_TYPES"]
                    else:
                        enabled_types = [
                            barcode_type for barcode_type, checkbox in barcode_type_checkboxes.items()
                            if barcode_type != "ALL_TYPES" and checkbox.isChecked()
                        ]
                    config['enabled_types'] = enabled_types
                
                # 验证并保存配置
                errors = self.config_manager.set_plugin_config(plugin_name, config)
                if errors:
                    # 显示验证错误
                    from PyQt5.QtWidgets import QMessageBox
                    error_msg = "\n".join([f"{key}: {msg}" for key, msg in errors.items()])
                    QMessageBox.warning(self, "配置验证失败", 
                                      f"插件 {plugin_name} 配置验证失败:\n{error_msg}")
                    return
            
            # 保存配置到文件
            self.config_manager.save_config()
            
            # 调用父类方法关闭对话框
            super().accept()
            
        except Exception as e:
            from app.utils.logger import get_logger
            logger = get_logger('barcode_settings_dialog')
            logger.error(f"保存配置时出错: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "保存失败", f"保存配置时发生错误: {str(e)}")
    
    def test_detection(self):
        """测试检测功能"""
        try:
            from PyQt5.QtWidgets import QMessageBox, QFileDialog
            
            # 获取当前选中的插件
            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index < 0:
                QMessageBox.warning(self, "警告", "没有选中的插件")
                return
            
            plugin_name = self.tab_widget.tabText(current_tab_index)
            plugin = self.plugin_manager.get_plugin(plugin_name)
            
            if not plugin:
                QMessageBox.critical(self, "错误", f"无法获取插件: {plugin_name}")
                return
            
            # 获取插件配置
            config = self.get_plugin_config_for_saving(plugin_name)
            
            # 初始化插件
            init_result = plugin.initialize(config)
            if not init_result.is_success():
                QMessageBox.critical(self, "错误", f"插件初始化失败: {init_result.message}")
                return
            
            # 选择测试文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择测试文件", "", "PDF文件 (*.pdf);;图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
            )
            
            if not file_path:
                return  # 用户取消了选择
            
            # 根据文件类型调用相应的检测方法
            if file_path.lower().endswith('.pdf'):
                # 对于PDF文件，使用插件的PDF检测功能
                import fitz
                doc = fitz.open(file_path)
                try:
                    result = plugin.detect_from_pdf(doc, config)
                finally:
                    doc.close()
            else:
                # 对于图片文件，直接检测
                result = plugin.detect_from_file(file_path)
            
            if result.is_success():
                QMessageBox.information(self, "测试检测结果", f"检测成功！\n{result.message}\n\n检测到的条码数据:\n{result.data}")
            else:
                QMessageBox.warning(self, "测试检测结果", f"检测失败:\n{result.message}")
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"测试检测时出错: {str(e)}")
    
    def start_split(self):
        """开始拆分功能"""
        try:
            from PyQt5.QtWidgets import QMessageBox, QFileDialog
            from app.utils.logger import get_logger
            logger = get_logger('barcode_settings_dialog')

            # 获取当前选中的插件
            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index < 0:
                QMessageBox.warning(self, "警告", "没有选中的插件")
                return

            plugin_name = self.tab_widget.tabText(current_tab_index)
            logger.info(f"开始拆分，使用插件: {plugin_name}")

            plugin = self.plugin_manager.get_plugin(plugin_name)

            if not plugin:
                QMessageBox.critical(self, "错误", f"无法获取插件: {plugin_name}")
                return

            # 获取插件配置
            config = self.get_plugin_config_for_saving(plugin_name)
            logger.info(f"获取到插件配置: {config}")

            # 初始化插件
            init_result = plugin.initialize(config)
            if not init_result.is_success():
                QMessageBox.critical(self, "错误", f"插件初始化失败: {init_result.message}")
                return

            logger.info(f"插件 {plugin_name} 初始化成功")
            
            # 选择要拆分的PDF文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择PDF文件", "", "PDF文件 (*.pdf)"
            )
            
            if not file_path:
                return  # 用户取消了选择
            
            # 如果没有配置输出目录，则使用PDF文件所在目录
            output_dir = config.get('output_dir', '')
            if not output_dir:
                import os
                output_dir = os.path.dirname(file_path)  # 使用PDF文件所在目录
                config['output_dir'] = output_dir
            
            # 调用插件的拆分功能
            doc = fitz.open(file_path)
            
            # 使用插件进行拆分，带进度反馈
            from PyQt5.QtWidgets import QProgressDialog
            from PyQt5.QtCore import Qt
            
            # 创建进度对话框
            progress_dialog = QProgressDialog("正在拆分文档...", "取消", 0, 100, self)
            progress_dialog.setWindowTitle("拆分进度")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)
            
            def progress_callback(current, total, message=""):
                if progress_dialog.wasCanceled():
                    return False  # 告诉拆分过程取消
                # 确保total是整数类型
                try:
                    total = int(total)
                except (ValueError, TypeError):
                    total = 0
                # 确保current是整数类型
                try:
                    current = int(current)
                except (ValueError, TypeError):
                    current = 0
                progress_percent = int((current / total) * 100) if total > 0 else 0
                progress_dialog.setValue(progress_percent)
                if message:
                    progress_dialog.setLabelText(message)
                QApplication.processEvents()  # 允许界面更新
                return True  # 继续处理
            
            # 调用插件的拆分功能，传入进度回调
            result = self.plugin_manager.split_document_with_plugin(plugin_name, doc, output_dir, config, progress_callback)
            
            progress_dialog.close()
            
            if result.get('success', False):
                QMessageBox.information(self, "拆分完成", f"拆分成功！\n{result.get('message', '')}\n\n创建了 {len(result.get('files_created', []))} 个文件")
            else:
                QMessageBox.critical(self, "拆分失败", f"拆分失败:\n{result.get('message', '未知错误')}")
            
            doc.close()
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"开始拆分时出错: {str(e)}")
    
    def get_plugin_config_for_saving(self, plugin_name):
        """获取插件配置用于保存"""
        if plugin_name not in self.plugin_widgets:
            return {}

        config = {}
        plugin_widgets = self.plugin_widgets[plugin_name]

        for key, widget in plugin_widgets.items():
            if key.endswith('_options'):
                continue  # 跳过选项映射
            elif key == 'barcode_type_checkboxes':
                # 处理条码类型复选框组
                barcode_type_checkboxes = widget
                enabled_types = []
                all_types_checked = barcode_type_checkboxes.get("ALL_TYPES", QCheckBox()).isChecked()

                if all_types_checked:
                    enabled_types = ["ALL_TYPES"]
                else:
                    enabled_types = [
                        barcode_type for barcode_type, checkbox in barcode_type_checkboxes.items()
                        if barcode_type != "ALL_TYPES" and checkbox.isChecked()
                    ]
                config[key] = enabled_types
            else:
                from app.utils.logger import get_logger
                logger = get_logger('barcode_settings_dialog')
                logger.debug(f"获取配置项 {key}, widget类型={type(widget).__name__}")
                value = self.get_widget_value(widget)
                # 特殊处理：split_position_rule为None时使用默认值
                if key == 'split_position_rule' and value is None:
                    logger.warning(f"split_position_rule值为None，使用默认值separator_page")
                    value = 'separator_page'
                config[key] = value
                # 添加日志记录配置值
                logger.debug(f"配置项 {key}: {value} (类型: {type(value).__name__})")

        from app.utils.logger import get_logger
        logger = get_logger('barcode_settings_dialog')
        logger.info(f"插件 {plugin_name} 完整配置: {config}")

        return config
    
    def _on_all_types_toggled(self, checked, barcode_type_checkboxes):
        """当"所有类型"复选框状态改变时"""
        # 如果选中了"所有类型"，禁用其他复选框
        if checked:
            for barcode_type, checkbox in barcode_type_checkboxes.items():
                if barcode_type != "ALL_TYPES":
                    checkbox.setEnabled(False)
                    checkbox.setChecked(False)  # 取消选中其他类型
        else:
            # 如果取消选中"所有类型"，启用其他复选框
            for barcode_type, checkbox in barcode_type_checkboxes.items():
                if barcode_type != "ALL_TYPES":
                    checkbox.setEnabled(True)
    
    def _on_specific_type_toggled(self):
        """当具体类型复选框状态改变时"""
        # 检查是否没有任何类型被选中
        # 这里需要获取当前插件的复选框
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0:
            return
        
        plugin_name = self.tab_widget.tabText(current_tab_index)
        if plugin_name in self.plugin_widgets:
            plugin_widgets = self.plugin_widgets[plugin_name]
            if 'barcode_type_checkboxes' in plugin_widgets:
                barcode_type_checkboxes = plugin_widgets['barcode_type_checkboxes']
                
                # 检查是否有具体类型被选中
                any_selected = any(
                    checkbox.isChecked() 
                    for barcode_type, checkbox in barcode_type_checkboxes.items()
                    if barcode_type != "ALL_TYPES"
                )
                
                # 如果没有任何具体类型被选中，自动选中"所有类型"
                all_types_checkbox = barcode_type_checkboxes.get("ALL_TYPES")
                if all_types_checkbox and not any_selected and not all_types_checkbox.isChecked():
                    all_types_checkbox.setChecked(True)
    
    def _select_output_directory(self, line_edit):
        """选择输出目录"""
        from PyQt5.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self, "选择输出目录", line_edit.text() or ""
        )
        
        if directory:
            line_edit.setText(directory)
    
    def create_plugin_settings_tabs(self):
        """为每个插件创建设置标签页"""
        # 获取所有已加载的插件
        plugins = self.plugin_manager.list_plugins()
        
        if not plugins:
            # 如果没有插件，显示提示信息
            no_plugin_widget = QWidget()
            no_plugin_layout = QVBoxLayout(no_plugin_widget)
            no_plugin_label = QLabel("暂无条码插件加载")
            no_plugin_label.setAlignment(Qt.AlignCenter)
            no_plugin_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
            no_plugin_layout.addWidget(no_plugin_label)
            self.tab_widget.addTab(no_plugin_widget, "插件设置")
            return
        
        # 为每个插件创建标签页
        for plugin_name in plugins:
            self.create_plugin_tab(plugin_name)
    
    def create_plugin_tab(self, plugin_name):
        """为指定插件创建设置标签页"""
        plugin_widget = QWidget()
        plugin_layout = QVBoxLayout(plugin_widget)
        plugin_layout.setSpacing(12)  # 适当增加组件间距
        plugin_layout.setContentsMargins(12, 12, 12, 12)  # 适当增加边距
        
        # 获取插件信息
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            error_label = QLabel(f"无法获取插件信息: {plugin_name}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-weight: bold;")
            plugin_layout.addWidget(error_label)
            self.tab_widget.addTab(plugin_widget, plugin_name)
            return
        
        # 获取插件配置定义
        # 从配置管理器获取插件配置定义
        config_definitions = self.config_manager.config_definitions.get(plugin_name, [])
        
        if config_definitions:
            # 如果有配置定义，使用配置定义创建控件
            self.create_config_controls(plugin_name, plugin_widget, config_definitions)
        else:
            # 尝试从插件的PluginInfo获取配置信息
            plugin_info = getattr(plugin, 'PluginInfo', {})
            local_options = plugin_info.get('local_options', {})
            global_options = plugin_info.get('global_options', {})
            
            # 如果PluginInfo中包含配置定义信息，使用它们
            if local_options or global_options:
                # 创建基于PluginInfo的配置控件
                self.create_config_controls_from_plugin_info(plugin_name, plugin_widget, plugin_info)
            else:
                # 如果没有配置定义，创建默认配置界面
                self.create_default_config_controls(plugin_name, plugin_widget, plugin)
        
        # 添加标签页
        self.tab_widget.addTab(plugin_widget, plugin_name)
    
    def create_config_controls(self, plugin_name, parent_widget, config_definitions):
        """根据配置定义创建控件"""
        plugin_layout = parent_widget.layout()
        
        # 插件说明标题
        title_label = QLabel(f"{plugin_name} - 插件配置")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        plugin_layout.addWidget(title_label)
        
        # 创建滚动区域以容纳设置
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 移除灰色背景
        scroll_area.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        # 设置滚动区域大小策略
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)  # 适当增加滚动区域内部间距
        scroll_layout.setContentsMargins(8, 8, 8, 8)  # 适当增加滚动区域边距
        
        # 为每个配置项创建控件
        self.plugin_widgets[plugin_name] = {}
        
        for config_item in config_definitions:
            # 特殊处理启用的条码类型，使用复选框组
            if config_item.key == 'enabled_types':
                # 创建条码类型选择组
                type_group = QGroupBox(config_item.title)
                type_layout = QVBoxLayout(type_group)
                
                # 使用滚动区域来容纳条码类型复选框，支持多选
                type_scroll_area = QScrollArea()
                type_scroll_area.setWidgetResizable(True)
                type_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                type_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                type_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                
                # 创建一个容器widget来放置所有复选框
                container_widget = QWidget()
                type_grid_layout = QGridLayout(container_widget)
                type_grid_layout.setSpacing(5)  # 减少间距
                
                # 创建条码类型复选框
                barcode_type_checkboxes = {}
                
                # 首先添加"所有类型"选项
                all_types_checkbox = QCheckBox("🔍 所有类型")
                all_types_checkbox.setChecked("ALL_TYPES" in (config_item.default or []))
                all_types_checkbox.toggled.connect(lambda checked, atc=all_types_checkbox: self._on_all_types_toggled(checked, barcode_type_checkboxes))
                barcode_type_checkboxes["ALL_TYPES"] = all_types_checkbox
                type_grid_layout.addWidget(all_types_checkbox, 0, 0, 1, 4)
                
                # 然后添加具体类型复选框
                supported_types = ["QRCODE", "CODE128", "CODE39", "EAN13", "EAN8", "UPCA", "UPCE", "CODE93", "CODEBAR", "PDF417", "DATAMATRIX"]
                type_index = 0  # 用于布局索引的计数器
                for barcode_type in supported_types:
                    if barcode_type == "ALL_TYPES":
                        continue
                        
                    checkbox = QCheckBox(barcode_type.replace('_', ' '))
                    checkbox.setChecked(barcode_type in (config_item.default or []))
                    checkbox.toggled.connect(lambda checked: self._on_specific_type_toggled())
                    barcode_type_checkboxes[barcode_type] = checkbox
                    
                    row = type_index // 4 + 1  # +1 因为第一行是"所有类型"
                    col = type_index % 4
                    type_grid_layout.addWidget(checkbox, row, col)
                    type_index += 1
                
                type_scroll_area.setWidget(container_widget)
                type_layout.addWidget(type_scroll_area)
                
                # 保存复选框引用
                self.plugin_widgets[plugin_name]['barcode_type_checkboxes'] = barcode_type_checkboxes
                
                scroll_layout.addWidget(type_group)
            elif config_item.key == 'output_dir':
                # 特殊处理输出目录，使用选择目录按钮
                output_layout = QHBoxLayout()
                output_label = QLabel(config_item.title + ":")
                output_label.setStyleSheet("QLabel { font-weight: bold; }")
                output_label.setToolTip(config_item.description)
                
                output_dir_edit = QLineEdit()
                output_dir_edit.setPlaceholderText("点击右侧按钮选择输出目录")
                output_dir_edit.setFixedHeight(30)
                output_dir_edit.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }\n")
                if config_item.default:
                    output_dir_edit.setText(str(config_item.default))
                output_dir_edit.setToolTip(config_item.description)
                
                select_dir_btn = QPushButton("📁 选择目录")
                select_dir_btn.clicked.connect(lambda: self._select_output_directory(output_dir_edit))
                
                output_layout.addWidget(output_label)
                output_layout.addWidget(output_dir_edit)
                output_layout.addWidget(select_dir_btn)
                
                scroll_layout.addLayout(output_layout)
                
                # 存储控件引用
                self.plugin_widgets[plugin_name][config_item.key] = output_dir_edit
            else:
                widget = self.create_config_widget(plugin_name, config_item)
                if widget:
                    h_layout = QHBoxLayout()
                    label = QLabel(config_item.title + ":")
                    label.setStyleSheet("QLabel { font-weight: bold; }")
                    label.setToolTip(config_item.description)
                    widget.setToolTip(config_item.description)
                    
                    h_layout.addWidget(label)
                    h_layout.addWidget(widget)
                    h_layout.addStretch()
                    
                    scroll_layout.addLayout(h_layout)
                    
                    # 存储控件引用
                    self.plugin_widgets[plugin_name][config_item.key] = widget
        
        scroll_layout.addStretch()
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        
        plugin_layout.addWidget(scroll_area)
    
    def create_default_config_controls(self, plugin_name, parent_widget, plugin):
        """创建默认配置控件"""
        plugin_layout = parent_widget.layout()
        
        # 插件说明标题
        title_label = QLabel(f"{plugin_name} - 插件配置")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        plugin_layout.addWidget(title_label)
        
        # 创建滚动区域以容纳设置
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 移除灰色背景
        scroll_area.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        # 设置滚动区域大小策略
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)  # 适当增加滚动区域内部间距
        scroll_layout.setContentsMargins(8, 8, 8, 8)  # 适当增加滚动区域边距
        
        # 创建默认配置控件
        self.plugin_widgets[plugin_name] = {}
        
        # 最大检测数量
        max_count_layout = QHBoxLayout()
        max_count_label = QLabel("最大检测数量:")
        max_count_label.setStyleSheet("QLabel { font-weight: bold; }")
        max_count_spin = QSpinBox()
        max_count_spin.setRange(1, 10000)
        max_count_spin.setValue(100)
        max_count_spin.setSuffix(" 个")
        max_count_spin.setFixedHeight(30)
        max_count_spin.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
        max_count_layout.addWidget(max_count_label)
        max_count_layout.addWidget(max_count_spin)
        max_count_layout.addStretch()
        scroll_layout.addLayout(max_count_layout)
        self.plugin_widgets[plugin_name]['max_barcode_count'] = max_count_spin
        
        # 检测模式
        detection_mode_layout = QHBoxLayout()
        detection_mode_label = QLabel("检测模式:")
        detection_mode_label.setStyleSheet("QLabel { font-weight: bold; }")
        detection_mode_combo = QComboBox()
        detection_mode_combo.addItems(["快速", "标准", "详细"])
        detection_mode_combo.setFixedHeight(30)
        detection_mode_combo.setStyleSheet("""
            QComboBox { 
                padding: 4px; 
                font-size: 11pt; 
                background-color: white;
                color: black;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: white !important;
                color: black !important;
                selection-background-color: #0078d4 !important;
                selection-color: white !important;
            }
        """)
        detection_mode_layout.addWidget(detection_mode_label)
        detection_mode_layout.addWidget(detection_mode_combo)
        detection_mode_layout.addStretch()
        scroll_layout.addLayout(detection_mode_layout)
        self.plugin_widgets[plugin_name]['detection_mode'] = detection_mode_combo
        
        # 启用旋转检测
        enable_rotation_layout = QHBoxLayout()
        enable_rotation_label = QLabel("启用旋转检测:")
        enable_rotation_label.setStyleSheet("QLabel { font-weight: bold; }")
        enable_rotation_check = QCheckBox()
        enable_rotation_check.setStyleSheet("QCheckBox { spacing: 8px; font-size: 11pt; }")
        enable_rotation_layout.addWidget(enable_rotation_label)
        enable_rotation_layout.addWidget(enable_rotation_check)
        enable_rotation_layout.addStretch()
        scroll_layout.addLayout(enable_rotation_layout)
        self.plugin_widgets[plugin_name]['enable_rotation'] = enable_rotation_check
        
        # 超时时间
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("超时时间:")
        timeout_label.setStyleSheet("QLabel { font-weight: bold; }")
        timeout_spin = QSpinBox()
        timeout_spin.setRange(1, 300)
        timeout_spin.setValue(30)
        timeout_spin.setSuffix(" 秒")
        timeout_spin.setFixedHeight(30)
        timeout_spin.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(timeout_spin)
        timeout_layout.addStretch()
        scroll_layout.addLayout(timeout_layout)
        self.plugin_widgets[plugin_name]['timeout'] = timeout_spin
        
        # 并行处理
        parallel_layout = QHBoxLayout()
        parallel_label = QLabel("并行处理:")
        parallel_label.setStyleSheet("QLabel { font-weight: bold; }")
        parallel_check = QCheckBox()
        parallel_check.setStyleSheet("QCheckBox { spacing: 8px; font-size: 11pt; }")
        parallel_layout.addWidget(parallel_label)
        parallel_layout.addWidget(parallel_check)
        parallel_layout.addStretch()
        scroll_layout.addLayout(parallel_layout)
        self.plugin_widgets[plugin_name]['parallel_processing'] = parallel_check
        
        # 图像预处理
        preprocess_layout = QHBoxLayout()
        preprocess_label = QLabel("图像预处理:")
        preprocess_label.setStyleSheet("QLabel { font-weight: bold; }")
        preprocess_check = QCheckBox()
        preprocess_check.setStyleSheet("QCheckBox { spacing: 8px; font-size: 11pt; }")
        preprocess_layout.addWidget(preprocess_label)
        preprocess_layout.addWidget(preprocess_check)
        preprocess_layout.addStretch()
        scroll_layout.addLayout(preprocess_layout)
        self.plugin_widgets[plugin_name]['enable_preprocessing'] = preprocess_check
        
        # DPI设置
        dpi_layout = QHBoxLayout()
        dpi_label = QLabel("图像DPI:")
        dpi_label.setStyleSheet("QLabel { font-weight: bold; }")
        dpi_spin = QSpinBox()
        dpi_spin.setRange(72, 600)
        dpi_spin.setValue(300)
        dpi_spin.setSuffix(" DPI")
        dpi_spin.setFixedHeight(30)
        dpi_spin.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
        dpi_layout.addWidget(dpi_label)
        dpi_layout.addWidget(dpi_spin)
        dpi_layout.addStretch()
        scroll_layout.addLayout(dpi_layout)
        self.plugin_widgets[plugin_name]['dpi'] = dpi_spin
        
        # 最小长度
        min_length_layout = QHBoxLayout()
        min_length_label = QLabel("最小长度:")
        min_length_label.setStyleSheet("QLabel { font-weight: bold; }")
        min_length_spin = QSpinBox()
        min_length_spin.setRange(1, 10000)
        min_length_spin.setValue(1)
        min_length_spin.setFixedHeight(30)
        min_length_spin.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
        min_length_layout.addWidget(min_length_label)
        min_length_layout.addWidget(min_length_spin)
        min_length_layout.addStretch()
        scroll_layout.addLayout(min_length_layout)
        self.plugin_widgets[plugin_name]['min_length'] = min_length_spin
        
        # 最大长度
        max_length_layout = QHBoxLayout()
        max_length_label = QLabel("最大长度:")
        max_length_label.setStyleSheet("QLabel { font-weight: bold; }")
        max_length_spin = QSpinBox()
        max_length_spin.setRange(1, 10000)
        max_length_spin.setValue(1000)
        max_length_spin.setFixedHeight(30)
        max_length_spin.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
        max_length_layout.addWidget(max_length_label)
        max_length_layout.addWidget(max_length_spin)
        max_length_layout.addStretch()
        scroll_layout.addLayout(max_length_layout)
        self.plugin_widgets[plugin_name]['max_length'] = max_length_spin
        
        # 包含关键词
        include_keywords_layout = QHBoxLayout()
        include_keywords_label = QLabel("包含关键词:")
        include_keywords_label.setStyleSheet("QLabel { font-weight: bold; }")
        include_keywords_edit = QLineEdit()
        include_keywords_edit.setPlaceholderText("用逗号分隔多个关键词")
        include_keywords_edit.setFixedHeight(30)
        include_keywords_edit.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
        include_keywords_layout.addWidget(include_keywords_label)
        include_keywords_layout.addWidget(include_keywords_edit)
        include_keywords_layout.addStretch()
        scroll_layout.addLayout(include_keywords_layout)
        self.plugin_widgets[plugin_name]['include_keywords'] = include_keywords_edit
        
        # 排除关键词
        exclude_keywords_layout = QHBoxLayout()
        exclude_keywords_label = QLabel("排除关键词:")
        exclude_keywords_label.setStyleSheet("QLabel { font-weight: bold; }")
        exclude_keywords_edit = QLineEdit()
        exclude_keywords_edit.setPlaceholderText("用逗号分隔多个关键词")
        exclude_keywords_edit.setFixedHeight(30)
        exclude_keywords_edit.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
        exclude_keywords_layout.addWidget(exclude_keywords_label)
        exclude_keywords_layout.addWidget(exclude_keywords_edit)
        exclude_keywords_layout.addStretch()
        scroll_layout.addLayout(exclude_keywords_layout)
        self.plugin_widgets[plugin_name]['exclude_keywords'] = exclude_keywords_edit
        
        # 包含正则
        include_regex_layout = QHBoxLayout()
        include_regex_label = QLabel("包含正则:")
        include_regex_label.setStyleSheet("QLabel { font-weight: bold; }")
        include_regex_edit = QLineEdit()
        include_regex_edit.setPlaceholderText("匹配条码内容的正则表达式")
        include_regex_edit.setFixedHeight(30)
        include_regex_edit.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
        include_regex_layout.addWidget(include_regex_label)
        include_regex_layout.addWidget(include_regex_edit)
        include_regex_layout.addStretch()
        scroll_layout.addLayout(include_regex_layout)
        self.plugin_widgets[plugin_name]['include_regex'] = include_regex_edit
        
        # 排除正则
        exclude_regex_layout = QHBoxLayout()
        exclude_regex_label = QLabel("排除正则:")
        exclude_regex_label.setStyleSheet("QLabel { font-weight: bold; }")
        exclude_regex_edit = QLineEdit()
        exclude_regex_edit.setPlaceholderText("排除条码内容的正则表达式")
        exclude_regex_edit.setFixedHeight(30)
        exclude_regex_edit.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
        exclude_regex_layout.addWidget(exclude_regex_label)
        exclude_regex_layout.addWidget(exclude_regex_edit)
        exclude_regex_layout.addStretch()
        scroll_layout.addLayout(exclude_regex_layout)
        self.plugin_widgets[plugin_name]['exclude_regex'] = exclude_regex_edit
        
        # 重复处理模式
        duplicate_handling_layout = QHBoxLayout()
        duplicate_handling_label = QLabel("重复处理模式:")
        duplicate_handling_label.setStyleSheet("QLabel { font-weight: bold; }")
        duplicate_handling_combo = QComboBox()
        # 创建选项字典，将显示文本映射到实际值
        duplicate_handling_options = {"分离": "separate", "合并": "merge"}
        duplicate_handling_combo.addItems(list(duplicate_handling_options.keys()))
        duplicate_handling_combo.setFixedHeight(30)
        duplicate_handling_combo.setStyleSheet('''
            QComboBox { 
                padding: 4px; 
                font-size: 11pt; 
                background-color: white;
                color: black;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: white !important;
                color: black !important;
                selection-background-color: #0078d4 !important;
                selection-color: white !important;
            }
        ''')
        duplicate_handling_layout.addWidget(duplicate_handling_label)
        duplicate_handling_layout.addWidget(duplicate_handling_combo)
        duplicate_handling_layout.addStretch()
        scroll_layout.addLayout(duplicate_handling_layout)
        self.plugin_widgets[plugin_name]['duplicate_handling'] = duplicate_handling_combo
        # 保存选项映射
        self.plugin_widgets[plugin_name]['duplicate_handling_options'] = duplicate_handling_options
                
        # 多条码处理模式
        multi_barcode_handling_layout = QHBoxLayout()
        multi_barcode_handling_label = QLabel("多条码处理:")
        multi_barcode_handling_label.setStyleSheet("QLabel { font-weight: bold; }")
        multi_barcode_handling_combo = QComboBox()
        # 创建选项字典，将显示文本映射到实际值
        multi_barcode_handling_options = {"首个": "first", "复制页面": "duplicate_page"}
        multi_barcode_handling_combo.addItems(list(multi_barcode_handling_options.keys()))
        multi_barcode_handling_combo.setFixedHeight(30)
        multi_barcode_handling_combo.setStyleSheet('''
            QComboBox { 
                padding: 4px; 
                font-size: 11pt; 
                background-color: white;
                color: black;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: white !important;
                color: black !important;
                selection-background-color: #0078d4 !important;
                selection-color: white !important;
            }
        ''')
        multi_barcode_handling_layout.addWidget(multi_barcode_handling_label)
        multi_barcode_handling_layout.addWidget(multi_barcode_handling_combo)
        multi_barcode_handling_layout.addStretch()
        scroll_layout.addLayout(multi_barcode_handling_layout)
        self.plugin_widgets[plugin_name]['multi_barcode_handling'] = multi_barcode_handling_combo
        # 保存选项映射
        self.plugin_widgets[plugin_name]['multi_barcode_handling_options'] = multi_barcode_handling_options
        
        scroll_layout.addStretch()
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        
        plugin_layout.addWidget(scroll_area)
    
    def create_config_controls_from_plugin_info(self, plugin_name, parent_widget, plugin_info):
        """根据插件信息创建控件"""
        plugin_layout = parent_widget.layout()
        
        # 插件说明标题
        title_label = QLabel(f"{plugin_name} - 插件配置")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        plugin_layout.addWidget(title_label)
        
        # 创建滚动区域以容纳设置
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 移除灰色背景
        scroll_area.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        # 设置滚动区域大小策略
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)  # 适当增加滚动区域内部间距
        scroll_layout.setContentsMargins(8, 8, 8, 8)  # 适当增加滚动区域边距
        
        # 为每个配置项创建控件
        self.plugin_widgets[plugin_name] = {}
        
        # 这里可以根据PluginInfo的内容创建默认控件
        # 简单地创建一些通用的配置控件
        # 最大检测数量
        max_count_layout = QHBoxLayout()
        max_count_label = QLabel("最大检测数量:")
        max_count_label.setStyleSheet("QLabel { font-weight: bold; }")
        max_count_spin = QSpinBox()
        max_count_spin.setRange(1, 10000)
        max_count_spin.setValue(100)
        max_count_spin.setSuffix(" 个")
        max_count_spin.setFixedHeight(30)
        max_count_spin.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
        max_count_layout.addWidget(max_count_label)
        max_count_layout.addWidget(max_count_spin)
        max_count_layout.addStretch()
        scroll_layout.addLayout(max_count_layout)
        self.plugin_widgets[plugin_name]['max_barcode_count'] = max_count_spin
        
        # 检测模式
        detection_mode_layout = QHBoxLayout()
        detection_mode_label = QLabel("检测模式:")
        detection_mode_label.setStyleSheet("QLabel { font-weight: bold; }")
        detection_mode_combo = QComboBox()
        # 创建选项字典，将显示文本映射到实际值
        detection_mode_options = {"快速": "fast", "标准": "standard", "详细": "detailed"}
        detection_mode_combo.addItems(list(detection_mode_options.keys()))
        detection_mode_combo.setFixedHeight(30)
        detection_mode_combo.setStyleSheet('''
            QComboBox { 
                padding: 4px; 
                font-size: 11pt; 
                background-color: white;
                color: black;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: white !important;
                color: black !important;
                selection-background-color: #0078d4 !important;
                selection-color: white !important;
            }
        ''')
        detection_mode_layout.addWidget(detection_mode_label)
        detection_mode_layout.addWidget(detection_mode_combo)
        detection_mode_layout.addStretch()
        scroll_layout.addLayout(detection_mode_layout)
        self.plugin_widgets[plugin_name]['detection_mode'] = detection_mode_combo
        # 保存选项映射
        if plugin_name not in self.plugin_widgets:
            self.plugin_widgets[plugin_name] = {}
        self.plugin_widgets[plugin_name]['detection_mode_options'] = detection_mode_options
        
        # 启用旋转检测
        enable_rotation_layout = QHBoxLayout()
        enable_rotation_label = QLabel("启用旋转检测:")
        enable_rotation_label.setStyleSheet("QLabel { font-weight: bold; }")
        enable_rotation_check = QCheckBox()
        enable_rotation_check.setStyleSheet("QCheckBox { spacing: 8px; font-size: 11pt; }")
        enable_rotation_layout.addWidget(enable_rotation_label)
        enable_rotation_layout.addWidget(enable_rotation_check)
        enable_rotation_layout.addStretch()
        scroll_layout.addLayout(enable_rotation_layout)
        self.plugin_widgets[plugin_name]['enable_rotation'] = enable_rotation_check
        
        # 超时时间
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("超时时间:")
        timeout_label.setStyleSheet("QLabel { font-weight: bold; }")
        timeout_spin = QSpinBox()
        timeout_spin.setRange(1, 300)
        timeout_spin.setValue(30)
        timeout_spin.setSuffix(" 秒")
        timeout_spin.setFixedHeight(30)
        timeout_spin.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(timeout_spin)
        timeout_layout.addStretch()
        scroll_layout.addLayout(timeout_layout)
        self.plugin_widgets[plugin_name]['timeout'] = timeout_spin
        
        scroll_layout.addStretch()
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        
        plugin_layout.addWidget(scroll_area)
    
    def create_config_widget(self, plugin_name, config_item):
        """根据配置定义创建相应的控件"""
        try:
            if config_item.type == 'string':
                widget = QLineEdit()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if config_item.default:
                    widget.setText(str(config_item.default))
                if config_item.description:
                    widget.setPlaceholderText(config_item.description)
            elif config_item.type == 'integer':
                widget = QSpinBox()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
                min_val = config_item.min_value if config_item.min_value is not None else 0
                max_val = config_item.max_value if config_item.max_value is not None else 999999
                widget.setRange(min_val, max_val)
                if config_item.default is not None:
                    widget.setValue(int(config_item.default))
            elif config_item.type == 'float':
                widget = QDoubleSpinBox()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QDoubleSpinBox { padding: 4px; font-size: 11pt; }")
                min_val = config_item.min_value if config_item.min_value is not None else 0.0
                max_val = config_item.max_value if config_item.max_value is not None else 999999.0
                widget.setRange(min_val, max_val)
                if config_item.default is not None:
                    widget.setValue(float(config_item.default))
                widget.setDecimals(2)
            elif config_item.type == 'boolean':
                widget = QCheckBox()
                widget.setStyleSheet("QCheckBox { spacing: 8px; font-size: 11pt; }")
                if config_item.default is not None:
                    widget.setChecked(bool(config_item.default))
                # 对于checkbox，我们需要一个包装布局
                cb_wrapper = QWidget()
                cb_layout = QHBoxLayout(cb_wrapper)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                cb_layout.addWidget(widget)
                cb_layout.addStretch()
                return cb_wrapper
            elif config_item.type == 'list':
                widget = QLineEdit()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if config_item.default:
                    widget.setText(','.join(map(str, config_item.default)))
                if config_item.description:
                    widget.setPlaceholderText(config_item.description)
            elif config_item.type == 'enum':  # ConfigItemType.ENUM 的值是 'enum'
                widget = QComboBox()
                widget.setFixedHeight(30)
                widget.setStyleSheet('''
                    QComboBox { 
                        padding: 4px; 
                        font-size: 11pt; 
                        background-color: white;
                        color: black;
                        border: 1px solid #CCCCCC;
                        border-radius: 4px;
                    }
                    QComboBox QAbstractItemView {
                        background-color: white !important;
                        color: black !important;
                        selection-background-color: #0078d4 !important;
                        selection-color: white !important;
                    }
                ''')
                if hasattr(config_item, 'options_list') and config_item.options_list:
                    widget.addItems([str(opt) for opt in config_item.options_list])
                if config_item.default:
                    index = widget.findText(str(config_item.default))
                    if index >= 0:
                        widget.setCurrentIndex(index)
            else:
                widget = QLineEdit()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if config_item.default:
                    widget.setText(str(config_item.default))
            
            return widget
        except Exception as e:
            print(f"创建配置控件时出错: {e}")
            return None
    
    def load_settings(self):
        """加载设置"""
        try:
            from app.utils.logger import get_logger
            logger = get_logger('barcode_settings_dialog')
            logger.info("开始加载设置")

            # 为每个插件加载配置
            for plugin_name in self.plugin_manager.list_plugins():
                logger.info(f"加载插件 {plugin_name} 的配置")
                config = self.config_manager.get_plugin_config(plugin_name)
                logger.info(f"插件 {plugin_name} 的配置: {config}")
                if not config:
                    config = {}

                # 为每个配置项设置值
                if plugin_name in self.plugin_widgets:
                    logger.info(f"插件 {plugin_name} 在 plugin_widgets 中，包含 {len(self.plugin_widgets[plugin_name])} 个配置项")
                    for key, widget in self.plugin_widgets[plugin_name].items():
                        value = config.get(key)
                        logger.debug(f"插件 {plugin_name} 配置项 {key}: {value} (widget类型: {type(widget).__name__})")
                        if value is not None:
                            self.set_widget_value(widget, value)
                else:
                    logger.warning(f"插件 {plugin_name} 未在 plugin_widgets 中")
        except Exception as e:
            logger.error(f"加载设置时出错: {e}", exc_info=True)
    
    def set_widget_value(self, widget, value):
        """设置控件的值"""
        try:
            from app.utils.logger import get_logger
            logger = get_logger('barcode_settings_dialog')
            logger.debug(f"set_widget_value: widget类型={type(widget).__name__}, value={value}, widget类={widget.__class__.__name__}")

            if isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QLineEdit):
                if isinstance(value, list):
                    # 检查是否是filter_region字段
                    for plugin_widgets in self.plugin_widgets.values():
                        for key, w in plugin_widgets.items():
                            if w is widget and key == 'filter_region':
                                # filter_region用JSON格式显示
                                import json
                                widget.setText(json.dumps(value))
                                break
                        else:
                            continue
                        break
                    else:
                        # 其他列表用逗号分隔
                        widget.setText(','.join(map(str, value)))
                else:
                    widget.setText(str(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QWidget):
                # 检查是否是包装QCheckBox的QWidget
                layout = widget.layout()
                if layout:
                    item = layout.itemAt(0)
                    if item:
                        actual_widget = item.widget()
                        if isinstance(actual_widget, QCheckBox):
                            logger.debug(f"设置包装的QCheckBox: {value}")
                            actual_widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                # 检查是否存在选项映射
                if hasattr(self, 'current_plugin_name') and self.current_plugin_name:
                    options_map_key = f"{self.current_plugin_name}_options_map"
                    if hasattr(self, options_map_key):
                        options_map = getattr(self, options_map_key)
                        # 根据实际值查找显示文本
                        display_text = None
                        for disp, actual in options_map.items():
                            if actual == value:
                                display_text = disp
                                break
                        if display_text:
                            index = widget.findText(display_text)
                            if index >= 0:
                                widget.setCurrentIndex(index)
                        else:
                            index = widget.findText(str(value))
                            if index >= 0:
                                widget.setCurrentIndex(index)
                    else:
                        index = widget.findText(str(value))
                        if index >= 0:
                            widget.setCurrentIndex(index)
                        else:
                            # 如果找不到对应的值，设置为第一个选项
                            if widget.count() > 0:
                                widget.setCurrentIndex(0)
                else:
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
                    else:
                        # 如果找不到对应的值，设置为第一个选项
                        if widget.count() > 0:
                            widget.setCurrentIndex(0)
        except Exception as e:
            print(f"设置控件值时出错: {e}")
    
    def save_settings(self):
        """保存设置"""
        try:
            from app.utils.logger import get_logger
            logger = get_logger('barcode_settings_dialog')
            logger.info("开始保存设置")
            success = True
            error_messages = []

            # 为每个插件保存配置
            for plugin_name in self.plugin_manager.list_plugins():
                logger.info(f"保存插件 {plugin_name} 的配置")
                if plugin_name in self.plugin_widgets:
                    config = {}
                    for key, widget in self.plugin_widgets[plugin_name].items():
                        value = self.get_widget_value(widget)
                        config[key] = value
                        logger.debug(f"插件 {plugin_name} 配置项 {key}: {value}")

                    try:
                        self.config_manager.set_plugin_config(plugin_name, config)
                        logger.info(f"插件 {plugin_name} 配置已设置到管理器")
                    except Exception as e:
                        success = False
                        error_messages.append(f"{plugin_name}: {str(e)}")
                        logger.error(f"保存插件 {plugin_name} 配置失败: {e}", exc_info=True)
                else:
                    logger.warning(f"插件 {plugin_name} 未在 plugin_widgets 中")

            # 保存到文件
            save_result = self.config_manager.save_config()
            logger.info(f"配置保存到文件结果: {save_result}")

            if success:
                QMessageBox.information(self, "成功", "所有设置已保存")
            else:
                QMessageBox.warning(self, "部分保存失败", f"以下插件保存失败:\n" + "\n".join(error_messages))

        except Exception as e:
            logger.error(f"保存设置时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存设置时出错: {str(e)}")
    
    def get_widget_value(self, widget):
        """获取控件的值"""
        try:
            from app.utils.logger import get_logger
            logger = get_logger('barcode_settings_dialog')
            logger.debug(f"get_widget_value: widget类型={type(widget).__name__}, widget类={widget.__class__.__name__}")

            if isinstance(widget, QSpinBox):
                value = widget.value()
                logger.debug(f"get_widget_value: QSpinBox, value={value}")
                return value
            elif isinstance(widget, QDoubleSpinBox):
                value = widget.value()
                logger.debug(f"get_widget_value: QDoubleSpinBox, value={value}")
                return value
            elif isinstance(widget, QLineEdit):
                text = widget.text()
                logger.debug(f"get_widget_value: QLineEdit, text={text}")
                # 检查控件的键名以确定是否为关键词字段或filter_region字段
                # 遍历所有插件的控件映射，找到当前控件对应的键名
                for plugin_name, plugin_widgets in self.plugin_widgets.items():
                    for key, w in plugin_widgets.items():
                        if w is widget:
                            logger.debug(f"找到控件对应的键名: {plugin_name}.{key}")
                            # 关键词字段，分割为列表
                            if 'keyword' in key.lower() or 'keywords' in key.lower():
                                result = [kw.strip() for kw in text.split(',') if kw.strip()]
                                logger.debug(f"关键词字段: {result}")
                                return result
                            # filter_region字段，分割为数字列表
                            elif key == 'filter_region':
                                if not text.strip():
                                    logger.debug("filter_region字段为空，返回[]")
                                    return []
                                try:
                                    import json
                                    result = json.loads(text)
                                    logger.debug(f"filter_region字段(JSON解析): {result}")
                                    return result
                                except json.JSONDecodeError:
                                    # 尝试按逗号分割并转换为数字
                                    parts = [p.strip() for p in text.split(',') if p.strip()]
                                    result = [float(p) for p in parts]
                                    logger.debug(f"filter_region字段(逗号分割): {result}")
                                    return result
                logger.debug(f"L QLineEdit没有找到对应的键名，直接返回文本: {text}")
                return text
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
                logger.debug(f"get_widget_value: QCheckBox, value={value}")
                return value
            elif isinstance(widget, QWidget):
                # 检查是否是包装QCheckBox的QWidget
                layout = widget.layout()
                if layout:
                    item = layout.itemAt(0)
                    if item:
                        actual_widget = item.widget()
                        if isinstance(actual_widget, QCheckBox):
                            value = actual_widget.isChecked()
                            logger.debug(f"get_widget_value: 包装的QCheckBox, value={value}")
                            return value
            elif isinstance(widget, QComboBox):
                try:
                    value = widget.currentText()
                    logger.debug(f"get_widget_value: QComboBox, value={value}")
                    # 检查值是否为空
                    if not value or value.strip() == "":
                        logger.warning(f"QComboBox值为空，返回None")
                        return None
                    # 检查是否存在选项映射
                    if hasattr(self, 'current_plugin_name') and self.current_plugin_name:
                        # 尝试获取插件特定的选项映射
                        plugin_widget_dict = self.plugin_widgets.get(self.current_plugin_name, {})
                        if 'detection_mode_options' in plugin_widget_dict and widget == plugin_widget_dict['detection_mode']:
                            # 这是检测模式下拉框
                            options_map = plugin_widget_dict['detection_mode_options']
                            # 将显示文本转换为实际值
                            mapped_value = options_map.get(value, value)
                            logger.debug(f"QComboBox detection_mode: {value} -> {mapped_value}")
                            return mapped_value
                        elif 'duplicate_handling' in plugin_widget_dict and widget == plugin_widget_dict['duplicate_handling']:
                            # 重复处理模式下拉框
                            options_map = {"分离": "separate", "合并": "merge"}
                            mapped_value = options_map.get(value, value)
                            logger.debug(f"QComboBox duplicate_handling: {value} -> {mapped_value}")
                            return mapped_value
                        elif 'multi_barcode_handling' in plugin_widget_dict and widget == plugin_widget_dict['multi_barcode_handling']:
                            # 多条码处理模式下拉框
                            options_map = {"首个": "first", "复制页面": "duplicate_page"}
                            mapped_value = options_map.get(value, value)
                            logger.debug(f"QComboBox multi_barcode_handling: {value} -> {mapped_value}")
                            return mapped_value
                        else:
                            # 没有特殊映射，返回当前文本
                            logger.debug(f"QComboBox没有特殊映射，直接返回: {value}")
                            return value
                    else:
                        logger.debug(f"QComboBox没有current_plugin_name或值为空，直接返回: {value}")
                        return value
                except Exception as e:
                    logger.error(f"获取QComboBox值时出错: {e}", exc_info=True)
                    # 尝试返回当前文本作为fallback
                    try:
                        value = widget.currentText()
                        return value
                    except:
                        return None
            else:
                logger.debug(f"get_widget_value: 未知控件类型 {type(widget).__name__}")
                return None
        except Exception as e:
            from app.utils.logger import get_logger
            logger = get_logger('barcode_settings_dialog')
            logger.error(f"获取控件值时出错: {e}", exc_info=True)
            return None
    
    def reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(self, "确认重置", 
                                   "确定要将所有设置重置为默认值吗？",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # 重置所有插件配置
                for plugin_name in self.plugin_manager.list_plugins():
                    if plugin_name in self.config_manager.plugin_configs:
                        del self.config_manager.plugin_configs[plugin_name]
                
                # 重新加载默认设置
                self.load_settings()
                
                QMessageBox.information(self, "重置完成", "所有设置已重置为默认值")
            except Exception as e:
                QMessageBox.critical(self, "重置失败", f"重置设置时发生错误: {str(e)}")


def show_barcode_settings_dialog(parent=None):
    """显示条码设置对话框"""
    dialog = BarcodeSettingsDialog(parent)
    return dialog.exec_()