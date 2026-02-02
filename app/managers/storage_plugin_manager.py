"""
云存储插件管理器
负责加载、初始化和管理云存储插件
"""

import os
import importlib.util
from typing import Dict, Any, List
from app.core.storage.storage_plugin_interface import StoragePluginInterface, StorageResult, StorageErrorCode
from app.utils.logger import get_logger
from app.utils.app_path import get_plugin_dir

logger = get_logger('storage_plugin_manager')


class StoragePluginManager:
    """云存储插件管理器"""

    def __init__(self):
        self.plugins: Dict[str, StoragePluginInterface] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}

    def load_plugins(self, plugins_dir: str = None) -> List[str]:
        """
        从指定目录加载所有云存储插件

        Args:
            plugins_dir: 插件目录路径，默认为 app/plugins-storage/

        Returns:
            List[str]: 成功加载的插件名称列表
        """
        if plugins_dir is None:
            plugins_dir = get_plugin_dir('plugins-storage')

        if not os.path.exists(plugins_dir):
            logger.warning(f"云存储插件目录不存在: {plugins_dir}")
            return []

        loaded_plugins = []

        for plugin_dir_name in os.listdir(plugins_dir):
            plugin_dir = os.path.join(plugins_dir, plugin_dir_name)
            if os.path.isdir(plugin_dir):
                # 尝试从 __init__.py 导入
                init_file = os.path.join(plugin_dir, '__init__.py')
                if os.path.exists(init_file):
                    try:
                        # 使用更可靠的方式加载插件模块
                        # 不依赖相对导入，直接导入插件包
                        plugin_package = f"app.plugins-storage.{plugin_dir_name}"

                        try:
                            # 首先尝试直接导入
                            plugin_module = importlib.import_module(plugin_package)
                        except ImportError:
                            # 如果直接导入失败，尝试使用 spec 方式
                            spec = importlib.util.spec_from_file_location(
                                plugin_package,
                                init_file
                            )
                            plugin_module = importlib.util.module_from_spec(spec)

                            # 设置包路径，使相对导入能正确解析
                            spec.loader.exec_module(plugin_module)

                        # 查找插件类
                        plugin_class = None
                        for attr_name in dir(plugin_module):
                            if not attr_name.startswith('_'):
                                attr = getattr(plugin_module, attr_name)
                                if (isinstance(attr, type) and
                                    issubclass(attr, StoragePluginInterface) and
                                    attr != StoragePluginInterface):
                                    plugin_class = attr
                                    break

                        if plugin_class:
                            plugin_instance = plugin_class()
                            # 如果模块中有PluginInfo，设置到插件实例上
                            if hasattr(plugin_module, 'PluginInfo'):
                                plugin_instance.PluginInfo = plugin_module.PluginInfo
                            self.plugins[plugin_dir_name] = plugin_instance
                            loaded_plugins.append(plugin_dir_name)
                            logger.info(f"成功加载云存储插件: {plugin_dir_name}")
                        else:
                            logger.warning(f"在 {init_file} 中未找到云存储插件类")

                    except Exception as e:
                        logger.error(f"加载云存储插件 {plugin_dir_name} 失败: {e}")
                        import traceback
                        logger.error(traceback.format_exc())

        return loaded_plugins

    def get_available_plugins(self) -> List[str]:
        """
        获取所有可用的插件名称

        Returns:
            List[str]: 插件名称列表
        """
        return list(self.plugins.keys())

    def initialize_plugin(self, plugin_name: str, config: Dict[str, Any]) -> StorageResult:
        """
        初始化指定插件

        Args:
            plugin_name: 插件名称
            config: 插件配置

        Returns:
            StorageResult: 初始化结果
        """
        if plugin_name not in self.plugins:
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"插件 {plugin_name} 不存在",
                plugin_name=plugin_name
            )

        try:
            plugin = self.plugins[plugin_name]
            result = plugin.initialize(config)
            if result.is_success():
                self.plugin_configs[plugin_name] = config
            return result
        except Exception as e:
            logger.error(f"初始化插件 {plugin_name} 失败: {e}")
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"插件初始化失败: {str(e)}",
                plugin_name=plugin_name
            )

    def download_with_plugin(self, plugin_name: str, url: str, local_path: str, **kwargs) -> StorageResult:
        """
        使用指定插件下载文件

        Args:
            plugin_name: 插件名称
            url: 远程URL
            local_path: 本地保存路径
            **kwargs: 额外参数

        Returns:
            StorageResult: 下载结果
        """
        if plugin_name not in self.plugins:
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"插件 {plugin_name} 不存在",
                plugin_name=plugin_name
            )

        plugin = self.plugins[plugin_name]

        # 如果插件未初始化，尝试使用保存的配置初始化
        if not plugin.is_initialized and plugin_name in self.plugin_configs:
            init_result = self.initialize_plugin(plugin_name, self.plugin_configs[plugin_name])
            if not init_result.is_success():
                return init_result

        try:
            return plugin.download_file(url, local_path, **kwargs)
        except Exception as e:
            logger.error(f"使用插件 {plugin_name} 下载文件失败: {e}")
            return StorageResult(
                code=StorageErrorCode.DOWNLOAD_FAILED,
                message=f"下载失败: {str(e)}",
                plugin_name=plugin_name
            )

    def download_bytes_with_plugin(self, plugin_name: str, url: str, **kwargs) -> StorageResult:
        """
        使用指定插件下载文件为字节流

        Args:
            plugin_name: 插件名称
            url: 远程URL
            **kwargs: 额外参数

        Returns:
            StorageResult: 下载结果
        """
        if plugin_name not in self.plugins:
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"插件 {plugin_name} 不存在",
                plugin_name=plugin_name
            )

        plugin = self.plugins[plugin_name]

        # 如果插件未初始化，尝试使用保存的配置初始化
        if not plugin.is_initialized and plugin_name in self.plugin_configs:
            init_result = self.initialize_plugin(plugin_name, self.plugin_configs[plugin_name])
            if not init_result.is_success():
                return init_result

        try:
            return plugin.download_bytes(url, **kwargs)
        except Exception as e:
            logger.error(f"使用插件 {plugin_name} 下载字节流失败: {e}")
            return StorageResult(
                code=StorageErrorCode.DOWNLOAD_FAILED,
                message=f"下载失败: {str(e)}",
                plugin_name=plugin_name
            )

    def upload_with_plugin(self, plugin_name: str, local_path: str, remote_path: str, **kwargs) -> StorageResult:
        """
        使用指定插件上传文件

        Args:
            plugin_name: 插件名称
            local_path: 本地文件路径
            remote_path: 远程保存路径
            **kwargs: 额外参数

        Returns:
            StorageResult: 上传结果
        """
        if plugin_name not in self.plugins:
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"插件 {plugin_name} 不存在",
                plugin_name=plugin_name
            )

        plugin = self.plugins[plugin_name]

        # 如果插件未初始化，尝试使用保存的配置初始化
        if not plugin.is_initialized and plugin_name in self.plugin_configs:
            init_result = self.initialize_plugin(plugin_name, self.plugin_configs[plugin_name])
            if not init_result.is_success():
                return init_result

        try:
            return plugin.upload_file(local_path, remote_path, **kwargs)
        except Exception as e:
            logger.error(f"使用插件 {plugin_name} 上传文件失败: {e}")
            return StorageResult(
                code=StorageErrorCode.UPLOAD_FAILED,
                message=f"上传失败: {str(e)}",
                plugin_name=plugin_name
            )

    def delete_with_plugin(self, plugin_name: str, remote_path: str) -> StorageResult:
        """
        使用指定插件删除文件

        Args:
            plugin_name: 插件名称
            remote_path: 远程文件路径

        Returns:
            StorageResult: 删除结果
        """
        if plugin_name not in self.plugins:
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"插件 {plugin_name} 不存在",
                plugin_name=plugin_name
            )

        plugin = self.plugins[plugin_name]

        # 如果插件未初始化，尝试使用保存的配置初始化
        if not plugin.is_initialized and plugin_name in self.plugin_configs:
            init_result = self.initialize_plugin(plugin_name, self.plugin_configs[plugin_name])
            if not init_result.is_success():
                return init_result

        try:
            return plugin.delete_file(remote_path)
        except Exception as e:
            logger.error(f"使用插件 {plugin_name} 删除文件失败: {e}")
            return StorageResult(
                code=StorageErrorCode.DELETE_FAILED,
                message=f"删除失败: {str(e)}",
                plugin_name=plugin_name
            )

    def list_files_with_plugin(self, plugin_name: str, remote_path: str = "", **kwargs) -> StorageResult:
        """
        使用指定插件列出文件

        Args:
            plugin_name: 插件名称
            remote_path: 远程路径
            **kwargs: 额外参数

        Returns:
            StorageResult: 文件列表结果
        """
        if plugin_name not in self.plugins:
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"插件 {plugin_name} 不存在",
                plugin_name=plugin_name
            )

        plugin = self.plugins[plugin_name]

        # 如果插件未初始化，尝试使用保存的配置初始化
        if not plugin.is_initialized and plugin_name in self.plugin_configs:
            init_result = self.initialize_plugin(plugin_name, self.plugin_configs[plugin_name])
            if not init_result.is_success():
                return init_result

        try:
            return plugin.list_files(remote_path, **kwargs)
        except Exception as e:
            logger.error(f"使用插件 {plugin_name} 列出文件失败: {e}")
            return StorageResult(
                code=StorageErrorCode.DOWNLOAD_FAILED,
                message=f"列出文件失败: {str(e)}",
                plugin_name=plugin_name
            )

    def get_plugin_features(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件支持的特性

        Args:
            plugin_name: 插件名称

        Returns:
            Dict[str, Any]: 插件特性
        """
        if plugin_name not in self.plugins:
            return {}

        try:
            return self.plugins[plugin_name].get_supported_features()
        except Exception as e:
            logger.error(f"获取插件 {plugin_name} 特性失败: {e}")
            return {}

    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件信息，包括配置选项定义

        Args:
            plugin_name: 插件名称

        Returns:
            Dict[str, Any]: 插件信息
        """
        if plugin_name not in self.plugins:
            return {}

        try:
            plugin = self.plugins[plugin_name]
            # 检查插件是否包含PluginInfo属性
            if hasattr(plugin, 'PluginInfo'):
                return getattr(plugin, 'PluginInfo', {})
            else:
                # 如果插件没有PluginInfo，尝试从配置文件加载
                from app.utils.app_path import get_plugin_dir
                plugin_root_dir = get_plugin_dir('plugins-storage')
                plugin_dir = os.path.join(plugin_root_dir, plugin_name)
                config_file = os.path.join(plugin_dir, 'config.py')

                if os.path.exists(config_file):
                    spec = importlib.util.spec_from_file_location(f"storage_config_{plugin_name}", config_file)
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)

                    # 构建插件信息结构
                    plugin_info = {}
                    if hasattr(config_module, 'global_options'):
                        plugin_info['global_options'] = config_module.global_options
                    if hasattr(config_module, 'local_options'):
                        plugin_info['local_options'] = config_module.local_options

                    return plugin_info

            return {}
        except Exception as e:
            logger.error(f"获取插件 {plugin_name} 信息失败: {e}")
            return {}

    def get_plugin(self, plugin_name: str) -> StoragePluginInterface:
        """
        获取指定插件实例

        Args:
            plugin_name: 插件名称

        Returns:
            StoragePluginInterface: 插件实例
        """
        return self.plugins.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """
        获取所有已加载插件的名称列表

        Returns:
            List[str]: 插件名称列表
        """
        return list(self.plugins.keys())

    def cleanup_all(self) -> None:
        """清理所有插件资源"""
        for plugin_name, plugin in self.plugins.items():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"清理插件 {plugin_name} 资源失败: {e}")

        self.plugins.clear()
        self.plugin_configs.clear()

    def get_current_plugin_instance(self) -> StoragePluginInterface:
        """
        获取当前插件实例

        Returns:
            StoragePluginInterface: 当前插件实例
        """
        from app.config.storage_plugin_config import storage_config_manager
        current_plugin = storage_config_manager.get_current_plugin()
        return self.plugins.get(current_plugin)


# 全局云存储插件管理器实例
storage_plugin_manager = StoragePluginManager()
