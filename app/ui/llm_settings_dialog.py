"""
LLM设置对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QComboBox, QLabel, QTabWidget,
    QWidget, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt
from typing import Dict, Any
from app.config.llm_plugin_config import LLMPluginConfigManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMSettingsDialog(QDialog):
    """LLM设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_manager = LLMPluginConfigManager()
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("LLM 设置")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # 创建选项卡
        tab_widget = QTabWidget()

        # 插件设置选项卡
        plugin_tab = self._create_plugin_tab()
        tab_widget.addTab(plugin_tab, "插件设置")

        # 记忆系统选项卡
        memory_tab = self._create_memory_tab()
        tab_widget.addTab(memory_tab, "记忆系统")

        # 聊天设置选项卡
        chat_tab = self._create_chat_tab()
        tab_widget.addTab(chat_tab, "聊天设置")

        # 安全设置选项卡
        security_tab = self._create_security_tab()
        tab_widget.addTab(security_tab, "安全设置")

        layout.addWidget(tab_widget)

        # 按钮区域
        button_layout = QHBoxLayout()

        save_button = QPushButton("保存")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # 加载当前设置
        self._load_settings()

    def _create_plugin_tab(self) -> QWidget:
        """创建插件设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 插件选择
        plugin_layout = QHBoxLayout()
        plugin_layout.addWidget(QLabel("选择插件:"))
        self._plugin_combo = QComboBox()
        self._plugin_combo.addItems(["openai_llm", "claude_llm", "qwen_llm"])
        self._plugin_combo.currentTextChanged.connect(self._on_plugin_changed)
        plugin_layout.addWidget(self._plugin_combo)
        layout.addLayout(plugin_layout)

        # 插件设置表单
        form_layout = QFormLayout()

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.setPlaceholderText("请输入API密钥")
        form_layout.addRow("API密钥:", self._api_key_edit)

        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText("API基础URL")
        form_layout.addRow("基础URL:", self._base_url_edit)

        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("默认模型")
        form_layout.addRow("默认模型:", self._model_edit)

        self._max_tokens_spin = QSpinBox()
        self._max_tokens_spin.setRange(1, 128000)
        self._max_tokens_spin.setValue(4096)
        form_layout.addRow("最大Tokens:", self._max_tokens_spin)

        self._temperature_spin = QDoubleSpinBox()
        self._temperature_spin.setRange(0.0, 2.0)
        self._temperature_spin.setSingleStep(0.1)
        self._temperature_spin.setValue(0.7)
        form_layout.addRow("温度:", self._temperature_spin)

        self._enabled_check = QCheckBox("启用此插件")
        form_layout.addRow("", self._enabled_check)

        layout.addLayout(form_layout)
        layout.addStretch()

        return widget

    def _create_memory_tab(self) -> QWidget:
        """创建记忆系统选项卡"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 记忆后端选择
        self._memory_backend_combo = QComboBox()
        self._memory_backend_combo.addItems(["in_memory", "file"])
        layout.addRow("存储后端:", self._memory_backend_combo)

        # 存储路径
        self._memory_path_edit = QLineEdit()
        self._memory_path_edit.setPlaceholderText("记忆存储路径")
        layout.addRow("存储路径:", self._memory_path_edit)

        # 最大记忆数
        self._max_memory_spin = QSpinBox()
        self._max_memory_spin.setRange(1, 10000)
        self._max_memory_spin.setValue(1000)
        layout.addRow("最大记忆数:", self._max_memory_spin)

        return widget

    def _create_chat_tab(self) -> QWidget:
        """创建聊天设置选项卡"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 流式输出
        self._stream_check = QCheckBox("启用流式输出")
        self._stream_check.setChecked(True)
        layout.addRow("", self._stream_check)

        # 最大历史记录
        self._max_history_spin = QSpinBox()
        self._max_history_spin.setRange(1, 100)
        self._max_history_spin.setValue(20)
        layout.addRow("最大历史记录:", self._max_history_spin)

        # 自动保存
        self._auto_save_check = QCheckBox("自动保存对话")
        self._auto_save_check.setChecked(True)
        layout.addRow("", self._auto_save_check)

        # 系统提示词
        self._system_prompt_edit = QLineEdit()
        self._system_prompt_edit.setPlaceholderText("系统提示词")
        self._system_prompt_edit.setText("你是一个PDF文档助手,可以帮助用户处理PDF文件。")
        layout.addRow("系统提示词:", self._system_prompt_edit)

        return widget

    def _create_security_tab(self) -> QWidget:
        """创建安全设置选项卡"""
        widget = QWidget()
        layout = QFormLayout(widget)

        # 启用速率限制
        self._rate_limit_check = QCheckBox("启用速率限制")
        self._rate_limit_check.setChecked(True)
        layout.addRow("", self._rate_limit_check)

        # 每分钟最大调用次数
        self._max_calls_spin = QSpinBox()
        self._max_calls_spin.setRange(1, 1000)
        self._max_calls_spin.setValue(60)
        layout.addRow("每分钟最大调用次数:", self._max_calls_spin)

        return widget

    def _on_plugin_changed(self, plugin_name: str):
        """插件改变"""
        # 加载插件的配置
        config = self._config_manager.get_plugin_config(plugin_name)

        self._api_key_edit.setText(config.get("api_key", ""))
        self._base_url_edit.setText(config.get("base_url", ""))
        self._model_edit.setText(config.get("default_model", ""))
        self._max_tokens_spin.setValue(config.get("max_tokens", 4096))
        self._temperature_spin.setValue(config.get("temperature", 0.7))
        self._enabled_check.setChecked(config.get("enabled", False))

    def _load_settings(self):
        """加载设置"""
        # 加载当前选中插件的配置
        plugin_name = self._plugin_combo.currentText()
        self._on_plugin_changed(plugin_name)

        # 加载记忆系统配置
        memory_config = self._config_manager.get_memory_config()
        self._memory_backend_combo.setCurrentText(memory_config.get("backend", "in_memory"))
        self._memory_path_edit.setText(memory_config.get("storage_path", ""))
        self._max_memory_spin.setValue(memory_config.get("max_memory_size", 1000))

        # 加载聊天设置
        chat_settings = self._config_manager.get_chat_settings()
        self._stream_check.setChecked(chat_settings.get("stream_enabled", True))
        self._max_history_spin.setValue(chat_settings.get("max_history", 20))
        self._auto_save_check.setChecked(chat_settings.get("auto_save", True))
        self._system_prompt_edit.setText(chat_settings.get("default_system_prompt", ""))

        # 加载安全设置
        security_config = self._config_manager.get_security_config()
        self._rate_limit_check.setChecked(security_config.get("rate_limit_enabled", True))
        self._max_calls_spin.setValue(security_config.get("max_calls_per_minute", 60))

    def _save_settings(self):
        """保存设置"""
        try:
            # 保存插件配置
            plugin_name = self._plugin_combo.currentText()
            plugin_config = {
                "enabled": self._enabled_check.isChecked(),
                "api_key": self._api_key_edit.text(),
                "base_url": self._base_url_edit.text(),
                "default_model": self._model_edit.text(),
                "max_tokens": self._max_tokens_spin.value(),
                "temperature": self._temperature_spin.value()
            }
            self._config_manager.set_plugin_config(plugin_name, plugin_config)

            # 保存记忆系统配置
            memory_config = {
                "backend": self._memory_backend_combo.currentText(),
                "storage_path": self._memory_path_edit.text(),
                "max_memory_size": self._max_memory_spin.value()
            }
            self._config_manager.set_memory_config(memory_config)

            # 保存聊天设置
            chat_settings = {
                "stream_enabled": self._stream_check.isChecked(),
                "max_history": self._max_history_spin.value(),
                "auto_save": self._auto_save_check.isChecked(),
                "default_system_prompt": self._system_prompt_edit.text()
            }
            self._config_manager.set_chat_settings(chat_settings)

            # 保存安全设置
            security_config = {
                "rate_limit_enabled": self._rate_limit_check.isChecked(),
                "max_calls_per_minute": self._max_calls_spin.value()
            }
            self._config_manager.set_security_config(security_config)

            QMessageBox.information(self, "成功", "设置已保存")
            self.accept()

        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")
