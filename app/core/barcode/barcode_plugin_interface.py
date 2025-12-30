"""
条码插件接口规范定义
所有条码插件必须实现此接口定义的所有方法
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Optional
from enum import Enum
import fitz  # PyMuPDF


class BarcodeErrorCode(Enum):
    """条码错误码枚举"""
    SUCCESS = 0
    INIT_ERROR = 1001
    FILE_NOT_FOUND = 1002
    INVALID_FORMAT = 1003
    DETECTION_FAILED = 1004
    UNSUPPORTED_TYPE = 1005
    RESOURCE_LIMIT = 1006
    NETWORK_ERROR = 1007
    PERMISSION_DENIED = 1008
    UNKNOWN_ERROR = 9999


class BarcodeResult:
    """条码检测结果统一格式"""
    
    def __init__(self, 
                 code: BarcodeErrorCode = BarcodeErrorCode.SUCCESS,
                 data: Union[List[Dict], str, None] = None,
                 message: str = "",
                 plugin_name: str = ""):
        """
        初始化条码检测结果
        
        Args:
            code: 错误码
            data: 检测结果数据，格式为包含条码内容、类型、位置等信息的字典列表
                  格式示例: [
                      {
                          "data": "条码内容",
                          "type": "条码类型",  # 如 'QRCODE', 'CODE128' 等
                          "bbox": [x1, y1, x2, y2],  # 条码框坐标
                          "confidence": 0.95,  # 置信度 0-1
                          "page_num": 0  # 页码
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
        """判断检测是否成功"""
        return self.code == BarcodeErrorCode.SUCCESS
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"BarcodeResult(code={self.code.name}, data_length={len(self.data)}, message='{self.message}')"


class BarcodePluginInterface(ABC):
    """条码插件接口抽象基类"""
    
    def __init__(self):
        """初始化插件"""
        self.plugin_name = ""
        self.plugin_version = ""
        self.plugin_author = ""
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> BarcodeResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            BarcodeResult: 初始化结果
        """
        pass
    
    @abstractmethod
    def detect_from_file(self, file_path: str) -> BarcodeResult:
        """
        从文件路径检测条码
        
        Args:
            file_path: 图片文件路径
            
        Returns:
            BarcodeResult: 检测结果
        """
        pass
    
    @abstractmethod
    def detect_from_bytes(self, image_bytes: bytes) -> BarcodeResult:
        """
        从字节流检测条码
        
        Args:
            image_bytes: 图片字节流
            
        Returns:
            BarcodeResult: 检测结果
        """
        pass
    
    @abstractmethod
    def detect_from_base64(self, base64_string: str) -> BarcodeResult:
        """
        从Base64字符串检测条码
        
        Args:
            base64_string: Base64编码的图片字符串
            
        Returns:
            BarcodeResult: 检测结果
        """
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """
        获取支持的条码类型列表
            
        Returns:
            List[str]: 支持的条码类型标识列表
        """
        pass
    
    @abstractmethod
    def split_document_by_barcodes(self, 
                                 doc: fitz.Document, 
                                 output_dir: str, 
                                 config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        根据条码拆分PDF文档
            
        Args:
            doc: PyMuPDF文档对象
            output_dir: 输出目录
            config: 拆分配置参数
                
        Returns:
            Dict[str, Any]: 拆分结果，包含以下键：
                - success: bool, 拆分是否成功
                - message: str, 结果消息
                - files_created: List[str], 创建的文件路径列表
                - barcodes_found: int, 找到的条码数量
                - pages_processed: int, 处理的页面数
        """
        pass
    
    @abstractmethod
    def preview_split_result(self, 
                            doc: fitz.Document, 
                            config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        预览拆分结果（不实际拆分）
            
        Args:
            doc: PyMuPDF文档对象
            config: 拆分配置参数
                
        Returns:
            Dict[str, Any]: 预览结果，包含以下键：
                - total_pages: int, 总页数
                - total_barcodes: int, 总条码数
                - groups: int, 分组数
                - output_files: int, 预计输出文件数
                - preview: List[Dict], 预览详情列表
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