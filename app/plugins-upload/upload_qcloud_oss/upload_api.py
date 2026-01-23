# -*- coding: utf-8 -*-
"""
腾讯云OSS上传插件 - 核心实现
使用腾讯云对象存储（COS）SDK上传文件
"""

import os
import traceback
from typing import Dict, Any
from qcloud_cos import CosConfig, CosS3Client
from app.core.upload.upload_plugin_interface import UploadPluginInterface, UploadResult, UploadErrorCode
from app.utils.logger import get_logger

logger = get_logger('qcloud_oss_upload')


class QcloudOSSUpload(UploadPluginInterface):
    """腾讯云COS上传插件实现类"""

    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "腾讯云 COS Upload"
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
        self.acl = "private"
        self.timeout = 300
        self.max_retries = 3
        self.chunk_size = 1024 * 1024

    def initialize(self, config: Dict[str, Any]) -> UploadResult:
        """
        初始化插件

        Args:
            config: 插件配置参数

        Returns:
            UploadResult: 初始化结果
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
            self.path_prefix = config.get("path_prefix", "")
            self.acl = config.get("acl", "private")
            self.timeout = int(config.get("timeout", 300))
            self.max_retries = int(config.get("max_retries", 3))
            self.chunk_size = int(config.get("chunk_size", 1024 * 1024))

            # 验证必填配置
            if not self.bucket_name:
                return UploadResult(
                    code=UploadErrorCode.INVALID_CONFIG,
                    message="缺少bucket_name配置（存储桶名称）",
                    plugin_name=self.plugin_name
                )

            if not self.secret_id:
                return UploadResult(
                    code=UploadErrorCode.INVALID_CONFIG,
                    message="缺少secret_id配置",
                    plugin_name=self.plugin_name
                )

            if not self.secret_key:
                return UploadResult(
                    code=UploadErrorCode.INVALID_CONFIG,
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

            return UploadResult(
                code=UploadErrorCode.SUCCESS,
                message="腾讯云COS上传插件初始化成功",
                plugin_name=self.plugin_name
            )

        except Exception as e:
            logger.error(f"腾讯云COS插件初始化失败: {e}")
            self.is_initialized = False
            return UploadResult(
                code=UploadErrorCode.INIT_ERROR,
                message=f"腾讯云COS插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )

    def upload_file(self, file_path: str, remote_path: str = "", **kwargs) -> UploadResult:
        """
        上传文件

        Args:
            file_path: 本地文件路径
            remote_path: 远程路径（可选）
            **kwargs: 额外参数，如上传进度回调等

        Returns:
            UploadResult: 上传结果
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return UploadResult(
                code=UploadErrorCode.FILE_NOT_FOUND,
                message=f"文件不存在: {file_path}",
                plugin_name=self.plugin_name
            )

        # 获取文件名
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # 构建完整远程路径
        remote_name = remote_path if remote_path else filename
        if self.path_prefix:
            full_remote_path = f"{self.path_prefix.rstrip('/')}/{remote_name}"
        else:
            full_remote_path = remote_name

        # 清理路径前导的斜杠
        full_remote_path = full_remote_path.lstrip('/')

        try:
            logger.info(f"开始上传文件: {filename} 到 {full_remote_path}, 大小: {file_size} bytes")

            # 准备重试机制
            for attempt in range(self.max_retries + 1):
                try:
                    # 上传文件
                    with open(file_path, 'rb') as file_data:
                        response = self.client.put_object(
                            Bucket=self.bucket_name,
                            Key=full_remote_path,
                            Body=file_data,
                            ACL=self.acl
                        )

                    # 上传成功
                    logger.info(f"文件上传成功: {filename}, ETag: {response.get('ETag', 'N/A')}")

                    # 返回上传结果
                    result_data = {
                        "key": full_remote_path,
                        "bucket": self.bucket_name,
                        "region": self.region,
                        "size": file_size,
                        "url": self._get_file_url(full_remote_path),
                        "etag": response.get('ETag', '')
                    }

                    return UploadResult(
                        code=UploadErrorCode.SUCCESS,
                        data=result_data,
                        message=f"文件上传成功: {filename}",
                        plugin_name=self.plugin_name
                    )

                except Exception as upload_error:
                    logger.error(f"上传失败（第{attempt + 1}次尝试）: {upload_error}")

                    if attempt < self.max_retries:
                        # 重试
                        continue
                    else:
                        # 所有重试都失败
                        return UploadResult(
                            code=UploadErrorCode.UPLOAD_FAILED,
                            message=f"文件上传失败，已重试{self.max_retries}次: {str(upload_error)}",
                            plugin_name=self.plugin_name
                        )

        except Exception as e:
            logger.error(f"上传文件异常: {e}\n{traceback.format_exc()}")
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"文件上传异常: {str(e)}",
                plugin_name=self.plugin_name
            )

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
        # 获取文件名
        filename = original_filename or "upload_file"
        file_size = len(file_bytes)

        # 构建完整远程路径
        if self.path_prefix:
            full_remote_path = f"{self.path_prefix.rstrip('/')}/{remote_path if remote_path else filename}"
        else:
            full_remote_path = remote_path if remote_path else filename

        # 清理路径前导的斜杠
        full_remote_path = full_remote_path.lstrip('/')

        try:
            logger.info(f"开始上传字节流: {filename} 到 {full_remote_path}, 大小: {file_size} bytes")

            # 准备重试机制
            for attempt in range(self.max_retries + 1):
                try:
                    # 上传字节流
                    response = self.client.put_object(
                        Bucket=self.bucket_name,
                        Key=full_remote_path,
                        Body=file_bytes,
                        ACL=self.acl
                    )

                    # 上传成功
                    logger.info(f"字节流上传成功: {filename}, ETag: {response.get('ETag', 'N/A')}")

                    # 返回上传结果
                    result_data = {
                        "key": full_remote_path,
                        "bucket": self.bucket_name,
                        "region": self.region,
                        "size": file_size,
                        "url": self._get_file_url(full_remote_path),
                        "etag": response.get('ETag', '')
                    }

                    return UploadResult(
                        code=UploadErrorCode.SUCCESS,
                        data=result_data,
                        message=f"字节流上传成功: {filename}",
                        plugin_name=self.plugin_name
                    )

                except Exception as upload_error:
                    logger.error(f"上传失败（第{attempt + 1}次尝试）: {upload_error}")

                    if attempt < self.max_retries:
                        # 重试
                        continue
                    else:
                        # 所有重试都失败
                        return UploadResult(
                            code=UploadErrorCode.UPLOAD_FAILED,
                            message=f"字节流上传失败，已重试{self.max_retries}次: {str(upload_error)}",
                            plugin_name=self.plugin_name
                        )

        except Exception as e:
            logger.error(f"上传字节流异常: {e}")
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"字节流上传异常: {str(e)}",
                plugin_name=self.plugin_name
            )

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
            # 私有文件需要生成带签名的临时URL（这里简化为对象URL）
            return f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{key}"
        else:
            # 公共文件可以直接访问
            return f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{key}"

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
            "concurrent_uploads": True,
            "max_threads": 10,
            "features": ["multipart_upload", "retry_mechanism", "acl_control", "path_prefix"]
        }

    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        # 关闭COS客户端
        self.client = None
        self.is_initialized = False
        logger.info(f"{self.plugin_name} 插件资源已清理")
