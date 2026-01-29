# -*- coding: utf-8 -*-
"""
FTP云存储插件 - 核心实现
使用Python标准库ftplib实现FTP文件操作
"""

import os
import ftplib
from typing import Dict, Any
from datetime import datetime
from app.core.storage.storage_plugin_interface import StoragePluginInterface, StorageResult, StorageErrorCode
from app.utils.logger import get_logger

logger = get_logger('ftp_storage')


class FTPStorage(StoragePluginInterface):
    """FTP云存储插件实现类"""

    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "FTP Storage"
        self.plugin_version = "1.0.0"
        self.plugin_author = "PyPDF Team"
        self.config = config or {}

        # FTP连接
        self.ftp = None

        # 配置参数
        self.host = ""
        self.port = 21
        self.username = ""
        self.password = ""
        self.path_prefix = ""
        self.passive_mode = True
        self.encoding = "utf-8"
        self.timeout = 30

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

            # 从配置中获取FTP参数
            self.host = config.get("host", "")
            self.port = int(config.get("port", 21))
            self.username = config.get("username", "")
            self.password = config.get("password", "")
            path_prefix = config.get("path_prefix", "")
            self.path_prefix = str(path_prefix) if path_prefix is not None else ""
            self.passive_mode = config.get("passive_mode", True)
            self.encoding = config.get("encoding", "utf-8")
            self.timeout = int(config.get("timeout", 30))

            # 验证必填配置
            if not self.host:
                return StorageResult(
                    code=StorageErrorCode.INVALID_CONFIG,
                    message="缺少host配置（FTP服务器地址）",
                    plugin_name=self.plugin_name
                )

            if not self.username:
                return StorageResult(
                    code=StorageErrorCode.INVALID_CONFIG,
                    message="缺少username配置（FTP用户名）",
                    plugin_name=self.plugin_name
                )

            # 测试连接
            try:
                self.ftp = ftplib.FTP()
                self.ftp.encoding = self.encoding
                self.ftp.connect(self.host, self.port, timeout=self.timeout)
                self.ftp.login(self.username, self.password)

                # 设置传输模式（主动或被动）
                self.ftp.set_pasv(self.passive_mode)
                mode_name = "被动" if self.passive_mode else "主动"
                logger.info(f"FTP连接成功: {self.host}:{self.port}，使用{mode_name}模式")
                self.is_initialized = True
                return StorageResult(
                    code=StorageErrorCode.SUCCESS,
                    message="FTP插件初始化成功",
                    plugin_name=self.plugin_name
                )
            except ftplib.error_perm as e:
                return StorageResult(
                    code=StorageErrorCode.PERMISSION_DENIED,
                    message=f"FTP认证失败: {str(e)}",
                    plugin_name=self.plugin_name
                )
            except Exception as e:
                logger.error(f"FTP连接失败: {e}")
                return StorageResult(
                    code=StorageErrorCode.INIT_ERROR,
                    message=f"FTP连接失败: {str(e)}",
                    plugin_name=self.plugin_name
                )

        except Exception as e:
            logger.error(f"FTP插件初始化异常: {e}")
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"FTP插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def _ensure_connection(self):
        """确保FTP连接可用"""
        if not self.ftp:
            logger.warning("FTP连接不存在")
            return False

        try:
            # 发送NOOP命令保持连接并检查连接状态
            self.ftp.voidcmd('NOOP')
            # 确保传输模式设置正确
            self.ftp.set_pasv(self.passive_mode)
            logger.debug("FTP连接检查通过")
            return True
        except Exception as e:
            logger.warning(f"FTP连接检查失败: {e}，尝试重新连接")
            # 关闭旧连接
            try:
                self.ftp.quit()
            except:
                try:
                    self.ftp.close()
                except:
                    pass
            self.ftp = None

            # 重新连接
            try:
                logger.info(f"正在重新连接FTP: {self.host}:{self.port}")
                self.ftp = ftplib.FTP()
                self.ftp.encoding = self.encoding
                self.ftp.connect(self.host, self.port, timeout=self.timeout)
                self.ftp.login(self.username, self.password)
                self.ftp.set_pasv(self.passive_mode)
                logger.info("FTP重新连接成功")
                return True
            except Exception as reconnect_error:
                logger.error(f"FTP重新连接失败: {reconnect_error}")
                self.ftp = None
                return False

    def _get_full_path(self, remote_path: str) -> str:
        """获取完整路径"""
        remote_path = remote_path.lstrip('/')
        if self.path_prefix:
            # 确保 path_prefix 没有前导斜杠，然后拼接
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
                    message="FTP连接已断开，无法下载",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            remote_path = self._get_full_path(url)
            logger.info(f"下载文件准备: url={url}, remote_path={remote_path}, local_path={local_path}")

            # 先回到根目录，确保路径解析正确
            try:
                self.ftp.cwd('/')
                logger.debug("下载前已返回根目录")
            except Exception as e:
                logger.warning(f"下载前返回根目录失败: {e}")

            # 确保本地目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # 下载文件
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f'RETR {remote_path}', f.write)

            logger.info(f"文件下载成功: {remote_path} -> {local_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件下载成功",
                plugin_name=self.plugin_name
            )

        except ftplib.error_perm as e:
            logger.error(f"FTP下载失败（权限）: {e}")
            return StorageResult(
                code=StorageErrorCode.PERMISSION_DENIED,
                message=f"下载文件失败，权限不足: {str(e)}",
                plugin_name=self.plugin_name
            )
        except ftplib.error_temp as e:
            logger.error(f"FTP下载失败（临时错误）: {e}")
            return StorageResult(
                code=StorageErrorCode.NETWORK_ERROR,
                message=f"下载文件失败: {str(e)}",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            logger.error(f"FTP下载失败: {e}")
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
                    message="FTP连接已断开，无法下载",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            remote_path = self._get_full_path(url)

            # 先回到根目录，确保路径解析正确
            try:
                self.ftp.cwd('/')
                logger.debug("下载字节流前已返回根目录")
            except Exception as e:
                logger.warning(f"下载字节流前返回根目录失败: {e}")

            # 下载文件到内存
            from io import BytesIO
            buffer = BytesIO()
            self.ftp.retrbinary(f'RETR {remote_path}', buffer.write)
            data = buffer.getvalue()

            logger.info(f"文件下载到内存成功: {remote_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件下载成功",
                data={'bytes': data},
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"FTP下载字节流失败: {e}")
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
                    message="FTP连接已断开，无法上传",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_remote_path = self._get_full_path(remote_path)
            logger.info(f"FTP上传，remote_path={remote_path}, full_remote_path={full_remote_path}, path_prefix={self.path_prefix}")

            # 先回到根目录，确保路径解析正确
            try:
                self.ftp.cwd('/')
                logger.debug("上传前已返回根目录")
            except Exception as e:
                logger.warning(f"上传前返回根目录失败: {e}")

            # 确保远程目录存在
            remote_dir = os.path.dirname(full_remote_path)
            if remote_dir:
                self._ensure_directory_exists(remote_dir)

            # 上传文件
            filename = kwargs.get('filename', os.path.basename(local_path))
            if filename:
                # 构建完整远程路径
                if full_remote_path and full_remote_path != filename:
                    full_remote_path = os.path.join(os.path.dirname(full_remote_path), filename).replace('\\', '/')
                else:
                    full_remote_path = filename

            # 获取文件大小用于日志
            file_size = os.path.getsize(local_path)
            logger.info(f"准备上传文件: {local_path}, 大小: {file_size} 字节, 远程路径: {full_remote_path}")

            # 上传文件，使用更大的块大小以提高性能
            with open(local_path, 'rb') as f:
                # 使用8192字节块大小（默认是8192）
                self.ftp.storbinary(f'STOR {full_remote_path}', f, blocksize=8192)

            logger.info(f"文件上传成功: {local_path} -> {full_remote_path}")
            logger.info(f"上传返回的相对路径: {remote_path}")
            # 返回相对路径（相对于path_prefix）
            result = StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件上传成功",
                data={'path': remote_path},
                plugin_name=self.plugin_name
            )
            logger.info(f"创建StorageResult成功，准备返回")
            return result

        except ftplib.error_temp as e:
            error_msg = str(e)
            logger.error(f"FTP上传失败（临时错误）: {error_msg}")
            # 如果是超时或连接错误，尝试重试一次
            if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
                logger.info("检测到连接问题，尝试重新连接并重试上传")
                try:
                    # 关闭旧连接
                    if self.ftp:
                        try:
                            self.ftp.quit()
                        except:
                            try:
                                self.ftp.close()
                            except:
                                pass
                        self.ftp = None

                    # 重新连接
                    self.ftp = ftplib.FTP()
                    self.ftp.encoding = self.encoding
                    self.ftp.connect(self.host, self.port, timeout=self.timeout)
                    self.ftp.login(self.username, self.password)
                    self.ftp.set_pasv(self.passive_mode)
                    logger.info("重新连接成功，准备重试上传")

                    # 重新上传
                    full_remote_path = self._get_full_path(remote_path)

                    # 先回到根目录，确保路径解析正确
                    try:
                        self.ftp.cwd('/')
                    except:
                        pass

                    remote_dir = os.path.dirname(full_remote_path)
                    if remote_dir:
                        self._ensure_directory_exists(remote_dir)

                    filename = kwargs.get('filename', os.path.basename(local_path))
                    if filename:
                        if full_remote_path and full_remote_path != filename:
                            full_remote_path = os.path.join(os.path.dirname(full_remote_path), filename).replace('\\', '/')
                        else:
                            full_remote_path = filename

                    with open(local_path, 'rb') as f:
                        self.ftp.storbinary(f'STOR {full_remote_path}', f, blocksize=8192)

                    logger.info(f"重试上传成功: {local_path} -> {full_remote_path}")
                    return StorageResult(
                        code=StorageErrorCode.SUCCESS,
                        message="文件上传成功",
                        data={'path': remote_path},
                        plugin_name=self.plugin_name
                    )
                except Exception as retry_error:
                    logger.error(f"重试上传失败: {retry_error}")
                    return StorageResult(
                        code=StorageErrorCode.UPLOAD_FAILED,
                        message=f"上传文件失败（重试后仍失败）: {str(retry_error)}",
                        plugin_name=self.plugin_name
                    )

            return StorageResult(
                code=StorageErrorCode.UPLOAD_FAILED,
                message=f"上传文件失败: {error_msg}",
                plugin_name=self.plugin_name
            )
        except ftplib.error_perm as e:
            logger.error(f"FTP上传失败（权限）: {e}")
            return StorageResult(
                code=StorageErrorCode.PERMISSION_DENIED,
                message=f"上传文件失败，权限不足: {str(e)}",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            logger.error(f"FTP上传失败: {e}")
            import traceback
            logger.error(f"上传异常堆栈: {traceback.format_exc()}")
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
                    message="FTP连接已断开，无法删除",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_path = self._get_full_path(remote_path)
            logger.info(f"准备删除文件，remote_path={remote_path}, full_path={full_path}")

            # 先回到根目录，确保路径解析正确
            try:
                self.ftp.cwd('/')
                logger.debug("删除前已返回根目录")
            except Exception as e:
                logger.warning(f"删除前返回根目录失败: {e}")

            # 删除文件
            self.ftp.delete(full_path)

            logger.info(f"文件删除成功: {full_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件删除成功",
                plugin_name=self.plugin_name
            )

        except ftplib.error_perm as e:
            logger.error(f"FTP删除失败（权限）: {e}")
            return StorageResult(
                code=StorageErrorCode.PERMISSION_DENIED,
                message=f"删除文件失败，权限不足: {str(e)}",
                plugin_name=self.plugin_name
            )
        except ftplib.error_temp as e:
            if '550' in str(e):
                return StorageResult(
                    code=StorageErrorCode.FILE_NOT_FOUND,
                    message="文件不存在",
                    plugin_name=self.plugin_name
                )
            logger.error(f"FTP删除失败（临时错误）: {e}")
            return StorageResult(
                code=StorageErrorCode.DELETE_FAILED,
                message=f"删除文件失败: {str(e)}",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            logger.error(f"FTP删除失败: {e}")
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
                    message="FTP连接已断开，无法删除",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_path = self._get_full_path(remote_path)
            logger.info(f"准备删除目录，remote_path={remote_path}, full_path={full_path}")

            # 先回到根目录，确保路径解析正确
            try:
                self.ftp.cwd('/')
                logger.debug("删除目录前已返回根目录")
            except Exception as e:
                logger.warning(f"删除目录前返回根目录失败: {e}")

            # 删除目录及其内容
            def _delete_recursive(path):
                """递归删除目录"""
                try:
                    # 尝试删除文件
                    self.ftp.delete(path)
                    logger.debug(f"删除文件: {path}")
                except ftplib.error_perm:
                    # 如果是目录，递归删除
                    try:
                        original_cwd = self.ftp.pwd()
                        self.ftp.cwd(path)
                        items = self.ftp.nlst()
                        for item in items:
                            _delete_recursive(os.path.join(path, item).replace('\\', '/'))
                        self.ftp.cwd(original_cwd)
                        self.ftp.rmd(path)
                        logger.debug(f"删除目录: {path}")
                    except Exception as e:
                        logger.error(f"删除目录失败: {path}, {e}")
            
            _delete_recursive(full_path)
            
            logger.info(f"目录删除成功: {full_path}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="目录删除成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"FTP删除目录失败: {e}")
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
                    message="FTP连接已断开，无法复制",
                    plugin_name=self.plugin_name
                )

            # FTP不支持直接复制，需要下载后重新上传
            from io import BytesIO

            # 获取完整路径
            full_source = self._get_full_path(source_path)
            full_target = self._get_full_path(target_path)
            logger.info(f"准备复制文件，source_path={source_path}, target_path={target_path}, full_source={full_source}, full_target={full_target}")

            # 先回到根目录，确保路径解析正确
            try:
                self.ftp.cwd('/')
                logger.debug("复制前已返回根目录")
            except Exception as e:
                logger.warning(f"复制前返回根目录失败: {e}")

            # 确保目标目录存在
            target_dir = os.path.dirname(full_target)
            if target_dir:
                self._ensure_directory_exists(target_dir)

            # 下载到内存
            buffer = BytesIO()
            self.ftp.retrbinary(f'RETR {full_source}', buffer.write)

            # 上传到目标位置
            buffer.seek(0)
            self.ftp.storbinary(f'STOR {full_target}', buffer)

            logger.info(f"文件复制成功: {full_source} -> {full_target}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="文件复制成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"FTP复制失败: {e}")
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
                    message="FTP连接已断开，无法列出文件",
                    plugin_name=self.plugin_name
                )

            # 获取完整路径
            full_path = self._get_full_path(remote_path)
            logger.info(f"FTP列出文件，remote_path={remote_path}, full_path={full_path}")

            # 先回到根目录，然后切换到目标目录
            try:
                self.ftp.cwd('/')
            except:
                pass

            # 切换到目标目录
            if full_path:
                try:
                    self.ftp.cwd(full_path)
                    logger.info(f"成功切换到目录: {full_path}")
                except ftplib.error_perm as e:
                    logger.error(f"切换目录失败: {full_path}, 错误: {e}")
                    return StorageResult(
                        code=StorageErrorCode.PATH_NOT_FOUND,
                        message=f"目录不存在或无权访问: {full_path}",
                        plugin_name=self.plugin_name
                    )

            # 获取文件列表
            files = []
            dirs = []

            # 获取文件列表
            items = self.ftp.nlst()
            logger.info(f"获取到 {len(items)} 个项目")
            
            for item in items:
                try:
                    # 尝试解析文件信息
                    try:
                        # 获取文件大小和修改时间
                        file_info = self.ftp.size(item)
                        size = file_info
                        file_type = 'file'
                    except ftplib.error_perm:
                        # 如果无法获取大小，可能是目录
                        size = 0
                        file_type = 'dir'
                    
                    # 构建文件信息
                    # 返回相对于path_prefix的路径，与COS插件保持一致
                    relative_path = f"{remote_path}/{item}".lstrip('/') if remote_path else item
                    file_path = relative_path
                    logger.debug(f"构建文件路径: item={item}, remote_path={remote_path}, file_path={file_path}")

                    if file_type == 'dir':
                        dirs.append({
                            'name': item,
                            'path': file_path,
                            'size': 0,
                            'type': 'dir',
                            'modified_time': ''
                        })
                    else:
                        # 尝试获取修改时间（FTP标准可能不支持）
                        modified_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        files.append({
                            'name': item,
                            'path': file_path,
                            'size': size,
                            'type': 'file',
                            'modified_time': modified_time
                        })
                
                except Exception as e:
                    logger.warning(f"解析文件信息失败: {item}, {e}")
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
                
                logger.info(f"FTP文件列表获取成功: 总共{len(all_items)}个文件, 返回第{page}页({len(paginated_items)}条), 每页{page_size}条")
                
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
                logger.info(f"FTP文件列表获取成功: {len(all_items)}个文件")
                
                return StorageResult(
                    code=StorageErrorCode.SUCCESS,
                    message="获取文件列表成功",
                    data={'files': all_items},
                    plugin_name=self.plugin_name
                )

        except Exception as e:
            logger.error(f"FTP列出文件失败: {e}")
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
            # 尝试切换到目录
            original_cwd = self.ftp.pwd()
            try:
                self.ftp.cwd(remote_path)
                self.ftp.cwd(original_cwd)
            except ftplib.error_perm:
                # 目录不存在，创建
                parts = remote_path.split('/')
                current_path = ""
                for part in parts:
                    if not part:
                        continue
                    current_path = f"{current_path}/{part}" if current_path else part
                    try:
                        self.ftp.cwd(current_path)
                    except ftplib.error_perm:
                        try:
                            self.ftp.mkd(current_path)
                            self.ftp.cwd(current_path)
                        except:
                            pass
                self.ftp.cwd(original_cwd)
        except Exception as e:
            logger.warning(f"创建目录失败: {remote_path}, {e}")

    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性

        Returns:
            Dict[str, Any]: 支持的特性
        """
        return {
            'download': self.config.get("enable_download", True),
            'upload': self.config.get("enable_upload", False),
            'delete': self.config.get("enable_delete", False),
            'copy': True,
            'list_directories': True,
            'pagination': True,
            'protocol': 'FTP',
            'passive_mode': self.passive_mode
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
            if self.ftp:
                try:
                    self.ftp.quit()
                except:
                    self.ftp.close()
                self.ftp = None
                logger.info("FTP连接已关闭")
        except Exception as e:
            logger.error(f"清理FTP连接失败: {e}")
