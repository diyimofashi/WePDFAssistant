"""
条码插件管理器
负责插件的加载、初始化、管理和卸载
"""

import os
import sys
import importlib.util
import traceback
import inspect
from typing import Dict, List, Any, Optional
from app.core.barcode.barcode_plugin_interface import BarcodePluginInterface, BarcodeResult, BarcodeErrorCode
from app.utils.logger import get_logger
from app.config.barcode_plugin_config import barcode_config_manager


logger = get_logger('barcode_plugin_manager')


class BarcodePluginManager:
    """条码插件管理器"""
    
    def __init__(self, plugin_dirs: List[str] = None):
        """
        初始化插件管理器
        
        Args:
            plugin_dirs: 插件目录列表，默认为应用的plugins-barcode目录
        """
        self.plugins: Dict[str, BarcodePluginInterface] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.plugin_dirs = plugin_dirs or []
        
        # 如果没有指定插件目录，使用默认目录
        if not self.plugin_dirs:
            # 获取应用根目录
            app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            default_plugin_dir = os.path.join(app_root, 'app', 'plugins-barcode')
            self.plugin_dirs = [default_plugin_dir]
        
        logger.info(f"条码插件管理器初始化，插件目录: {self.plugin_dirs}")
    
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
    
    def load_plugin(self, plugin_path: str) -> Optional[BarcodePluginInterface]:
        """
        加载单个插件
        
        Args:
            plugin_path: 插件目录路径
            
        Returns:
            BarcodePluginInterface: 插件实例，加载失败返回None
        """
        try:
            plugin_name = os.path.basename(plugin_path)
            init_file = os.path.join(plugin_path, '__init__.py')
            
            if not os.path.exists(init_file):
                error_msg = f"插件缺少__init__.py文件: {plugin_path}"
                logger.error(error_msg)
                return None
            
            # 动态导入插件
            spec = importlib.util.spec_from_file_location(f"barcode_plugin_{plugin_name}", init_file)
            plugin_module = importlib.util.module_from_spec(spec)
            sys.modules[f"barcode_plugin_{plugin_name}"] = plugin_module
            spec.loader.exec_module(plugin_module)
            
            # 获取插件信息
            if not hasattr(plugin_module, 'PluginInfo'):
                error_msg = f"插件缺少PluginInfo定义: {plugin_path}"
                logger.error(error_msg)
                return None
            
            plugin_info = plugin_module.PluginInfo
            api_class_name = plugin_info.get('api_class')
            
            if not api_class_name:
                error_msg = f"插件缺少api_class定义: {plugin_path}"
                logger.error(error_msg)
                return None
            
            # 从模块中获取实际的类
            if hasattr(plugin_module, api_class_name):
                api_class = getattr(plugin_module, api_class_name)
            else:
                error_msg = f"插件模块中找不到类 {api_class_name}: {plugin_path}"
                logger.error(error_msg)
                return None
            
            # 创建插件实例
            # 检查是否需要传递参数给构造函数
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
            
            # 从插件的配置文件中加载配置定义
            self.register_plugin_config_definitions(plugin_name, plugin_path)
            
            logger.info(f"成功加载插件: {plugin_name}")
            
            return plugin_instance
            
        except Exception as e:
            logger.error(f"加载插件失败: {plugin_path}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    def register_plugin_config_definitions(self, plugin_name: str, plugin_path: str) -> None:
        """
        注册插件的配置定义
        
        Args:
            plugin_name: 插件名称
            plugin_path: 插件路径
        """
        try:
            config_path = os.path.join(plugin_path, 'config.py')
            if os.path.exists(config_path):
                # 动态导入配置模块
                spec = importlib.util.spec_from_file_location(f"plugin_config_{plugin_name}", config_path)
                config_module = importlib.util.module_from_spec(spec)
                sys.modules[f"plugin_config_{plugin_name}"] = config_module
                spec.loader.exec_module(config_module)
                
                # 检查是否存在配置定义
                if hasattr(config_module, 'PLUGIN_CONFIG_DEFINITIONS'):
                    config_definitions = config_module.PLUGIN_CONFIG_DEFINITIONS
                    # 注册到配置管理器
                    barcode_config_manager.register_config_definition(plugin_name, config_definitions)
                    logger.info(f"成功注册插件配置定义: {plugin_name}")
                else:
                    logger.info(f"插件无配置定义: {plugin_name}")
            else:
                logger.info(f"插件无配置文件: {plugin_name}")
        
        except Exception as e:
            logger.error(f"注册插件配置定义失败: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
    
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
    
    def initialize_plugin(self, plugin_name: str, config: Dict[str, Any] = None) -> BarcodeResult:
        """
        初始化指定插件
        
        Args:
            plugin_name: 插件名称
            config: 插件配置参数
            
        Returns:
            BarcodeResult: 初始化结果
        """
        if plugin_name not in self.plugins:
            error_result = BarcodeResult(
                code=BarcodeErrorCode.INIT_ERROR,
                message=f"插件未加载: {plugin_name}"
            )
            error_result.plugin_name = plugin_name
            return error_result
        
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
            error_result = BarcodeResult(
                code=BarcodeErrorCode.UNKNOWN_ERROR,
                message=f"初始化插件时发生异常: {str(e)}"
            )
            error_result.plugin_name = plugin_name
            return error_result
    
    def initialize_all_plugins(self, configs: Dict[str, Dict[str, Any]] = None) -> Dict[str, BarcodeResult]:
        """
        初始化所有已加载的插件
        
        Args:
            configs: 插件配置字典，键为插件名，值为配置参数
            
        Returns:
            Dict[str, BarcodeResult]: 各插件初始化结果
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
    
    def get_plugin(self, plugin_name: str) -> Optional[BarcodePluginInterface]:
        """
        获取指定插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            BarcodePluginInterface: 插件实例，不存在返回None
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
    
    def detect_with_plugin(self, plugin_name: str, file_path: str = None, 
                           image_bytes: bytes = None, base64_string: str = None) -> BarcodeResult:
        """
        使用指定插件进行条码检测
        
        Args:
            plugin_name: 插件名称
            file_path: 图片文件路径
            image_bytes: 图片字节流
            base64_string: Base64编码的图片字符串
            
        Returns:
            BarcodeResult: 检测结果
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            error_result = BarcodeResult(
                code=BarcodeErrorCode.INIT_ERROR,
                message=f"插件未加载或不存在: {plugin_name}"
            )
            error_result.plugin_name = plugin_name
            return error_result
        
        try:
            # 根据输入类型调用相应的检测方法
            if file_path:
                result = plugin.detect_from_file(file_path)
            elif image_bytes:
                result = plugin.detect_from_bytes(image_bytes)
            elif base64_string:
                result = plugin.detect_from_base64(base64_string)
            else:
                error_result = BarcodeResult(
                    code=BarcodeErrorCode.INVALID_FORMAT,
                    message="未提供有效的输入数据"
                )
                error_result.plugin_name = plugin_name
                return error_result
            
            result.plugin_name = plugin_name
            
            return result
            
        except Exception as e:
            logger.error(f"使用插件进行条码检测时发生异常: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            error_result = BarcodeResult(
                code=BarcodeErrorCode.UNKNOWN_ERROR,
                message=f"使用插件进行条码检测时发生异常: {str(e)}"
            )
            error_result.plugin_name = plugin_name
            return error_result
    
    def split_document_with_plugin(self, plugin_name: str, doc: 'fitz.Document', output_dir: str, config: Dict[str, Any] = None, progress_callback=None) -> Dict[str, Any]:
        """
        使用指定插件拆分文档
        
        Args:
            plugin_name: 插件名称
            doc: PyMuPDF文档对象
            output_dir: 输出目录
            config: 拆分配置参数
            progress_callback: 进度回调函数，接收(current, total, message)参数
            
        Returns:
            Dict[str, Any]: 拆分结果
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {
                "success": False,
                "message": f"插件未加载或不存在: {plugin_name}",
                "files_created": [],
                "barcodes_found": 0,
                "pages_processed": 0
            }
        
        try:
            # 确保插件已初始化
            if not plugin.is_initialized:
                plugin_config = self.get_plugin_config(plugin_name)
                init_result = self.initialize_plugin(plugin_name, plugin_config)
                if not init_result.is_success():
                    return {
                        "success": False,
                        "message": f"插件初始化失败: {init_result.message}",
                        "files_created": [],
                        "barcodes_found": 0,
                        "pages_processed": 0
                    }
            
            # 检查插件是否支持进度回调
            if hasattr(plugin, 'split_document_by_barcodes_with_progress') and progress_callback:
                # 如果插件支持带进度的拆分方法
                result = plugin.split_document_by_barcodes_with_progress(doc, output_dir, config, progress_callback)
            else:
                # 否则调用常规拆分方法
                result = plugin.split_document_by_barcodes(doc, output_dir, config)
            
            return result
            
        except Exception as e:
            logger.error(f"使用插件拆分文档时发生异常: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return {
                "success": False,
                "message": f"使用插件拆分文档时发生异常: {str(e)}",
                "files_created": [],
                "barcodes_found": 0,
                "pages_processed": 0
            }
    
    def preview_split_with_plugin(self, plugin_name: str, doc: 'fitz.Document', config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        使用指定插件预览拆分结果
        
        Args:
            plugin_name: 插件名称
            doc: PyMuPDF文档对象
            config: 拆分配置参数
            
        Returns:
            Dict[str, Any]: 预览结果
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {
                "error": f"插件未加载或不存在: {plugin_name}"
            }
        
        try:
            # 确保插件已初始化
            if not plugin.is_initialized:
                plugin_config = self.get_plugin_config(plugin_name)
                init_result = self.initialize_plugin(plugin_name, plugin_config)
                if not init_result.is_success():
                    return {
                        "error": f"插件初始化失败: {init_result.message}"
                    }
            
            # 预览拆分结果
            result = plugin.preview_split_result(doc, config)
            
            return result
            
        except Exception as e:
            logger.error(f"使用插件预览拆分结果时发生异常: {plugin_name}, 错误: {str(e)}")
            logger.debug(traceback.format_exc())
            return {
                "error": f"使用插件预览拆分结果时发生异常: {str(e)}"
            }
    
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
barcode_plugin_manager = BarcodePluginManager()