"""
云存储插件设置对话框
用于配置所有云存储插件的全局和局部选项
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QWidget, QFormLayout, QLineEdit, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QComboBox, QPushButton,
                             QLabel, QGroupBox, QScrollArea,
                             QMessageBox, QLayout, QSizePolicy, QToolButton)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.managers.storage_plugin_manager import storage_plugin_manager
from app.config.storage_plugin_config import storage_config_manager
from app.utils.logger import get_logger

logger = get_logger('storage_settings_dialog')


class StorageSettingsDialog(QDialog):
    """云存储插件设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("云存储插件设置")
        self.resize(800, 700)
        self.setMinimumSize(700, 500)
        self.setMaximumSize(1200, 900)
        self.setModal(True)

        self.setWindowFlags(self.windowFlags() | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.plugin_manager = storage_plugin_manager
        self.config_manager = storage_config_manager

        self.plugin_widgets = {}

        self.plugin_manager.load_plugins()

        self.setup_ui()
        self.load_settings()

    def populate_plugin_combo(self):
        """填充插件选择组合框"""
        self.current_plugin_combo.clear()

        plugins = self.plugin_manager.list_plugins()

        for plugin_name in plugins:
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if plugin:
                plugin_info = getattr(plugin, 'PluginInfo', {})
                local_options = plugin_info.get('local_options', {})
                plugin_title = plugin_info.get('title', local_options.get('title', plugin_name))
                self.current_plugin_combo.addItem(f"{plugin_title} ({plugin_name})", plugin_name)

        current_plugin = self.config_manager.get_current_plugin()
        if current_plugin:
            index = self.current_plugin_combo.findData(current_plugin)
            if index >= 0:
                self.current_plugin_combo.setCurrentIndex(index)

    def center_on_screen(self):
        """将窗口居中显示在屏幕中央"""
        screen_geo = self.screen().availableGeometry()
        dialog_x = screen_geo.center().x() - self.width() // 2
        dialog_y = screen_geo.center().y() - self.height() // 2
        margin = 30
        dialog_x = max(screen_geo.left() + margin, min(dialog_x, screen_geo.right() - self.width() - margin))
        dialog_y = max(screen_geo.top() + margin, min(dialog_y, screen_geo.bottom() - self.height() - margin))
        self.move(dialog_x, dialog_y)
        self.setAttribute(Qt.WA_Moved, True)

    def showEvent(self, event):
        """窗口显示事件，用于居中显示对话框"""
        super().showEvent(event)
        self.adjustSize()
        if not self.testAttribute(Qt.WA_Moved):
            self.center_on_screen()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSizeConstraint(QLayout.SetMinimumSize)

        current_plugin_layout = QHBoxLayout()
        current_plugin_label = QLabel("当前使用的云存储插件:")
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

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CCCCCC;
                border-top: none;
                border-radius: 4px;
                top: -1px;
                background: transparent;
            }
            QTabBar::tab {
                background: #F0F0F0;
                border: 1px solid #CCCCCC;
                border-bottom: none;
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
                margin-top: 2px;
            }
            QTabBar {
                alignment: left;
                qproperty-drawBase: 0;
            }
            QTabWidget QTabBar::tab-bar {
                alignment: left;
                left: 0px;
            }
            QTabWidget::tab-bar {
                alignment: left;
                left: 0;
            }
            QTabBar::tab-bar {
                alignment: left;
                left: 0;
            }
        """)
        self.tab_widget.tabBar().setStyleSheet("alignment: left;")
        self.tab_widget.tabBar().setExpanding(False)
        layout.addWidget(self.tab_widget)

        self.create_plugin_settings_tabs()

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.reset_button = QPushButton("重置默认")
        self.reset_button.clicked.connect(self.reset_settings)
        self.reset_button.setFixedHeight(30)
        self.reset_button.setStyleSheet("QPushButton { font-weight: normal; padding: 5px 15px; }")
        button_layout.addWidget(self.reset_button)

        button_layout.addStretch()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setFixedHeight(30)
        self.cancel_button.setStyleSheet("QPushButton { font-weight: normal; padding: 5px 15px; }")
        button_layout.addWidget(self.cancel_button)

        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        self.ok_button.setFixedHeight(30)
        self.ok_button.setStyleSheet("QPushButton { font-weight: normal; background-color: #2196F3; color: white; border-radius: 4px; padding: 5px 15px; }")
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

    def create_plugin_settings_tabs(self):
        """为每个插件创建设置标签页"""
        plugins = self.plugin_manager.list_plugins()

        if not plugins:
            no_plugin_widget = QWidget()
            no_plugin_layout = QVBoxLayout(no_plugin_widget)
            no_plugin_label = QLabel("暂无云存储插件加载")
            no_plugin_label.setAlignment(Qt.AlignCenter)
            no_plugin_layout.addWidget(no_plugin_label)
            self.tab_widget.addTab(no_plugin_widget, "插件设置")
            return

        for plugin_name in plugins:
            self.create_plugin_tab(plugin_name)

    def create_plugin_tab(self, plugin_name):
        """为指定插件创建设置标签页"""
        plugin_widget = QWidget()
        plugin_layout = QVBoxLayout(plugin_widget)
        plugin_layout.setSpacing(12)
        plugin_layout.setContentsMargins(12, 12, 12, 12)

        plugin = self.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            error_label = QLabel(f"无法获取插件信息: {plugin_name}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-weight: bold;")
            plugin_layout.addWidget(error_label)
            self.tab_widget.addTab(plugin_widget, plugin_name)
            return

        plugin_info = self.plugin_manager.get_plugin_info(plugin_name)
        global_options = plugin_info.get('global_options', {})
        local_options = plugin_info.get('local_options', {})

        plugin_title = local_options.get('title', plugin_name)
        title_label = QLabel(f"{plugin_title} - 插件配置")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        plugin_layout.addWidget(title_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(8, 8, 8, 8)

        self.plugin_widgets[plugin_name] = {}

        if global_options:
            global_group = self.create_global_config_group(plugin_name, global_options)
            scroll_layout.addWidget(global_group)

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
        group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        group_layout.setRowWrapPolicy(QFormLayout.WrapLongRows)
        group_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        group_layout.setHorizontalSpacing(12)
        group_layout.setVerticalSpacing(8)

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
                if plugin_name not in self.plugin_widgets:
                    self.plugin_widgets[plugin_name] = {}
                self.plugin_widgets[plugin_name][option_key] = widget

        return group_box

    def create_local_config_group(self, plugin_name, local_config):
        """创建局部配置组"""
        group_box = QGroupBox("局部配置")
        group_box.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #CCCCCC; border-radius: 4px; margin-top: 1ex; padding-top: 8px; background: transparent; }")
        group_layout = QFormLayout(group_box)
        group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        group_layout.setRowWrapPolicy(QFormLayout.WrapLongRows)
        group_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        group_layout.setHorizontalSpacing(12)
        group_layout.setVerticalSpacing(8)

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
                if plugin_name not in self.plugin_widgets:
                    self.plugin_widgets[plugin_name] = {}
                self.plugin_widgets[plugin_name][option_key] = widget

        return group_box

    def create_config_widget(self, plugin_name, option_key, option_config):
        """根据配置定义创建相应的控件"""
        option_type = option_config.get('type', 'string')
        default_value = option_config.get('default')

        try:
            if option_type in ['string', 'str']:
                widget = QLineEdit()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if default_value:
                    widget.setText(str(default_value))
            elif option_type == 'password':
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(5)

                password_edit = QLineEdit()
                password_edit.setFixedHeight(30)
                password_edit.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                password_edit.setEchoMode(QLineEdit.Password)
                if default_value:
                    password_edit.setText(str(default_value))

                eye_button = QToolButton()
                eye_button.setFixedSize(30, 30)
                eye_button.setCheckable(True)
                eye_button.setStyleSheet("""
                    QToolButton {
                        border: none;
                        background-color: transparent;
                        border-radius: 4px;
                    }
                    QToolButton:hover {
                        background-color: #E3F2FD;
                    }
                """)
                eye_button.setText("👁")
                eye_button.setToolTip("显示/隐藏密码")

                def toggle_password_visibility(checked):
                    if checked:
                        password_edit.setEchoMode(QLineEdit.Normal)
                        eye_button.setText("👁‍🗨")
                    else:
                        password_edit.setEchoMode(QLineEdit.Password)
                        eye_button.setText("👁")

                eye_button.toggled.connect(toggle_password_visibility)

                layout.addWidget(password_edit, 1)
                layout.addWidget(eye_button)

                widget = container
                widget.password_edit = password_edit
                widget.eye_button = eye_button
            elif option_type in ['integer', 'int']:
                widget = QSpinBox()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QSpinBox { padding: 4px; font-size: 11pt; }")
                min_val = option_config.get('min', 0)
                max_val = option_config.get('max', 999999)
                widget.setRange(min_val, max_val)
                if default_value is not None:
                    widget.setValue(int(default_value))
                if option_config.get('isInt'):
                    widget.setSingleStep(1)
            elif option_type in ['float', 'double']:
                widget = QDoubleSpinBox()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QDoubleSpinBox { padding: 4px; font-size: 11pt; }")
                min_val = option_config.get('min', 0.0)
                max_val = option_config.get('max', 999999.0)
                widget.setRange(min_val, max_val)
                if default_value is not None:
                    widget.setValue(float(default_value))
                widget.setDecimals(2)
            elif option_type == 'boolean':
                widget = QCheckBox()
                widget.setStyleSheet("QCheckBox { spacing: 8px; font-size: 11pt; }")
                if default_value is not None:
                    widget.setChecked(bool(default_value))
            elif option_type == 'enum':
                widget = QComboBox()
                widget.setFixedHeight(30)
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
                widget.view().setStyleSheet("""
                    background-color: white;
                    color: black;
                    selection-background-color: #2196F3;
                    selection-color: white;
                """)
                options_list = option_config.get('optionsList', [])
                for option in options_list:
                    if isinstance(option, list) and len(option) >= 2:
                        widget.addItem(option[1], option[0])
                    elif isinstance(option, str):
                        widget.addItem(option, option)
                if default_value is not None:
                    index = widget.findData(default_value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
            else:
                widget = QLineEdit()
                widget.setFixedHeight(30)
                widget.setStyleSheet("QLineEdit { padding: 4px; font-size: 11pt; }")
                if default_value:
                    widget.setText(str(default_value))

            return widget
        except Exception as e:
            logger.error(f"创建配置控件时出错: {plugin_name}.{option_key}, 错误: {e}")
            return None

    def load_settings(self):
        """加载当前配置到UI控件"""
        for plugin_name in self.plugin_widgets:
            config = self.config_manager.get_plugin_config(plugin_name)

            for option_key, widget in self.plugin_widgets[plugin_name].items():
                if option_key in config:
                    value = config[option_key]
                    self.set_widget_value(widget, value)

    def load_plugin_settings(self, plugin_name):
        """加载指定插件的配置到UI控件"""
        if plugin_name not in self.plugin_widgets:
            return

        config = self.config_manager.get_plugin_config(plugin_name)

        plugin = self.plugin_manager.get_plugin(plugin_name)
        default_values = {}
        if plugin and hasattr(plugin, 'PluginInfo'):
            plugin_info = plugin.PluginInfo
            for config_section in [plugin_info.get('global_options', {}), plugin_info.get('local_options', {})]:
                for key, value in config_section.items():
                    if isinstance(value, dict) and 'default' in value:
                        default_values[key] = value['default']

        for option_key, widget in self.plugin_widgets[plugin_name].items():
            if option_key in config:
                value = config[option_key]
                self.set_widget_value(widget, value)
            elif option_key in default_values:
                value = default_values[option_key]
                self.set_widget_value(widget, value)
            else:
                self.set_widget_default_value(widget)

    def set_widget_value(self, widget, value):
        """设置控件值"""
        try:
            if hasattr(widget, 'password_edit'):
                widget.password_edit.setText(str(value))
            elif isinstance(widget, QLineEdit):
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
            if hasattr(widget, 'password_edit'):
                return widget.password_edit.text()
            elif isinstance(widget, QLineEdit):
                return widget.text()
            elif isinstance(widget, QSpinBox):
                return widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                return widget.value()
            elif isinstance(widget, QCheckBox):
                return widget.isChecked()
            elif isinstance(widget, QComboBox):
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
            for plugin_name, widgets in self.plugin_widgets.items():
                config = {}

                for option_key, widget in widgets.items():
                    value = self.get_widget_value(widget)
                    if value is not None:
                        config[option_key] = value

                errors = self.config_manager.set_plugin_config(plugin_name, config)
                if errors:
                    error_msg = "\n".join([f"{key}: {msg}" for key, msg in errors.items()])
                    QMessageBox.warning(self, "配置验证失败",
                                      f"插件 {plugin_name} 配置验证失败:\n{error_msg}")
                    return

            current_plugin = self.current_plugin_combo.currentData()
            if current_plugin:
                self.config_manager.set_current_plugin(current_plugin)

            self.config_manager.save_config()

            parent = self.parent()
            while parent and not hasattr(parent, 'update_file_list_panel'):
                parent = parent.parent()

            if parent and hasattr(parent, 'update_file_list_panel'):
                parent.update_file_list_panel()

            super().accept()

        except Exception as e:
            logger.error(f"保存配置时出错: {e}")
            QMessageBox.critical(self, "保存失败", f"保存配置时发生错误: {str(e)}")

    def reset_settings(self):
        """重置设置为默认值"""
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0:
            return

        current_plugin_name = self.tab_widget.tabText(current_tab_index)

        reply = QMessageBox.question(self, "确认重置",
                                   f"确定要将 {current_plugin_name} 的云存储设置重置为默认值吗？",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                self.config_manager.reset_plugin_config(current_plugin_name)
                self.load_plugin_settings(current_plugin_name)
                QMessageBox.information(self, "重置完成", f"{current_plugin_name} 的云存储设置已重置为默认值")
            except Exception as e:
                logger.error(f"重置配置时出错: {e}")
                QMessageBox.critical(self, "重置失败", f"重置配置时发生错误: {str(e)}")


def show_storage_settings_dialog(parent=None):
    """显示云存储设置对话框"""
    dialog = StorageSettingsDialog(parent)
    return dialog.exec_()
