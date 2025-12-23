"""
OCR插件安全机制
负责插件的安全检查、权限控制和恶意代码防护
"""

import os
import hashlib
import threading
import time
import psutil
import signal
from typing import Dict, Any, List, Callable
from functools import wraps
from app.utils.logger import get_logger

logger = get_logger('ocr_plugin_security')


class PluginSecurityManager:
    """插件安全管理器"""
    
    def __init__(self):
        """初始化安全管理器"""
        self.plugin_permissions: Dict[str, Dict[str, bool]] = {}
        self.plugin_resource_limits: Dict[str, Dict[str, Any]] = {}
        self.plugin_signatures: Dict[str, str] = {}
        self.running_processes: Dict[str, List[int]] = {}
        self.monitoring_threads: Dict[str, threading.Thread] = {}
        self.lock = threading.RLock()
        
        logger.info("OCR插件安全管理器初始化")
    
    def register_plugin_permissions(self, plugin_name: str, permissions: Dict[str, bool]) -> None:
        """
        注册插件权限
        
        Args:
            plugin_name: 插件名称
            permissions: 权限字典，键为权限类型，值为是否允许
                        支持的权限类型：
                        - file_access: 文件访问权限
                        - network_access: 网络访问权限
                        - execute_commands: 执行外部命令权限
                        - system_calls: 系统调用权限
        """
        with self.lock:
            self.plugin_permissions[plugin_name] = permissions.copy()
            logger.debug(f"注册插件权限: {plugin_name}")
    
    def check_permission(self, plugin_name: str, permission_type: str) -> bool:
        """
        检查插件是否具有指定权限
        
        Args:
            plugin_name: 插件名称
            permission_type: 权限类型
            
        Returns:
            bool: 是否具有权限
        """
        with self.lock:
            permissions = self.plugin_permissions.get(plugin_name, {})
            return permissions.get(permission_type, False)
    
    def set_resource_limits(self, plugin_name: str, limits: Dict[str, Any]) -> None:
        """
        设置插件资源限制
        
        Args:
            plugin_name: 插件名称
            limits: 资源限制字典，支持的键：
                   - memory_mb: 内存限制(MB)
                   - cpu_percent: CPU使用率限制(%)
                   - timeout_seconds: 执行超时限制(秒)
                   - max_processes: 最大进程数
        """
        with self.lock:
            self.plugin_resource_limits[plugin_name] = limits.copy()
            logger.debug(f"设置插件资源限制: {plugin_name}")
    
    def verify_plugin_signature(self, plugin_name: str, plugin_path: str, expected_signature: str = None) -> bool:
        """
        验证插件签名
        
        Args:
            plugin_name: 插件名称
            plugin_path: 插件路径
            expected_signature: 期望的签名值（可选）
            
        Returns:
            bool: 签名是否有效
        """
        try:
            # 计算插件目录的哈希值
            calculated_signature = self._calculate_directory_hash(plugin_path)
            
            with self.lock:
                if expected_signature:
                    # 验证特定签名
                    is_valid = calculated_signature == expected_signature
                    if is_valid:
                        self.plugin_signatures[plugin_name] = calculated_signature
                else:
                    # 检查是否已有记录的签名
                    stored_signature = self.plugin_signatures.get(plugin_name)
                    is_valid = stored_signature is None or stored_signature == calculated_signature
                    if is_valid and stored_signature is None:
                        self.plugin_signatures[plugin_name] = calculated_signature
            
            if not is_valid:
                logger.warning(f"插件签名验证失败: {plugin_name}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"验证插件签名时发生异常: {plugin_name}, 错误: {str(e)}")
            return False
    
    def _calculate_directory_hash(self, directory_path: str) -> str:
        """
        计算目录内容的哈希值
        
        Args:
            directory_path: 目录路径
            
        Returns:
            str: 目录内容的SHA256哈希值
        """
        hash_sha256 = hashlib.sha256()
        
        for root, dirs, files in os.walk(directory_path):
            # 排序以确保一致性
            dirs.sort()
            files.sort()
            
            for file_name in files:
                file_path = os.path.join(root, file_name)
                
                # 跳过某些不需要计算哈希的文件
                if file_name in ['.DS_Store', 'Thumbs.db']:
                    continue
                
                try:
                    with open(file_path, 'rb') as f:
                        # 分块读取文件以节省内存
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_sha256.update(chunk)
                except Exception as e:
                    logger.warning(f"读取文件时出错: {file_path}, 错误: {str(e)}")
        
        return hash_sha256.hexdigest()
    
    def start_resource_monitoring(self, plugin_name: str, process_func: Callable) -> Callable:
        """
        启动资源监控装饰器
        
        Args:
            plugin_name: 插件名称
            process_func: 被监控的处理函数
            
        Returns:
            Callable: 装饰后的函数
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 启动资源监控
                monitor_thread = threading.Thread(
                    target=self._monitor_resources, 
                    args=(plugin_name, func.__name__),
                    daemon=True
                )
                monitor_thread.start()
                
                with self.lock:
                    if plugin_name not in self.monitoring_threads:
                        self.monitoring_threads[plugin_name] = []
                    self.monitoring_threads[plugin_name].append(monitor_thread)
                
                try:
                    # 执行原函数
                    return func(*args, **kwargs)
                finally:
                    # 停止监控
                    self._stop_monitoring(plugin_name, monitor_thread)
            
            return wrapper
        return decorator
    
    def _monitor_resources(self, plugin_name: str, function_name: str) -> None:
        """
        监控插件资源使用情况
        
        Args:
            plugin_name: 插件名称
            function_name: 函数名称
        """
        limits = self.plugin_resource_limits.get(plugin_name, {})
        memory_limit = limits.get('memory_mb', 1024) * 1024 * 1024  # 转换为字节
        cpu_limit = limits.get('cpu_percent', 80)
        timeout = limits.get('timeout_seconds', 300)
        
        start_time = time.time()
        
        try:
            current_process = psutil.Process(os.getpid())
            
            while True:
                # 检查超时
                if time.time() - start_time > timeout:
                    logger.warning(f"插件执行超时: {plugin_name}.{function_name}")
                    # 发送中断信号
                    os.kill(os.getpid(), signal.SIGINT)
                    break
                
                # 检查内存使用
                memory_info = current_process.memory_info()
                if memory_info.rss > memory_limit:
                    logger.warning(f"插件内存使用超出限制: {plugin_name}.{function_name}")
                    # 发送中断信号
                    os.kill(os.getpid(), signal.SIGINT)
                    break
                
                # 检查CPU使用率
                cpu_percent = current_process.cpu_percent()
                if cpu_percent > cpu_limit:
                    logger.warning(f"插件CPU使用率超出限制: {plugin_name}.{function_name}")
                    # 这里可以采取措施，比如暂停一段时间
                
                time.sleep(1)  # 每秒检查一次
                
        except psutil.NoSuchProcess:
            # 进程已结束
            pass
        except Exception as e:
            logger.error(f"资源监控时发生异常: {plugin_name}.{function_name}, 错误: {str(e)}")
    
    def _stop_monitoring(self, plugin_name: str, monitor_thread: threading.Thread) -> None:
        """
        停止资源监控
        
        Args:
            plugin_name: 插件名称
            monitor_thread: 监控线程
        """
        with self.lock:
            if plugin_name in self.monitoring_threads:
                if monitor_thread in self.monitoring_threads[plugin_name]:
                    self.monitoring_threads[plugin_name].remove(monitor_thread)
    
    def scan_for_malicious_patterns(self, plugin_path: str) -> List[str]:
        """
        扫描插件中的恶意代码模式
        
        Args:
            plugin_path: 插件路径
            
        Returns:
            List[str]: 发现的可疑模式列表
        """
        suspicious_patterns = [
            r'os\.system\s*\(',           # 系统命令执行
            r'subprocess\.',              # 子进程操作
            r'eval\s*\(',                 # 动态代码执行
            r'exec\s*\(',                 # 动态代码执行
            r'__import__\s*\(',           # 动态导入
            r'open\s*\([^)]*\/etc\/',     # 访问系统敏感文件
            r'open\s*\([^)]*\\system32\\', # Windows系统文件访问
            r'urllib\.request\.',         # 网络请求
            r'requests\.',                # 网络请求
        ]
        
        findings = []
        
        try:
            for root, dirs, files in os.walk(plugin_path):
                for file_name in files:
                    if file_name.endswith('.py'):
                        file_path = os.path.join(root, file_name)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                for pattern in suspicious_patterns:
                                    import re
                                    if re.search(pattern, content):
                                        findings.append(f"{file_path}: 发现可疑模式 - {pattern}")
                                        
                        except Exception as e:
                            logger.warning(f"扫描文件时出错: {file_path}, 错误: {str(e)}")
                            
        except Exception as e:
            logger.error(f"扫描插件时发生异常: {plugin_path}, 错误: {str(e)}")
        
        if findings:
            logger.warning(f"在插件中发现可疑代码模式: {plugin_path}")
            for finding in findings:
                logger.warning(finding)
        
        return findings
    
    def sandbox_execute(self, plugin_name: str, func: Callable, *args, **kwargs):
        """
        在沙箱环境中执行插件函数
        
        Args:
            plugin_name: 插件名称
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        # 检查权限
        if not self.check_permission(plugin_name, 'execute_commands'):
            raise PermissionError(f"插件没有执行命令的权限: {plugin_name}")
        
        # 启动资源监控
        @self.start_resource_monitoring(plugin_name, func)
        def monitored_func():
            return func(*args, **kwargs)
        
        return monitored_func()


# 全局安全管理器实例
security_manager = PluginSecurityManager()