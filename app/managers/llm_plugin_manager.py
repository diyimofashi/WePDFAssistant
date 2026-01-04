"""
LLM插件管理器 - 业务层
"""
import os
import importlib
from typing import Dict, List, Optional, Any
from pathlib import Path
from app.utils.logger import get_logger
from app.core.llm.llm_plugin_interface import LLMPluginInterface, LLMResult

logger = get_logger(__name__)


class LLMPluginManager:
    """LLM插件管理器"""

    def __init__(self, plugin_dir: str = None):
        """
        初始化插件管理器

        Args:
            plugin_dir: 插件目录路径
        """
        if plugin_dir is None:
            # 默认使用项目中的插件目录
            base_dir = Path(__file__).parent.parent
            plugin_dir = base_dir / "plugins_llm"

        self.plugin_dir = Path(plugin_dir)
        self._plugins: Dict[str, LLMPluginInterface] = {}
        self._plugin_info: Dict[str, Dict] = {}
        self._plugin_configs: Dict[str, Dict] = {}

    def discover_plugins(self) -> List[str]:
        """
        发现所有可用的插件

        Returns:
            插件名称列表
        """
        discovered = []

        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {self.plugin_dir}")
            return discovered

        for item in self.plugin_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_') and not item.name.startswith('.'):
                plugin_name = item.name
                init_file = item / "__init__.py"

                if init_file.exists():
                    discovered.append(plugin_name)
                    logger.debug(f"Discovered plugin: {plugin_name}")

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    def load_plugin(self, plugin_name: str, config: Optional[Dict] = None) -> bool:
        """
        加载插件

        Args:
            plugin_name: 插件名称
            config: 插件配置

        Returns:
            是否加载成功
        """
        if plugin_name in self._plugins:
            logger.warning(f"Plugin '{plugin_name}' already loaded")
            return True

        plugin_path = self.plugin_dir / plugin_name
        if not plugin_path.exists():
            logger.error(f"Plugin directory not found: {plugin_path}")
            return False

        try:
            # 动态导入插件模块
            module_path = f"app.plugins_llm.{plugin_name}"
            module = importlib.import_module(module_path)

            # 获取插件类(假设模块中有get_plugin函数返回插件实例)
            if hasattr(module, 'get_plugin'):
                plugin_instance = module.get_plugin()
            else:
                # 尝试从模块中查找LLMPluginInterface的子类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, LLMPluginInterface) and
                        attr is not LLMPluginInterface):
                        plugin_instance = attr()
                        break
                else:
                    logger.error(f"No plugin class found in {plugin_name}")
                    return False

            # 初始化插件
            init_config = config or {}
            init_result = plugin_instance.initialize(init_config)

            if not init_result.success:
                logger.error(f"Failed to initialize plugin '{plugin_name}': {init_result.error}")
                return False

            # 存储插件
            self._plugins[plugin_name] = plugin_instance
            self._plugin_info[plugin_name] = plugin_instance.get_plugin_info()
            self._plugin_configs[plugin_name] = init_config

            logger.info(f"Plugin loaded successfully: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error loading plugin '{plugin_name}': {e}", exc_info=True)
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否卸载成功
        """
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin '{plugin_name}' not loaded")
            return False

        try:
            # 清理插件资源
            self._plugins[plugin_name].cleanup()

            # 从管理器中移除
            del self._plugins[plugin_name]
            del self._plugin_info[plugin_name]
            del self._plugin_configs[plugin_name]

            logger.info(f"Plugin unloaded: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin '{plugin_name}': {e}", exc_info=True)
            return False

    def reload_plugin(self, plugin_name: str, config: Optional[Dict] = None) -> bool:
        """
        重新加载插件

        Args:
            plugin_name: 插件名称
            config: 插件配置

        Returns:
            是否重新加载成功
        """
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name, config)

    def get_plugin(self, plugin_name: str) -> Optional[LLMPluginInterface]:
        """
        获取插件实例

        Args:
            plugin_name: 插件名称

        Returns:
            插件实例或None
        """
        return self._plugins.get(plugin_name)

    def get_loaded_plugins(self) -> List[str]:
        """获取已加载的插件列表"""
        return list(self._plugins.keys())

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict]:
        """
        获取插件信息

        Args:
            plugin_name: 插件名称

        Returns:
            插件信息字典或None
        """
        return self._plugin_info.get(plugin_name)

    def get_all_plugin_info(self) -> Dict[str, Dict]:
        """获取所有插件信息"""
        return self._plugin_info.copy()

    def load_all_plugins(self, configs: Optional[Dict[str, Dict]] = None) -> Dict[str, bool]:
        """
        加载所有插件

        Args:
            configs: 插件配置字典 {plugin_name: config}

        Returns:
            加载结果字典 {plugin_name: success}
        """
        discovered = self.discover_plugins()
        configs = configs or {}
        results = {}

        for plugin_name in discovered:
            config = configs.get(plugin_name)
            results[plugin_name] = self.load_plugin(plugin_name, config)

        logger.info(f"Loaded {sum(results.values())}/{len(results)} plugins")
        return results

    def unload_all_plugins(self) -> None:
        """卸载所有插件"""
        plugin_names = list(self._plugins.keys())
        for plugin_name in plugin_names:
            self.unload_plugin(plugin_name)
        logger.info("All plugins unloaded")
