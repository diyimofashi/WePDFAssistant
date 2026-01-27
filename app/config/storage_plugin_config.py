"""
云存储插件配置管理器
负责管理云存储插件的配置信息
"""

import os
import json
from typing import Dict, Any, Optional
from app.utils.logger import get_logger
from app.utils.app_path import get_config_dir


logger = get_logger('storage_plugin_config')


class StoragePluginConfigManager:
    """云存储插件配置管理器"""

    def __init__(self, config_file: str = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，默认为应用目录下的storage_plugins_config.json
        """
        self.config_file = config_file or os.path.join(get_config_dir(), 'storage_plugins_config.json')

        # 配置数据
        self.config_data: Dict[str, Any] = {}

        # 加载现有配置
        self.load_config()

    def load_config(self) -> bool:
        """
        从文件加载配置

        Returns:
            bool: 加载是否成功
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)

                return True
            else:
                self.config_data = {
                    "current_plugin": "",
                    "plugins": {}
                }
                return True

        except Exception as e:
            logger.error(f"加载云存储插件配置失败: {e}")
            self.config_data = {
                "current_plugin": "",
                "plugins": {}
            }
            return False

    def save_config(self) -> bool:
        """
        保存配置到文件

        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"保存云存储插件配置失败: {e}")
            return False

    def get_current_plugin(self) -> str:
        """
        获取当前使用的插件名称

        Returns:
            str: 当前插件名称
        """
        return self.config_data.get("current_plugin", "")

    def set_current_plugin(self, plugin_name: str) -> None:
        """
        设置当前使用的插件名称

        Args:
            plugin_name: 插件名称
        """
        self.config_data["current_plugin"] = plugin_name
        self.save_config()

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取指定插件的配置

        Args:
            plugin_name: 插件名称

        Returns:
            Dict[str, Any]: 插件配置字典
        """
        plugins = self.config_data.get("plugins", {})
        plugin_config = plugins.get(plugin_name, {})

        # 如果没有配置，从插件的配置定义文件中获取默认值
        if not plugin_config:
            plugin_config = self.get_plugin_default_config(plugin_name)

        return plugin_config

    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        设置指定插件的配置

        Args:
            plugin_name: 插件名称
            config: 配置字典

        Returns:
            Optional[Dict[str, str]]: 验证错误字典，None表示没有错误
        """
        # 验证配置
        errors = self.validate_plugin_config(plugin_name, config)
        if errors:
            return errors

        # 确保plugins键存在
        if "plugins" not in self.config_data:
            self.config_data["plugins"] = {}

        # 设置插件配置
        self.config_data["plugins"][plugin_name] = config

        # 保存配置
        self.save_config()

        return None

    def validate_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        验证插件配置

        Args:
            plugin_name: 插件名称
            config: 配置字典

        Returns:
            Optional[Dict[str, str]]: 验证错误字典，None表示没有错误
        """
        errors = {}

        # 这里可以添加具体的验证逻辑
        # 例如：检查必需字段、数据类型等

        # 云存储插件通用验证
        if not config.get("bucket_name"):
            errors["bucket_name"] = "存储桶名称不能为空"

        if not config.get("secret_id"):
            errors["secret_id"] = "Secret ID不能为空"

        if not config.get("secret_key"):
            errors["secret_key"] = "Secret Key不能为空"

        return errors if errors else None

    def get_plugin_default_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        从插件的配置定义文件中获取默认配置

        Args:
            plugin_name: 插件名称

        Returns:
            Dict[str, Any]: 默认配置字典
        """
        try:
            import os
            import importlib.util

            # 获取插件目录
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            plugin_dir = os.path.join(app_root, 'plugins-storage', plugin_name)
            config_file = os.path.join(plugin_dir, 'config.py')

            if os.path.exists(config_file):
                spec = importlib.util.spec_from_file_location(f"storage_config_{plugin_name}", config_file)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)

                # 合并全局和局部选项的默认值
                default_config = {}

                # 添加全局选项默认值
                if hasattr(config_module, 'global_options'):
                    for option_name, option_config in config_module.global_options.items():
                        # 确保option_config是字典类型
                        if isinstance(option_config, dict):
                            default_config[option_name] = option_config.get("default", "")

                # 添加局部选项默认值
                if hasattr(config_module, 'local_options'):
                    for option_name, option_config in config_module.local_options.items():
                        # 确保option_config是字典类型
                        if isinstance(option_config, dict):
                            default_config[option_name] = option_config.get("default", "")

                return default_config

            # 如果无法获取默认配置，返回空字典
            return {}

        except Exception as e:
            logger.error(f"获取插件 {plugin_name} 默认配置失败: {e}")
            return {}

    def reset_plugin_config(self, plugin_name: str) -> None:
        """
        重置指定插件的配置为默认值

        Args:
            plugin_name: 插件名称
        """
        if "plugins" in self.config_data:
            if plugin_name in self.config_data["plugins"]:
                del self.config_data["plugins"][plugin_name]
                self.save_config()

    def get_all_configs(self) -> Dict[str, Any]:
        """
        获取所有配置

        Returns:
            Dict[str, Any]: 所有配置字典
        """
        return self.config_data.copy()


# 全局云存储插件配置管理器实例
storage_config_manager = StoragePluginConfigManager()
