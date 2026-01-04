"""
LLM插件配置管理器
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMPluginConfigManager:
    """LLM插件配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径,如果为None则使用默认路径
        """
        if config_file is None:
            # 使用项目配置目录
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "llm_plugins_config.json"

        self.config_file = Path(config_file)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_file.exists():
            logger.info(f"Config file not found, creating default: {self.config_file}")
            self._create_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            logger.info(f"Config loaded from: {self.config_file}")
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            self._create_default_config()

    def _create_default_config(self) -> None:
        """创建默认配置"""
        project_root = Path(__file__).parent.parent
        self._config = {
            "plugins": {
                "openai_llm": {
                    "enabled": False,
                    "api_key": "",
                    "base_url": "https://api.openai.com/v1",
                    "default_model": "gpt-3.5-turbo",
                    "max_tokens": 4096,
                    "temperature": 0.7
                },
                "claude_llm": {
                    "enabled": False,
                    "api_key": "",
                    "base_url": "https://api.anthropic.com",
                    "default_model": "claude-3-sonnet-20240229",
                    "max_tokens": 4096
                },
                "qwen_llm": {
                    "enabled": False,
                    "api_key": "",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "default_model": "qwen-turbo",
                    "max_tokens": 4096
                }
            },
            "memory": {
                "backend": "file",
                "storage_path": str(project_root / "data" / "llm_memory"),
                "max_memory_size": 1000
            },
            "chat_settings": {
                "stream_enabled": True,
                "max_history": 20,
                "auto_save": True,
                "default_system_prompt": "你是一个PDF文档助手,可以帮助用户处理PDF文件。"
            },
            "security": {
                "rate_limit_enabled": True,
                "max_calls_per_minute": 60,
                "allowed_plugins": [],
                "allowed_tools": []
            },
            "performance": {
                "cache_enabled": True,
                "cache_ttl": 3600,
                "cache_max_size": 1000
            }
        }
        self._save_config()

    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Config saved to: {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件配置

        Args:
            plugin_name: 插件名称

        Returns:
            插件配置字典
        """
        return self._config.get("plugins", {}).get(plugin_name, {})

    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """
        设置插件配置

        Args:
            plugin_name: 插件名称
            config: 配置字典
        """
        if "plugins" not in self._config:
            self._config["plugins"] = {}

        self._config["plugins"][plugin_name] = config
        self._save_config()

    def get_all_plugin_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件配置"""
        return self._config.get("plugins", {})

    def get_last_selected_plugin(self) -> str | None:
        """
        获取上次选择的插件

        Returns:
            上次选择的插件名称,如果未选择过则返回None
        """
        return self._config.get("last_selected_plugin")

    def set_last_selected_plugin(self, plugin_name: str) -> None:
        """
        设置上次选择的插件

        Args:
            plugin_name: 插件名称
        """
        self._config["last_selected_plugin"] = plugin_name
        self._save_config()

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        检查插件是否启用

        Args:
            plugin_name: 插件名称

        Returns:
            是否启用
        """
        return self.get_plugin_config(plugin_name).get("enabled", False)

    def set_plugin_enabled(self, plugin_name: str, enabled: bool) -> None:
        """
        设置插件启用状态

        Args:
            plugin_name: 插件名称
            enabled: 是否启用
        """
        plugin_config = self.get_plugin_config(plugin_name)
        plugin_config["enabled"] = enabled
        self.set_plugin_config(plugin_name, plugin_config)

    def get_memory_config(self) -> Dict[str, Any]:
        """获取记忆系统配置"""
        return self._config.get("memory", {})

    def set_memory_config(self, config: Dict[str, Any]) -> None:
        """
        设置记忆系统配置

        Args:
            config: 配置字典
        """
        self._config["memory"] = config
        self._save_config()

    def get_chat_settings(self) -> Dict[str, Any]:
        """获取聊天设置"""
        return self._config.get("chat_settings", {})

    def set_chat_settings(self, settings: Dict[str, Any]) -> None:
        """
        设置聊天设置

        Args:
            settings: 设置字典
        """
        self._config["chat_settings"] = settings
        self._save_config()

    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return self._config.get("security", {})

    def set_security_config(self, config: Dict[str, Any]) -> None:
        """
        设置安全配置

        Args:
            config: 配置字典
        """
        self._config["security"] = config
        self._save_config()

    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能配置"""
        return self._config.get("performance", {})

    def set_performance_config(self, config: Dict[str, Any]) -> None:
        """
        设置性能配置

        Args:
            config: 配置字典
        """
        self._config["performance"] = config
        self._save_config()

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键(支持点号分隔,如 "plugins.openai.api_key")
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        设置配置值

        Args:
            key: 配置键(支持点号分隔,如 "plugins.openai.api_key")
            value: 配置值
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        self._save_config()

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()

    def reset_to_default(self) -> None:
        """重置为默认配置"""
        logger.info("Resetting config to default")
        self._create_default_config()

    def export_config(self, export_path: str) -> None:
        """
        导出配置

        Args:
            export_path: 导出文件路径
        """
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Config exported to: {export_path}")
        except Exception as e:
            logger.error(f"Error exporting config: {e}", exc_info=True)

    def import_config(self, import_path: str) -> None:
        """
        导入配置

        Args:
            import_path: 导入文件路径
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)

            self._config = imported_config
            self._save_config()
            logger.info(f"Config imported from: {import_path}")
        except Exception as e:
            logger.error(f"Error importing config: {e}", exc_info=True)
