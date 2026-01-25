"""
下载插件接口定义
定义所有下载插件必须实现的接口
"""

import abc
from typing import Dict, Any, Optional
from enum import Enum


class DownloadErrorCode(Enum):
    """下载错误代码枚举"""
    SUCCESS = 0  # 成功
    DOWNLOAD_FAILED = 1  # 下载失败
    NETWORK_ERROR = 2  # 网络错误
    FILE_NOT_FOUND = 3  # 文件不存在
    INVALID_URL = 4  # URL无效
    INVALID_CONFIG = 5  # 配置无效
    INIT_ERROR = 6  # 初始化错误
    PERMISSION_DENIED = 7  # 权限不足
    TIMEOUT = 8  # 超时


class DownloadResult:
    """下载结果类"""
    def __init__(self, code: DownloadErrorCode, message: str = "", data: Optional[Dict[str, Any]] = None, 
                 plugin_name: str = ""):
        self.code = code
        self.message = message
        self.data = data or {}
        self.plugin_name = plugin_name

    def is_success(self) -> bool:
        """检查是否成功"""
        return self.code.value == 0  # SUCCESS的值是0


class DownloadPluginInterface(metaclass=abc.ABCMeta):
    """下载插件接口 - 所有下载插件必须继承此类并实现其方法"""

    def __init__(self):
        self.is_initialized = False
        self.plugin_name = ""
        self.plugin_version = ""
        self.plugin_author = ""
        self.config = {}

    @abc.abstractmethod
    def initialize(self, config: Dict[str, Any]) -> DownloadResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            DownloadResult: 初始化结果
        """
        pass

    @abc.abstractmethod
    def download_file(self, url: str, local_path: str, **kwargs) -> DownloadResult:
        """
        下载文件
        
        Args:
            url: 远程文件URL
            local_path: 本地保存路径
            **kwargs: 额外参数，如下载进度回调等
            
        Returns:
            DownloadResult: 下载结果
        """
        pass

    @abc.abstractmethod
    def download_bytes(self, url: str, **kwargs) -> DownloadResult:
        """
        下载文件为字节流

        Args:
            url: 远程文件URL
            **kwargs: 额外参数

        Returns:
            DownloadResult: 下载结果
        """
        pass

    @abc.abstractmethod
    def list_files(self, remote_path: str = "", **kwargs) -> DownloadResult:
        """
        列出远程文件

        Args:
            remote_path: 远程路径（可选）
            **kwargs: 额外参数

        Returns:
            DownloadResult: 包含文件列表数据，data.files 包含文件信息列表
        """
        pass

    @abc.abstractmethod
    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性
        
        Returns:
            Dict[str, Any]: 支持的特性
        """
        pass

    @abc.abstractmethod
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        pass