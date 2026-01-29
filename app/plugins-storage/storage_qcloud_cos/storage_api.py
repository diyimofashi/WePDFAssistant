# -*- coding: utf-8 -*-
"""
腾讯云COS云存储插件 - 核心实现
使用腾讯云对象存储（COS）SDK实现下载、上传、删除、列表功能
"""

import os
from typing import Dict, Any
from qcloud_cos import CosConfig, CosS3Client
from app.core.storage.storage_plugin_interface import StoragePluginInterface, StorageResult, StorageErrorCode
from app.utils.logger import get_logger

logger = get_logger('qcloud_cos_storage')


class QcloudCosStorage(StoragePluginInterface):
    """腾讯云COS云存储插件实现类"""

    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "腾讯云 COS Storage"
        self.plugin_version = "2.0.0"
        self.plugin_author = "PyPDF Team"
        self.config = config or {}

        # COS客户端
        self.client = None

        # 配置参数
        self.region = ""
        self.bucket_name = ""
        self.secret_id = ""
        self.secret_key = ""
        self.app_id = ""
        self.path_prefix = ""
        self.acl = "private"
        self.timeout = 300
        self.max_retries = 3

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

            # 从配置中获取COS参数
            self.region = config.get("region", "ap-guangzhou")
            self.bucket_name = config.get("bucket_name", "")
            self.secret_id = config.get("secret_id", "")
            self.secret_key = config.get("secret_key", "")
            self.app_id = config.get("app_id", "")
            # 确保 path_prefix 是字符串类型
            path_prefix = config.get("path_prefix", "")
            self.path_prefix = str(path_prefix) if path_prefix is not None else ""
            self.acl = config.get("acl", "private")
            self.timeout = int(config.get("timeout", 300))
            self.max_retries = int(config.get("max_retries", 3))

            # 验证必填配置
            if not self.bucket_name:
                return StorageResult(
                    code=StorageErrorCode.INVALID_CONFIG,
                    message="缺少bucket_name配置（存储桶名称）",
                    plugin_name=self.plugin_name
                )

            if not self.secret_id:
                return StorageResult(
                    code=StorageErrorCode.INVALID_CONFIG,
                    message="缺少secret_id配置",
                    plugin_name=self.plugin_name
                )

            if not self.secret_key:
                return StorageResult(
                    code=StorageErrorCode.INVALID_CONFIG,
                    message="缺少secret_key配置",
                    plugin_name=self.plugin_name
                )

            # 配置COS客户端
            cos_config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
                Token=None,
                Scheme='https',
                Timeout=self.timeout
            )

            # 创建COS客户端
            self.client = CosS3Client(cos_config)

            self.is_initialized = True
            logger.info(f"{self.plugin_name} 插件初始化成功，存储桶: {self.bucket_name}, 地域: {self.region}")

            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message="腾讯云COS云存储插件初始化成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"腾讯云COS插件初始化失败: {e}")
            self.is_initialized = False
            return StorageResult(
                code=StorageErrorCode.INIT_ERROR,
                message=f"腾讯云COS插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def download_file(self, url: str, local_path: str, **kwargs) -> StorageResult:
        """
        下载文件

        Args:
            url: 远程文件路径（COS中的Key）
            local_path: 本地保存路径
            **kwargs: 额外参数

        Returns:
            StorageResult: 下载结果
        """
        try:
            # 确保 url 是字符串类型
            url = str(url) if url is not None else ""
            logger.info(f"开始下载文件: {url} 到 {local_path}")

            # 构建完整远程路径
            if self.path_prefix:
                full_remote_path = f"{self.path_prefix.strip('/')}/{url.lstrip('/')}"
            else:
                full_remote_path = url.lstrip('/')

            # 准备重试机制
            for attempt in range(self.max_retries + 1):
                try:
                    # 下载文件
                    response = self.client.get_object(
                        Bucket=self.bucket_name,
                        Key=full_remote_path
                    )

                    # 确保本地目录存在
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    # 保存文件
                    with open(local_path, 'wb') as f:
                        f.write(response['Body'].get_raw_stream().read())

                    # 下载成功
                    logger.info(f"文件下载成功: {full_remote_path}")

                    result_data = {
                        "key": full_remote_path,
                        "bucket": self.bucket_name,
                        "region": self.region,
                        "local_path": local_path,
                        "size": os.path.getsize(local_path)
                    }

                    return StorageResult(
                        code=StorageErrorCode.SUCCESS,
                        data=result_data,
                        message=f"文件下载成功: {os.path.basename(local_path)}",
                        plugin_name=self.plugin_name
                    )

                except Exception as download_error:
                    logger.error(f"下载失败（第{attempt + 1}次尝试）: {download_error}")

                    if attempt < self.max_retries:
                        # 重试
                        continue
                    else:
                        # 所有重试都失败
                        return StorageResult(
                            code=StorageErrorCode.DOWNLOAD_FAILED,
                            message=f"文件下载失败，已重试{self.max_retries}次: {str(download_error)}",
                            plugin_name=self.plugin_name
                        )

        except Exception as e:
            logger.error(f"下载文件异常: {e}")
            return StorageResult(
                code=StorageErrorCode.DOWNLOAD_FAILED,
                message=f"文件下载异常: {str(e)}",
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
            # 确保 url 是字符串类型
            url = str(url) if url is not None else ""
            logger.info(f"开始下载字节流: {url}")

            # 构建完整远程路径
            if self.path_prefix:
                full_remote_path = f"{self.path_prefix.strip('/')}/{url.lstrip('/')}"
            else:
                full_remote_path = url.lstrip('/')

            # 下载文件
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=full_remote_path
            )

            # 获取字节数据
            file_bytes = response['Body'].get_raw_stream().read()

            logger.info(f"字节流下载成功: {full_remote_path}, 大小: {len(file_bytes)} bytes")

            result_data = {
                "key": full_remote_path,
                "bucket": self.bucket_name,
                "region": self.region,
                "bytes": file_bytes,
                "size": len(file_bytes)
            }

            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                data=result_data,
                message=f"字节流下载成功: {full_remote_path}",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"下载字节流异常: {e}")
            return StorageResult(
                code=StorageErrorCode.DOWNLOAD_FAILED,
                message=f"字节流下载异常: {str(e)}",
                plugin_name=self.plugin_name
            )

    def upload_file(self, local_path: str, remote_path: str, **kwargs) -> StorageResult:
        """
        上传文件到远程

        Args:
            local_path: 本地文件路径
            remote_path: 远程保存路径（相对于path_prefix）
            **kwargs: 额外参数

        Returns:
            StorageResult: 上传结果
                data.path: 上传后的完整路径
        """
        try:
            if not self.client:
                return StorageResult(
                    code=StorageErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )

            # 检查本地文件是否存在
            if not os.path.exists(local_path):
                return StorageResult(
                    code=StorageErrorCode.FILE_NOT_FOUND,
                    message=f"本地文件不存在: {local_path}"
                )

            # 构建完整的对象键
            if self.path_prefix:
                object_key = f"{self.path_prefix.rstrip('/')}/{remote_path}"
            else:
                object_key = remote_path

            logger.info(f"准备上传文件: {local_path} -> {object_key}")

            # 上传文件
            with open(local_path, 'rb') as file:
                response = self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=file,
                    ACL=self.acl
                )

            logger.info(f"文件上传成功: {object_key}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message=f"文件上传成功: {remote_path}",
                data={
                    'path': remote_path,
                    'object_key': object_key,
                    'url': self._get_file_url(object_key),
                    'size': os.path.getsize(local_path),
                    'etag': response.get('ETag', '')
                }
            )

        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return StorageResult(
                code=StorageErrorCode.UPLOAD_FAILED,
                message=f"上传文件失败: {str(e)}"
            )

    def delete_file(self, remote_path: str) -> StorageResult:
        """
        删除远程文件

        Args:
            remote_path: 远程文件路径（相对于path_prefix）

        Returns:
            StorageResult: 删除结果
        """
        try:
            if not self.client:
                return StorageResult(
                    code=StorageErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )

            # 构建完整的对象键
            if self.path_prefix:
                object_key = f"{self.path_prefix.rstrip('/')}/{remote_path}"
            else:
                object_key = remote_path

            logger.info(f"准备删除文件: {object_key}")

            # 删除文件
            response = self.client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )

            logger.info(f"文件删除成功: {object_key}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message=f"文件 '{remote_path}' 删除成功",
                data={'path': remote_path}
            )

        except Exception as e:
            logger.error(f"删除文件失败: {e}", exc_info=True)
            return StorageResult(
                code=StorageErrorCode.DELETE_FAILED,
                message=f"删除失败: {str(e)}"
            )

    def delete_directory(self, remote_path: str) -> StorageResult:
        """
        删除远程目录（递归删除目录下所有文件）

        Args:
            remote_path: 远程目录路径（相对于path_prefix）

        Returns:
            StorageResult: 删除结果
        """
        try:
            if not self.client:
                return StorageResult(
                    code=StorageErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )

            # 构建完整的对象键
            if self.path_prefix:
                object_key = f"{self.path_prefix.rstrip('/')}/{remote_path}"
            else:
                object_key = remote_path

            # 确保以 / 结尾作为前缀
            # 注意：腾讯云 COS 的对象键不应以 / 开头（除非是根目录）
            if object_key.startswith('/'):
                prefix = object_key[1:].rstrip('/') + '/'  # 移除开头的 /
            else:
                prefix = object_key.rstrip('/') + '/'

            logger.info(f"[delete_directory] 准备删除目录: prefix={prefix}, path_prefix={self.path_prefix}, remote_path={remote_path}, object_key={object_key}")
            logger.info(f"[delete_directory] Bucket={self.bucket_name}")

            # 参考官方代码，使用 Marker 和 IsTruncated 进行分页
            is_over = False
            marker = ''
            delete_count = 0

            while not is_over:
                # 列出对象
                list_result = self.client.list_objects(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    Marker=marker
                )

                logger.info(f"[delete_directory] list_objects 结果: marker={marker}, IsTruncated={list_result.get('IsTruncated', 'false')}, Contents数量={len(list_result.get('Contents', []))}")
                logger.info(f"[delete_directory] list_result keys: {list(list_result.keys())}")

                # 删除所有对象
                if 'Contents' in list_result:
                    for content in list_result['Contents']:
                        key = content['Key']
                        logger.info(f"[delete_directory] 准备删除对象: {key}, Size={content.get('Size', 0)}")
                        try:
                            self.client.delete_object(Bucket=self.bucket_name, Key=key)
                            delete_count += 1
                            logger.info(f"[delete_directory] 删除成功: {key}")
                        except Exception as e:
                            logger.error(f"[delete_directory] 删除失败: {key}, 错误: {e}", exc_info=True)

                # 检查是否还有更多对象
                # 注意：IsTruncated 可能是字符串 'false'/'true' 或布尔值
                is_truncated = list_result.get('IsTruncated', False)
                if isinstance(is_truncated, str):
                    is_truncated = is_truncated.lower() == 'true'

                if not is_truncated:
                    is_over = True
                else:
                    # 获取下一个 marker
                    if 'Contents' in list_result and list_result['Contents']:
                        marker = list_result['Contents'][-1]['Key']
                    else:
                        # 如果没有 Contents 但 IsTruncated 为 true，使用 NextMarker
                        marker = list_result.get('NextMarker', '')
                        if not marker:
                            is_over = True

            logger.info(f"目录删除完成，共删除 {delete_count} 个对象")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message=f"目录 '{remote_path}' 删除成功（共 {delete_count} 个文件）",
                data={'path': remote_path, 'count': delete_count}
            )

        except Exception as e:
            logger.error(f"删除目录失败: {e}", exc_info=True)
            return StorageResult(
                code=StorageErrorCode.DELETE_FAILED,
                message=f"删除目录失败: {str(e)}"
            )

    def delete_file(self, remote_path: str) -> StorageResult:
        """
        删除远程文件或目录

        Args:
            remote_path: 远程文件路径（相对于path_prefix）

        Returns:
            StorageResult: 删除结果
        """
        try:
            if not self.client:
                return StorageResult(
                    code=StorageErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )

            # 构建完整的对象键
            if self.path_prefix:
                object_key = f"{self.path_prefix.rstrip('/')}/{remote_path}"
            else:
                object_key = remote_path

            ***REMOVED*** COS 的对象键不应以 / 开头（除非是根目录）
            if object_key.startswith('/'):
                object_key = object_key[1:]

            logger.info(f"准备删除: {object_key}")

            # 尝试删除（如果是目录，需要递归删除目录下的所有文件）
            # 先尝试直接删除
            try:
                response = self.client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
                logger.info(f"删除成功: {object_key}")
                return StorageResult(
                    code=StorageErrorCode.SUCCESS,
                    message=f"文件 '{remote_path}' 删除成功",
                    data={'path': remote_path}
                )
            except Exception as e:
                # 如果删除失败，可能是目录，尝试列出目录内容并递归删除
                logger.info(f"直接删除失败，可能是目录，尝试递归删除: {object_key}, 错误: {e}")

                # 确保以 / 结尾作为前缀
                prefix = object_key.rstrip('/') + '/'

                # 参考官方代码，使用 Marker 和 IsTruncated 进行分页
                is_over = False
                marker = ''
                delete_count = 0

                while not is_over:
                    # 列出对象
                    list_result = self.client.list_objects(
                        Bucket=self.bucket_name,
                        Prefix=prefix,
                        Marker=marker
                    )

                    logger.info(f"递归删除 list_objects 结果: marker={marker}, IsTruncated={list_result.get('IsTruncated', 'false')}, Contents数量={len(list_result.get('Contents', []))}")

                    # 删除所有对象
                    if 'Contents' in list_result:
                        for content in list_result['Contents']:
                            key = content['Key']
                            logger.info(f"递归删除对象: {key}, Size={content.get('Size', 0)}")
                            try:
                                self.client.delete_object(Bucket=self.bucket_name, Key=key)
                                delete_count += 1
                                logger.info(f"递归删除成功: {key}")
                            except Exception as e:
                                logger.error(f"递归删除失败: {key}, 错误: {e}")

                    # 检查是否还有更多对象
                    is_truncated = list_result.get('IsTruncated', False)
                    if isinstance(is_truncated, str):
                        is_truncated = is_truncated.lower() == 'true'

                    if not is_truncated:
                        is_over = True
                    else:
                        # 获取下一个 marker
                        if 'Contents' in list_result and list_result['Contents']:
                            marker = list_result['Contents'][-1]['Key']
                        else:
                            marker = list_result.get('NextMarker', '')
                            if not marker:
                                is_over = True

                logger.info(f"递归删除完成，共删除 {delete_count} 个对象")
                return StorageResult(
                    code=StorageErrorCode.SUCCESS,
                    message=f"目录 '{remote_path}' 删除成功（共 {delete_count} 个文件）",
                    data={'path': remote_path, 'count': delete_count}
                )

        except Exception as e:
            logger.error(f"删除失败: {e}", exc_info=True)
            return StorageResult(
                code=StorageErrorCode.DELETE_FAILED,
                message=f"删除文件失败: {str(e)}"
            )

    def copy_file(self, source_path: str, target_path: str) -> StorageResult:
        """
        复制远程文件

        Args:
            source_path: 源文件路径（相对于path_prefix）
            target_path: 目标文件路径（相对于path_prefix）

        Returns:
            StorageResult: 复制结果
        """
        try:
            if not self.client:
                return StorageResult(
                    code=StorageErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )

            # 构建完整的对象键
            if self.path_prefix:
                source_key = f"{self.path_prefix.rstrip('/')}/{source_path}"
                target_key = f"{self.path_prefix.rstrip('/')}/{target_path}"
            else:
                source_key = source_path
                target_key = target_path

            logger.info(f"准备复制文件: {source_key} -> {target_key}")

            # 复制文件，Python SDK 使用 copy 方法
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_key,
                'Region': self.region
            }

            response = self.client.copy(
                Bucket=self.bucket_name,
                Key=target_key,
                CopySource=copy_source
            )

            logger.info(f"文件复制成功: {target_key}")
            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                message=f"文件复制成功",
                data={
                    'source_path': source_path,
                    'target_path': target_path,
                    'target_key': target_key
                }
            )

        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            return StorageResult(
                code=StorageErrorCode.COPY_FAILED,
                message=f"复制文件失败: {str(e)}"
            )

    def list_files(self, remote_path: str = "", **kwargs) -> StorageResult:
        """
        列出远程文件

        Args:
            remote_path: 远程路径（可选）
            **kwargs: 额外参数，支持分页

        Returns:
            StorageResult: 包含文件列表数据
        """
        try:
            # 确保 remote_path 是字符串类型
            remote_path = str(remote_path) if remote_path is not None else ""

            logger.info(f"list_files 被调用，参数: remote_path={remote_path!r}, kwargs={kwargs!r}")

            # 检查是否需要分页
            page = kwargs.get('page', 1)
            page_size = kwargs.get('page_size', 50)

            enable_pagination = 'page' in kwargs or 'page_size' in kwargs

            if enable_pagination:
                logger.info(f"开始列出文件（分页）: {remote_path}, 第{page}页, 每页{page_size}条")
            else:
                logger.info(f"开始列出文件: {remote_path}")

            # 构建完整远程路径
            if self.path_prefix:
                full_remote_path = f"{self.path_prefix.strip('/')}/{remote_path.lstrip('/')}"
            else:
                full_remote_path = remote_path.lstrip('/')

            # 清理路径尾随的斜杠（保留空字符串用于根目录）
            full_remote_path = full_remote_path.rstrip('/')

            # 获取对象列表
            if full_remote_path:
                prefix = full_remote_path + '/'
            else:
                prefix = ''

            # 如果是服务端分页，使用 Marker 参数
            if enable_pagination:
                # 先获取所有文件（使用不分页的方式）
                all_files = []
                dirs_processed = set()  # 记录已处理的目录，避免重复
                marker = None
                first_loop = True  # 标记是否第一次循环

                while True:
                    list_kwargs = {
                        'Bucket': self.bucket_name,
                        'Prefix': prefix,
                        'MaxKeys': 1000,
                        'Delimiter': '/'  # 添加分隔符来获取子目录
                    }

                    if marker:
                        list_kwargs['Marker'] = marker

                    response = self.client.list_objects(**list_kwargs)

                    # 调试日志
                    common_prefixes = response.get('CommonPrefixes', [])
                    contents = response.get('Contents', [])
                    logger.info(f"CommonPrefixes count: {len(common_prefixes)}")
                    logger.info(f"Contents count: {len(contents)}")
                    if common_prefixes:
                        for cp in common_prefixes:
                            logger.info(f"  CommonPrefix: {cp.get('Prefix')}")
                    if contents:
                        for c in contents[:5]:  # 只打印前5个
                            logger.info(f"  Content: {c.get('Key')}")

                    # 只在第一次循环时解析目录列表（CommonPrefixes）
                    if first_loop and 'CommonPrefixes' in response:
                        for prefix_obj in response['CommonPrefixes']:
                            prefix_key = prefix_obj['Prefix']

                            # 返回相对于 path_prefix 的路径
                            prefix_with_slash = self.path_prefix.strip('/') + '/'
                            if self.path_prefix and prefix_key.startswith(prefix_with_slash):
                                relative_path = prefix_key[len(prefix_with_slash):]
                            else:
                                relative_path = prefix_key

                            # 移除末尾的斜杠
                            dir_path = relative_path.rstrip('/')

                            # 检查是否已经处理过这个目录
                            if dir_path in dirs_processed:
                                continue
                            dirs_processed.add(dir_path)

                            # 如果 remote_path 不为空，name 应该是相对于 remote_path 的子目录名
                            if full_remote_path:
                                # 获取相对于 full_remote_path 的子路径
                                if dir_path.startswith(full_remote_path + '/'):
                                    name = dir_path[len(full_remote_path) + 1:]
                                    # 只取第一层子目录
                                    if '/' in name:
                                        name = name.split('/')[0]
                                else:
                                    name = os.path.basename(dir_path)
                            else:
                                # 根目录，直接使用 basename
                                name = os.path.basename(dir_path)
                                # 只取第一层子目录
                                if '/' in name:
                                    name = name.split('/')[0]

                            all_files.append({
                                'name': name,
                                'size': 0,
                                'modified_time': '',
                                'type': 'dir',
                                'path': dir_path
                            })

                        first_loop = False  # 标记目录已处理

                    # 解析文件列表
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            key = obj['Key']

                            # 跳过前缀本身的条目
                            if key == prefix.rstrip('/'):
                                continue

                            # 跳过以 / 结尾的目录（已经在 CommonPrefixes 中处理）
                            if key.endswith('/'):
                                continue

                            # 处理修改时间格式
                            modified_time = obj.get('LastModified', '')
                            if hasattr(modified_time, 'strftime'):
                                modified_time = modified_time.strftime('%Y-%m-%d %H:%M:%S')
                            elif isinstance(modified_time, str):
                                modified_time = modified_time
                            else:
                                modified_time = str(modified_time)

                            # 返回相对于 path_prefix 的路径
                            prefix_with_slash = self.path_prefix.strip('/') + '/'
                            if self.path_prefix and key.startswith(prefix_with_slash):
                                relative_path = key[len(prefix_with_slash):]
                            else:
                                relative_path = key

                            all_files.append({
                                'name': os.path.basename(key),
                                'size': obj['Size'],
                                'modified_time': modified_time,
                                'type': 'file',
                                'path': relative_path
                            })

                    # 检查是否还有更多数据
                    is_truncated = response.get('IsTruncated', False)
                    if not is_truncated:
                        break

                    # 使用最后一个 key 作为下一页的 marker
                    if 'Contents' in response and response['Contents']:
                        marker = response['Contents'][-1]['Key']
                    else:
                        break

                # 本地分页
                total_count = len(all_files)
                total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                files = all_files[start_idx:end_idx]

                logger.info(f"文件列表获取成功: 总共{total_count}个文件, 返回第{page}页({len(files)}条), 每页{page_size}条")
            else:
                # 不分页，一次性获取所有数据（使用分页循环确保获取所有文件）
                all_files = []
                dirs_processed = set()  # 记录已处理的目录，避免重复
                marker = None
                first_loop = True  # 标记是否第一次循环

                while True:
                    list_kwargs = {
                        'Bucket': self.bucket_name,
                        'Prefix': prefix,
                        'MaxKeys': 1000,
                        'Delimiter': '/'  # 添加分隔符来获取子目录
                    }

                    if marker:
                        list_kwargs['Marker'] = marker

                    response = self.client.list_objects(**list_kwargs)

                    # 调试日志
                    common_prefixes = response.get('CommonPrefixes', [])
                    contents = response.get('Contents', [])
                    logger.info(f"CommonPrefixes count: {len(common_prefixes)}")
                    logger.info(f"Contents count: {len(contents)}")
                    if common_prefixes:
                        for cp in common_prefixes:
                            logger.info(f"  CommonPrefix: {cp.get('Prefix')}")
                    if contents:
                        for c in contents[:5]:  # 只打印前5个
                            logger.info(f"  Content: {c.get('Key')}")

                    # 只在第一次循环时解析目录列表（CommonPrefixes）
                    if first_loop and 'CommonPrefixes' in response:
                        for prefix_obj in response['CommonPrefixes']:
                            prefix_key = prefix_obj['Prefix']

                            # 返回相对于 path_prefix 的路径
                            prefix_with_slash = self.path_prefix.strip('/') + '/'
                            if self.path_prefix and prefix_key.startswith(prefix_with_slash):
                                relative_path = prefix_key[len(prefix_with_slash):]
                            else:
                                relative_path = prefix_key

                            # 移除末尾的斜杠
                            dir_path = relative_path.rstrip('/')

                            # 检查是否已经处理过这个目录
                            if dir_path in dirs_processed:
                                continue
                            dirs_processed.add(dir_path)

                            # 如果 remote_path 不为空，name 应该是相对于 remote_path 的子目录名
                            if full_remote_path:
                                # 获取相对于 full_remote_path 的子路径
                                if dir_path.startswith(full_remote_path + '/'):
                                    name = dir_path[len(full_remote_path) + 1:]
                                    # 只取第一层子目录
                                    if '/' in name:
                                        name = name.split('/')[0]
                                else:
                                    name = os.path.basename(dir_path)
                            else:
                                # 根目录，直接使用 basename
                                name = os.path.basename(dir_path)
                                # 只取第一层子目录
                                if '/' in name:
                                    name = name.split('/')[0]

                            all_files.append({
                                'name': name,
                                'size': 0,
                                'modified_time': '',
                                'type': 'dir',
                                'path': dir_path
                            })

                        first_loop = False  # 标记目录已处理

                    # 解析文件列表
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            key = obj['Key']

                            # 跳过前缀本身的条目
                            if key == prefix.rstrip('/'):
                                continue

                            # 跳过以 / 结尾的目录（已经在 CommonPrefixes 中处理）
                            if key.endswith('/'):
                                continue

                            # 处理修改时间格式
                            modified_time = obj.get('LastModified', '')
                            if hasattr(modified_time, 'strftime'):
                                modified_time = modified_time.strftime('%Y-%m-%d %H:%M:%S')
                            elif isinstance(modified_time, str):
                                modified_time = modified_time
                            else:
                                modified_time = str(modified_time)

                            # 返回相对于 path_prefix 的路径
                            prefix_with_slash = self.path_prefix.strip('/') + '/'
                            if self.path_prefix and key.startswith(prefix_with_slash):
                                relative_path = key[len(prefix_with_slash):]
                            else:
                                relative_path = key

                            all_files.append({
                                'name': os.path.basename(key),
                                'size': obj['Size'],
                                'modified_time': modified_time,
                                'type': 'file',
                                'path': relative_path
                            })

                    # 检查是否还有更多数据
                    is_truncated = response.get('IsTruncated', False)
                    if not is_truncated:
                        break

                    # 使用最后一个 key 作为下一页的 marker
                    if 'Contents' in response and response['Contents']:
                        marker = response['Contents'][-1]['Key']
                    else:
                        break

                files = all_files
                total_count = len(files)
                total_pages = 1

                logger.info(f"文件列表获取成功: {len(files)} 个文件")

            result_data = {'files': files}

            if enable_pagination:
                result_data['total'] = total_count
                result_data['page'] = page
                result_data['page_size'] = page_size
                result_data['total_pages'] = total_pages

            return StorageResult(
                code=StorageErrorCode.SUCCESS,
                data=result_data,
                message=f"获取文件列表成功: {len(files)} 个文件",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"列出文件异常: {e}")
            return StorageResult(
                code=StorageErrorCode.DOWNLOAD_FAILED,
                message=f"列出文件异常: {str(e)}",
                plugin_name=self.plugin_name
            )

    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性

        Returns:
            Dict[str, Any]: 支持的特性
        """
        return {
            "protocols": ["cos", "s3"],
            "storage_provider": "Tencent Cloud COS",
            "auth_methods": ["secret_key"],
            "max_file_size": "5TB (取决于存储桶配置）",
            "concurrent_downloads": True,
            "concurrent_uploads": True,
            "features": ["retry_mechanism", "list_files", "path_prefix", "pagination", "acl_control"]
        }

    def supports_pagination(self) -> bool:
        """
        检查插件是否支持分页

        Returns:
            bool: 支持分页返回True
        """
        return True

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

    def _get_file_url(self, key: str) -> str:
        """
        获取文件的访问URL

        Args:
            key: 文件在COS中的Key

        Returns:
            str: 文件的访问URL
        """
        # 根据ACL返回不同的URL
        if self.acl == "private":
            return f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{key}"
        else:
            return f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{key}"

    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        # 关闭COS客户端
        self.client = None
        self.is_initialized = False
