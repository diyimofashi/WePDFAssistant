"""
条码插件配置管理系统
负责插件配置的加载、验证、保存和管理
"""

import os
import json
import threading
from typing import Dict, Any, List, Union
from app.utils.logger import get_logger

logger = get_logger('barcode_plugin_config')


class ConfigItemType:
    """配置项类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    LIST = "list"
    DICT = "dict"


class ConfigItem:
    """配置项定义"""
    
    def __init__(self, 
                 key: str,
                 title: str,
                 type_: str = ConfigItemType.STRING,
                 default: Any = None,
                 min_value: Union[int, float] = None,
                 max_value: Union[int, float] = None,
                 options_list: List[Any] = None,
                 required: bool = False,
                 description: str = ""):
        """
        初始化配置项
        
        Args:
            key: 配置项键名
            title: 配置项显示标题
            type_: 配置项类型
            default: 默认值
            min_value: 最小值（数值类型）
            max_value: 最大值（数值类型）
            options_list: 选项列表（枚举类型）
            required: 是否必需
            description: 配置项描述
        """
        self.key = key
        self.title = title
        self.type = type_
        self.default = default
        self.min_value = min_value
        self.max_value = max_value
        self.options_list = options_list or []
        self.required = required
        self.description = description
    
    def validate(self, value: Any) -> bool:
        """
        验证配置值是否有效
        
        Args:
            value: 待验证的值
            
        Returns:
            bool: 验证是否通过
        """
        # 检查必需项
        if self.required and (value is None or value == ""):
            return False
        
        # 检查类型
        if value is not None:
            if self.type == ConfigItemType.STRING:
                if not isinstance(value, str):
                    return False
            elif self.type == ConfigItemType.INTEGER:
                if not isinstance(value, int):
                    return False
                # 检查范围
                if self.min_value is not None and value < self.min_value:
                    return False
                if self.max_value is not None and value > self.max_value:
                    return False
            elif self.type == ConfigItemType.FLOAT:
                if not isinstance(value, (int, float)):
                    return False
                # 检查范围
                if self.min_value is not None and value < self.min_value:
                    return False
                if self.max_value is not None and value > self.max_value:
                    return False
            elif self.type == ConfigItemType.BOOLEAN:
                if not isinstance(value, bool):
                    return False
            elif self.type == ConfigItemType.ENUM:
                if value not in self.options_list:
                    return False
            elif self.type == ConfigItemType.LIST:
                if not isinstance(value, list):
                    return False
            elif self.type == ConfigItemType.DICT:
                if not isinstance(value, dict):
                    return False
        
        return True


class BarcodePluginConfigManager:
    """条码插件配置管理器"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，默认为应用配置目录下的barcode_plugins.json
        """
        if config_file is None:
            # 获取应用配置目录
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(app_dir, 'config', 'barcode_plugins.json')

        self.config_file = config_file
        self.global_config: Dict[str, Any] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.config_definitions: Dict[str, List[ConfigItem]] = {}
        self.lock = threading.RLock()
        
        # 加载现有配置
        self.load_config()
    
    def register_config_definition(self, plugin_name: str, config_items: List[ConfigItem]) -> None:
        """
        注册插件配置定义
        
        Args:
            plugin_name: 插件名称
            config_items: 配置项列表
        """
        with self.lock:
            self.config_definitions[plugin_name] = config_items
            logger.debug(f"注册插件配置定义: {plugin_name}")
    
    def validate_config(self, plugin_name: str, config: Dict[str, Any]) -> Dict[str, str]:
        """
        验证插件配置
        
        Args:
            plugin_name: 插件名称
            config: 配置参数字典
            
        Returns:
            Dict[str, str]: 验证结果，键为配置项键名，值为错误信息，空字典表示验证通过
        """
        errors = {}
        
        # 获取配置定义
        config_items = self.config_definitions.get(plugin_name, [])
        config_definitions = {item.key: item for item in config_items}
        
        # 验证每个配置项
        for key, value in config.items():
            config_item = config_definitions.get(key)
            if config_item:
                if not config_item.validate(value):
                    errors[key] = f"配置项 '{config_item.title}' 验证失败"
            # 对于未定义的配置项，我们不进行验证
        
        # 检查必需项
        for config_item in config_items:
            if config_item.required and config_item.key not in config:
                errors[config_item.key] = f"必需配置项 '{config_item.title}' 缺失"
        
        return errors
    
    def set_global_config(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        设置全局配置
        
        Args:
            config: 全局配置参数字典
            
        Returns:
            Dict[str, str]: 验证错误信息，空字典表示验证通过
        """
        with self.lock:
            # 这里可以添加全局配置的验证逻辑
            # 目前简化处理，直接保存
            self.global_config.update(config)
            self.save_config()
            logger.debug("全局配置已更新")
            return {}
    
    def get_global_config(self) -> Dict[str, Any]:
        """
        获取全局配置
        
        Returns:
            Dict[str, Any]: 全局配置参数字典
        """
        with self.lock:
            return self.global_config.copy()
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> Dict[str, str]:
        """
        设置插件配置

        Args:
            plugin_name: 插件名称
            config: 插件配置参数字典

        Returns:
            Dict[str, str]: 验证错误信息，空字典表示验证通过
        """
        with self.lock:
            # 验证配置
            errors = self.validate_config(plugin_name, config)
            if errors:
                logger.warning(f"插件配置验证失败: {plugin_name}, 错误: {errors}")
                return errors

            # 更新配置
            if plugin_name not in self.plugin_configs:
                self.plugin_configs[plugin_name] = {}
            self.plugin_configs[plugin_name].update(config)
            
            # 保存到文件
            self.save_config()
            logger.debug(f"插件配置已更新: {plugin_name}")
            return {}
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件配置
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 插件配置参数字典
        """
        with self.lock:
            return self.plugin_configs.get(plugin_name, {}).copy()
    
    def get_plugin_config_with_defaults(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件配置，包含默认值
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 插件配置参数字典，包含默认值
        """
        with self.lock:
            # 获取配置定义
            config_items = self.config_definitions.get(plugin_name, [])
            
            # 构建默认配置
            default_config = {item.key: item.default for item in config_items if item.default is not None}
            
            # 合并实际配置
            actual_config = self.plugin_configs.get(plugin_name, {})
            default_config.update(actual_config)
            
            return default_config
    
    def load_config(self) -> bool:
        """
        从文件加载配置
        
        Returns:
            bool: 是否加载成功
        """
        try:
            with self.lock:
                if not os.path.exists(self.config_file):
                    return True
                
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.global_config = data.get('global', {})
                self.plugin_configs = data.get('plugins', {})
                
                return True
                
        except Exception as e:
            logger.error(f"加载配置文件失败: {self.config_file}, 错误: {str(e)}")
            return False
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 是否保存成功
        """
        try:
            with self.lock:
                # 创建配置目录
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                
                # 准备保存的数据
                data = {
                    'global': self.global_config,
                    'plugins': self.plugin_configs
                }
                
                # 保存到文件
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.debug(f"配置已保存到文件: {self.config_file}")
                return True
                
        except Exception as e:
            logger.error(f"保存配置文件失败: {self.config_file}, 错误: {str(e)}")
            return False
    
    def reset_plugin_config(self, plugin_name: str) -> None:
        """
        重置插件配置为默认值
        
        Args:
            plugin_name: 插件名称
        """
        with self.lock:
            if plugin_name in self.plugin_configs:
                del self.plugin_configs[plugin_name]
                self.save_config()
    
    def reset_all_configs(self) -> None:
        """
        重置所有配置为默认值
        """
        with self.lock:
            self.global_config.clear()
            self.plugin_configs.clear()
            self.save_config()
    
    def get_current_plugin(self) -> str:
        """
        获取当前使用的插件
        
        Returns:
            str: 当前插件名称，如果没有设置则返回None
        """
        with self.lock:
            return self.global_config.get('current_plugin', None)
    
    def set_current_plugin(self, plugin_name: str) -> None:
        """
        设置当前使用的插件
        
        Args:
            plugin_name: 插件名称
        """
        with self.lock:
            self.global_config['current_plugin'] = plugin_name
            logger.debug(f"当前插件已设置为: {plugin_name}")


# 全局配置管理器实例
barcode_config_manager = BarcodePluginConfigManager()