"""
下载插件模板 - 核心实现
这是一个下载插件的模板，开发者可以基于此模板创建自己的下载插件
"""

import os
from typing import Dict, Any
from app.core.download.download_plugin_interface import DownloadPluginInterface, DownloadResult, DownloadErrorCode


class TemplateDownload(DownloadPluginInterface):
    """下载插件模板实现类"""
    
    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "Template Download Plugin"
        self.plugin_version = "1.0.0"
        self.plugin_author = "Developer"
        self.config = config or {}
        
        # 插件特定配置
        self.server_url = ""
        self.timeout = 30
        self.max_retries = 3
        self.auth_method = "none"  # none, basic, token, api_key
        self.username = ""
        self.password = ""
        self.token = ""
        self.api_key = ""
        
        # 连接对象（如果需要）
        self.connection = None
    
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
            
            # 从配置中获取参数
            self.server_url = config.get("server_url", "")
            self.timeout = int(config.get("timeout", 30))
            self.max_retries = int(config.get("max_retries", 3))
            self.auth_method = config.get("auth_method", "none")
            self.username = config.get("username", "")
            self.password = config.get("password", "")
            self.token = config.get("token", "")
            self.api_key = config.get("api_key", "")
            
            # 验证配置
            if self.auth_method == "basic" and (not self.username or not self.password):
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="基本认证需要用户名和密码",
                    plugin_name=self.plugin_name
                )
            elif self.auth_method == "token" and not self.token:
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="Token认证需要Token",
                    plugin_name=self.plugin_name
                )
            elif self.auth_method == "api_key" and not self.api_key:
                return DownloadResult(
                    code=DownloadErrorCode.INVALID_CONFIG,
                    message="API Key认证需要API Key",
                    plugin_name=self.plugin_name
                )
            
            # 这里可以添加连接测试逻辑
            # self.test_connection()
            
            self.is_initialized = True
            
            return DownloadResult(
                code=DownloadErrorCode.SUCCESS,
                message="下载插件初始化成功",
                plugin_name=self.plugin_name
            )
            
        except Exception as e:
            self.is_initialized = False
            return DownloadResult(
                code=DownloadErrorCode.INIT_ERROR,
                message=f"下载插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
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
            # 这里实现具体的下载逻辑
            # 示例：使用HTTP请求下载文件
            import requests
            
            # 构建完整URL
            if not url.startswith(('http://', 'https://')):
                if self.server_url and not self.server_url.endswith('/') and not url.startswith('/'):
                    full_url = f"{self.server_url}/{url}"
                elif self.server_url:
                    full_url = f"{self.server_url}{url}"
                else:
                    return DownloadResult(
                        code=DownloadErrorCode.INVALID_URL,
                        message="URL无效，且未设置基础URL",
                        plugin_name=self.plugin_name
                    )
            else:
                full_url = url
            
            # 准备请求头部（包含认证信息）
            headers = {}
            if self.auth_method == "token":
                headers["Authorization"] = f"Bearer {self.token}"
            elif self.auth_method == "api_key":
                headers["X-API-Key"] = self.api_key
            
            # 发送请求
            response = requests.get(full_url, timeout=self.timeout, headers=headers, stream=True)
            response.raise_for_status()
            
            # 获取进度回调函数
            progress_callback = kwargs.get('progress_callback')
            
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
                message=f"文件下载失败: {str(e)}",
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
            # 这里实现具体的字节流下载逻辑
            import requests
            
            # 构建完整URL
            if not url.startswith(('http://', 'https://')):
                if self.server_url and not self.server_url.endswith('/') and not url.startswith('/'):
                    full_url = f"{self.server_url}/{url}"
                elif self.server_url:
                    full_url = f"{self.server_url}{url}"
                else:
                    return DownloadResult(
                        code=DownloadErrorCode.INVALID_URL,
                        message="URL无效，且未设置基础URL",
                        plugin_name=self.plugin_name
                    )
            else:
                full_url = url
            
            # 准备请求头部（包含认证信息）
            headers = {}
            if self.auth_method == "token":
                headers["Authorization"] = f"Bearer {self.token}"
            elif self.auth_method == "api_key":
                headers["X-API-Key"] = self.api_key
            
            # 发送请求
            response = requests.get(full_url, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            
            file_bytes = response.content
            
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
                message=f"字节流下载失败: {str(e)}",
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
            "features": ["authentication", "timeout_config", "progress_callback"]
        }
    
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        # 关闭连接（如果有的话）
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
        
        self.is_initialized = False