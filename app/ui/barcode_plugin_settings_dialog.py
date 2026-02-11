"""
条码插件设置对话框
提供GUI界面来配置条码插件的各种设置，模仿OCR设置对话框的结构
"""

import json
import fitz  # PyMuPDF
import os
from typing import Dict, Any
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFileDialog,
                            QPushButton, QLineEdit, QProgressDialog, QCheckBox,
                            QSpinBox, QDoubleSpinBox, QGroupBox, QTabWidget,
                            QMessageBox, QLabel, QComboBox, QScrollArea,
                            QSizePolicy, QWidget, QLayout, QGridLayout, QApplication,
                            QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.managers.barcode_plugin_manager import barcode_plugin_manager
from app.config.barcode_plugin_config import barcode_config_manager
from app.utils.logger import get_logger


class BarcodeSettingsDialog(QDialog):
    """条码插件设置对话框"""

    def __init__(self, parent=None, current_file_path=None):
        super().__init__(parent)
        self.setWindowTitle("条码插件设置")
        self.resize(800, 920)  # 增加高度到750
        self.setMinimumHeight(600)  # 设置最小高度
        self.setModal(False)  # 设置为非模态对话框

        # 初始化当前文件路径
        self.current_file_path = current_file_path

        # 初始化配置管理器
        self.plugin_manager = barcode_plugin_manager
        self.config_manager = barcode_config_manager

        # 存储控件引用
        self.plugin_widgets = {}
        # 存储显示名称到插件名称的映射
        self.display_name_to_plugin_name = {}
        
        # 自动加载插件
        try:
            self.plugin_manager.load_all_plugins()
        except Exception as e:
            print(f"加载条码插件时出错: {e}")
        
        self.setup_ui()
        self.create_plugin_settings_tabs()
        self.load_settings()

        # 设置标签页样式，与OCR引擎设置保持一致
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #CCCCCC; 
                border-top: none;  /* 移去顶部边框避免重叠 */
                border-radius: 4px; 
                top: -1px; 
                background: transparent;
            }
            QTabBar::tab { 
                background: #F0F0F0;
                border: 1px solid #CCCCCC;
                border-bottom: none;  /* 移去底部边框避免重叠 */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 8ex;
                padding: 6px 12px;
                margin: 0px;
                alignment: left;
            }
            QTabBar::tab:selected { 
                background: #FFFFFF;
                border-color: #9B9B9B;
                border-bottom-color: #FFFFFF;
                font-weight: bold;
            }
            QTabBar::tab:!selected { 
                margin-top: 2px; /* 未选中的标签稍微下沉 */
            }
            /* 确保标签栏靠左对齐 */
            QTabBar { 
                alignment: left;
                qproperty-drawBase: 0;
            }
            /* 强制标签栏内容左对齐 */
            QTabWidget QTabBar::tab-bar {
                alignment: left;
                left: 0px;
            }
            /* 确保标签页容器左对齐 */
            QTabWidget::tab-bar {
                alignment: left;
                left: 0;
            }
            /* 强制标签栏左对齐 */
            QTabBar::tab-bar {
                alignment: left;
                left: 0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                margin-top: 1ex;
                padding-top: 8px;
                background: transparent;
            }
        """)
    
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
        # 强制设置标签栏左对齐
        self.tab_widget.tabBar().setStyleSheet("alignment: left;")
        # 设置标签栏扩展策略以确保左对齐
        self.tab_widget.tabBar().setExpanding(False)
        
        # 添加插件设置标签页
        layout.addWidget(self.tab_widget)
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout()

        file_path_layout = QHBoxLayout()
        file_path_label = QLabel("PDF文件:")
        file_path_label.setStyleSheet("QLabel { font-weight: bold; }")
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择要处理的PDF文件")
        self.file_path_edit.setFixedHeight(30)
        self.file_path_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.file_path_edit.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")

        # 如果有传入的当前文件路径，自动填充
        if self.current_file_path and os.path.exists(self.current_file_path):
            self.file_path_edit.setText(self.current_file_path)

        self.browse_file_btn = QPushButton("📂 浏览")
        self.browse_file_btn.setFixedHeight(30)
        self.browse_file_btn.clicked.connect(self.browse_file)

        file_path_layout.addWidget(file_path_label)
        file_path_layout.addWidget(self.file_path_edit)
        file_path_layout.addWidget(self.browse_file_btn)

        file_layout.addLayout(file_path_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

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

    def browse_file(self):
        """浏览选择文件"""
        # 获取初始目录
        initial_dir = ""
        current_text = self.file_path_edit.text().strip()
        if current_text and os.path.exists(os.path.dirname(current_text)):
            initial_dir = os.path.dirname(current_text)

        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PDF文件", initial_dir, "PDF文件 (*.pdf)"
        )

        if file_path:
            self.file_path_edit.setText(file_path)

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
                    error_msg = "\n".join([f"{key}: {msg}" for key, msg in errors.items()])
                    QMessageBox.warning(self, "配置验证失败", 
                                      f"插件 {plugin_name} 配置验证失败:\n{error_msg}")
                    return
            
            # 保存配置到文件
            self.config_manager.save_config()
            
            # 调用父类方法关闭对话框
            super().accept()
            
        except Exception as e:
            logger = get_logger('barcode_settings_dialog')
            logger.error(f"保存配置时出错: {e}")
            QMessageBox.critical(self, "保存失败", f"保存配置时发生错误: {str(e)}")
    
    def test_detection(self):
        """测试检测功能"""
        try:
            # 获取文件路径
            file_path = self.file_path_edit.text().strip()
            if not file_path:
                QMessageBox.warning(self, "警告", "请先选择文件")
                return

            if not os.path.exists(file_path):
                QMessageBox.warning(self, "警告", f"文件不存在: {file_path}")
                return

            # 获取当前选中的插件
            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index < 0:
                QMessageBox.warning(self, "警告", "没有选中的插件")
                return

            display_name = self.tab_widget.tabText(current_tab_index)
            # 通过显示名称获取实际的插件名称
            plugin_name = self.display_name_to_plugin_name.get(display_name, display_name)
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

            # 创建进度对话框
            progress_dialog = QProgressDialog("正在检测条码...", "取消", 0, 100, self)
            progress_dialog.setWindowTitle("检测进度")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)

            # 显示进度对话框并处理事件
            progress_dialog.show()
            QApplication.processEvents()

            # 根据文件类型调用相应的检测方法
            if file_path.lower().endswith('.pdf'):
                # 对于PDF文件，打开文档并获取页数
                doc = fitz.open(file_path)
                total_pages = len(doc)

                # 定义进度回调函数
                def progress_callback(current, total, message=""):
                    if progress_dialog.wasCanceled():
                        return False
                    progress_percent = int((current / total) * 100) if total > 0 else 0
                    progress_dialog.setValue(progress_percent)
                    if message:
                        progress_dialog.setLabelText(message)
                    else:
                        progress_dialog.setLabelText(f"正在检测: {current}/{total}")
                    QApplication.processEvents()
                    return True

                # 使用进度回调进行检测
                try:
                    progress_dialog.setLabelText(f"正在检测 PDF 文档 (共 {total_pages} 页)...")
                    progress_dialog.setValue(0)
                    QApplication.processEvents()

                    # 传递进度回调
                    result = plugin.detect_from_pdf(doc, config, progress_callback)

                    # 更新进度到100%
                    if not progress_dialog.wasCanceled():
                        progress_dialog.setValue(100)
                        QApplication.processEvents()

                finally:
                    doc.close()
            else:
                # 对于图片文件，直接检测
                progress_dialog.setLabelText("正在检测图片文件...")
                progress_dialog.setValue(50)
                QApplication.processEvents()
                result = plugin.detect_from_file(file_path)
                progress_dialog.setValue(100)
                QApplication.processEvents()

            # 关闭进度对话框
            progress_dialog.close()

            if result.is_success():
                # 格式化检测结果
                barcode_data = result.data
                if isinstance(barcode_data, list) and barcode_data:
                    result_text = f"检测成功！\n\n{result.message}\n\n检测到的条码数据:\n\n"
                    for i, barcode in enumerate(barcode_data, 1):
                        result_text += f"{i}. 条码类型: {barcode.get('type', 'Unknown')}\n"
                        result_text += f"   条码数据: {barcode.get('data', 'N/A')}\n"
                        result_text += f"   页码: {barcode.get('page_num', 'N/A') + 1}\n"
                        bbox = barcode.get('bbox', [])
                        if bbox:
                            result_text += f"   位置: ({bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f})\n"
                        result_text += "\n"
                elif isinstance(barcode_data, list) and not barcode_data:
                    result_text = f"{result.message}\n\n未检测到任何条码"
                else:
                    result_text = f"检测成功！\n\n{result.message}\n\n检测到的条码数据:\n{str(barcode_data)}"

                # 直接弹出文本对话框
                dialog = QDialog(self)
                dialog.setWindowTitle("测试检测结果")
                dialog.setMinimumWidth(600)
                dialog.setMinimumHeight(400)

                layout = QVBoxLayout()

                # 创建文本编辑框
                text_edit = QTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setPlainText(result_text)
                layout.addWidget(text_edit)

                # 添加关闭按钮
                btn_box = QHBoxLayout()
                btn_box.addStretch()
                close_btn = QPushButton("关闭")
                close_btn.clicked.connect(dialog.accept)
                btn_box.addWidget(close_btn)
                layout.addLayout(btn_box)

                dialog.setLayout(layout)
                dialog.exec_()
            else:
                QMessageBox.warning(self, "测试检测结果", f"检测失败:\n{result.message}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"测试检测时出错: {str(e)}")
    
    def start_split(self):
        """开始拆分功能"""
        try:
            logger = get_logger('barcode_settings_dialog')

            # 获取文件路径
            file_path = self.file_path_edit.text().strip()
            if not file_path:
                QMessageBox.warning(self, "警告", "请先选择PDF文件")
                return

            if not os.path.exists(file_path):
                QMessageBox.warning(self, "警告", f"文件不存在: {file_path}")
                return

            if not file_path.lower().endswith('.pdf'):
                QMessageBox.warning(self, "警告", "请选择PDF文件")
                return

            # 获取当前选中的插件
            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index < 0:
                QMessageBox.warning(self, "警告", "没有选中的插件")
                return

            display_name = self.tab_widget.tabText(current_tab_index)
            # 通过显示名称获取实际的插件名称
            plugin_name = self.display_name_to_plugin_name.get(display_name, display_name)

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

            # 如果没有配置输出目录，则使用PDF文件所在目录+文件名同名目录
            output_dir = config.get('output_dir', '')
            if not output_dir:
                file_dir = os.path.dirname(file_path)  # PDF文件所在目录
                file_basename = os.path.splitext(os.path.basename(file_path))[0]  # PDF文件名（不含扩展名）
                output_dir = os.path.join(file_dir, file_basename)  # 输出目录：目录/文件名/
                config['output_dir'] = output_dir

            
            # 调用插件的拆分功能
            doc = fitz.open(file_path)
            
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

        logger = get_logger('barcode_settings_dialog')
        return config
    
    def _on_all_types_toggled(self, checked, barcode_type_checkboxes):
        """当"所有类型"复选框状态改变时"""
        # 阻止信号递归
        sender = self.sender()
        if sender:
            sender.blockSignals(True)

        if checked:
            # 选中"所有类型"时，选中所有具体类型
            for barcode_type, checkbox in barcode_type_checkboxes.items():
                if barcode_type != "ALL_TYPES":
                    checkbox.setChecked(True)
        else:
            # 取消选中"所有类型"时，取消所有具体类型的选中
            for barcode_type, checkbox in barcode_type_checkboxes.items():
                if barcode_type != "ALL_TYPES":
                    checkbox.setChecked(False)

        # 恢复信号
        if sender:
            sender.blockSignals(False)

    def _on_specific_type_toggled(self):
        """当具体类型复选框状态改变时"""
        # 获取当前插件的复选框
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0:
            return

        display_name = self.tab_widget.tabText(current_tab_index)
        # 通过显示名称获取实际的插件名称
        plugin_name = self.display_name_to_plugin_name.get(display_name, display_name)
        if plugin_name in self.plugin_widgets:
            plugin_widgets = self.plugin_widgets[plugin_name]
            if 'barcode_type_checkboxes' in plugin_widgets:
                barcode_type_checkboxes = plugin_widgets['barcode_type_checkboxes']

                # 检查所有具体类型是否都被选中
                all_selected = all(
                    checkbox.isChecked()
                    for barcode_type, checkbox in barcode_type_checkboxes.items()
                    if barcode_type != "ALL_TYPES"
                )

                # 检查是否没有任何具体类型被选中
                none_selected = not any(
                    checkbox.isChecked()
                    for barcode_type, checkbox in barcode_type_checkboxes.items()
                    if barcode_type != "ALL_TYPES"
                )

                all_types_checkbox = barcode_type_checkboxes.get("ALL_TYPES")
                if all_types_checkbox:
                    # 如果所有具体类型都被选中，则选中"所有类型"
                    if all_selected:
                        all_types_checkbox.blockSignals(True)
                        all_types_checkbox.setChecked(True)
                        all_types_checkbox.blockSignals(False)
                    # 如果没有任何具体类型被选中，则取消选中"所有类型"
                    elif none_selected:
                        all_types_checkbox.blockSignals(True)
                        all_types_checkbox.setChecked(False)
                        all_types_checkbox.blockSignals(False)
                    # 否则，部分选中，取消选中"所有类型"
                    else:
                        all_types_checkbox.blockSignals(True)
                        all_types_checkbox.setChecked(False)
                        all_types_checkbox.blockSignals(False)
    
    def _select_output_directory(self, line_edit):
        """选择输出目录"""
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

        # 获取插件显示名称（从PluginInfo的title字段）
        plugin_info = getattr(plugin, 'PluginInfo', {})
        display_name = plugin_info.get('title', plugin_name)

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
        
        # 添加标签页，使用插件的显示名称
        self.tab_widget.addTab(plugin_widget, display_name)
        # 建立显示名称到插件名称的映射
        self.display_name_to_plugin_name[display_name] = plugin_name
    
    def create_config_controls(self, plugin_name, parent_widget, config_definitions):
        """根据配置定义创建控件"""
        plugin_layout = parent_widget.layout()

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

                # 检查默认值是否包含"ALL_TYPES"
                is_all_types_default = "ALL_TYPES" in (config_item.default or [])

                # 首先添加"所有类型"选项
                all_types_checkbox = QCheckBox("🔍 所有类型")
                all_types_checkbox.setChecked(is_all_types_default)
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
                    # 如果是"所有类型"模式，选中所有具体类型；否则根据默认值设置
                    if is_all_types_default:
                        checkbox.setChecked(True)
                    else:
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
                output_dir_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
                widget, options_map = self.create_config_widget(plugin_name, config_item)
                if widget:
                    h_layout = QHBoxLayout()
                    label = QLabel(config_item.title + ":")
                    label.setStyleSheet("QLabel { font-weight: bold; }")
                    label.setToolTip(config_item.description)
                    widget.setToolTip(config_item.description)

                    h_layout.addWidget(label)
                    h_layout.addWidget(widget)
                    # 移除addStretch，让输入框能够铺满
                    # h_layout.addStretch()

                    scroll_layout.addLayout(h_layout)

                    # 存储控件引用
                    self.plugin_widgets[plugin_name][config_item.key] = widget
                    # 如果有选项映射，保存为实例属性
                    if options_map:
                        options_map_key = f"{plugin_name}_{config_item.key}_options"
                        setattr(self, options_map_key, options_map)

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
        """根据配置定义创建相应的控件，返回 (widget, options_map) 元组

        Args:
            plugin_name: 插件名称
            config_item: 配置项定义

        Returns:
            tuple: (widget, options_map)，options_map 为显示文本到实际值的映射，如果没有则为 None
        """
        try:
            options_map = None

            if config_item.type == 'string':
                widget = QLineEdit()
                widget.setFixedHeight(30)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if config_item.default:
                    widget.setText(str(config_item.default))
                if config_item.description:
                    widget.setPlaceholderText(config_item.description)
            elif config_item.type == 'integer':
                widget = QSpinBox()
                widget.setFixedHeight(30)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                widget.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
                min_val = config_item.min_value if config_item.min_value is not None else 0
                max_val = config_item.max_value if config_item.max_value is not None else 999999
                widget.setRange(min_val, max_val)
                if config_item.default is not None:
                    widget.setValue(int(config_item.default))
            elif config_item.type == 'float':
                widget = QDoubleSpinBox()
                widget.setFixedHeight(30)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
                return (cb_wrapper, None)
            elif config_item.type == 'list':
                widget = QLineEdit()
                widget.setFixedHeight(30)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if config_item.default:
                    widget.setText(','.join(map(str, config_item.default)))
                if config_item.description:
                    widget.setPlaceholderText(config_item.description)
            elif config_item.type == 'enum':  # ConfigItemType.ENUM 的值是 'enum'
                widget = QComboBox()
                widget.setFixedHeight(30)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
                    # 为 enum 类型创建中文显示文本映射
                    display_texts = []
                    options_map = {}

                    for opt in config_item.options_list:
                        # 为常见的选项创建中文映射
                        if opt == "merge":
                            display_text = "合并"
                        elif opt == "separate":
                            display_text = "创建单独文件"
                        elif opt == "first":
                            display_text = "首个"
                        elif opt == "first_page":
                            display_text = "首页"
                        elif opt == "last_page":
                            display_text = "尾页"
                        elif opt == "duplicate_page":
                            display_text = "复制页面"
                        elif opt == "separator_page":
                            display_text = "分隔页"
                        else:
                            # 其他情况直接使用原值
                            display_text = str(opt)

                        display_texts.append(display_text)
                        options_map[display_text] = opt

                    # 添加显示文本到下拉框
                    widget.addItems(display_texts)

                    # 设置默认值
                    if config_item.default:
                        # 找到默认值对应的显示文本
                        default_display = None
                        for display, actual in options_map.items():
                            if actual == config_item.default:
                                default_display = display
                                break
                        if default_display:
                            index = widget.findText(default_display)
                            if index >= 0:
                                widget.setCurrentIndex(index)
            else:
                widget = QLineEdit()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if config_item.default:
                    widget.setText(str(config_item.default))

            return (widget, options_map)
        except Exception as e:
            print(f"创建配置控件时出错: {e}")
            return (None, None)
    
    def load_settings(self):
        """加载设置"""
        try:
            logger = get_logger('barcode_settings_dialog')
            # 为每个插件加载配置（使用带默认值的加载方法）
            for plugin_name in self.plugin_manager.list_plugins():
                config = self.config_manager.get_plugin_config_with_defaults(plugin_name)

                # 为每个配置项设置值
                if plugin_name in self.plugin_widgets:
                    # 特殊处理条码类型复选框
                    if 'barcode_type_checkboxes' in self.plugin_widgets[plugin_name] and 'enabled_types' in config:
                        self._load_barcode_type_checkboxes(plugin_name, config['enabled_types'])

                    # 处理其他配置项
                    for key, widget in self.plugin_widgets[plugin_name].items():
                        if key == 'barcode_type_checkboxes':
                            continue  # 跳过已处理的条码类型复选框
                        value = config.get(key)
                        logger.debug(f"插件 {plugin_name} 配置项 {key}: {value} (widget类型: {type(widget).__name__})")
                        if value is not None:
                            self.set_widget_value(widget, value)
                else:
                    logger.warning(f"插件 {plugin_name} 未在 plugin_widgets 中")
        except Exception as e:
            logger.error(f"加载设置时出错: {e}", exc_info=True)

    def _load_barcode_type_checkboxes(self, plugin_name, enabled_types):
        """加载条码类型复选框的状态"""
        try:
            logger = get_logger('barcode_settings_dialog')

            if plugin_name not in self.plugin_widgets:
                return

            barcode_type_checkboxes = self.plugin_widgets[plugin_name].get('barcode_type_checkboxes')
            if not barcode_type_checkboxes:
                return

            # 阻止所有信号
            for checkbox in barcode_type_checkboxes.values():
                checkbox.blockSignals(True)

            all_types_checkbox = barcode_type_checkboxes.get("ALL_TYPES")
            if all_types_checkbox:
                # 检查是否是"所有类型"模式
                is_all_types = "ALL_TYPES" in (enabled_types or [])
                all_types_checkbox.setChecked(is_all_types)

                # 设置具体类型复选框的状态
                for barcode_type, checkbox in barcode_type_checkboxes.items():
                    if barcode_type == "ALL_TYPES":
                        continue
                    if is_all_types:
                        # "所有类型"模式，选中所有具体类型
                        checkbox.setChecked(True)
                    else:
                        # 具体类型模式，根据配置设置
                        checkbox.setChecked(barcode_type in (enabled_types or []))

            # 恢复所有信号
            for checkbox in barcode_type_checkboxes.values():
                checkbox.blockSignals(False)

            logger.debug(f"加载条码类型复选框状态: {enabled_types}")
        except Exception as e:
            logger.error(f"加载条码类型复选框时出错: {e}", exc_info=True)
    
    def set_widget_value(self, widget, value):
        """设置控件的值"""
        try:
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
            elif isinstance(widget, QComboBox):
                # 查找对应的选项映射
                options_map = None
                for plugin_name, plugin_widgets in self.plugin_widgets.items():
                    for key, w in plugin_widgets.items():
                        if w is widget:
                            # 找到配置键名，构建选项映射键名
                            options_map_key = f"{plugin_name}_{key}_options"
                            if hasattr(self, options_map_key):
                                options_map = getattr(self, options_map_key)
                            break
                    if options_map is not None:
                        break

                if options_map:
                    # 使用选项映射查找显示文本
                    display_text = None
                    for disp, actual in options_map.items():
                        if actual == value:
                            display_text = disp
                            break
                    if display_text:
                        index = widget.findText(display_text)
                        if index >= 0:
                            widget.setCurrentIndex(index)
                            return
                # fallback: 直接使用值查找
                index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)
                else:
                    # 如果找不到对应的值,设置为第一个选项
                    if widget.count() > 0:
                        widget.setCurrentIndex(0)
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
        except Exception as e:
            print(f"设置控件值时出错: {e}")
    
    def save_settings(self):
        """保存设置"""
        try:
            logger = get_logger('barcode_settings_dialog')
            success = True
            error_messages = []

            # 为每个插件保存配置
            for plugin_name in self.plugin_manager.list_plugins():
                if plugin_name in self.plugin_widgets:
                    config = {}
                    for key, widget in self.plugin_widgets[plugin_name].items():
                        # 跳过选项映射和内部键
                        if key.endswith('_options') or key == 'barcode_type_checkboxes':
                            continue
                        value = self.get_widget_value(widget)
                        config[key] = value
                        # 特别输出枚举类型的值
                        if 'handling' in key or 'rule' in key:
                            print(f"[DEBUG] 保存配置: {plugin_name}.{key} = '{value}' (类型: {type(value).__name__})")

                    # 处理条码类型复选框组
                    if 'barcode_type_checkboxes' in self.plugin_widgets[plugin_name]:
                        barcode_type_checkboxes = self.plugin_widgets[plugin_name]['barcode_type_checkboxes']
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

                    # 打印完整配置以供调试
                    print(f"[DEBUG] 准备保存 {plugin_name} 的完整配置: {config}")

                    try:
                        self.config_manager.set_plugin_config(plugin_name, config)
                    except Exception as e:
                        success = False
                        error_messages.append(f"{plugin_name}: {str(e)}")
                        logger.error(f"保存插件 {plugin_name} 配置失败: {e}", exc_info=True)
                else:
                    logger.warning(f"插件 {plugin_name} 未在 plugin_widgets 中")

            # 保存到文件
            save_result = self.config_manager.save_config()

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
            logger = get_logger('barcode_settings_dialog')
            print(f"[DEBUG] get_widget_value: widget类型={type(widget).__name__}, widget类={widget.__class__.__name__}")

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
            elif isinstance(widget, QComboBox):
                try:
                    print(f"[DEBUG] 进入 QComboBox 分支, count={widget.count()}, currentIndex={widget.currentIndex()}")
                    value = widget.currentText()
                    print(f"[DEBUG] QComboBox.currentText() 返回: {value!r} (type: {type(value).__name__})")
                    # 检查值是否为空
                    if value is None or (isinstance(value, str) and not value.strip()):
                        print(f"[DEBUG] QComboBox值为空或None, value={value!r}, 返回None")
                        logger.warning(f"QComboBox值为空或None, value={value!r}, 返回None")
                        return None

                    # 查找对应的选项映射 - 策略1: 从实例属性中查找
                    options_map = None
                    found_plugin_name = None
                    found_key = None
                    for plugin_name, plugin_widgets in self.plugin_widgets.items():
                        for key, w in plugin_widgets.items():
                            if w is widget:
                                found_plugin_name = plugin_name
                                found_key = key
                                # 找到配置键名，构建选项映射键名
                                options_map_key = f"{plugin_name}_{key}_options"
                                if hasattr(self, options_map_key):
                                    options_map = getattr(self, options_map_key)
                                    # 直接转换并返回
                                    mapped_value = options_map.get(value, value)
                                    print(f"[DEBUG] QComboBox[{found_plugin_name}.{found_key}] 值转换: '{value}' -> '{mapped_value}'")
                                    return mapped_value

                    # 策略2: 从 plugin_widgets 中查找
                    for plugin_name, plugin_widgets in self.plugin_widgets.items():
                        for key, w in plugin_widgets.items():
                            if w is widget:
                                # 检查是否有 xxx_options 键
                                options_map_key = f"{key}_options"
                                if options_map_key in self.plugin_widgets[plugin_name]:
                                    options_map = self.plugin_widgets[plugin_name][options_map_key]
                                    logger.debug(f"从 plugin_widgets 找到选项映射: {options_map}")
                                    mapped_value = options_map.get(value, value)
                                    logger.debug(f"QComboBox使用 plugin_widgets 选项映射: {value} -> {mapped_value}")
                                    return mapped_value

                    # 最后的 fallback: 直接返回当前文本
                    logger.warning(f"QComboBox没有找到选项映射，直接返回: {value}")
                    return value
                except Exception as e:
                    logger.error(f"获取QComboBox值时出错: {e}", exc_info=True)
                    # 尝试返回当前文本作为fallback
                    try:
                        value = widget.currentText()
                        return value
                    except:
                        return None
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
            else:
                logger.debug(f"get_widget_value: 未知控件类型 {type(widget).__name__}")
                return None
        except Exception as e:
            logger = get_logger('barcode_settings_dialog')
            logger.error(f"获取控件值时出错: {e}", exc_info=True)
            return None
    
    def reset_settings(self):
        """重置设置"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认重置")
        msg_box.setText("确定要将所有设置重置为默认值吗？")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮文本为中文
        msg_box.setButtonText(QMessageBox.Yes, "是")
        msg_box.setButtonText(QMessageBox.No, "否")
        reply = msg_box.exec_()
        
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


def show_barcode_settings_dialog(parent=None, current_file_path=None):
    """显示条码设置对话框"""
    dialog = BarcodeSettingsDialog(parent, current_file_path)
    return dialog.exec_()