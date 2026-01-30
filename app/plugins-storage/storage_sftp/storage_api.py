# -*- coding: utf-8 -*-
"""
SFTP云存储插件 - 核心实现
使用paramiko库实现SFTP文件操作
"""

import os
import paramiko
from typing import Dict, Any
from datetime import datetime
from app.core.storage.storage_plugin_interface import StoragePluginInterface, StorageResult, StorageErrorCode
from app.utils.logger import get_logger

# 导入配置信息
from .config import PluginInfo

logger = get_logger('sftp_storage')


class SFTPStorage(StoragePluginInterface):
    """SFTP云存储插件实现类"""
    
    # 插件配置信息
    PluginInfo = PluginInfo

    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "SFTP Storage"
        self.plugin_version = "1.0.0"
        self.plugin_author = "PyPDF Team"
        self.config = config or {}

        # SFTP连接
        self.sftp = None
        self.ssh = None

        # 配置参数
        self.host = ""
        self.port = 22
        self.username = ""
        self.password = ""
        self.private_key_file = ""
        self.path_prefix = ""
        self.encoding = "utf-8"
        self.timeout = 30
        self.host_key_fingerprint = ""

    def initialize(self, config: Dict[str, Any]) -> StorageResult:
        """
        初始化插件

        Args:
            config: 插件配置参数

        Returns:
            StorageResult: 初始化结果
        """
        try:
            # 保存配置
            self.config = config

            # 从配置中获取SFTP参数
            self.host = config.get("host", "")
            self.port = int(config.get("port", 22))
            self.username = config.get("username", "")
            self.password = config.get("password", "")
            private_key_file = config.get("private_key_file", "")
            path_prefix = config.get("path_prefix", "")
            self.path_prefix = str(path_prefix) if path_prefix is not None else ""
            self.encoding = config.get("encoding", "utf-8")
            self.timeout = int(config.get("timeout", 30))
            self.host_key_fingerprint = config.get("host_key_fingerprint", "")

            # 规范化私钥文件路径
            if private_key_file:
                private_key_file = private_key_file.replace('\\', os.sep)
                if not os.path.isabs(private_key_file):
                    # 私钥文件相对于插件目录
                    plugin_dir = os.path.dirname(os.path.abspath(__file__))
                    private_key_file = os.path.join(plugin_dir, private_key_file)
                private_key_file = os.path.normpath(private_key_file)

            self.private_key_file = private_key_file

            logger.info(f"SFTP配置: host={self.host}:{self.port}, username={self.username}")
            logger.info(f"私钥文件存在: {os.path.exists(self.private_key_file) if self.private_key_file else False}")

            # 验证必填配置
            if not self.host:
                return StorageResult(
                    code=StorageErrorCode.INVALID_CONFIG,
                    message="缺少host配置（SFTP服务器地址）",
                    plugin_name=self.plugin_name
                )

            if not self.username:
                return StorageResult(
                    code=StorageErrorCode.INVALID_CONFIG,
                    message="缺少username配置（SFTP用户名）",
                    plugin_name=self.plugin_name
                )

            if not self.password and not self.private_key_file:
                return StorageResult(
                    code=StorageErrorCode.INVALID_CONFIG,
                    message="必须配置密码或私钥文件之一",
                    plugin_name=self.plugin_name
                )

            # 测试连接
            try:
                # 创建SSH客户端
                self.ssh = paramiko.SSHClient()
                self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # 验证主机密钥指纹（如果配置了）
                if self.host_key_fingerprint:
                    try:
                        self.ssh.get_host_keys().add(
                            self.host,
                            'ssh-rsa',
                            self.host_key_fingerprint
                        )
                    except Exception as e:
                        logger.warning(f"设置主机密钥指纹失败: {e}")

                # 准备认证方式
                auth_methods = []
                if self.private_key_file:
                    try:
                        if os.path.exists(self.private_key_file):
                            private_key = paramiko.RSAKey.from_private_key_file(self.private_key_file)
                            auth_methods.append(("私钥", {'pkey': private_key}))
                        else:
                            logger.warning(f"私钥文件不存在: {self.private_key_file}")
                    except Exception as e:
                        logger.error(f"加载私钥失败: {e}")

                if self.password:
                    auth_methods.append(("密码", {'password': self.password}))

                # 尝试连接
                connection_success = False
                last_error = None

                for method_name, kwargs in auth_methods:
                    try:
                        logger.info(f"尝试使用{method_name}连接...")
                        self.ssh.connect(
                            self.host,
                            port=self.port,
                            username=self.username,
                            timeout=self.timeout,
                            **kwargs
                        )
                        connection_success = True
                        logger.info(f"使用{method_name}连接成功")
                        break
                    except Exception as e:
                        last_error = e
                        logger.warning(f"使用{method_name}连接失败: {e}")
                        if self.ssh._transport:
                            self.ssh._transport.close()

                if not connection_success:
                    raise last_error or Exception("所有认证方式都失败")

                # 创建SFTP客户端
                self.sftp = self.ssh.open_sftp()
                logger.info(f"SFTP客户端创建成功")

                # 测试目录切换
                if self.path_prefix:
                    try:
                        self.sftp.chdir(self.path_prefix)
                        logger.info(f"成功切换到目录: {self.path_prefix}")
                    except Exception as e:
                        logger.warning(f"切换目录失败: {self.path_prefix}, {e}")

                logger.info(f"SFTP连接成功: {self.host}:{self.port}")
                self.is_initialized = True
                return StorageResult(
                    code=StorageErrorCode.SUCCESS,
                    message="SFTP插件初始化成功",
                    plugin_name=self.plugin_name
                )

            except paramiko.AuthenticationException as e:
                return StorageResult(
                    code=StorageErrorCode.PERMISSION_DENIED,
                    message=f"SFTP认证失败: {str(e)}",
                    plugin_name=self.plugin_name
                )
            except Exception as e:
                logger.error(f"SFTP连接失败: {e}")
                return StorageResult(
                    code=StorageErrorCode.INIT_ERROR,
                    message=f"SFTP连接失败: {str(e)}",
                    plugin_name=self.plugin_name
                )

        except Exception as e:
            logger.error(f"SFTP插件初始化异常: {e}")
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"SFTP插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def _ensure_connection(self):
        """确保SFTP连接可用"""
        if not self.sftp or not self.ssh:
            logger.warning("SFTP连接不存在")
            return False

        try:
            # 测试连接
            self.sftp.listdir()
            logger.debug("SFTP连接检查通过")
            return True
        except Exception as e:
            logger.warning(f"SFTP连接检查失败: {e}，尝试重新连接")
            self.sftp = None
            self.ssh = None
            return False

    def _get_full_path(self, remote_path: str) -> str:
        """获取完整路径"""
        remote_path = remote_path.lstrip('/')
        if self.path_prefix:
            prefix = self.path_prefix.lstrip('/')
            if prefix:
                return f"{prefix}/{remote_path}".lstrip('/')
            return remote_path
        return remote_path

    def download_file(self, url: str, local_path: str, **kwargs) -> StorageResult:
        """
        下载文件

        Args:
            url: 远程文件路径
            local_path: 本地保存路径
            **kwargs: 额外参数

        Returns:
            StorageResult: 下载结果
        """
        try:
            # 检查下载功能是否启用
            if not self.config.get("enable_download", True):
                return StorageResult(
                    code=StorageErrorCode.PERMISSION_DENIED,
                    message="下载功能未启用",
                    plugin_name=self.plugin_name
                )

            if not self._ensure_connection():
                return StorageResult(
                    code=StorageErrorCode.NETWORK_ERROR,
                    message="SFTP连接已断开，无法下载",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            remote_path = self._get_full_path(url)
            logger.info(f"下载文件: {remote_path} -> {local_path}")

            # 确保本地目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # 下载文件
            self.sftp.get(remote_path, local_path)

            logger.info(f"文件下载成功: {remote_path} -> {local_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件下载成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"SFTP下载失败: {e}")
            return StorageResult(
                code=StorageErrorCode.DOWNLOAD_FAILED,
                message=f"下载文件失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def download_bytes(self, url: str, **kwargs) -> StorageResult:
        """
        下载文件为字节流

        Args:
            url: 远程文件路径
            **kwargs: 额外参数

        Returns:
            StorageResult: 下载结果
        """
        try:
            # 检查下载功能是否启用
            if not self.config.get("enable_download", True):
                return StorageResult(
                    code=StorageErrorCode.PERMISSION_DENIED,
                    message="下载功能未启用",
                    plugin_name=self.plugin_name
                )

            if not self._ensure_connection():
                return StorageResult(
                    code=StorageErrorCode.NETWORK_ERROR,
                    message="SFTP连接已断开，无法下载",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            remote_path = self._get_full_path(url)

            # 下载文件到内存
            with self.sftp.open(remote_path, 'rb') as f:
                data = f.read()

            logger.info(f"文件下载到内存成功: {remote_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件下载成功",
                data={'bytes': data},
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"SFTP下载字节流失败: {e}")
            return StorageResult(
                code=StorageErrorCode.DOWNLOAD_FAILED,
                message=f"下载文件失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def upload_file(self, local_path: str, remote_path: str, **kwargs) -> StorageResult:
        """
        上传文件到远程

        Args:
            local_path: 本地文件路径
            remote_path: 远程保存路径
            **kwargs: 额外参数

        Returns:
            StorageResult: 上传结果
        """
        try:
            # 检查上传功能是否启用
            if not self.config.get("enable_upload", False):
                return StorageResult(
                    code=StorageErrorCode.PERMISSION_DENIED,
                    message="上传功能未启用",
                    plugin_name=self.plugin_name
                )

            if not self._ensure_connection():
                return StorageResult(
                    code=StorageErrorCode.NETWORK_ERROR,
                    message="SFTP连接已断开，无法上传",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_remote_path = self._get_full_path(remote_path)
            logger.info(f"上传文件: {local_path} -> {full_remote_path}")

            # 确保远程目录存在
            remote_dir = os.path.dirname(full_remote_path)
            if remote_dir:
                self._ensure_directory_exists(remote_dir)

            # 获取文件名
            filename = kwargs.get('filename', os.path.basename(local_path))
            if filename:
                full_remote_path = os.path.join(os.path.dirname(full_remote_path), filename).replace('\\', '/')

            # 上传文件
            self.sftp.put(local_path, full_remote_path)

            logger.info(f"文件上传成功: {local_path} -> {full_remote_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件上传成功",
                data={'path': remote_path},
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"SFTP上传失败: {e}")
            return StorageResult(
                code=StorageErrorCode.UPLOAD_FAILED,
                message=f"上传文件失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def delete_file(self, remote_path: str) -> StorageResult:
        """
        删除远程文件

        Args:
            remote_path: 远程文件路径

        Returns:
            StorageResult: 删除结果
        """
        try:
            # 检查删除功能是否启用
            if not self.config.get("enable_delete", False):
                return StorageResult(
                    code=StorageErrorCode.PERMISSION_DENIED,
                    message="删除功能未启用",
                    plugin_name=self.plugin_name
                )

            if not self._ensure_connection():
                return StorageResult(
                    code=StorageErrorCode.NETWORK_ERROR,
                    message="SFTP连接已断开，无法删除",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_path = self._get_full_path(remote_path)
            logger.info(f"删除文件: {full_path}")

            # 删除文件
            self.sftp.remove(full_path)

            logger.info(f"文件删除成功: {full_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件删除成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"SFTP删除失败: {e}")
            return StorageResult(
                code=StorageErrorCode.DELETE_FAILED,
                message=f"删除文件失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def delete_directory(self, remote_path: str) -> StorageResult:
        """
        删除远程目录

        Args:
            remote_path: 远程目录路径

        Returns:
            StorageResult: 删除结果
        """
        try:
            # 检查删除功能是否启用
            if not self.config.get("enable_delete", False):
                return StorageResult(
                    code=StorageErrorCode.PERMISSION_DENIED,
                    message="删除功能未启用",
                    plugin_name=self.plugin_name
                )

            if not self._ensure_connection():
                return StorageResult(
                    code=StorageErrorCode.NETWORK_ERROR,
                    message="SFTP连接已断开，无法删除",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_path = self._get_full_path(remote_path)
            logger.info(f"删除目录: {full_path}")

            # 递归删除目录
            self._delete_recursive(full_path)

            logger.info(f"目录删除成功: {full_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="目录删除成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"SFTP删除目录失败: {e}")
            return StorageResult(
                code=StorageErrorCode.DELETE_FAILED,
                message=f"删除目录失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def copy_file(self, source_path: str, target_path: str) -> StorageResult:
        """
        复制远程文件

        Args:
            source_path: 源文件路径
            target_path: 目标文件路径

        Returns:
            StorageResult: 复制结果
        """
        try:
            if not self._ensure_connection():
                return StorageResult(
                    code=StorageErrorCode.NETWORK_ERROR,
                    message="SFTP连接已断开，无法复制",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_source = self._get_full_path(source_path)
            full_target = self._get_full_path(target_path)
            logger.info(f"复制文件: {full_source} -> {full_target}")

            # 确保目标目录存在
            target_dir = os.path.dirname(full_target)
            if target_dir:
                self._ensure_directory_exists(target_dir)

            # SFTP不支持直接复制，需要下载后重新上传
            with self.sftp.open(full_source, 'rb') as src_file:
                with self.sftp.open(full_target, 'wb') as dst_file:
                    dst_file.write(src_file.read())

            logger.info(f"文件复制成功: {full_source} -> {full_target}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件复制成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"SFTP复制失败: {e}")
            return StorageResult(
                code=StorageErrorCode.COPY_FAILED,
                message=f"复制文件失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def list_files(self, remote_path: str = "", **kwargs) -> StorageResult:
        """
        列出远程文件

        Args:
            remote_path: 远程路径
            **kwargs: 额外参数，支持分页

        Returns:
            StorageResult: 包含文件列表数据
        """
        try:
            if not self._ensure_connection():
                return StorageResult(
                    code=StorageErrorCode.NETWORK_ERROR,
                    message="SFTP连接已断开，无法列出文件",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_path = self._get_full_path(remote_path)
            logger.info(f"列出文件: {full_path}")

            # 切换到目标目录
            if full_path:
                try:
                    self.sftp.chdir(full_path)
                except Exception as e:
                    logger.error(f"切换目录失败: {full_path}, {e}")
                    return StorageResult(
                        code=StorageErrorCode.PATH_NOT_FOUND,
                        message=f"目录不存在或无权访问: {full_path}",
                        plugin_name=self.plugin_name
                    )

            # 获取文件列表
            files = []
            dirs = []

            for item in self.sftp.listdir_attr():
                try:
                    file_info = {
                        'name': item.filename,
                        'size': item.st_size if not paramiko.S_ISDIR(item.st_mode) else 0,
                        'modified_time': datetime.fromtimestamp(item.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'type': 'dir' if paramiko.S_ISDIR(item.st_mode) else 'file'
                    }

                    # 构建相对路径
                    relative_path = f"{remote_path}/{item.filename}".lstrip('/') if remote_path else item.filename
                    file_info['path'] = relative_path

                    if file_info['type'] == 'dir':
                        dirs.append(file_info)
                    else:
                        files.append(file_info)

                except Exception as e:
                    logger.warning(f"解析文件信息失败: {item.filename}, {e}")
                    continue

            # 合并文件和目录（目录排在前面）
            all_items = dirs + files

            # 分页支持
            page = kwargs.get('page', 1)
            page_size = kwargs.get('page_size', 50)

            if page and page_size:
                start = (page - 1) * page_size
                end = start + page_size
                paginated_items = all_items[start:end]

                logger.info(f"SFTP文件列表获取成功: 总共{len(all_items)}个文件, 返回第{page}页({len(paginated_items)}条)")

                return StorageResult(
                    code=StorageErrorCode.SUCCESS,
                    message="获取文件列表成功",
                    data={
                        'files': paginated_items,
                        'total': len(all_items),
                        'page': page,
                        'page_size': page_size,
                        'total_pages': (len(all_items) + page_size - 1) // page_size
                    },
                    plugin_name=self.plugin_name
                )
            else:
                logger.info(f"SFTP文件列表获取成功: {len(all_items)}个文件")

                return StorageResult(
                    code=StorageErrorCode.SUCCESS,
                    message="获取文件列表成功",
                    data={'files': all_items},
                    plugin_name=self.plugin_name
                )

        except Exception as e:
            logger.error(f"SFTP列出文件失败: {e}")
            return StorageResult(
                code=StorageErrorCode.NETWORK_ERROR,
                message=f"列出文件失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def supports_pagination(self) -> bool:
        """
        检查插件是否支持分页

        Returns:
            bool: 是否支持分页
        """
        return True

    def _ensure_directory_exists(self, remote_path: str):
        """确保远程目录存在，不存在则创建"""
        try:
            # 尝试创建目录（如果已存在会忽略）
            parts = remote_path.split('/')
            current_path = ""
            for part in parts:
                if not part:
                    continue
                current_path = f"{current_path}/{part}" if current_path else part
                try:
                    self.sftp.mkdir(current_path)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"创建目录失败: {remote_path}, {e}")

    def _delete_recursive(self, path: str):
        """递归删除目录"""
        try:
            for item in self.sftp.listdir_attr(path):
                item_path = f"{path}/{item.filename}"
                if paramiko.S_ISDIR(item.st_mode):
                    self._delete_recursive(item_path)
                else:
                    self.sftp.remove(item_path)
            self.sftp.rmdir(path)
        except Exception as e:
            logger.error(f"删除目录失败: {path}, {e}")

    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性

        Returns:
            Dict[str, Any]: 支持的特性
        """
        return {
            'download': self.config.get("enable_download", True),
            'upload': self.config.get("enable_upload", True),
            'delete': self.config.get("enable_delete", True),
            'copy': True,
            'list_directories': True,
            'pagination': True,
            'protocol': 'SFTP'
        }

    def get_file_list_columns(self) -> list:
        """
        获取文件列表表格的列配置

        Returns:
            list: 列配置列表（对象字典格式）
        """
        return [
            {
                "field": "name",
                "title": "文件名",
                "width": 300,
                "min_width": 150,
                "resize_mode": "stretch"
            },
            {
                "field": "size",
                "title": "文件大小",
                "width": 120,
                "min_width": 80,
                "max_width": 200,
                "resize_mode": "interactive"
            },
            {
                "field": "modified_time",
                "title": "修改时间",
                "width": 180,
                "min_width": 150,
                "max_width": 250,
                "resize_mode": "interactive"
            },
            {
                "field": "type",
                "title": "文件类型",
                "width": 100,
                "min_width": 80,
                "max_width": 120,
                "resize_mode": "fixed"
            }
        ]

    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        try:
            if self.sftp:
                self.sftp.close()
                self.sftp = None
                logger.info("SFTP连接已关闭")
            if self.ssh:
                self.ssh.close()
                self.ssh = None
                logger.info("SSH连接已关闭")
        except Exception as e:
            logger.error(f"清理SFTP连接失败: {e}")
