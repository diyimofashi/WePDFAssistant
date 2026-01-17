"""
条码插件管理器对话框
提供GUI界面来管理条码插件
"""

from typing import Dict
import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QPushButton,  QLabel, QGroupBox, 
                            QTextEdit,  QFileDialog, QMessageBox,
                            QListWidget, QListWidgetItem, QFormLayout)
from PyQt5.QtCore import Qt
from app.managers.barcode_plugin_manager import barcode_plugin_manager
from app.config.barcode_plugin_config import barcode_config_manager
from app.core.barcode.barcode_integration import barcode_integration


class BarcodePluginManagerDialog(QDialog):
    """条码插件管理器对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("条码插件管理器")
        self.resize(800, 600)
        
        # 初始化组件
        self.plugin_manager = barcode_plugin_manager
        self.config_manager = barcode_config_manager
        self.integration = barcode_integration
        
        self.setup_ui()
        self.refresh_plugin_list()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        
        # 顶部按钮区域
        top_layout = QHBoxLayout()
        
        self.load_all_btn = QPushButton("加载所有插件")
        self.load_all_btn.clicked.connect(self.load_all_plugins)
        top_layout.addWidget(self.load_all_btn)
        
        self.refresh_btn = QPushButton("刷新插件列表")
        self.refresh_btn.clicked.connect(self.refresh_plugin_list)
        top_layout.addWidget(self.refresh_btn)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 主要内容区域
        main_splitter = QHBoxLayout()
        
        # 左侧：插件列表
        left_group = QGroupBox("可用插件")
        left_layout = QVBoxLayout(left_group)
        
        self.plugin_list = QListWidget()
        self.plugin_list.itemClicked.connect(self.on_plugin_selected)
        left_layout.addWidget(self.plugin_list)
        
        # 插件操作按钮
        plugin_btn_layout = QHBoxLayout()
        
        self.init_plugin_btn = QPushButton("初始化")
        self.init_plugin_btn.clicked.connect(self.init_selected_plugin)
        plugin_btn_layout.addWidget(self.init_plugin_btn)
        
        self.test_plugin_btn = QPushButton("测试检测")
        self.test_plugin_btn.clicked.connect(self.test_selected_plugin)
        plugin_btn_layout.addWidget(self.test_plugin_btn)
        
        left_layout.addLayout(plugin_btn_layout)
        main_splitter.addWidget(left_group)
        
        # 右侧：插件信息和配置
        right_splitter = QVBoxLayout()
        
        # 插件信息
        info_group = QGroupBox("插件信息")
        info_layout = QFormLayout(info_group)
        
        self.plugin_name_label = QLabel("-")
        self.plugin_version_label = QLabel("-")
        self.plugin_author_label = QLabel("-")
        self.plugin_status_label = QLabel("-")
        
        info_layout.addRow("插件名称:", self.plugin_name_label)
        info_layout.addRow("版本:", self.plugin_version_label)
        info_layout.addRow("作者:", self.plugin_author_label)
        info_layout.addRow("状态:", self.plugin_status_label)
        
        right_splitter.addWidget(info_group)
        
        # 插件配置
        config_group = QGroupBox("插件配置")
        config_layout = QVBoxLayout(config_group)
        
        self.config_text = QTextEdit()
        self.config_text.setMaximumHeight(100)
        config_layout.addWidget(self.config_text)
        
        config_btn_layout = QHBoxLayout()
        
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.clicked.connect(self.save_plugin_config)
        config_btn_layout.addWidget(self.save_config_btn)
        
        config_layout.addLayout(config_btn_layout)
        right_splitter.addWidget(config_group)
        
        # 支持的条码类型
        types_group = QGroupBox("支持的条码类型")
        types_layout = QVBoxLayout(types_group)
        
        self.types_list = QListWidget()
        types_layout.addWidget(self.types_list)
        right_splitter.addWidget(types_group)
        
        # 日志输出
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(150)
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        
        right_splitter.addWidget(log_group)
        
        main_splitter.addLayout(right_splitter)
        layout.addLayout(main_splitter)
        
        # 底部操作区域
        bottom_layout = QHBoxLayout()
        
        self.select_current_btn = QPushButton("设为当前插件")
        self.select_current_btn.clicked.connect(self.set_current_plugin)
        bottom_layout.addWidget(self.select_current_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
    
    def refresh_plugin_list(self):
        """刷新插件列表"""
        self.plugin_list.clear()
        
        # 获取已加载的插件
        plugin_names = self.plugin_manager.list_plugins()
        
        for plugin_name in plugin_names:
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if plugin:
                item = QListWidgetItem(f"{plugin_name} ({plugin.plugin_version})")
                item.setData(Qt.UserRole, plugin_name)
                self.plugin_list.addItem(item)
        
        self.log_message(f"已加载 {len(plugin_names)} 个插件")
    
    def on_plugin_selected(self, item):
        """插件选择事件"""
        plugin_name = item.data(Qt.UserRole)
        
        # 获取插件信息
        plugin_info = self.plugin_manager.get_plugin_info(plugin_name)
        
        # 显示插件信息
        self.plugin_name_label.setText(plugin_info.get('name', '-'))
        self.plugin_version_label.setText(plugin_info.get('version', '-'))
        self.plugin_author_label.setText(plugin_info.get('author', '-'))
        self.plugin_status_label.setText("已初始化" if plugin_info.get('initialized', False) else "未初始化")
        
        # 显示插件配置
        config = self.config_manager.get_plugin_config(plugin_name)
        self.config_text.setPlainText(str(config))
        
        # 显示支持的条码类型
        self.types_list.clear()
        try:
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if plugin:
                supported_types = plugin.get_supported_types()
                for barcode_type in supported_types:
                    self.types_list.addItem(barcode_type)
        except Exception as e:
            self.log_message(f"获取插件支持的条码类型失败: {str(e)}")
    
    def load_all_plugins(self):
        """加载所有插件"""
        try:
            results = self.plugin_manager.load_all_plugins()
            loaded_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            self.log_message(f"插件加载完成: {loaded_count}/{total_count} 个插件加载成功")
            self.refresh_plugin_list()
            
        except Exception as e:
            self.log_message(f"加载插件失败: {str(e)}")
    
    def init_selected_plugin(self):
        """初始化选中的插件"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个插件")
            return
        
        plugin_name = current_item.data(Qt.UserRole)
        
        try:
            # 获取当前配置
            config = self.config_manager.get_plugin_config(plugin_name)
            
            # 初始化插件
            result = self.plugin_manager.initialize_plugin(plugin_name, config)
            
            if result.is_success():
                self.log_message(f"插件 '{plugin_name}' 初始化成功")
                self.on_plugin_selected(current_item)  # 刷新信息显示
            else:
                self.log_message(f"插件 '{plugin_name}' 初始化失败: {result.message}")
                
        except Exception as e:
            self.log_message(f"初始化插件失败: {str(e)}")
    
    def test_selected_plugin(self):
        """测试选中的插件"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个插件")
            return
        
        plugin_name = current_item.data(Qt.UserRole)
        
        # 选择测试图片文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择测试图片", 
            "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.gif);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        try:
            # 使用插件检测条码
            result = self.plugin_manager.detect_with_plugin(plugin_name, file_path=file_path)
            
            if result.is_success():
                self.log_message(f"插件 '{plugin_name}' 检测成功，找到 {len(result.data)} 个条码")
                for i, barcode in enumerate(result.data):
                    self.log_message(f"  条码 {i+1}: {barcode['data']} ({barcode['type']})")
            else:
                self.log_message(f"插件 '{plugin_name}' 检测失败: {result.message}")
                
        except Exception as e:
            self.log_message(f"测试插件失败: {str(e)}")
    
    def save_plugin_config(self):
        """保存插件配置"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个插件")
            return
        
        plugin_name = current_item.data(Qt.UserRole)
        
        try:
            # 解析配置文本
            config_text = self.config_text.toPlainText()
            # 这里应该解析配置文本，简单起见我们直接保存文本
            config = eval(config_text) if config_text.strip() else {}
            
            # 保存配置
            self.config_manager.set_plugin_config(plugin_name, config)
            self.log_message(f"插件 '{plugin_name}' 配置已保存")
            
        except Exception as e:
            self.log_message(f"保存配置失败: {str(e)}")
    
    def set_current_plugin(self):
        """设置当前插件"""
        current_item = self.plugin_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个插件")
            return
        
        plugin_name = current_item.data(Qt.UserRole)
        
        try:
            self.config_manager.set_current_plugin(plugin_name)
            self.log_message(f"当前插件已设置为: {plugin_name}")
            
        except Exception as e:
            self.log_message(f"设置当前插件失败: {str(e)}")
    
    def log_message(self, message: str):
        """记录日志消息"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")