"""
HTTP上传插件 - 核心实现
使用HTTP协议上传文件到服务器
"""

import os
import requests
from typing import Dict, Any
from app.core.upload.upload_plugin_interface import UploadPluginInterface, UploadResult, UploadErrorCode


class HttpUpload(UploadPluginInterface):
    """HTTP上传插件实现类"""
    
    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "HTTP Upload Plugin"
        self.plugin_version = "1.0.0"
        self.plugin_author = "Developer"
        self.config = config or {}
        
        # HTTP客户端配置
        self.base_url = ""
        self.headers = {}
        self.auth = None
        self.timeout = 30
        self.max_retries = 3
    
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
            
            # 从配置中获取HTTP参数
            self.base_url = config.get("base_url", "")
            # 确保custom_headers是字典类型，然后复制
            custom_headers = config.get("custom_headers", {})
            if isinstance(custom_headers, dict):
                self.headers = custom_headers.copy()
            else:
                self.headers = {}
            self.timeout = config.get("timeout", 30)
            self.max_retries = config.get("max_retries", 3)
            
            # 设置认证信息
            auth_type = config.get("auth_type", "none")
            if auth_type == "basic":
                username = config.get("username", "")
                password = config.get("password", "")
                if username and password:
                    self.auth = (username, password)
            elif auth_type == "token":
                token = config.get("token", "")
                if token:
                    self.headers["Authorization"] = f"Bearer {token}"
            elif auth_type == "api_key":
                api_key = config.get("api_key", "")
                api_key_header = config.get("api_key_header", "X-API-Key")
                if api_key:
                    self.headers[api_key_header] = api_key
            
            # 验证配置
            if not self.base_url:
                return UploadResult(
                    code=UploadErrorCode.INVALID_CONFIG,
                    message="缺少base_url配置",
                    plugin_name=self.plugin_name
                )
            
            self.is_initialized = True
            
            return UploadResult(
                code=UploadErrorCode.SUCCESS,
                message="HTTP上传插件初始化成功",
                plugin_name=self.plugin_name
            )
            
        except Exception as e:
            self.is_initialized = False
            return UploadResult(
                code=UploadErrorCode.INIT_ERROR,
                message=f"HTTP上传插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def upload_file(self, file_path: str, remote_path: str = "", **kwargs) -> UploadResult:
        """
        上传文件
        
        Args:
            file_path: 本地文件路径
            remote_path: 远程路径（可选，会附加到base_url后面）
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
        
        try:
            # 构建上传URL
            upload_url = self.base_url
            if remote_path:
                upload_url = f"{upload_url.rstrip('/')}/{remote_path.lstrip('/')}"
            
            # 准备重试机制
            for attempt in range(self.max_retries + 1):
                try:
                    # 打开文件并上传
                    with open(file_path, 'rb') as file:
                        files = {'file': (os.path.basename(file_path), file)}
                        
                        # 执行HTTP POST请求
                        response = requests.post(
                            upload_url,
                            files=files,
                            headers=self.headers,
                            auth=self.auth,
                            timeout=self.timeout
                        )
                        
                        if response.status_code in [200, 201]:
                            # 上传成功
                            try:
                                response_data = response.json() if response.content else {}
                            except ValueError:
                                # 如果响应不是JSON格式，返回文本内容
                                response_data = {"response_text": response.text}
                            
                            return UploadResult(
                                code=UploadErrorCode.SUCCESS,
                                data=response_data,
                                message="文件上传成功",
                                plugin_name=self.plugin_name
                            )
                        else:
                            # 上传失败，准备重试
                            if attempt < self.max_retries:
                                continue
                            else:
                                # 所有重试都失败
                                return UploadResult(
                                    code=UploadErrorCode.UPLOAD_FAILED,
                                    message=f"HTTP上传失败，状态码: {response.status_code}, 响应: {response.text}",
                                    plugin_name=self.plugin_name
                                )
                
                except requests.exceptions.RequestException as e:
                    if attempt < self.max_retries:
                        continue  # 重试
                    else:
                        # 所有重试都失败
                        return UploadResult(
                            code=UploadErrorCode.CONNECTION_ERROR,
                            message=f"HTTP连接错误: {str(e)}",
                            plugin_name=self.plugin_name
                        )
            
        except Exception as e:
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"HTTP文件上传失败: {str(e)}",
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
        try:
            # 构建上传URL
            upload_url = self.base_url
            if remote_path:
                upload_url = f"{upload_url.rstrip('/')}/{remote_path.lstrip('/')}"
            
            # 准备重试机制
            for attempt in range(self.max_retries + 1):
                try:
                    # 准备文件数据
                    filename = original_filename or "upload_file"
                    files = {'file': (filename, file_bytes)}
                    
                    # 执行HTTP POST请求
                    response = requests.post(
                        upload_url,
                        files=files,
                        headers=self.headers,
                        auth=self.auth,
                        timeout=self.timeout
                    )
                    
                    if response.status_code in [200, 201]:
                        # 上传成功
                        try:
                            response_data = response.json() if response.content else {}
                        except ValueError:
                            # 如果响应不是JSON格式，返回文本内容
                            response_data = {"response_text": response.text}
                        
                        return UploadResult(
                            code=UploadErrorCode.SUCCESS,
                            data=response_data,
                            message="字节流上传成功",
                            plugin_name=self.plugin_name
                        )
                    else:
                        # 上传失败，准备重试
                        if attempt < self.max_retries:
                            continue
                        else:
                            # 所有重试都失败
                            return UploadResult(
                                code=UploadErrorCode.UPLOAD_FAILED,
                                message=f"HTTP上传失败，状态码: {response.status_code}, 响应: {response.text}",
                                plugin_name=self.plugin_name
                            )
                
                except requests.exceptions.RequestException as e:
                    if attempt < self.max_retries:
                        continue  # 重试
                    else:
                        # 所有重试都失败
                        return UploadResult(
                            code=UploadErrorCode.CONNECTION_ERROR,
                            message=f"HTTP连接错误: {str(e)}",
                            plugin_name=self.plugin_name
                        )
            
        except Exception as e:
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"HTTP字节流上传失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性
        
        Returns:
            Dict[str, Any]: 支持的特性
        """
        return {
            "protocols": ["http", "https"],
            "auth_methods": ["basic", "token", "api_key", "none"],
            "max_file_size": "无限制（取决于服务器）",
            "concurrent_uploads": True,
            "features": ["multipart_form_data", "custom_headers", "retry_mechanism"]
        }
    
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        # HTTP插件不需要特殊清理
        self.is_initialized = False