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
            **kwargs: 额外参数，支持：
                - page: 页码（从1开始）
                - page_size: 每页数量
                - offset: 偏移量
                - limit: 限制数量

        Returns:
            DownloadResult: 包含文件列表数据
                data.files: 文件信息列表
                data.total: 总数量（如果支持分页）
                data.page: 当前页码（如果支持分页）
                data.page_size: 每页数量（如果支持分页）
                data.total_pages: 总页数（如果支持分页）
        """
        pass

    def delete_file(self, remote_path: str) -> DownloadResult:
        """
        删除远程文件（可选实现）

        Args:
            remote_path: 远程文件路径

        Returns:
            DownloadResult: 删除结果
        """
        return DownloadResult(
            code=DownloadErrorCode.NETWORK_ERROR,
            message="删除功能未实现"
        )

    def upload_file(self, local_path: str, remote_path: str, **kwargs) -> DownloadResult:
        """
        上传文件到远程（可选实现）

        Args:
            local_path: 本地文件路径
            remote_path: 远程保存路径
            **kwargs: 额外参数，如上传进度回调等

        Returns:
            DownloadResult: 上传结果
                data.path: 上传后的文件路径
        """
        return DownloadResult(
            code=DownloadErrorCode.NETWORK_ERROR,
            message="上传功能未实现"
        )

    def supports_pagination(self) -> bool:
        """
        检查插件是否支持分页

        Returns:
            bool: 是否支持分页
        """
        return False

    @abc.abstractmethod
    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性

        Returns:
            Dict[str, Any]: 支持的特性
        """
        pass

    def get_file_list_columns(self) -> list:
        """
        获取文件列表表格的列名

        Returns:
            list: 列名列表，例如 ["文件名", "文件大小", "修改时间", "文件类型", "路径"]
        """
        return ["文件名", "文件大小", "修改时间", "文件类型", "路径"]

    def get_file_list_row(self, file_info: Dict[str, Any]) -> list:
        """
        获取文件列表表格的一行数据

        Args:
            file_info: 文件信息字典，包含 name, size, modified_time, type, path 等字段

        Returns:
            list: 一行数据列表，例如 ["filename.pdf", "1.23 MB", "2024-01-25 10:00", "file", "/path/to/file"]
        """
        return [
            file_info.get('name', ''),
            self._format_size(file_info.get('size', 0)),
            file_info.get('modified_time', ''),
            '文件夹' if file_info.get('type') == 'dir' else '文件',
            file_info.get('path', '')
        ]

    def _format_size(self, size: int) -> str:
        """
        格式化文件大小（默认实现，子类可重写）

        Args:
            size: 文件大小（字节）

        Returns:
            str: 格式化后的大小字符串，例如 "1.23 MB"
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"

    @abc.abstractmethod
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        pass