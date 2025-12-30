"""
条码系统与现有应用集成模块
提供简单的API接口调用插件功能
"""

import os
import threading
from typing import Dict, List, Any, Optional
from app.managers.barcode_plugin_manager import barcode_plugin_manager
from app.config.barcode_plugin_config import barcode_config_manager
from .barcode_plugin_interface import BarcodeResult, BarcodeErrorCode
from app.utils.logger import get_logger

logger = get_logger('barcode_integration')


class BarcodeIntegration:
    """条码系统集成类"""
    
    def __init__(self):
        """初始化条码集成"""
        self.plugin_manager = barcode_plugin_manager
        self.config_manager = barcode_config_manager
        self.performance_stats = {}
        
        logger.info("条码系统集成模块初始化")
    
    def initialize_system(self, plugin_configs: Dict[str, Dict[str, Any]] = None) -> Dict[str, bool]:
        """
        初始化条码系统
        
        Args:
            plugin_configs: 插件配置字典
            
        Returns:
            Dict[str, bool]: 各插件初始化结果
        """
        try:
            # 加载所有插件
            load_results = self.plugin_manager.load_all_plugins()
            logger.info(f"插件加载结果: {load_results}")
            
            # 初始化所有插件
            init_results = self.plugin_manager.initialize_all_plugins(plugin_configs)
            
            # 转换为布尔值结果
            results = {}
            for plugin_name, result in init_results.items():
                results[plugin_name] = result.is_success()
                if not result.is_success():
                    logger.error(f"插件初始化失败: {plugin_name}, 错误: {result.message}")
            
            logger.info(f"条码系统初始化完成，结果: {results}")
            return results
            
        except Exception as e:
            logger.error(f"初始化条码系统时发生异常: {str(e)}")
            logger.debug(f"异常详情: {str(e)}")
            return {}
    
    def detect_from_file(self, file_path: str, plugin_name: str = None) -> BarcodeResult:
        """
        从文件路径检测条码
        
        Args:
            file_path: 图片文件路径
            plugin_name: 使用的插件名称，如果为None则使用当前配置的插件
            
        Returns:
            BarcodeResult: 检测结果
        """
        try:
            # 如果未指定插件，则使用当前配置的插件
            if not plugin_name:
                plugin_name = self.config_manager.get_current_plugin()
                if not plugin_name:
                    # 如果没有设置当前插件，使用第一个可用插件
                    available_plugins = self.plugin_manager.list_plugins()
                    if available_plugins:
                        plugin_name = available_plugins[0]
                    else:
                        return BarcodeResult(
                            code=BarcodeErrorCode.INIT_ERROR,
                            message="没有可用的条码插件"
                        )
            
            # 检查插件是否已加载
            if plugin_name not in self.plugin_manager.plugins:
                return BarcodeResult(
                    code=BarcodeErrorCode.INIT_ERROR,
                    message=f"插件未加载: {plugin_name}"
                )
            
            # 获取插件配置
            plugin_config = self.config_manager.get_plugin_config(plugin_name)
            
            # 初始化插件（如果尚未初始化）
            plugin = self.plugin_manager.plugins[plugin_name]
            if not plugin.is_initialized:
                init_result = self.plugin_manager.initialize_plugin(plugin_name, plugin_config)
                if not init_result.is_success():
                    return init_result
            
            # 执行检测
            result = self.plugin_manager.detect_with_plugin(plugin_name, file_path=file_path)
            
            return result
            
        except Exception as e:
            logger.error(f"从文件检测条码时发生异常: {str(e)}")
            return BarcodeResult(
                code=BarcodeErrorCode.UNKNOWN_ERROR,
                message=f"检测条码时发生异常: {str(e)}"
            )
    
    def detect_from_bytes(self, image_bytes: bytes, plugin_name: str = None) -> BarcodeResult:
        """
        从字节流检测条码
        
        Args:
            image_bytes: 图片字节流
            plugin_name: 使用的插件名称，如果为None则使用当前配置的插件
            
        Returns:
            BarcodeResult: 检测结果
        """
        try:
            # 如果未指定插件，则使用当前配置的插件
            if not plugin_name:
                plugin_name = self.config_manager.get_current_plugin()
                if not plugin_name:
                    # 如果没有设置当前插件，使用第一个可用插件
                    available_plugins = self.plugin_manager.list_plugins()
                    if available_plugins:
                        plugin_name = available_plugins[0]
                    else:
                        return BarcodeResult(
                            code=BarcodeErrorCode.INIT_ERROR,
                            message="没有可用的条码插件"
                        )
            
            # 检查插件是否已加载
            if plugin_name not in self.plugin_manager.plugins:
                return BarcodeResult(
                    code=BarcodeErrorCode.INIT_ERROR,
                    message=f"插件未加载: {plugin_name}"
                )
            
            # 获取插件配置
            plugin_config = self.config_manager.get_plugin_config(plugin_name)
            
            # 初始化插件（如果尚未初始化）
            plugin = self.plugin_manager.plugins[plugin_name]
            if not plugin.is_initialized:
                init_result = self.plugin_manager.initialize_plugin(plugin_name, plugin_config)
                if not init_result.is_success():
                    return init_result
            
            # 执行检测
            result = self.plugin_manager.detect_with_plugin(plugin_name, image_bytes=image_bytes)
            
            return result
            
        except Exception as e:
            logger.error(f"从字节流检测条码时发生异常: {str(e)}")
            return BarcodeResult(
                code=BarcodeErrorCode.UNKNOWN_ERROR,
                message=f"检测条码时发生异常: {str(e)}"
            )
    
    def detect_from_base64(self, base64_string: str, plugin_name: str = None) -> BarcodeResult:
        """
        从Base64字符串检测条码
        
        Args:
            base64_string: Base64编码的图片字符串
            plugin_name: 使用的插件名称，如果为None则使用当前配置的插件
            
        Returns:
            BarcodeResult: 检测结果
        """
        try:
            # 如果未指定插件，则使用当前配置的插件
            if not plugin_name:
                plugin_name = self.config_manager.get_current_plugin()
                if not plugin_name:
                    # 如果没有设置当前插件，使用第一个可用插件
                    available_plugins = self.plugin_manager.list_plugins()
                    if available_plugins:
                        plugin_name = available_plugins[0]
                    else:
                        return BarcodeResult(
                            code=BarcodeErrorCode.INIT_ERROR,
                            message="没有可用的条码插件"
                        )
            
            # 检查插件是否已加载
            if plugin_name not in self.plugin_manager.plugins:
                return BarcodeResult(
                    code=BarcodeErrorCode.INIT_ERROR,
                    message=f"插件未加载: {plugin_name}"
                )
            
            # 获取插件配置
            plugin_config = self.config_manager.get_plugin_config(plugin_name)
            
            # 初始化插件（如果尚未初始化）
            plugin = self.plugin_manager.plugins[plugin_name]
            if not plugin.is_initialized:
                init_result = self.plugin_manager.initialize_plugin(plugin_name, plugin_config)
                if not init_result.is_success():
                    return init_result
            
            # 执行检测
            result = self.plugin_manager.detect_with_plugin(plugin_name, base64_string=base64_string)
            
            return result
            
        except Exception as e:
            logger.error(f"从Base64字符串检测条码时发生异常: {str(e)}")
            return BarcodeResult(
                code=BarcodeErrorCode.UNKNOWN_ERROR,
                message=f"检测条码时发生异常: {str(e)}"
            )
    
    def get_available_plugins(self) -> List[str]:
        """
        获取可用的插件列表
        
        Returns:
            List[str]: 可用插件名称列表
        """
        return self.plugin_manager.list_plugins()
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件信息
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 插件信息
        """
        return self.plugin_manager.get_plugin_info(plugin_name)
    
    def get_supported_types(self, plugin_name: str = None) -> List[str]:
        """
        获取支持的条码类型
        
        Args:
            plugin_name: 插件名称，如果为None则使用当前配置的插件
            
        Returns:
            List[str]: 支持的条码类型列表
        """
        try:
            if not plugin_name:
                plugin_name = self.config_manager.get_current_plugin()
                if not plugin_name:
                    # 如果没有设置当前插件，使用第一个可用插件
                    available_plugins = self.plugin_manager.list_plugins()
                    if available_plugins:
                        plugin_name = available_plugins[0]
                    else:
                        return []
            
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if not plugin:
                return []
            
            return plugin.get_supported_types()
            
        except Exception as e:
            logger.error(f"获取支持的条码类型时发生异常: {str(e)}")
            return []
    
    def split_document_by_barcodes(self, 
                                 doc: 'fitz.Document', 
                                 output_dir: str, 
                                 plugin_name: str = None, 
                                 config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        使用插件拆分文档
        
        Args:
            doc: PyMuPDF文档对象
            output_dir: 输出目录
            plugin_name: 插件名称，如果为None则使用当前配置的插件
            config: 拆分配置参数
            
        Returns:
            Dict[str, Any]: 拆分结果
        """
        try:
            if not plugin_name:
                plugin_name = self.config_manager.get_current_plugin()
                if not plugin_name:
                    # 如果没有设置当前插件，使用第一个可用插件
                    available_plugins = self.plugin_manager.list_plugins()
                    if available_plugins:
                        plugin_name = available_plugins[0]
                    else:
                        return {
                            "success": False,
                            "message": "没有可用的条码插件",
                            "files_created": [],
                            "barcodes_found": 0,
                            "pages_processed": 0
                        }
            
            # 检查插件是否已加载
            if plugin_name not in self.plugin_manager.plugins:
                return {
                    "success": False,
                    "message": f"插件未加载: {plugin_name}",
                    "files_created": [],
                    "barcodes_found": 0,
                    "pages_processed": 0
                }
            
            # 获取插件配置
            plugin_config = self.config_manager.get_plugin_config(plugin_name)
            
            # 初始化插件（如果尚未初始化）
            plugin = self.plugin_manager.plugins[plugin_name]
            if not plugin.is_initialized:
                init_result = self.plugin_manager.initialize_plugin(plugin_name, plugin_config)
                if not init_result.is_success():
                    return {
                        "success": False,
                        "message": f"插件初始化失败: {init_result.message}",
                        "files_created": [],
                        "barcodes_found": 0,
                        "pages_processed": 0
                    }
            
            # 执行文档拆分
            result = self.plugin_manager.split_document_with_plugin(plugin_name, doc, output_dir, config)
            
            return result
            
        except Exception as e:
            logger.error(f"拆分文档时发生异常: {str(e)}")
            return {
                "success": False,
                "message": f"拆分文档时发生异常: {str(e)}",
                "files_created": [],
                "barcodes_found": 0,
                "pages_processed": 0
            }
    
    def preview_split_result(self, 
                            doc: 'fitz.Document', 
                            plugin_name: str = None, 
                            config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        预览拆分结果
        
        Args:
            doc: PyMuPDF文档对象
            plugin_name: 插件名称，如果为None则使用当前配置的插件
            config: 拆分配置参数
            
        Returns:
            Dict[str, Any]: 预览结果
        """
        try:
            if not plugin_name:
                plugin_name = self.config_manager.get_current_plugin()
                if not plugin_name:
                    # 如果没有设置当前插件，使用第一个可用插件
                    available_plugins = self.plugin_manager.list_plugins()
                    if available_plugins:
                        plugin_name = available_plugins[0]
                    else:
                        return {"error": "没有可用的条码插件"}
            
            # 检查插件是否已加载
            if plugin_name not in self.plugin_manager.plugins:
                return {"error": f"插件未加载: {plugin_name}"}
            
            # 获取插件配置
            plugin_config = self.config_manager.get_plugin_config(plugin_name)
            
            # 初始化插件（如果尚未初始化）
            plugin = self.plugin_manager.plugins[plugin_name]
            if not plugin.is_initialized:
                init_result = self.plugin_manager.initialize_plugin(plugin_name, plugin_config)
                if not init_result.is_success():
                    return {"error": f"插件初始化失败: {init_result.message}"}
            
            # 预览拆分结果
            result = self.plugin_manager.preview_split_with_plugin(plugin_name, doc, config)
            
            return result
            
        except Exception as e:
            logger.error(f"预览拆分结果时发生异常: {str(e)}")
            return {"error": f"预览拆分结果时发生异常: {str(e)}"}


# 全局条码集成实例
barcode_integration = BarcodeIntegration()