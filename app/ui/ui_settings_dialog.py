# -*- coding: utf-8 -*-
"""
界面设置对话框
用于配置应用界面的各种显示选项
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QCheckBox, QSpinBox, QComboBox,
                             QPushButton, QGroupBox, QFormLayout, QTabWidget, QWidget)
from PyQt5.QtCore import Qt
from app.config.settings import AppSettings
from app.utils.logger import get_logger

logger = get_logger('ui_settings_dialog')


class UISettingsDialog(QDialog):
    """界面设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("界面设置")
        self.setMinimumWidth(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 创建选项卡
        tab_widget = QTabWidget()

        # 文件列表面板设置
        file_list_tab = self._create_file_list_tab()
        tab_widget.addTab(file_list_tab, "📁 文件列表")

        # 浏览设置
        view_tab = self._create_view_tab()
        tab_widget.addTab(view_tab, "👁️ 浏览")

        # 日志设置
        log_tab = self._create_log_tab()
        tab_widget.addTab(log_tab, "📝 日志")

        layout.addWidget(tab_widget)

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

    def _create_file_list_tab(self):
        """创建文件列表面板设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

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
        layout.addStretch()

        return widget

    def _create_view_tab(self):
        """创建浏览设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # 浏览设置组
        view_group = QGroupBox("浏览选项")
        view_layout = QVBoxLayout(view_group)
        view_layout.setSpacing(15)

        # 默认显示缩略图
        self.show_thumbnails_checkbox = QCheckBox("打开新文件时默认显示缩略图")
        show_thumbnails = AppSettings.get_show_thumbnails_default()
        self.show_thumbnails_checkbox.setChecked(show_thumbnails)
        view_layout.addWidget(self.show_thumbnails_checkbox)

        # 使用A4缩放
        self.a4_scaling_checkbox = QCheckBox("使用A4缩放模式")
        a4_scaling = AppSettings.get_use_a4_scaling()
        self.a4_scaling_checkbox.setChecked(a4_scaling)
        view_layout.addWidget(self.a4_scaling_checkbox)

        # OCR文本层高亮
        self.ocr_highlight_checkbox = QCheckBox("OCR文本层高亮模式")
        ocr_highlight = AppSettings.get_ocr_highlight_mode()
        self.ocr_highlight_checkbox.setChecked(ocr_highlight)
        view_layout.addWidget(self.ocr_highlight_checkbox)

        # 添加设置组到主布局
        layout.addWidget(view_group)
        layout.addStretch()

        return widget

    def _create_log_tab(self):
        """创建日志设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # 日志设置组
        log_group = QGroupBox("日志设置")
        log_form = QFormLayout(log_group)
        log_form.setSpacing(15)

        # 日志级别
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        current_level = AppSettings.get_log_level()
        self.log_level_combo.setCurrentText(current_level)
        log_form.addRow("日志级别:", self.log_level_combo)

        # 日志级别说明
        log_level_desc = QLabel("DEBUG: 详细调试信息\nINFO: 一般信息\nWARNING: 警告信息\nERROR: 错误信息\nCRITICAL: 严重错误")
        log_level_desc.setStyleSheet("color: #666; font-size: 11px;")
        log_form.addRow("", log_level_desc)

        # 添加设置组到主布局
        layout.addWidget(log_group)
        layout.addStretch()

        return widget

    def save_settings(self):
        """保存设置"""
        try:
            # 保存文件列表面板设置
            AppSettings.set_file_list_panel_visible(self.visible_checkbox.isChecked())
            AppSettings.set_file_list_panel_width(self.width_spinbox.value())

            # 保存浏览设置
            AppSettings.set_show_thumbnails_default(self.show_thumbnails_checkbox.isChecked())
            AppSettings.set_use_a4_scaling(self.a4_scaling_checkbox.isChecked())
            AppSettings.set_ocr_highlight_mode(self.ocr_highlight_checkbox.isChecked())

            # 保存日志设置
            AppSettings.set_log_level(self.log_level_combo.currentText())

            logger.info(f"界面设置已保存")
            self.accept()
        except Exception as e:
            logger.error(f"保存界面设置失败: {e}")

    def reset_to_default(self):
        """恢复默认设置"""
        try:
            # 文件列表面板
            self.visible_checkbox.setChecked(False)
            self.width_spinbox.setValue(600)

            # 浏览设置
            self.show_thumbnails_checkbox.setChecked(False)
            self.a4_scaling_checkbox.setChecked(True)
            self.ocr_highlight_checkbox.setChecked(False)

            # 日志设置
            self.log_level_combo.setCurrentText("DEBUG")

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
