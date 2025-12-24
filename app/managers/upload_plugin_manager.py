"""
上传插件管理器
负责上传插件的加载、初始化、管理和卸载
"""

import os
import sys
import importlib.util
import traceback
from typing import Dict, List, Any, Optional
from app.core.upload.upload_plugin_interface import UploadPluginInterface, UploadResult, UploadErrorCode
from app.config.upload_plugin_config import upload_config_manager
from app.utils.logger import get_logger

logger = get_logger('upload_plugin_manager')


class UploadPluginManager:
    """上传插件管理器"""
    
    def __init__(self, plugin_dirs: List[str] = None):
        """
        初始化插件管理器
        
        Args:
            plugin_dirs: 插件目录列表，默认为应用的upload_plugins目录
        """
        self.plugins: Dict[str, UploadPluginInterface] = {}
        self.plugin_dirs = plugin_dirs or []
        
        # 使用配置管理器
        self.config_manager = upload_config_manager
        
        # 如果没有指定插件目录，使用默认目录
        if not self.plugin_dirs:
            # 获取应用根目录
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_plugin_dir = os.path.join(app_root, 'plugins-upload')
            self.plugin_dirs = [default_plugin_dir]
        
        logger.info(f"上传插件管理器初始化，插件目录: {self.plugin_dirs}")
    
    def discover_plugins(self) -> List[str]:
        """
        发现所有可用的插件目录
        
        Returns:
            List[str]: 插件目录路径列表
        """
        plugin_dirs = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                logger.warning(f"插件目录不存在: {plugin_dir}")
                continue
                
            # 遍历插件目录下的所有子目录
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                if os.path.isdir(item_path):
                    # 检查是否包含__init__.py文件
                    init_file = os.path.join(item_path, '__init__.py')
                    if os.path.exists(init_file):
                        plugin_dirs.append(item_path)
                        logger.debug(f"发现上传插件目录: {item_path}")
        
        return plugin_dirs
    
    def load_plugin(self, plugin_path: str) -> Optional[UploadPluginInterface]:
        """
        加载单个插件
        
        Args:
            plugin_path: 插件目录路径
            
        Returns:
            UploadPluginInterface: 插件实例，加载失败返回None
        """
        try:
            plugin_name = os.path.basename(plugin_path)
            init_file = os.path.join(plugin_path, '__init__.py')
            
            if not os.path.exists(init_file):
                logger.error(f"上传插件缺少__init__.py文件: {plugin_path}")
                return None
            
            # 动态导入插件
            spec = importlib.util.spec_from_file_location(f"upload_plugin_{plugin_name}", init_file)
            plugin_module = importlib.util.module_from_spec(spec)
            sys.modules[f"upload_plugin_{plugin_name}"] = plugin_module
            spec.loader.exec_module(plugin_module)
            
            # 获取插件信息
            if not hasattr(plugin_module, 'PluginInfo'):
                logger.error(f"上传插件缺少PluginInfo定义: {plugin_path}")
                return None
            
            plugin_info = plugin_module.PluginInfo
            api_class = plugin_info.get('api_class')
            
            if not api_class:
                logger.error(f"上传插件缺少api_class定义: {plugin_path}")
                return None
            
            # 创建插件实例
            # 检查是否需要传递参数给构造函数
            import inspect
            sig = inspect.signature(api_class.__init__)
            if len(sig.parameters) > 1:  # 除了self之外还有参数
                # 对于需要参数的插件，传递默认的全局配置
                default_config = {}
                plugin_instance = api_class(default_config)
            else:
                plugin_instance = api_class()
            
            # 设置插件基本信息
            if hasattr(plugin_instance, 'plugin_name'):
                plugin_instance.plugin_name = plugin_name
            
            # 保存插件引用和插件信息
            self.plugins[plugin_name] = plugin_instance
            # 将PluginInfo附加到插件实例上，以便后续访问
            plugin_instance.PluginInfo = plugin_info
            logger.info(f"成功加载上传插件: {plugin_name}")
            
            return plugin_instance
            
        except Exception as e:
            logger.error(f"加载上传插件失败: {plugin_path}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    def load_all_plugins(self) -> Dict[str, bool]:
        """
        加载所有插件
        
        Returns:
            Dict[str, bool]: 插件加载结果字典，键为插件名，值为是否加载成功
        """
        plugin_dirs = self.discover_plugins()
        results = {}
        
        for plugin_dir in plugin_dirs:
            plugin_name = os.path.basename(plugin_dir)
            plugin_instance = self.load_plugin(plugin_dir)
            results[plugin_name] = plugin_instance is not None
            
            if plugin_instance:
                logger.info(f"上传插件加载成功: {plugin_name}")
            else:
                logger.error(f"上传插件加载失败: {plugin_name}")
        
        return results
    
    def initialize_plugin(self, plugin_name: str, config: Dict[str, Any] = None) -> UploadResult:
        """
        初始化指定插件
        
        Args:
            plugin_name: 插件名称
            config: 插件配置参数
            
        Returns:
            UploadResult: 初始化结果
        """
        if plugin_name not in self.plugins:
            return UploadResult(
                code=UploadErrorCode.INIT_ERROR,
                message=f"上传插件未加载: {plugin_name}"
            )
        
        try:
            plugin = self.plugins[plugin_name]
            config = config or self.config_manager.get_plugin_config(plugin_name)
            
            result = plugin.initialize(config)
            result.plugin_name = plugin_name
            
            if result.is_success():
                logger.info(f"上传插件初始化成功: {plugin_name}")
            else:
                logger.error(f"上传插件初始化失败: {plugin_name}, 错误: {result.message}")
            
            return result
            
        except Exception as e:
            logger.error(f"初始化上传插件时发生异常: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return UploadResult(
                code=UploadErrorCode.INIT_ERROR,
                message=f"初始化上传插件时发生异常: {str(e)}"
            )
    
    def initialize_all_plugins(self, configs: Dict[str, Dict[str, Any]] = None) -> Dict[str, UploadResult]:
        """
        初始化所有已加载的插件
        
        Args:
            configs: 插件配置字典，键为插件名，值为配置参数
            
        Returns:
            Dict[str, UploadResult]: 各插件初始化结果
        """
        results = {}
        configs = configs or {}
        
        for plugin_name in self.plugins:
            config = configs.get(plugin_name, self.config_manager.get_plugin_config(plugin_name))
            results[plugin_name] = self.initialize_plugin(plugin_name, config)
        
        return results
    
    def upload_with_plugin(self, plugin_name: str, file_path: str = None, 
                          file_bytes: bytes = None, remote_path: str = "", 
                          original_filename: str = "", **kwargs) -> UploadResult:
        """
        使用指定插件进行文件上传
        
        Args:
            plugin_name: 插件名称
            file_path: 本地文件路径
            file_bytes: 文件字节流
            remote_path: 远程路径
            original_filename: 原始文件名
            **kwargs: 额外参数
            
        Returns:
            UploadResult: 上传结果
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return UploadResult(
                code=UploadErrorCode.INIT_ERROR,
                message=f"上传插件未加载或不存在: {plugin_name}"
            )
        
        try:
            # 根据输入类型调用相应的上传方法
            if file_path:
                result = plugin.upload_file(file_path, remote_path, **kwargs)
            elif file_bytes:
                result = plugin.upload_bytes(file_bytes, remote_path, original_filename, **kwargs)
            else:
                return UploadResult(
                    code=UploadErrorCode.INVALID_CONFIG,
                    message="未提供有效的上传数据"
                )
            
            result.plugin_name = plugin_name
            return result
            
        except Exception as e:
            logger.error(f"使用上传插件进行上传时发生异常: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"上传异常: {str(e)}"
            )
    
    def get_plugin(self, plugin_name: str) -> Optional[UploadPluginInterface]:
        """
        获取指定插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            UploadPluginInterface: 插件实例，不存在返回None
        """
        return self.plugins.get(plugin_name)
    
    def list_plugins(self) -> List[str]:
        """
        获取所有已加载插件的名称列表
        
        Returns:
            List[str]: 插件名称列表
        """
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件详细信息
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 插件信息字典
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return {"error": f"插件未加载: {plugin_name}"}
        
        return plugin.get_plugin_info()
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """
        设置插件配置
        
        Args:
            plugin_name: 插件名称
            config: 配置参数字典
        """
        self.config_manager.set_plugin_config(plugin_name, config)
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件配置
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 插件配置参数
        """
        return self.config_manager.get_plugin_config(plugin_name)


# 全局上传插件管理器实例
upload_plugin_manager = UploadPluginManager()