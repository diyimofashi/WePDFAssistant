"""
HTTP下载插件 - 核心实现
使用HTTP协议从服务器下载文件
"""

import os
import requests
from typing import Dict, Any
from app.core.download.download_plugin_interface import DownloadPluginInterface, DownloadResult, DownloadErrorCode


class HttpDownload(DownloadPluginInterface):
    """HTTP下载插件实现类"""
    
    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "HTTP Download Plugin"
        self.plugin_version = "1.0.0"
        self.plugin_author = "Developer"
        self.config = config or {}
        
        # HTTP连接配置
        self.base_url = ""
        self.timeout = 30
        self.max_retries = 3
        self.auth_type = "none"  # none, basic, token, api_key
        self.username = ""
        self.password = ""
        self.token = ""
        self.api_key = ""
        self.api_key_header = "X-API-Key"
        self.custom_headers = {}
        
        # HTTP会话对象
        self.session = None
    
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
            
            # 从配置中获取HTTP参数
            self.base_url = config.get("base_url", "")
            self.timeout = int(config.get("timeout", 30))
            self.max_retries = int(config.get("max_retries", 3))
            self.auth_type = config.get("auth_type", "none")
            self.username = config.get("username", "")
            self.password = config.get("password", "")
            self.token = config.get("token", "")
            self.api_key = config.get("api_key", "")
            self.api_key_header = config.get("api_key_header", "X-API-Key")
            
            # 处理自定义头部
            custom_headers_str = config.get("custom_headers", "")
            if isinstance(custom_headers_str, str) and custom_headers_str.strip():
                try:
                    import json
                    self.custom_headers = json.loads(custom_headers_str)
                except json.JSONDecodeError:
                    # 如果不是JSON格式，尝试按行分割键值对
                    headers = {}
                    for line in custom_headers_str.strip().split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            headers[key.strip()] = value.strip()
                    self.custom_headers = headers
            elif isinstance(custom_headers_str, dict):
                self.custom_headers = custom_headers_str.copy()
            else:
                self.custom_headers = {}
            
            # 验证配置
            if self.auth_type == "basic" and (not self.username or not self.password):
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="基本认证需要用户名和密码",
                    plugin_name=self.plugin_name
                )
            elif self.auth_type == "token" and not self.token:
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="Token认证需要Token",
                    plugin_name=self.plugin_name
                )
            elif self.auth_type == "api_key" and not self.api_key:
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="API Key认证需要API Key",
                    plugin_name=self.plugin_name
                )
            
            # 创建HTTP会话
            self.session = requests.Session()
            
            # 设置认证头部
            if self.auth_type == "basic":
                from requests.auth import HTTPBasicAuth
                self.session.auth = HTTPBasicAuth(self.username, self.password)
            elif self.auth_type == "token":
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            elif self.auth_type == "api_key":
                self.session.headers.update({self.api_key_header: self.api_key})
            
            # 设置自定义头部
            self.session.headers.update(self.custom_headers)
            
            self.is_initialized = True
            
            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                message="HTTP下载插件初始化成功",
                plugin_name=self.plugin_name
            )
            
        except Exception as e:
            self.is_initialized = False
            return DownloadResult(
                code=DownloadErrorCode.INIT_ERROR,
                message=f"HTTP下载插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头部"""
        headers = self.custom_headers.copy()
        
        if self.auth_type == "token":
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.auth_type == "api_key":
            headers[self.api_key_header] = self.api_key
        
        return headers
    
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
        # 确保目录存在
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir)
        
        try:
            # 获取进度回调函数
            progress_callback = kwargs.get('progress_callback')
            
            # 发送HTTP请求
            headers = self._get_auth_headers()
            
            # 如果URL不是绝对URL，尝试与基础URL组合
            if not url.startswith(('http://', 'https://')):
                if self.base_url and not self.base_url.endswith('/') and not url.startswith('/'):
                    full_url = f"{self.base_url}/{url}"
                elif self.base_url:
                    full_url = f"{self.base_url}{url}"
                else:
                    return DownloadResult(
                        code=DownloadErrorCode.INVALID_URL,
                        message="URL无效，且未设置基础URL",
                        plugin_name=self.plugin_name
                    )
            else:
                full_url = url
            
            response = self.session.get(full_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                return DownloadResult(
                    code=DownloadErrorCode.DOWNLOAD_FAILED,
                    message=f"下载失败: 服务器返回HTML内容，可能需要登录或认证。Content-Type: {content_type}",
                    plugin_name=self.plugin_name
                )
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 下载文件
            with open(local_path, 'wb') as file:
                downloaded_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # 过滤掉保持连接的空块
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 调用进度回调
                        if progress_callback and total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            progress_callback(progress)
            
            # 验证下载的文件类型（如果URL包含.pdf扩展名）
            if url.lower().endswith('.pdf') or local_path.lower().endswith('.pdf'):
                try:
                    with open(local_path, 'rb') as f:
                        file_start = f.read(10)
                        if not file_start.startswith(b'%PDF'):
                            # 检查是否是HTML内容
                            f.seek(0)
                            text_start = f.read(100).decode('utf-8', errors='ignore').lower()
                            if '<!doctype html' in text_start or '<html' in text_start:
                                return DownloadResult(
                                    code=DownloadErrorCode.DOWNLOAD_FAILED,
                                    message="下载失败: 服务器返回HTML内容而不是PDF文件，可能需要登录或认证",
                                    plugin_name=self.plugin_name
                                )
                except Exception as e:
                    # 如果验证失败，继续返回下载结果
                    pass
            
            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                data={
                    "local_path": local_path,
                    "size": downloaded_size,
                    "url": full_url
                },
                message="文件下载成功",
                plugin_name=self.plugin_name
            )
            
        except requests.exceptions.RequestException as e:
            return DownloadResult(
                code=DownloadErrorCode.NETWORK_ERROR,
                message=f"网络请求失败: {str(e)}",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            return DownloadResult(
                code=DownloadErrorCode.DOWNLOAD_FAILED,
                message=f"HTTP文件下载失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def download_bytes(self, url: str, **kwargs) -> DownloadResult:
        """
        下载文件为字节流
        
        Args:
            url: 远程文件URL
            **kwargs: 额外参数
            
        Returns:
            DownloadResult: 下载结果
        """
        try:
            # 发送HTTP请求
            headers = self._get_auth_headers()
            
            # 如果URL不是绝对URL，尝试与基础URL组合
            if not url.startswith(('http://', 'https://')):
                if self.base_url and not self.base_url.endswith('/') and not url.startswith('/'):
                    full_url = f"{self.base_url}/{url}"
                elif self.base_url:
                    full_url = f"{self.base_url}{url}"
                else:
                    return DownloadResult(
                        code=DownloadErrorCode.INVALID_URL,
                        message="URL无效，且未设置基础URL",
                        plugin_name=self.plugin_name
                    )
            else:
                full_url = url
            
            response = self.session.get(full_url, timeout=self.timeout)
            response.raise_for_status()
            
            file_bytes = response.content
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                return DownloadResult(
                    code=DownloadErrorCode.DOWNLOAD_FAILED,
                    message=f"下载失败: 服务器返回HTML内容，可能需要登录或认证。Content-Type: {content_type}",
                    plugin_name=self.plugin_name
                )
            
            # 验证下载的内容类型（如果URL包含.pdf扩展名）
            if url.lower().endswith('.pdf'):
                if not file_bytes.startswith(b'%PDF'):
                    # 检查是否是HTML内容
                    text_start = file_bytes[:100].decode('utf-8', errors='ignore').lower()
                    if '<!doctype html' in text_start or '<html' in text_start:
                        return DownloadResult(
                            code=DownloadErrorCode.DOWNLOAD_FAILED,
                            message="下载失败: 服务器返回HTML内容而不是PDF文件，可能需要登录或认证",
                            plugin_name=self.plugin_name
                        )
            
            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                data={
                    "bytes": file_bytes,
                    "size": len(file_bytes),
                    "url": full_url
                },
                message="字节流下载成功",
                plugin_name=self.plugin_name
            )
            
        except requests.exceptions.RequestException as e:
            return DownloadResult(
                code=DownloadErrorCode.NETWORK_ERROR,
                message=f"网络请求失败: {str(e)}",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            return DownloadResult(
                code=DownloadErrorCode.DOWNLOAD_FAILED,
                message=f"HTTP字节流下载失败: {str(e)}",
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
            "auth_methods": ["none", "basic", "token", "api_key"],
            "max_file_size": "取决于服务器限制",
            "concurrent_downloads": True,
            "features": ["authentication", "custom_headers", "timeout_config", "progress_callback"]
        }
    
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        if self.session:
            self.session.close()
        
        self.is_initialized = False


# 插件信息定义
PluginInfo = {
    "title": "HTTP下载",
    "description": "通过HTTP/HTTPS协议下载文件",
    "global_options": {
        "timeout": {
            "type": "integer",
            "title": "超时时间（秒）",
            "description": "HTTP请求超时时间",
            "default": 30,
            "min": 1,
            "max": 3600,
            "isInt": True
        },
        "max_retries": {
            "type": "integer",
            "title": "最大重试次数",
            "description": "下载失败时的最大重试次数",
            "default": 3,
            "min": 0,
            "max": 10,
            "isInt": True
        }
    },
    "local_options": {
        "base_url": {
            "type": "string",
            "title": "服务器基础URL",
            "default": "",
            "description": "服务器基础URL地址",
            "toolTip": "输入服务器的基础URL地址，例如：https://example.com/api"
        },
        "auth_type": {
            "type": "enum",
            "title": "认证类型",
            "description": "选择认证类型",
            "default": "none",
            "optionsList": [
                ["none", "无认证"],
                ["basic", "基本认证"],
                ["token", "Token认证"],
                ["api_key", "API Key认证"]
            ]
        },
        "username": {
            "type": "string",
            "title": "用户名",
            "default": "",
            "description": "基本认证用户名"
        },
        "password": {
            "type": "string",
            "title": "密码",
            "default": "",
            "description": "基本认证密码",
            "password": True
        },
        "token": {
            "type": "string",
            "title": "认证Token",
            "default": "",
            "description": "Token认证的Token值",
            "password": True
        },
        "api_key": {
            "type": "string",
            "title": "API密钥",
            "default": "",
            "description": "API Key认证的密钥",
            "password": True
        },
        "api_key_header": {
            "type": "string",
            "title": "API密钥头部",
            "default": "X-API-Key",
            "description": "API Key认证使用的头部名称"
        },
        "custom_headers": {
            "type": "string",
            "title": "自定义请求头部",
            "default": "",
            "description": "自定义请求头部 (JSON格式或key:value格式)"
        }
    }
}