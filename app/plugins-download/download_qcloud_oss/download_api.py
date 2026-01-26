# -*- coding: utf-8 -*-
"""
腾讯云OSS下载插件 - 核心实现
使用腾讯云对象存储（COS）SDK下载文件
"""

import os
from typing import Dict, Any
from qcloud_cos import CosConfig, CosS3Client
from app.core.download.download_plugin_interface import DownloadPluginInterface, DownloadResult, DownloadErrorCode
from app.utils.logger import get_logger

logger = get_logger('qcloud_oss_download')


class QcloudOSSDownload(DownloadPluginInterface):
    """腾讯云COS下载插件实现类"""

    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "腾讯云 COS Download"
        self.plugin_version = "1.0.0"
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
        self.timeout = 300
        self.max_retries = 3

    def initialize(self, config: Dict[str, Any]) -> DownloadResult:
        """
        初始化插件

        Args:
            config: 插件配置参数

        Returns:
            DownloadResult: 初始化结果
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
            self.timeout = int(config.get("timeout", 300))
            self.max_retries = int(config.get("max_retries", 3))

            # 验证必填配置
            if not self.bucket_name:
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="缺少bucket_name配置（存储桶名称）",
                    plugin_name=self.plugin_name
                )

            if not self.secret_id:
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="缺少secret_id配置",
                    plugin_name=self.plugin_name
                )

            if not self.secret_key:
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="缺少secret_key配置",
                    plugin_name=self.plugin_name
                )

            # 配置COS客户端
            cos_config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
                Token=None,  # 临时密钥，一般不需要
                Scheme='https',
                Timeout=self.timeout
            )

            # 创建COS客户端
            self.client = CosS3Client(cos_config)

            self.is_initialized = True
            logger.info(f"{self.plugin_name} 插件初始化成功，存储桶: {self.bucket_name}, 地域: {self.region}")

            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                message="腾讯云COS下载插件初始化成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"腾讯云COS插件初始化失败: {e}")
            self.is_initialized = False
            return DownloadResult(
                code=DownloadErrorCode.INIT_ERROR,
                message=f"腾讯云COS插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def download_file(self, url: str, local_path: str, **kwargs) -> DownloadResult:
        """
        下载文件

        Args:
            url: 远程文件路径（COS中的Key）
            local_path: 本地保存路径
            **kwargs: 额外参数

        Returns:
            DownloadResult: 下载结果
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

                    return DownloadResult(
                        code=DownloadErrorCode.SUCCESS,
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
                        return DownloadResult(
                            code=DownloadErrorCode.DOWNLOAD_FAILED,
                            message=f"文件下载失败，已重试{self.max_retries}次: {str(download_error)}",
                            plugin_name=self.plugin_name
                        )

        except Exception as e:
            logger.error(f"下载文件异常: {e}")
            return DownloadResult(
                code=DownloadErrorCode.DOWNLOAD_FAILED,
                message=f"文件下载异常: {str(e)}",
                plugin_name=self.plugin_name
            )

    def download_bytes(self, url: str, **kwargs) -> DownloadResult:
        """
        下载文件为字节流

        Args:
            url: 远程文件路径
            **kwargs: 额外参数

        Returns:
            DownloadResult: 下载结果
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

            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                data=result_data,
                message=f"字节流下载成功: {full_remote_path}",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"下载字节流异常: {e}")
            return DownloadResult(
                code=DownloadErrorCode.DOWNLOAD_FAILED,
                message=f"字节流下载异常: {str(e)}",
                plugin_name=self.plugin_name
            )

    def list_files(self, remote_path: str = "", **kwargs) -> DownloadResult:
        """
        列出远程文件

        Args:
            remote_path: 远程路径（可选）
            **kwargs: 额外参数，支持分页

        Returns:
            DownloadResult: 包含文件列表数据
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
                marker = None

                while True:
                    list_kwargs = {
                        'Bucket': self.bucket_name,
                        'Prefix': prefix,
                        'MaxKeys': 1000
                    }

                    if marker:
                        list_kwargs['Marker'] = marker

                    response = self.client.list_objects(**list_kwargs)

                    # 解析文件列表
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            key = obj['Key']

                            # 跳过前缀本身的条目
                            if key == prefix.rstrip('/'):
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
                marker = None

                while True:
                    list_kwargs = {
                        'Bucket': self.bucket_name,
                        'Prefix': prefix,
                        'MaxKeys': 1000
                    }

                    if marker:
                        list_kwargs['Marker'] = marker

                    response = self.client.list_objects(**list_kwargs)

                    # 解析文件列表
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            key = obj['Key']

                            # 跳过前缀本身的条目
                            if key == prefix.rstrip('/'):
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

            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                data=result_data,
                message=f"获取文件列表成功: {len(files)} 个文件",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"列出文件异常: {e}")
            return DownloadResult(
                code=DownloadErrorCode.DOWNLOAD_FAILED,
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
            "features": ["retry_mechanism", "list_files", "path_prefix", "pagination"]
        }

    def supports_pagination(self) -> bool:
        """
        检查插件是否支持分页

        Returns:
            bool: 支持分页返回True
        """
        return True

    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        # 关闭COS客户端
        self.client = None
        self.is_initialized = False

    def delete_file(self, remote_path: str) -> DownloadResult:
        """
        删除远程文件

        Args:
            remote_path: 远程文件路径（相对于path_prefix）

        Returns:
            DownloadResult: 删除结果
        """
        try:
            if not self.client:
                return DownloadResult(
                    code=DownloadErrorCode.INIT_ERROR,
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
            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                message=f"文件 '{remote_path}' 删除成功",
                data={'path': remote_path}
            )

        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return DownloadResult(
                code=DownloadErrorCode.DOWNLOAD_FAILED,
                message=f"删除文件失败: {str(e)}"
            )

    def upload_file(self, local_path: str, remote_path: str, **kwargs) -> DownloadResult:
        """
        上传文件到远程

        Args:
            local_path: 本地文件路径
            remote_path: 远程保存路径（相对于path_prefix）
            **kwargs: 额外参数，如上传进度回调等

        Returns:
            DownloadResult: 上传结果
                data.path: 上传后的完整路径
        """
        import os

        try:
            if not self.client:
                return DownloadResult(
                    code=DownloadErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )

            # 检查本地文件是否存在
            if not os.path.exists(local_path):
                return DownloadResult(
                    code=DownloadErrorCode.FILE_NOT_FOUND,
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
                    Body=file
                )

            logger.info(f"文件上传成功: {object_key}")
            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                message=f"文件上传成功: {remote_path}",
                data={'path': remote_path, 'object_key': object_key}
            )

        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return DownloadResult(
                code=DownloadErrorCode.DOWNLOAD_FAILED,
                message=f"上传文件失败: {str(e)}"
            )
        logger.info(f"{self.plugin_name} 插件资源已清理")
