# -*- coding: utf-8 -*-
"""
界面设置对话框
用于配置应用界面的各种显示选项
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QCheckBox, QSpinBox, 
                             QPushButton, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt
from app.config.settings import AppSettings
from app.utils.logger import get_logger

logger = get_logger('ui_settings_dialog')


class UISettingsDialog(QDialog):
    """界面设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("界面设置")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 文件列表面板设置组
        file_list_group = QGroupBox("文件列表面板")
        file_list_layout = QVBoxLayout(file_list_group)
        file_list_layout.setSpacing(15)

        # 默认显示复选框
        self.visible_checkbox = QCheckBox("启动时默认显示文件列表面板")
        visible = AppSettings.get_file_list_panel_visible()
        self.visible_checkbox.setChecked(visible)
        file_list_layout.addWidget(self.visible_checkbox)

        # 面板宽度设置
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("面板宽度(像素):"))
        
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(300, 2000)
        self.width_spinbox.setSuffix(" px")
        self.width_spinbox.setValue(AppSettings.get_file_list_panel_width())
        width_layout.addWidget(self.width_spinbox)
        
        file_list_layout.addLayout(width_layout)

        # 添加设置组到主布局
        layout.addWidget(file_list_group)

        # 添加弹性空间
        layout.addStretch()

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.reset_button = QPushButton("恢复默认")
        self.reset_button.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.reset_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.save_settings)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

    def save_settings(self):
        """保存设置"""
        try:
            # 保存文件列表面板显示状态
            AppSettings.set_file_list_panel_visible(self.visible_checkbox.isChecked())
            
            # 保存文件列表面板宽度
            AppSettings.set_file_list_panel_width(self.width_spinbox.value())
            
            logger.info(f"界面设置已保存: 文件列表面板显示={self.visible_checkbox.isChecked()}, 宽度={self.width_spinbox.value()}")
            
            self.accept()
        except Exception as e:
            logger.error(f"保存界面设置失败: {e}")

    def reset_to_default(self):
        """恢复默认设置"""
        try:
            self.visible_checkbox.setChecked(False)
            self.width_spinbox.setValue(600)
            logger.info("界面设置已恢复默认值")
        except Exception as e:
            logger.error(f"恢复默认设置失败: {e}")


def show_ui_settings_dialog(parent=None):
    """显示界面设置对话框的便捷函数"""
    dialog = UISettingsDialog(parent)
    if dialog.exec_() == QDialog.Accepted:
        # 如果设置改变，需要通知主窗口更新
        if parent and hasattr(parent, 'file_list_panel'):
            # 更新面板宽度
            panel_width = AppSettings.get_file_list_panel_width()
            parent.file_list_panel.setMinimumWidth(panel_width)
            
            # 更新面板可见性
            visible = AppSettings.get_file_list_panel_visible()
            if visible and not parent.file_list_dock.isVisible():
                parent.file_list_dock.show()
                parent.file_list_panel.load_current_plugin()
            elif not visible and parent.file_list_dock.isVisible():
                parent.file_list_dock.hide()
        
        return True
    return False
