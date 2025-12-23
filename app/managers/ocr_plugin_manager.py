"""
OCR插件管理器
负责插件的加载、初始化、管理和卸载
"""

import os
import sys
import importlib.util
import traceback
from typing import Dict, List, Any, Optional
from app.core.ocr.ocr_plugin_interface import OCRPluginInterface, OCRResult, OCRErrorCode
from app.utils.logger import get_logger

logger = get_logger('ocr_plugin_manager')


class OCRPluginManager:
    """OCR插件管理器"""
    
    def __init__(self, plugin_dirs: List[str] = None):
        """
        初始化插件管理器
        
        Args:
            plugin_dirs: 插件目录列表，默认为应用的plugins目录
        """
        self.plugins: Dict[str, OCRPluginInterface] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.plugin_dirs = plugin_dirs or []
        
        # 如果没有指定插件目录，使用默认目录
        if not self.plugin_dirs:
            # 获取应用根目录
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_plugin_dir = os.path.join(app_root, 'plugins')
            self.plugin_dirs = [default_plugin_dir]
        
        logger.info(f"OCR插件管理器初始化，插件目录: {self.plugin_dirs}")
    
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
                        logger.debug(f"发现插件目录: {item_path}")
        
        return plugin_dirs
    
    def load_plugin(self, plugin_path: str) -> Optional[OCRPluginInterface]:
        """
        加载单个插件
        
        Args:
            plugin_path: 插件目录路径
            
        Returns:
            OCRPluginInterface: 插件实例，加载失败返回None
        """
        try:
            plugin_name = os.path.basename(plugin_path)
            init_file = os.path.join(plugin_path, '__init__.py')
            
            if not os.path.exists(init_file):
                logger.error(f"插件缺少__init__.py文件: {plugin_path}")
                return None
            
            # 动态导入插件
            spec = importlib.util.spec_from_file_location(f"ocr_plugin_{plugin_name}", init_file)
            plugin_module = importlib.util.module_from_spec(spec)
            sys.modules[f"ocr_plugin_{plugin_name}"] = plugin_module
            spec.loader.exec_module(plugin_module)
            
            # 获取插件信息
            if not hasattr(plugin_module, 'PluginInfo'):
                logger.error(f"插件缺少PluginInfo定义: {plugin_path}")
                return None
            
            plugin_info = plugin_module.PluginInfo
            api_class = plugin_info.get('api_class')
            
            if not api_class:
                logger.error(f"插件缺少api_class定义: {plugin_path}")
                return None
            
            # 创建插件实例
            # 检查是否需要传递参数给构造函数
            import inspect
            sig = inspect.signature(api_class.__init__)
            if len(sig.parameters) > 1:  # 除了self之外还有参数
                # 对于需要参数的插件，传递默认的全局配置
                default_config = {
                    "numThread": 4  # 默认线程数
                }
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
            logger.info(f"成功加载插件: {plugin_name}")
            
            return plugin_instance
            
        except Exception as e:
            logger.error(f"加载插件失败: {plugin_path}, 错误: {str(e)}")
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
                logger.info(f"插件加载成功: {plugin_name}")
            else:
                logger.error(f"插件加载失败: {plugin_name}")
        
        return results
    
    def initialize_plugin(self, plugin_name: str, config: Dict[str, Any] = None) -> OCRResult:
        """
        初始化指定插件
        
        Args:
            plugin_name: 插件名称
            config: 插件配置参数
            
        Returns:
            OCRResult: 初始化结果
        """
        if plugin_name not in self.plugins:
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message=f"插件未加载: {plugin_name}"
            )
        
        try:
            plugin = self.plugins[plugin_name]
            config = config or self.plugin_configs.get(plugin_name, {})
            
            result = plugin.initialize(config)
            result.plugin_name = plugin_name
            
            if result.is_success():
                logger.info(f"插件初始化成功: {plugin_name}")
            else:
                logger.error(f"插件初始化失败: {plugin_name}, 错误: {result.message}")
            
            return result
            
        except Exception as e:
            logger.error(f"初始化插件时发生异常: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message=f"初始化插件时发生异常: {str(e)}"
            )
    
    def initialize_all_plugins(self, configs: Dict[str, Dict[str, Any]] = None) -> Dict[str, OCRResult]:
        """
        初始化所有已加载的插件
        
        Args:
            configs: 插件配置字典，键为插件名，值为配置参数
            
        Returns:
            Dict[str, OCRResult]: 各插件初始化结果
        """
        results = {}
        configs = configs or {}
        
        for plugin_name in self.plugins:
            config = configs.get(plugin_name, self.plugin_configs.get(plugin_name, {}))
            results[plugin_name] = self.initialize_plugin(plugin_name, config)
        
        return results
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载指定插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 是否卸载成功
        """
        if plugin_name not in self.plugins:
            logger.warning(f"尝试卸载未加载的插件: {plugin_name}")
            return False
        
        try:
            plugin = self.plugins[plugin_name]
            
            # 清理资源
            plugin.cleanup()
            
            # 从管理器中移除
            del self.plugins[plugin_name]
            
            logger.info(f"插件卸载成功: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"卸载插件时发生异常: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def unload_all_plugins(self) -> Dict[str, bool]:
        """
        卸载所有插件
        
        Returns:
            Dict[str, bool]: 各插件卸载结果
        """
        results = {}
        
        # 创建插件名列表副本，因为在迭代过程中会修改原字典
        plugin_names = list(self.plugins.keys())
        
        for plugin_name in plugin_names:
            results[plugin_name] = self.unload_plugin(plugin_name)
        
        return results
    
    def get_plugin(self, plugin_name: str) -> Optional[OCRPluginInterface]:
        """
        获取指定插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            OCRPluginInterface: 插件实例，不存在返回None
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
    
    def recognize_with_plugin(self, plugin_name: str, file_path: str = None, 
                            image_bytes: bytes = None, base64_string: str = None,
                            language: str = "auto") -> OCRResult:
        """
        使用指定插件进行OCR识别
        
        Args:
            plugin_name: 插件名称
            file_path: 图片文件路径
            image_bytes: 图片字节流
            base64_string: Base64编码的图片字符串
            language: 识别语言
            
        Returns:
            OCRResult: 识别结果
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message=f"插件未加载或不存在: {plugin_name}"
            )
        
        try:
            # 根据输入类型调用相应的识别方法
            if file_path:
                result = plugin.recognize_from_file(file_path, language)
            elif image_bytes:
                result = plugin.recognize_from_bytes(image_bytes, language)
            elif base64_string:
                result = plugin.recognize_from_base64(base64_string, language)
            else:
                return OCRResult(
                    code=OCRErrorCode.INVALID_FORMAT,
                    message="未提供有效的输入数据"
                )
            
            result.plugin_name = plugin_name
            return result
            
        except Exception as e:
            logger.error(f"使用插件进行OCR识别时发生异常: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"OCR识别异常: {str(e)}"
            )
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """
        设置插件配置
        
        Args:
            plugin_name: 插件名称
            config: 配置参数字典
        """
        self.plugin_configs[plugin_name] = config
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件配置
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 插件配置参数
        """
        return self.plugin_configs.get(plugin_name, {})


# 全局插件管理器实例
ocr_plugin_manager = OCRPluginManager()