"""
FTP上传插件 - 核心实现
使用FTP协议上传文件到服务器
"""

import os
import ftplib
from typing import Dict, Any
from io import BytesIO
from app.core.upload.upload_plugin_interface import UploadPluginInterface, UploadResult, UploadErrorCode


class FtpUpload(UploadPluginInterface):
    """FTP上传插件实现类"""
    
    def __init__(self, config=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "FTP Upload Plugin"
        self.plugin_version = "1.0.0"
        self.plugin_author = "Developer"
        self.config = config or {}
        
        # FTP连接配置
        self.host = ""
        self.port = 21
        self.username = ""
        self.password = ""
        self.remote_directory = "/uploads"
        self.use_tls = False
        self.passive_mode = True
        self.timeout = 30
        self.buffer_size = 8192
        
        # FTP连接对象
        self.ftp = None
    
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
            
            # 从配置中获取FTP参数
            self.host = config.get("host", "")
            self.port = int(config.get("port", 21))
            self.username = config.get("username", "")
            self.password = config.get("password", "")
            self.remote_directory = config.get("remote_directory", "/uploads")
            self.use_tls = bool(config.get("use_tls", False))
            self.passive_mode = bool(config.get("passive_mode", True))
            self.timeout = int(config.get("timeout", 30))
            self.buffer_size = int(config.get("buffer_size", 8192))
            
            # 验证配置
            if not self.host:
                return UploadResult(
                    code=UploadErrorCode.INVALID_CONFIG,
                    message="缺少FTP服务器地址配置",
                    plugin_name=self.plugin_name
                )
            
            # 如果提供了用户名和密码则使用它们，否则使用匿名登录
            # 不再强制要求用户名和密码
            
            self.is_initialized = True
            
            return UploadResult(
                code=UploadErrorCode.SUCCESS,
                message="FTP上传插件初始化成功",
                plugin_name=self.plugin_name
            )
            
        except Exception as e:
            self.is_initialized = False
            return UploadResult(
                code=UploadErrorCode.INIT_ERROR,
                message=f"FTP上传插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def _connect_ftp(self):
        """建立FTP连接"""
        try:
            if self.use_tls:
                # 使用TLS连接
                import ssl
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.ftp = ftplib.FTP_TLS(context=context)
                self.ftp.connect(self.host, self.port, timeout=self.timeout)
                # 根据用户名和密码的提供情况选择登录方式
                if self.username and self.password:
                    # 用户名和密码都提供了，使用认证登录
                    self.ftp.login(self.username, self.password)
                elif self.username and not self.password:
                    # 只提供了用户名，没有密码，适用于某些允许空密码的FTP服务器
                    self.ftp.login(self.username, "")
                else:
                    # 用户名和密码都没有提供，使用匿名登录
                    self.ftp.login()  # 使用匿名登录
                # 确保数据连接也使用TLS
                try:
                    self.ftp.prot_p()
                except:
                    # 如果prot_p失败，可能是服务器不支持数据通道加密
                    # 这在某些FTPS服务器上是正常的
                    pass
            else:
                # 使用普通FTP连接
                self.ftp = ftplib.FTP()
                self.ftp.connect(self.host, self.port, timeout=self.timeout)
                # 根据用户名和密码的提供情况选择登录方式
                if self.username and self.password:
                    # 用户名和密码都提供了，使用认证登录
                    self.ftp.login(self.username, self.password)
                elif self.username and not self.password:
                    # 只提供了用户名，没有密码，适用于某些允许空密码的FTP服务器
                    self.ftp.login(self.username, "")
                else:
                    # 用户名和密码都没有提供，使用匿名登录
                    self.ftp.login()  # 使用匿名登录
            
            # 设置被动模式
            self.ftp.set_pasv(self.passive_mode)
            
            # 确保远程目录存在
            try:
                self.ftp.cwd(self.remote_directory)
            except ftplib.error_perm:
                # 如果目录不存在，则创建
                self._create_remote_directory(self.remote_directory)
                self.ftp.cwd(self.remote_directory)
                
        except Exception as e:
            raise e
    
    def _create_remote_directory(self, directory):
        """递归创建远程目录"""
        dirs = directory.strip('/').split('/')
        current_path = ""
        
        for dir_name in dirs:
            if dir_name:
                current_path = f"{current_path}/{dir_name}"
                try:
                    self.ftp.cwd(current_path)
                except ftplib.error_perm:
                    # 目录不存在，创建它
                    self.ftp.mkd(current_path)
                    self.ftp.cwd(current_path)
    
    def upload_file(self, file_path: str, remote_path: str = "", **kwargs) -> UploadResult:
        """
        上传文件
        
        Args:
            file_path: 本地文件路径
            remote_path: 远程路径（可选，会附加到远程目录后面）
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
        
        ftp_conn = None
        try:
            # 建立FTP连接
            self._connect_ftp()
            ftp_conn = self.ftp
            
            # 确定远程文件名
            remote_filename = remote_path or os.path.basename(file_path)
            if remote_path and not remote_path.startswith('/'):
                # 如果remote_path不是绝对路径，则与远程目录合并
                remote_filename = f"{self.remote_directory}/{remote_path}".replace('//', '/')
                # 提取文件名部分用于上传
                remote_filename = os.path.basename(remote_path)
            
            # 执行文件上传
            with open(file_path, 'rb') as file:
                # 对于FTPS连接，可能需要处理数据传输的SSL问题
                if self.use_tls:
                    # 尝试使用保护缓冲区大小的上传
                    ftp_conn.storbinary(f'STOR {remote_filename}', file, self.buffer_size)
                else:
                    ftp_conn.storbinary(f'STOR {remote_filename}', file, self.buffer_size)
            
            # 获取上传后的文件信息
            file_size = os.path.getsize(file_path)
            
            return UploadResult(
                code=UploadErrorCode.SUCCESS,
                data={
                    "remote_path": f"{self.remote_directory}/{remote_filename}",
                    "file_name": remote_filename,
                    "size": file_size
                },
                message="文件上传成功",
                plugin_name=self.plugin_name
            )
            
        except ftplib.all_errors as e:
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"FTP上传失败: {str(e)}",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"FTP文件上传失败: {str(e)}",
                plugin_name=self.plugin_name
            )
        finally:
            # 关闭FTP连接
            if ftp_conn:
                try:
                    ftp_conn.quit()
                except:
                    # 如果QUIT失败，尝试关闭连接
                    ftp_conn.close()
    
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
        ftp_conn = None
        try:
            # 建立FTP连接
            self._connect_ftp()
            ftp_conn = self.ftp
            
            # 确定远程文件名
            remote_filename = remote_path or original_filename or "upload_file"
            if '/' in remote_filename:
                # 如果remote_filename包含路径，需要创建目录
                dirname = os.path.dirname(remote_filename)
                if dirname:
                    self._create_remote_directory(dirname)
                    ftp_conn.cwd(dirname)
                remote_filename = os.path.basename(remote_filename)
            
            # 使用BytesIO将字节流转换为类似文件的对象
            file_obj = BytesIO(file_bytes)
            file_obj.seek(0)
            
            # 执行字节流上传
            if self.use_tls:
                # 对于FTPS连接，可能需要处理数据传输的SSL问题
                ftp_conn.storbinary(f'STOR {remote_filename}', file_obj, self.buffer_size)
            else:
                ftp_conn.storbinary(f'STOR {remote_filename}', file_obj, self.buffer_size)
            
            return UploadResult(
                code=UploadErrorCode.SUCCESS,
                data={
                    "remote_path": f"{self.remote_directory}/{remote_filename}",
                    "file_name": remote_filename,
                    "size": len(file_bytes)
                },
                message="字节流上传成功",
                plugin_name=self.plugin_name
            )
            
        except ftplib.all_errors as e:
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"FTP上传失败: {str(e)}",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            return UploadResult(
                code=UploadErrorCode.UPLOAD_FAILED,
                message=f"FTP字节流上传失败: {str(e)}",
                plugin_name=self.plugin_name
            )
        finally:
            # 关闭FTP连接
            if ftp_conn:
                try:
                    ftp_conn.quit()
                except:
                    # 如果QUIT失败，尝试关闭连接
                    ftp_conn.close()
    
    def get_supported_features(self) -> Dict[str, Any]:
        """
        获取插件支持的特性
        
        Returns:
            Dict[str, Any]: 支持的特性
        """
        return {
            "protocols": ["ftp", "ftps"],
            "auth_methods": ["username_password", "username_only", "anonymous"],
            "max_file_size": "取决于服务器限制",
            "concurrent_uploads": False,
            "features": ["passive_active_mode", "directory_creation", "tls_encryption", "anonymous_access"]
        }
    
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                self.ftp.close()
            self.ftp = None
        
        self.is_initialized = False