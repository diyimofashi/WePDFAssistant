"""
OCR系统与现有应用集成模块
提供简单的API接口调用插件功能
"""

import os
import threading
import time
from typing import Dict, List, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.managers.ocr_plugin_manager import ocr_plugin_manager
from app.config.ocr_plugin_config import ocr_config_manager
from .ocr_plugin_interface import OCRResult, OCRErrorCode
from .ocr_plugin_security import security_manager
from .ocr_error_handler import error_handler, audit_logger
from app.utils.logger import get_logger

logger = get_logger('ocr_integration')


class OCRIntegration:
    """OCR系统集成类"""
    
    def __init__(self):
        """初始化OCR集成"""
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.plugin_manager = ocr_plugin_manager
        self.config_manager = ocr_config_manager
        self.security_manager = security_manager
        self.performance_stats = {}
        
        logger.info("OCR系统集成模块初始化")
    
    def initialize_system(self, plugin_configs: Dict[str, Dict[str, Any]] = None) -> Dict[str, bool]:
        """
        初始化OCR系统
        
        Args:
            plugin_configs: 插件配置字典
            
        Returns:
            Dict[str, bool]: 各插件初始化结果
        """
        try:
            # 加载所有插件
            load_results = self.plugin_manager.load_all_plugins()
            logger.info(f"插件加载完成: {load_results}")
            
            # 初始化所有插件
            init_results = self.plugin_manager.initialize_all_plugins(plugin_configs)
            
            # 转换结果格式
            results = {}
            for plugin_name, result in init_results.items():
                results[plugin_name] = result.is_success()
                if result.is_success():
                    logger.info(f"插件初始化成功: {plugin_name}")
                    # 注册默认权限
                    self.security_manager.register_plugin_permissions(plugin_name, {
                        'file_access': True,
                        'network_access': False,
                        'execute_commands': True,
                        'system_calls': False
                    })
                else:
                    logger.error(f"插件初始化失败: {plugin_name}, 错误: {result.message}")
            
            return results
            
        except Exception as e:
            result = error_handler.handle_exception("OCRSystem", e, "初始化OCR系统时发生异常")
            return {}
    
    def recognize_single(self, plugin_name: str, file_path: str = None, 
                        image_bytes: bytes = None, base64_string: str = None,
                        language: str = "auto") -> OCRResult:
        """
        单个OCR识别
        
        Args:
            plugin_name: 插件名称
            file_path: 图片文件路径
            image_bytes: 图片字节流
            base64_string: Base64编码的图片字符串
            language: 识别语言
            
        Returns:
            OCRResult: 识别结果
        """
        start_time = time.time()
        
        try:
            # 安全检查
            if not self.security_manager.check_permission(plugin_name, 'execute_commands'):
                error_result = OCRResult(
                    code=OCRErrorCode.PERMISSION_DENIED,
                    message=f"插件没有执行权限: {plugin_name}",
                    plugin_name=plugin_name
                )
                error_handler.log_security_violation(plugin_name, "permission_denied", f"execute_commands permission required")
                return error_result
            
            # 执行OCR识别
            result = self.plugin_manager.recognize_with_plugin(
                plugin_name, file_path, image_bytes, base64_string, language
            )
            
            # 记录性能统计
            elapsed_time = time.time() - start_time
            self._record_performance_stats(plugin_name, elapsed_time, result.is_success())
            
            return result
            
        except Exception as e:
            result = error_handler.handle_exception(plugin_name, e, "执行OCR识别时发生异常")
            error_handler.log_ocr_recognition_error(plugin_name, str(e), f"file={file_path or 'N/A'}")
            return result
    
    def recognize_batch(self, plugin_name: str, inputs: List[Dict[str, Any]], 
                       language: str = "auto", max_workers: int = 4) -> List[OCRResult]:
        """
        批量OCR识别
        
        Args:
            plugin_name: 插件名称
            inputs: 输入列表，每个元素为包含file_path/image_bytes/base64_string的字典
            language: 识别语言
            max_workers: 最大并发工作线程数
            
        Returns:
            List[OCRResult]: 识别结果列表
        """
        results = []
        start_time = time.time()
        
        try:
            # 创建线程池执行批量识别
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_input = {}
                for i, input_data in enumerate(inputs):
                    future = executor.submit(
                        self.recognize_single,
                        plugin_name,
                        input_data.get('file_path'),
                        input_data.get('image_bytes'),
                        input_data.get('base64_string'),
                        language
                    )
                    future_to_input[future] = i
                
                # 收集结果
                for future in as_completed(future_to_input):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        index = future_to_input[future]
                        logger.error(f"批量识别任务 {index} 发生异常: {str(e)}")
                        results.append(OCRResult(
                            code=OCRErrorCode.RECOGNITION_FAILED,
                            message=f"批量识别任务异常: {str(e)}",
                            plugin_name=plugin_name
                        ))
            
            # 记录批量处理性能统计
            elapsed_time = time.time() - start_time
            self._record_batch_performance_stats(plugin_name, len(inputs), elapsed_time)
            
            return results
            
        except Exception as e:
            result = error_handler.handle_exception(plugin_name, e, "批量OCR识别时发生异常")
            error_handler.log_ocr_recognition_error(plugin_name, str(e), f"batch_size={len(inputs)}")
            return [result] * len(inputs)
    
    def recognize_with_multiple_plugins(self, plugin_names: List[str], file_path: str = None,
                                      image_bytes: bytes = None, base64_string: str = None,
                                      language: str = "auto") -> Dict[str, OCRResult]:
        """
        使用多个插件进行OCR识别
        
        Args:
            plugin_names: 插件名称列表
            file_path: 图片文件路径
            image_bytes: 图片字节流
            base64_string: Base64编码的图片字符串
            language: 识别语言
            
        Returns:
            Dict[str, OCRResult]: 各插件的识别结果
        """
        results = {}
        start_time = time.time()
        
        try:
            # 并发执行多个插件的识别
            with ThreadPoolExecutor(max_workers=len(plugin_names)) as executor:
                # 提交所有任务
                future_to_plugin = {}
                for plugin_name in plugin_names:
                    future = executor.submit(
                        self.recognize_single,
                        plugin_name,
                        file_path,
                        image_bytes,
                        base64_string,
                        language
                    )
                    future_to_plugin[future] = plugin_name
                
                # 收集结果
                for future in as_completed(future_to_plugin):
                    plugin_name = future_to_plugin[future]
                    try:
                        result = future.result()
                        results[plugin_name] = result
                    except Exception as e:
                        logger.error(f"插件 {plugin_name} 识别时发生异常: {str(e)}")
                        results[plugin_name] = OCRResult(
                            code=OCRErrorCode.RECOGNITION_FAILED,
                            message=f"插件识别异常: {str(e)}",
                            plugin_name=plugin_name
                        )
            
            # 记录多插件处理性能统计
            elapsed_time = time.time() - start_time
            self._record_multi_plugin_performance_stats(plugin_names, elapsed_time)
            
            return results
            
        except Exception as e:
            result = error_handler.handle_exception("MultiPluginOCR", e, "多插件OCR识别时发生异常")
            for plugin_name in plugin_names:
                error_handler.log_ocr_recognition_error(plugin_name, str(e), "multi_plugin_recognition")
            return {
                plugin_name: result
                for plugin_name in plugin_names
            }
    
    def get_available_plugins(self) -> List[str]:
        """
        获取可用插件列表
        
        Returns:
            List[str]: 插件名称列表
        """
        return self.plugin_manager.list_plugins()
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件详细信息
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 插件信息
        """
        return self.plugin_manager.get_plugin_info(plugin_name)
    
    def get_supported_languages(self, plugin_name: str) -> List[str]:
        """
        获取插件支持的语言列表
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            List[str]: 支持的语言列表
        """
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            return []
        return plugin.get_supported_languages()
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> Dict[str, str]:
        """
        设置插件配置
        
        Args:
            plugin_name: 插件名称
            config: 配置参数字典
            
        Returns:
            Dict[str, str]: 验证错误信息
        """
        return self.config_manager.set_plugin_config(plugin_name, config)
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件配置
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 插件配置
        """
        return self.config_manager.get_plugin_config_with_defaults(plugin_name)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            Dict[str, Any]: 性能统计数据
        """
        return self.performance_stats.copy()
    
    def _record_performance_stats(self, plugin_name: str, elapsed_time: float, success: bool) -> None:
        """
        记录性能统计
        
        Args:
            plugin_name: 插件名称
            elapsed_time: 耗时（秒）
            success: 是否成功
        """
        with threading.Lock():
            if plugin_name not in self.performance_stats:
                self.performance_stats[plugin_name] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'total_time': 0.0,
                    'average_time': 0.0
                }
            
            stats = self.performance_stats[plugin_name]
            stats['total_requests'] += 1
            if success:
                stats['successful_requests'] += 1
            else:
                stats['failed_requests'] += 1
            stats['total_time'] += elapsed_time
            stats['average_time'] = stats['total_time'] / stats['total_requests']
    
    def _record_batch_performance_stats(self, plugin_name: str, batch_size: int, elapsed_time: float) -> None:
        """
        记录批量处理性能统计
        
        Args:
            plugin_name: 插件名称
            batch_size: 批量大小
            elapsed_time: 总耗时（秒）
        """
        with threading.Lock():
            if 'batch_processing' not in self.performance_stats:
                self.performance_stats['batch_processing'] = {}
            
            if plugin_name not in self.performance_stats['batch_processing']:
                self.performance_stats['batch_processing'][plugin_name] = {
                    'total_batches': 0,
                    'total_items': 0,
                    'total_time': 0.0,
                    'average_time_per_item': 0.0
                }
            
            stats = self.performance_stats['batch_processing'][plugin_name]
            stats['total_batches'] += 1
            stats['total_items'] += batch_size
            stats['total_time'] += elapsed_time
            stats['average_time_per_item'] = stats['total_time'] / stats['total_items']
    
    def _record_multi_plugin_performance_stats(self, plugin_names: List[str], elapsed_time: float) -> None:
        """
        记录多插件处理性能统计
        
        Args:
            plugin_names: 插件名称列表
            elapsed_time: 总耗时（秒）
        """
        with threading.Lock():
            if 'multi_plugin_processing' not in self.performance_stats:
                self.performance_stats['multi_plugin_processing'] = {
                    'total_requests': 0,
                    'total_time': 0.0,
                    'average_time': 0.0,
                    'plugins_used': {}
                }
            
            stats = self.performance_stats['multi_plugin_processing']
            stats['total_requests'] += 1
            stats['total_time'] += elapsed_time
            stats['average_time'] = stats['total_time'] / stats['total_requests']
            
            # 记录各插件使用次数
            for plugin_name in plugin_names:
                if plugin_name not in stats['plugins_used']:
                    stats['plugins_used'][plugin_name] = 0
                stats['plugins_used'][plugin_name] += 1
    
    def format_ocr_result(self, result: OCRResult, format_type: str = "text") -> str:
        """
        格式化OCR识别结果
        
        Args:
            result: OCR识别结果
            format_type: 格式类型 ("text", "json", "structured")
            
        Returns:
            str: 格式化后的结果
        """
        if not result.is_success():
            return f"OCR识别失败: {result.message}"
        
        if format_type == "text":
            # 纯文本格式
            texts = [item.get("text", "") for item in result.data]
            return "\n".join(texts)
        
        elif format_type == "json":
            # JSON格式
            import json
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        
        elif format_type == "structured":
            # 结构化格式
            formatted_lines = []
            for item in result.data:
                text = item.get("text", "")
                confidence = item.get("confidence", 0)
                bbox = item.get("bbox", [])
                formatted_lines.append(f"文本: {text}")
                formatted_lines.append(f"  置信度: {confidence:.2f}")
                if bbox:
                    formatted_lines.append(f"  位置: ({bbox[0]}, {bbox[1]}) - ({bbox[2]}, {bbox[3]})")
                formatted_lines.append("")
            return "\n".join(formatted_lines)
        
        else:
            return f"不支持的格式类型: {format_type}"
    
    def close(self) -> None:
        """
        关闭OCR系统，释放资源
        """
        try:
            # 关闭线程池
            self.executor.shutdown(wait=True)
            
            # 卸载所有插件
            self.plugin_manager.unload_all_plugins()
            
            logger.info("OCR系统已关闭")
        except Exception as e:
            result = error_handler.handle_exception("OCRSystem", e, "关闭OCR系统时发生异常")


# 全局OCR集成实例
ocr_integration = OCRIntegration()