"""
OCR插件接口规范定义
所有OCR插件必须实现此接口定义的所有方法
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union
from enum import Enum


class OCRErrorCode(Enum):
    """OCR错误码枚举"""
    SUCCESS = 0
    INIT_ERROR = 1001
    FILE_NOT_FOUND = 1002
    INVALID_FORMAT = 1003
    RECOGNITION_FAILED = 1004
    UNSUPPORTED_LANGUAGE = 1005
    RESOURCE_LIMIT = 1006
    NETWORK_ERROR = 1007
    PERMISSION_DENIED = 1008
    UNKNOWN_ERROR = 9999


class OCRResult:
    """OCR识别结果统一格式"""
    
    def __init__(self, 
                 code: OCRErrorCode = OCRErrorCode.SUCCESS,
                 data: Union[List[Dict], str, None] = None,
                 message: str = "",
                 plugin_name: str = ""):
        """
        初始化OCR识别结果
        
        Args:
            code: 错误码
            data: 识别结果数据，格式为包含文本、位置等信息的字典列表
                  格式示例: [
                      {
                          "text": "识别的文本",
                          "confidence": 0.95,  # 置信度 0-1
                          "bbox": [x1, y1, x2, y2],  # 文本框坐标
                          "language": "zh"  # 语言标识
                      }
                  ]
            message: 错误信息或附加说明
            plugin_name: 插件名称
        """
        self.code = code
        self.data = data or []
        self.message = message
        self.plugin_name = plugin_name
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code.value,
            "data": self.data,
            "message": self.message,
            "plugin_name": self.plugin_name
        }
    
    def is_success(self) -> bool:
        """判断识别是否成功"""
        return self.code == OCRErrorCode.SUCCESS
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"OCRResult(code={self.code.name}, data_length={len(self.data)}, message='{self.message}')"


class OCRPluginInterface(ABC):
    """OCR插件接口抽象基类"""
    
    def __init__(self):
        """初始化插件"""
        self.plugin_name = ""
        self.plugin_version = ""
        self.plugin_author = ""
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> OCRResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            OCRResult: 初始化结果
        """
        pass
    
    @abstractmethod
    def recognize_from_file(self, file_path: str, language: str = "auto") -> OCRResult:
        """
        从文件路径识别文本
        
        Args:
            file_path: 图片文件路径
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        pass
    
    @abstractmethod
    def recognize_from_bytes(self, image_bytes: bytes, language: str = "auto") -> OCRResult:
        """
        从字节流识别文本
        
        Args:
            image_bytes: 图片字节流
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        pass
    
    @abstractmethod
    def recognize_from_base64(self, base64_string: str, language: str = "auto") -> OCRResult:
        """
        从Base64字符串识别文本
        
        Args:
            base64_string: Base64编码的图片字符串
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        获取支持的语言列表
        
        Returns:
            List[str]: 支持的语言标识列表
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        pass
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """
        获取插件信息
        
        Returns:
            Dict[str, Any]: 插件信息字典
        """
        return {
            "name": self.plugin_name,
            "version": self.plugin_version,
            "author": self.plugin_author,
            "initialized": self.is_initialized
        }