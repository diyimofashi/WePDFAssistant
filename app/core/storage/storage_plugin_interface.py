"""
云存储插件接口定义
定义所有云存储插件必须实现的接口（合并下载、上传、删除功能）
"""

import abc
from typing import Dict, Any, Optional
from enum import Enum


class StorageErrorCode(Enum):
    """云存储错误代码枚举"""
    SUCCESS = 0  # 成功
    DOWNLOAD_FAILED = 1  # 下载失败
    UPLOAD_FAILED = 2  # 上传失败
    DELETE_FAILED = 3  # 删除失败
    COPY_FAILED = 4  # 复制失败
    NETWORK_ERROR = 5  # 网络错误
    FILE_NOT_FOUND = 6  # 文件不存在
    INVALID_URL = 7  # URL无效
    INVALID_CONFIG = 8  # 配置无效
    INIT_ERROR = 9  # 初始化错误
    PERMISSION_DENIED = 10  # 权限不足
    TIMEOUT = 11  # 超时


class StorageResult:
    """云存储操作结果类"""
    def __init__(self, code: StorageErrorCode, message: str = "", 
                 data: Optional[Dict[str, Any]] = None, 
                 plugin_name: str = ""):
        self.code = code
        self.message = message
        self.data = data or {}
        self.plugin_name = plugin_name

    def is_success(self) -> bool:
        """检查是否成功"""
        return self.code.value == 0  # SUCCESS的值是0


class StoragePluginInterface(metaclass=abc.ABCMeta):
    """云存储插件接口 - 所有云存储插件必须继承此类并实现其方法"""

    def __init__(self):
        self.is_initialized = False
        self.plugin_name = ""
        self.plugin_version = ""
        self.plugin_author = ""
        self.config = {}

    @abc.abstractmethod
    def initialize(self, config: Dict[str, Any]) -> StorageResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            StorageResult: 初始化结果
        """
        pass

    @abc.abstractmethod
    def download_file(self, url: str, local_path: str, **kwargs) -> StorageResult:
        """
        下载文件
        
        Args:
            url: 远程文件URL
            local_path: 本地保存路径
            **kwargs: 额外参数，如下载进度回调等
            
        Returns:
            StorageResult: 下载结果
        """
        pass

    @abc.abstractmethod
    def download_bytes(self, url: str, **kwargs) -> StorageResult:
        """
        下载文件为字节流

        Args:
            url: 远程文件URL
            **kwargs: 额外参数

        Returns:
            StorageResult: 下载结果
        """
        pass

    @abc.abstractmethod
    def upload_file(self, local_path: str, remote_path: str, **kwargs) -> StorageResult:
        """
        上传文件到远程

        Args:
            local_path: 本地文件路径
            remote_path: 远程保存路径
            **kwargs: 额外参数，如上传进度回调等

        Returns:
            StorageResult: 上传结果
                data.path: 上传后的文件路径
        """
        pass

    def delete_file(self, remote_path: str) -> StorageResult:
        """
        删除远程文件（可选实现）

        Args:
            remote_path: 远程文件路径

        Returns:
            StorageResult: 删除结果
        """
        return StorageResult(
            code=StorageErrorCode.NETWORK_ERROR,
            message="删除功能未实现"
        )

    def delete_directory(self, remote_path: str) -> StorageResult:
        """
        删除远程目录（可选实现）

        Args:
            remote_path: 远程目录路径

        Returns:
            StorageResult: 删除结果
        """
        return StorageResult(
            code=StorageErrorCode.NETWORK_ERROR,
            message="删除目录功能未实现"
        )
        """
        删除远程文件（可选实现）

        Args:
            remote_path: 远程文件路径

        Returns:
            StorageResult: 删除结果
        """
        return StorageResult(
            code=StorageErrorCode.NETWORK_ERROR,
            message="删除功能未实现"
        )

    def copy_file(self, source_path: str, target_path: str) -> StorageResult:
        """
        复制远程文件（可选实现）

        Args:
            source_path: 源文件路径
            target_path: 目标文件路径

        Returns:
            StorageResult: 复制结果
        """
        return StorageResult(
            code=StorageErrorCode.NETWORK_ERROR,
            message="复制功能未实现"
        )

    @abc.abstractmethod
    def list_files(self, remote_path: str = "", **kwargs) -> StorageResult:
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
            StorageResult: 包含文件列表数据
                data.files: 文件信息列表
                data.total: 总数量（如果支持分页）
                data.page: 当前页码（如果支持分页）
                data.page_size: 每页数量（如果支持分页）
                data.total_pages: 总页数（如果支持分页）
        """
        pass

    def supports_pagination(self) -> bool:
        """
        检查插件是否支持分页

        Returns:
            bool: 是否支持分页
        """
        return False

    def list_directories(self, remote_path: str = "") -> StorageResult:
        """
        列出远程目录（可选实现）

        Args:
            remote_path: 远程路径

        Returns:
            StorageResult: 包含目录列表数据
                data.directories: 目录信息列表
        """
        # 默认从 list_files 结果中提取目录
        result = self.list_files(remote_path)
        if not result.is_success():
            return result

        files = result.data.get('files', [])
        directories = [f for f in files if f.get('type') == 'dir']

        return StorageResult(
            code=StorageErrorCode.SUCCESS,
            message="获取目录列表成功",
            data={'directories': directories}
        )

    @abc.abstractmethod
    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性

        Returns:
            Dict[str, Any]: 支持的特性
        """
        pass

    def get_file_list_columns(self) -> list[str]:
        """
        获取文件列表表格的列名

        Returns:
            list: 列名列表，例如 ["文件名", "文件大小", "修改时间", "文件类型", "路径"]
        """
        return ["文件名", "文件大小", "修改时间", "文件类型", "路径"]

    def get_file_list_row(self, file_info: Dict[str, Any]) -> list[str]:
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
