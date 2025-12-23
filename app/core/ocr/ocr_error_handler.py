"""
OCR插件系统错误处理和日志记录模块
统一的错误码和错误信息格式，以及详细的日志分级记录
"""

import traceback
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from .ocr_plugin_interface import OCRErrorCode, OCRResult
from app.utils.logger import get_logger

# 获取模块特定的日志记录器
logger = get_logger('ocr_error_handler')


class OCRErrorHandler:
    """OCR错误处理器"""
    
    def __init__(self):
        """初始化错误处理器"""
        self.error_counts = {}
        self.lock = threading.Lock()
        
        # 错误码到用户友好消息的映射
        self.user_friendly_messages = {
            OCRErrorCode.SUCCESS: "操作成功",
            OCRErrorCode.INIT_ERROR: "插件初始化失败",
            OCRErrorCode.FILE_NOT_FOUND: "文件未找到",
            OCRErrorCode.INVALID_FORMAT: "无效的文件格式",
            OCRErrorCode.RECOGNITION_FAILED: "OCR识别失败",
            OCRErrorCode.UNSUPPORTED_LANGUAGE: "不支持的语言",
            OCRErrorCode.RESOURCE_LIMIT: "资源限制 exceeded",
            OCRErrorCode.NETWORK_ERROR: "网络连接错误",
            OCRErrorCode.PERMISSION_DENIED: "权限不足",
            OCRErrorCode.UNKNOWN_ERROR: "未知错误"
        }
        
        logger.info("OCR错误处理器初始化")
    
    def handle_exception(self, plugin_name: str, exception: Exception, 
                        context: str = "", log_level: str = "error") -> OCRResult:
        """
        处理异常并生成标准化的OCR结果
        
        Args:
            plugin_name: 插件名称
            exception: 捕获的异常
            context: 错误上下文描述
            log_level: 日志级别 ("debug", "info", "warning", "error")
            
        Returns:
            OCRResult: 标准化的错误结果
        """
        # 确定错误码
        error_code = self._determine_error_code(exception)
        
        # 生成错误消息
        error_message = str(exception)
        if context:
            error_message = f"{context}: {error_message}"
        
        # 记录详细的错误日志
        self._log_detailed_error(plugin_name, exception, context, log_level)
        
        # 更新错误计数
        self._update_error_count(plugin_name, error_code)
        
        # 返回标准化的OCR结果
        return OCRResult(
            code=error_code,
            message=error_message,
            plugin_name=plugin_name
        )
    
    def _determine_error_code(self, exception: Exception) -> OCRErrorCode:
        """
        根据异常类型确定错误码
        
        Args:
            exception: 异常对象
            
        Returns:
            OCRErrorCode: 对应的错误码
        """
        # 根据异常类型映射错误码
        exception_type = type(exception).__name__
        
        error_mapping = {
            'FileNotFoundError': OCRErrorCode.FILE_NOT_FOUND,
            'PermissionError': OCRErrorCode.PERMISSION_DENIED,
            'ValueError': OCRErrorCode.INVALID_FORMAT,
            'TypeError': OCRErrorCode.INVALID_FORMAT,
            'ConnectionError': OCRErrorCode.NETWORK_ERROR,
            'TimeoutError': OCRErrorCode.NETWORK_ERROR,
            'MemoryError': OCRErrorCode.RESOURCE_LIMIT,
            'NotImplementedError': OCRErrorCode.INIT_ERROR,
        }
        
        return error_mapping.get(exception_type, OCRErrorCode.UNKNOWN_ERROR)
    
    def _log_detailed_error(self, plugin_name: str, exception: Exception, 
                           context: str, log_level: str) -> None:
        """
        记录详细的错误日志
        
        Args:
            plugin_name: 插件名称
            exception: 异常对象
            context: 错误上下文
            log_level: 日志级别
        """
        # 获取异常的详细信息
        exception_details = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        
        # 构造日志消息
        log_message = f"插件 '{plugin_name}' 发生错误"
        if context:
            log_message += f" [{context}]"
        log_message += f": {type(exception).__name__}: {str(exception)}"
        
        # 记录不同级别的日志
        if log_level.lower() == "debug":
            logger.debug(log_message)
            logger.debug(f"详细异常信息:\n{exception_details}")
        elif log_level.lower() == "info":
            logger.info(log_message)
        elif log_level.lower() == "warning":
            logger.warning(log_message)
            logger.debug(f"详细异常信息:\n{exception_details}")
        else:  # error
            logger.error(log_message)
            logger.debug(f"详细异常信息:\n{exception_details}")
    
    def _update_error_count(self, plugin_name: str, error_code: OCRErrorCode) -> None:
        """
        更新错误计数
        
        Args:
            plugin_name: 插件名称
            error_code: 错误码
        """
        with self.lock:
            if plugin_name not in self.error_counts:
                self.error_counts[plugin_name] = {}
            
            error_code_str = error_code.name
            if error_code_str not in self.error_counts[plugin_name]:
                self.error_counts[plugin_name][error_code_str] = 0
            
            self.error_counts[plugin_name][error_code_str] += 1
    
    def get_user_friendly_message(self, error_code: OCRErrorCode) -> str:
        """
        获取用户友好的错误消息
        
        Args:
            error_code: 错误码
            
        Returns:
            str: 用户友好的错误消息
        """
        return self.user_friendly_messages.get(error_code, "操作失败")
    
    def format_error_for_user(self, ocr_result: OCRResult) -> str:
        """
        格式化错误信息供用户显示
        
        Args:
            ocr_result: OCR结果对象
            
        Returns:
            str: 格式化的用户友好错误信息
        """
        if ocr_result.is_success():
            return "操作成功"
        
        # 获取用户友好的错误消息
        user_message = self.get_user_friendly_message(ocr_result.code)
        
        # 添加详细信息（如果有的话）
        if ocr_result.message and ocr_result.message != user_message:
            return f"{user_message} ({ocr_result.message})"
        
        return user_message
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            Dict[str, Any]: 错误统计信息
        """
        with self.lock:
            return {
                'error_counts': self.error_counts.copy(),
                'generated_at': datetime.now().isoformat()
            }
    
    def clear_error_statistics(self) -> None:
        """清除错误统计信息"""
        with self.lock:
            self.error_counts.clear()
    
    def log_plugin_loading_error(self, plugin_path: str, error: str) -> None:
        """
        记录插件加载错误
        
        Args:
            plugin_path: 插件路径
            error: 错误信息
        """
        logger.error(f"插件加载失败: {plugin_path}, 错误: {error}")
    
    def log_plugin_initialization_error(self, plugin_name: str, error: str) -> None:
        """
        记录插件初始化错误
        
        Args:
            plugin_name: 插件名称
            error: 错误信息
        """
        logger.error(f"插件初始化失败: {plugin_name}, 错误: {error}")
    
    def log_ocr_recognition_error(self, plugin_name: str, error: str, 
                                 file_info: str = "") -> None:
        """
        记录OCR识别错误
        
        Args:
            plugin_name: 插件名称
            error: 错误信息
            file_info: 文件信息（可选）
        """
        message = f"OCR识别失败: {plugin_name}"
        if file_info:
            message += f" (文件: {file_info})"
        message += f", 错误: {error}"
        
        logger.error(message)
    
    def log_configuration_error(self, plugin_name: str, error: str) -> None:
        """
        记录配置错误
        
        Args:
            plugin_name: 插件名称
            error: 错误信息
        """
        logger.error(f"插件配置错误: {plugin_name}, 错误: {error}")
    
    def log_security_violation(self, plugin_name: str, violation_type: str, 
                              details: str = "") -> None:
        """
        记录安全违规
        
        Args:
            plugin_name: 插件名称
            violation_type: 违规类型
            details: 详细信息
        """
        message = f"安全违规: {plugin_name}, 类型: {violation_type}"
        if details:
            message += f", 详情: {details}"
        
        logger.warning(message)


class OCRAuditLogger:
    """OCR审计日志记录器"""
    
    def __init__(self):
        """初始化审计日志记录器"""
        self.audit_logger = get_logger('ocr_audit')
        logger.info("OCR审计日志记录器初始化")
    
    def log_plugin_load(self, plugin_name: str, plugin_path: str, success: bool) -> None:
        """
        记录插件加载事件
        
        Args:
            plugin_name: 插件名称
            plugin_path: 插件路径
            success: 是否成功
        """
        status = "成功" if success else "失败"
        self.audit_logger.info(f"插件加载[{status}]: {plugin_name} ({plugin_path})")
    
    def log_plugin_unload(self, plugin_name: str) -> None:
        """
        记录插件卸载事件
        
        Args:
            plugin_name: 插件名称
        """
        self.audit_logger.info(f"插件卸载: {plugin_name}")
    
    def log_ocr_request(self, plugin_name: str, input_type: str, file_info: str = "") -> None:
        """
        记录OCR请求事件
        
        Args:
            plugin_name: 插件名称
            input_type: 输入类型 (file/bytes/base64)
            file_info: 文件信息
        """
        message = f"OCR请求: 插件={plugin_name}, 输入类型={input_type}"
        if file_info:
            message += f", 文件={file_info}"
        
        self.audit_logger.info(message)
    
    def log_ocr_result(self, plugin_name: str, success: bool, processing_time: float,
                      text_length: int = 0) -> None:
        """
        记录OCR结果事件
        
        Args:
            plugin_name: 插件名称
            success: 是否成功
            processing_time: 处理时间（秒）
            text_length: 识别文本长度
        """
        status = "成功" if success else "失败"
        message = f"OCR结果[{status}]: 插件={plugin_name}, 耗时={processing_time:.2f}秒"
        if text_length > 0:
            message += f", 文本长度={text_length}"
        
        self.audit_logger.info(message)
    
    def log_configuration_change(self, plugin_name: str, config_key: str, 
                               old_value: Any, new_value: Any) -> None:
        """
        记录配置变更事件
        
        Args:
            plugin_name: 插件名称
            config_key: 配置键
            old_value: 旧值
            new_value: 新值
        """
        self.audit_logger.info(
            f"配置变更: 插件={plugin_name}, 配置项={config_key}, "
            f"旧值={old_value}, 新值={new_value}"
        )
    
    def log_security_check(self, plugin_name: str, check_type: str, 
                          passed: bool, details: str = "") -> None:
        """
        记录安全检查事件
        
        Args:
            plugin_name: 插件名称
            check_type: 检查类型
            passed: 是否通过
            details: 详细信息
        """
        status = "通过" if passed else "未通过"
        message = f"安全检查[{status}]: 插件={plugin_name}, 检查类型={check_type}"
        if details:
            message += f", 详情={details}"
        
        self.audit_logger.info(message)


# 全局错误处理器和审计日志记录器实例
error_handler = OCRErrorHandler()
audit_logger = OCRAuditLogger()