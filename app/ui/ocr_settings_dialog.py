"""
OCR设置对话框
用于配置所有OCR引擎插件的全局和局部选项
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QWidget, QFormLayout, QLineEdit, QCheckBox, 
                             QSpinBox, QDoubleSpinBox, QComboBox, QPushButton,
                             QLabel, QGroupBox, QScrollArea,
                             QMessageBox, QLayout, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.managers.ocr_plugin_manager import ocr_plugin_manager
from app.config.ocr_plugin_config import ocr_config_manager
from app.utils.logger import get_logger

logger = get_logger('ocr_settings_dialog')


class OCRSettingsDialog(QDialog):
    """OCR设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OCR引擎设置")
        self.resize(800, 600)  # 增加初始尺寸
        self.setMinimumSize(700, 500)  # 增加最小尺寸
        self.setMaximumSize(1200, 900)  # 增加最大尺寸
        self.setModal(True)
        
        # 设置窗口标志，确保对话框居中显示
        self.setWindowFlags(self.windowFlags() | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # 初始化配置管理器
        self.plugin_manager = ocr_plugin_manager
        self.config_manager = ocr_config_manager
        
        # 存储控件引用
        self.plugin_widgets = {}
        
        # 自动加载插件
        self.plugin_manager.load_all_plugins()
        
        self.setup_ui()
        self.load_settings()
    
    def populate_plugin_combo(self):
        """填充插件选择组合框"""
        # 清空现有项目
        self.current_plugin_combo.clear()
        
        # 获取所有已加载的插件
        plugins = self.plugin_manager.list_plugins()
        
        # 添加插件到组合框
        for plugin_name in plugins:
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if plugin:
                # 获取插件标题
                plugin_info = getattr(plugin, 'PluginInfo', {})
                local_options = plugin_info.get('local_options', {})
                plugin_title = local_options.get('title', plugin_name)
                # 添加带有标题的插件项
                self.current_plugin_combo.addItem(f"{plugin_title} ({plugin_name})", plugin_name)
        
        # 设置当前选中的插件
        current_plugin = self.config_manager.get_current_plugin()
        if current_plugin:
            index = self.current_plugin_combo.findData(current_plugin)
            if index >= 0:
                self.current_plugin_combo.setCurrentIndex(index)
    
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
        
        # 确保对话框在屏幕中央显示
        if not self.testAttribute(Qt.WA_Moved):
            self.center_on_screen()
    
    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # 适当增加组件间距
        layout.setContentsMargins(15, 15, 15, 15)  # 适当增加边距
        # 允许布局根据内容调整大小
        layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # 创建当前插件选择组合框
        current_plugin_layout = QHBoxLayout()
        current_plugin_label = QLabel("当前使用的OCR插件:")
        current_plugin_label.setStyleSheet("QLabel { font-weight: bold; }")
        self.current_plugin_combo = QComboBox()
        self.current_plugin_combo.setFixedHeight(30)
        self.current_plugin_combo.setStyleSheet("""
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
                selection-background-color: #2196F3;
                selection-color: white;
                border: 1px solid #CCCCCC;
                outline: 0px;
                min-width: 200px;
            }
            QComboBox QAbstractItemView::item {
                background-color: white;
                color: black;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #E3F2FD;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #CCCCCC;
                border-left-style: solid;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)
        # 设置全局样式以确保下拉列表正确显示
        self.current_plugin_combo.view().setStyleSheet("""
            background-color: white;
            color: black;
            selection-background-color: #2196F3;
            selection-color: white;
        """)
        self.populate_plugin_combo()
        current_plugin_layout.addWidget(current_plugin_label)
        current_plugin_layout.addWidget(self.current_plugin_combo)
        current_plugin_layout.addStretch()
        layout.addLayout(current_plugin_layout)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        # 设置标签页对齐方式为靠左
        self.tab_widget.setTabPosition(QTabWidget.North)
        # 确保标签页控件本身也左对齐
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
        """)
        # 强制设置标签栏左对齐
        self.tab_widget.tabBar().setStyleSheet("alignment: left;")
        # 设置标签栏扩展策略以确保左对齐
        self.tab_widget.tabBar().setExpanding(False)
        layout.addWidget(self.tab_widget)
        
        # 创建插件设置标签页
        self.create_plugin_settings_tabs()
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)  # 减少按钮间距
        
        self.reset_button = QPushButton("重置默认")
        self.reset_button.clicked.connect(self.reset_settings)
        self.reset_button.setFixedHeight(30)  # 调整按钮高度
        self.reset_button.setStyleSheet("QPushButton { font-weight: normal; padding: 5px 15px; }")
        button_layout.addWidget(self.reset_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setFixedHeight(30)  # 调整按钮高度
        self.cancel_button.setStyleSheet("QPushButton { font-weight: normal; padding: 5px 15px; }")
        button_layout.addWidget(self.cancel_button)
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        self.ok_button.setFixedHeight(30)  # 调整按钮高度
        self.ok_button.setStyleSheet("QPushButton { font-weight: normal; background-color: #2196F3; color: white; border-radius: 4px; padding: 5px 15px; }")
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
    
    def populate_plugin_combo(self):
        """填充插件选择组合框"""
        # 清空现有项目
        self.current_plugin_combo.clear()
        
        # 获取所有已加载的插件
        plugins = self.plugin_manager.list_plugins()
        
        # 添加插件到组合框
        for plugin_name in plugins:
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if plugin:
                # 获取插件标题
                plugin_info = getattr(plugin, 'PluginInfo', {})
                local_options = plugin_info.get('local_options', {})
                plugin_title = local_options.get('title', plugin_name)
                # 添加带有标题的插件项
                self.current_plugin_combo.addItem(f"{plugin_title} ({plugin_name})", plugin_name)
        
        # 设置当前选中的插件
        current_plugin = self.config_manager.get_current_plugin()
        if current_plugin:
            index = self.current_plugin_combo.findData(current_plugin)
            if index >= 0:
                self.current_plugin_combo.setCurrentIndex(index)
    

    
    def create_plugin_settings_tabs(self):
        """为每个插件创建设置标签页"""
        # 获取所有已加载的插件
        plugins = self.plugin_manager.list_plugins()
        
        if not plugins:
            # 如果没有插件，显示提示信息
            no_plugin_widget = QWidget()
            no_plugin_layout = QVBoxLayout(no_plugin_widget)
            no_plugin_label = QLabel("暂无OCR插件加载")
            no_plugin_label.setAlignment(Qt.AlignCenter)
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
        plugin_info = getattr(plugin, 'PluginInfo', {})
        global_options = plugin_info.get('global_options', {})
        local_options = plugin_info.get('local_options', {})
        
        # 插件说明标题
        plugin_title = local_options.get('title', plugin_name)
        title_label = QLabel(f"{plugin_title} - 插件配置")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        plugin_layout.addWidget(title_label)
        
        # 创建滚动区域以容纳设置
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 保留滚动策略
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
        
        # 显示全局配置
        if global_options:
            global_group = self.create_global_config_group(plugin_name, global_options)
            scroll_layout.addWidget(global_group)
        
        # 显示局部配置
        if local_options:
            local_group = self.create_local_config_group(plugin_name, local_options)
            scroll_layout.addWidget(local_group)
        
        scroll_layout.addStretch()
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        
        plugin_layout.addWidget(scroll_area)
        self.tab_widget.addTab(plugin_widget, plugin_name)
    
    def create_global_config_group(self, plugin_name, global_config):
        """创建全局配置组"""
        group_box = QGroupBox("全局配置")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #CCCCCC; border-radius: 4px; margin-top: 1ex; padding-top: 8px; background: transparent; }")
        group_layout = QFormLayout(group_box)
        group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # 让字段可以扩展
        group_layout.setRowWrapPolicy(QFormLayout.WrapLongRows)  # 长标签自动换行
        group_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 标签右对齐
        group_layout.setHorizontalSpacing(12)  # 调整水平间距
        group_layout.setVerticalSpacing(8)  # 调整垂直间距
        
        # 遍历全局配置项
        for option_key, option_config in global_config.items():
            if option_key == 'title' or option_key == 'type':
                continue
                
            widget = self.create_config_widget(plugin_name, option_key, option_config)
            if widget:
                title = option_config.get('title', option_key)
                tooltip = option_config.get('toolTip', option_config.get('description', ''))
                if tooltip:
                    widget.setToolTip(tooltip)
                
                group_layout.addRow(title, widget)
                # 存储控件引用
                if plugin_name not in self.plugin_widgets:
                    self.plugin_widgets[plugin_name] = {}
                self.plugin_widgets[plugin_name][option_key] = widget
        
        return group_box
    
    def create_local_config_group(self, plugin_name, local_config):
        """创建局部配置组"""
        group_box = QGroupBox("局部配置")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #CCCCCC; border-radius: 4px; margin-top: 1ex; padding-top: 8px; background: transparent; }")
        group_layout = QFormLayout(group_box)
        group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)  # 让字段可以扩展
        group_layout.setRowWrapPolicy(QFormLayout.WrapLongRows)  # 长标签自动换行
        group_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 标签右对齐
        group_layout.setHorizontalSpacing(12)  # 调整水平间距
        group_layout.setVerticalSpacing(8)  # 调整垂直间距
        
        # 遍历局部配置项
        for option_key, option_config in local_config.items():
            if option_key == 'title' or option_key == 'type':
                continue
                
            widget = self.create_config_widget(plugin_name, option_key, option_config)
            if widget:
                title = option_config.get('title', option_key)
                tooltip = option_config.get('toolTip', option_config.get('description', ''))
                if tooltip:
                    widget.setToolTip(tooltip)
                
                group_layout.addRow(title, widget)
                # 存储控件引用
                if plugin_name not in self.plugin_widgets:
                    self.plugin_widgets[plugin_name] = {}
                self.plugin_widgets[plugin_name][option_key] = widget
        
        return group_box
    
    def create_config_widget(self, plugin_name, option_key, option_config):
        """根据配置定义创建相应的控件"""
        option_type = option_config.get('type', 'string')
        default_value = option_config.get('default')
        
        try:
            if option_type == 'string':
                widget = QLineEdit()
                widget.setFixedHeight(30)  # 增加高度以提高可见性
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if default_value:
                    widget.setText(str(default_value))
            elif option_type == 'integer':
                widget = QSpinBox()
                widget.setFixedHeight(30)  # 增加高度以提高可见性
                widget.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
                min_val = option_config.get('min', 0)
                max_val = option_config.get('max', 999999)
                widget.setRange(min_val, max_val)
                if default_value is not None:
                    widget.setValue(int(default_value))
                if option_config.get('isInt'):
                    widget.setSingleStep(1)
            elif option_type == 'float':
                widget = QDoubleSpinBox()
                widget.setFixedHeight(30)  # 增加高度以提高可见性
                widget.setStyleSheet("QDoubleSpinBox { padding: 4px; font-size: 11pt; }")
                min_val = option_config.get('min', 0.0)
                max_val = option_config.get('max', 999999.0)
                widget.setRange(min_val, max_val)
                if default_value is not None:
                    widget.setValue(float(default_value))
                widget.setDecimals(2)
            elif option_type == 'boolean':
                widget = QCheckBox()
                widget.setStyleSheet("QCheckBox { spacing: 8px; font-size: 11pt; }")  # 增加文本间距和字体大小
                if default_value is not None:
                    widget.setChecked(bool(default_value))
            elif option_type == 'enum':
                widget = QComboBox()
                widget.setFixedHeight(30)  # 增加高度以提高可见性
                widget.setStyleSheet("""
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
                        selection-background-color: #2196F3;
                        selection-color: white;
                        border: 1px solid #CCCCCC;
                        outline: 0px;
                        min-width: 200px;
                    }
                    QComboBox QAbstractItemView::item {
                        background-color: white;
                        color: black;
                        padding: 4px;
                        min-height: 20px;
                    }
                    QComboBox QAbstractItemView::item:hover {
                        background-color: #E3F2FD;
                    }
                    QComboBox QAbstractItemView::item:selected {
                        background-color: #2196F3;
                        color: white;
                    }
                    QComboBox::drop-down {
                        subcontrol-origin: padding;
                        subcontrol-position: top right;
                        width: 20px;
                        border-left-width: 1px;
                        border-left-color: #CCCCCC;
                        border-left-style: solid;
                    }
                    QComboBox::down-arrow {
                        width: 12px;
                        height: 12px;
                    }
                """)
                # 设置视图样式确保下拉列表正确显示
                widget.view().setStyleSheet("""
                    background-color: white;
                    color: black;
                    selection-background-color: #2196F3;
                    selection-color: white;
                """)
                options_list = option_config.get('optionsList', [])
                for option in options_list:
                    if isinstance(option, list) and len(option) >= 2:
                        widget.addItem(option[1], option[0])  # 显示文本, 数据值
                    elif isinstance(option, str):
                        widget.addItem(option, option)
                # 设置默认值
                if default_value is not None:
                    index = widget.findData(default_value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
            else:
                # 对于未知类型，创建文本输入框
                widget = QLineEdit()
                widget.setFixedHeight(30)  # 增加高度以提高可见性
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if default_value:
                    widget.setText(str(default_value))
            
            return widget
        except Exception as e:
            logger.error(f"创建配置控件时出错: {plugin_name}.{option_key}, 错误: {e}")
            return None
    
    def load_settings(self):
        """加载当前配置到UI控件"""
        # 加载每个插件的配置
        for plugin_name in self.plugin_widgets:
            config = self.config_manager.get_plugin_config(plugin_name)
            
            # 设置控件值
            for option_key, widget in self.plugin_widgets[plugin_name].items():
                if option_key in config:
                    value = config[option_key]
                    self.set_widget_value(widget, value)
    
    def load_plugin_settings(self, plugin_name):
        """加载指定插件的配置到UI控件"""
        if plugin_name not in self.plugin_widgets:
            return
            
        config = self.config_manager.get_plugin_config(plugin_name)
        
        # 获取插件定义的默认值
        plugin = self.plugin_manager.get_plugin(plugin_name)
        default_values = {}
        if plugin and hasattr(plugin, 'PluginInfo'):
            plugin_info = plugin.PluginInfo
            # 从全局配置和局部配置中提取默认值
            for config_section in [plugin_info.get('global_options', {}), plugin_info.get('local_options', {})]:
                for key, value in config_section.items():
                    if isinstance(value, dict) and 'default' in value:
                        default_values[key] = value['default']
        
        # 设置控件值
        for option_key, widget in self.plugin_widgets[plugin_name].items():
            if option_key in config:
                # 使用配置中的值
                value = config[option_key]
                self.set_widget_value(widget, value)
            elif option_key in default_values:
                # 使用默认值
                value = default_values[option_key]
                self.set_widget_value(widget, value)
            else:
                # 如果既没有配置值也没有默认值，则根据控件类型设置合理的默认值
                self.set_widget_default_value(widget)
    
    def set_widget_value(self, widget, value):
        """设置控件值"""
        try:
            if isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
                else:
                    # 如果找不到匹配项，尝试按文本查找
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"设置控件值时出错: {e}")
    
    def set_widget_default_value(self, widget):
        """设置控件默认值"""
        try:
            if isinstance(widget, QLineEdit):
                widget.setText("")
            elif isinstance(widget, QSpinBox):
                widget.setValue(0)
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(0.0)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)
            elif isinstance(widget, QComboBox):
                if widget.count() > 0:
                    widget.setCurrentIndex(0)
        except Exception as e:
            logger.error(f"设置控件默认值时出错: {e}")
    
    def get_widget_value(self, widget):
        """获取控件值"""
        try:
            if isinstance(widget, QLineEdit):
                return widget.text()
            elif isinstance(widget, QSpinBox):
                return widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                return widget.value()
            elif isinstance(widget, QCheckBox):
                return widget.isChecked()
            elif isinstance(widget, QComboBox):
                # 返回当前选中项的数据值
                current_index = widget.currentIndex()
                if current_index >= 0:
                    return widget.itemData(current_index)
                return None
            else:
                return None
        except Exception as e:
            logger.error(f"获取控件值时出错: {e}")
            return None
    
    def accept(self):
        """点击确定按钮时保存设置"""
        try:
            # 保存每个插件的配置
            for plugin_name, widgets in self.plugin_widgets.items():
                config = {}
                
                # 收集配置值
                for option_key, widget in widgets.items():
                    value = self.get_widget_value(widget)
                    if value is not None:
                        config[option_key] = value
                
                # 验证配置
                errors = self.config_manager.set_plugin_config(plugin_name, config)
                if errors:
                    # 显示验证错误
                    error_msg = "\n".join([f"{key}: {msg}" for key, msg in errors.items()])
                    QMessageBox.warning(self, "配置验证失败", 
                                      f"插件 {plugin_name} 配置验证失败:\n{error_msg}")
                    return
            
            # 保存当前选中的插件
            current_plugin = self.current_plugin_combo.currentData()
            if current_plugin:
                self.config_manager.set_current_plugin(current_plugin)
            
            # 保存配置到文件
            self.config_manager.save_config()
            
            # 调用父类方法关闭对话框
            super().accept()
            
        except Exception as e:
            logger.error(f"保存配置时出错: {e}")
            QMessageBox.critical(self, "保存失败", f"保存配置时发生错误: {str(e)}")
    
    def reset_settings(self):
        """重置设置为默认值"""
        # 获取当前选中的tab
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0:
            return
            
        current_plugin_name = self.tab_widget.tabText(current_tab_index)
        
        reply = QMessageBox.question(self, "确认重置", 
                                   f"确定要将 {current_plugin_name} 的OCR设置重置为默认值吗？",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # 只重置当前插件的配置
                self.config_manager.reset_plugin_config(current_plugin_name)
                
                # 重新加载当前tab的设置
                self.load_plugin_settings(current_plugin_name)
                
                QMessageBox.information(self, "重置完成", f"{current_plugin_name} 的OCR设置已重置为默认值")
            except Exception as e:
                logger.error(f"重置配置时出错: {e}")
                QMessageBox.critical(self, "重置失败", f"重置配置时发生错误: {str(e)}")


def show_ocr_settings_dialog(parent=None):
    """显示OCR设置对话框"""
    dialog = OCRSettingsDialog(parent)
    return dialog.exec_()