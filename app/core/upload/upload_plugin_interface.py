"""
上传插件接口规范定义
所有上传插件必须实现此接口定义的所有方法
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class UploadErrorCode(Enum):
    """上传错误码枚举"""
    SUCCESS = 0
    INIT_ERROR = 2001
    UPLOAD_FAILED = 2002
    CONNECTION_ERROR = 2003
    AUTH_FAILED = 2004
    FILE_NOT_FOUND = 2005
    PERMISSION_DENIED = 2006
    INVALID_CONFIG = 2007
    UNKNOWN_ERROR = 9999


class UploadResult:
    """上传结果统一格式"""
    
    def __init__(self, 
                 code: UploadErrorCode = UploadErrorCode.SUCCESS,
                 data: Optional[Dict[str, Any]] = None,
                 message: str = "",
                 plugin_name: str = ""):
        """
        初始化上传结果
        
        Args:
            code: 错误码
            data: 上传结果数据，如上传后的URL、文件ID等
            message: 错误信息或附加说明
            plugin_name: 插件名称
        """
        self.code = code
        self.data = data or {}
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
        """判断上传是否成功"""
        return self.code == UploadErrorCode.SUCCESS
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"UploadResult(code={self.code.name}, data={self.data}, message='{self.message}')"


class UploadPluginInterface(ABC):
    """上传插件接口抽象基类"""
    
    def __init__(self):
        """初始化插件"""
        self.plugin_name = ""
        self.plugin_version = ""
        self.plugin_author = ""
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> UploadResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            UploadResult: 初始化结果
        """
        pass
    
    @abstractmethod
    def upload_file(self, file_path: str, remote_path: str = "", **kwargs) -> UploadResult:
        """
        上传文件
        
        Args:
            file_path: 本地文件路径
            remote_path: 远程路径（可选，取决于插件实现）
            **kwargs: 额外参数，如上传进度回调等
            
        Returns:
            UploadResult: 上传结果
        """
        pass
    
    @abstractmethod
    def upload_bytes(self, file_bytes: bytes, remote_path: str, original_filename: str = "", **kwargs) -> UploadResult:
        """
        上传字节流
        
        Args:
            file_bytes: 文件字节流
            remote_path: 远程路径
            original_filename: 原始文件名（可选）
            **kwargs: 额外参数
            
        Returns:
            UploadResult: 上传结果
        """
        pass
    
    @abstractmethod
    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性
        
        Returns:
            Dict[str, Any]: 支持的特性，如支持的协议、认证方式等
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