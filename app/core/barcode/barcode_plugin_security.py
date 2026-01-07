"""
条码插件安全机制
负责插件的安全检查、权限控制和恶意代码防护
"""

import os
import hashlib
import threading
import time
import psutil
from typing import Dict, Any, List, Callable
from functools import wraps
from app.utils.logger import get_logger

logger = get_logger('barcode_plugin_security')


class BarcodePluginSecurityManager:
    """条码插件安全管理器"""
    
    def __init__(self):
        """初始化安全管理器"""
        self.plugin_permissions: Dict[str, Dict[str, bool]] = {}
        self.plugin_resource_limits: Dict[str, Dict[str, Any]] = {}
        self.plugin_signatures: Dict[str, str] = {}
        self.running_processes: Dict[str, List[int]] = {}
        self.monitoring_threads: Dict[str, threading.Thread] = {}
        self.lock = threading.RLock()
        
    def register_plugin_permissions(self, plugin_name: str, permissions: Dict[str, bool]) -> None:
        """
        注册插件权限
        
        Args:
            plugin_name: 插件名称
            permissions: 权限字典，键为权限类型，值为是否允许
                        支持的权限类型：
                        - file_access: 文件访问权限
                        - network_access: 网络访问权限
                        - system_access: 系统调用权限
                        - process_spawn: 进程创建权限
        """
        with self.lock:
            self.plugin_permissions[plugin_name] = permissions
            logger.debug(f"注册插件权限: {plugin_name}, 权限: {permissions}")
    
    def check_permission(self, plugin_name: str, permission_type: str) -> bool:
        """
        检查插件是否有指定权限
        
        Args:
            plugin_name: 插件名称
            permission_type: 权限类型
            
        Returns:
            bool: 是否有权限
        """
        with self.lock:
            permissions = self.plugin_permissions.get(plugin_name, {})
            return permissions.get(permission_type, False)
    
    def set_resource_limits(self, plugin_name: str, limits: Dict[str, Any]) -> None:
        """
        设置插件资源限制
        
        Args:
            plugin_name: 插件名称
            limits: 资源限制字典
                    支持的限制类型：
                    - max_memory_mb: 最大内存使用量(MB)
                    - max_cpu_percent: 最大CPU使用率(%)
                    - max_runtime_seconds: 最大运行时间(秒)
                    - max_file_size_mb: 最大文件处理大小(MB)
        """
        with self.lock:
            self.plugin_resource_limits[plugin_name] = limits
            logger.debug(f"设置插件资源限制: {plugin_name}, 限制: {limits}")
    
    def validate_plugin_signature(self, plugin_path: str, expected_signature: str) -> bool:
        """
        验证插件签名
        
        Args:
            plugin_path: 插件路径
            expected_signature: 期望的签名
            
        Returns:
            bool: 签名是否有效
        """
        try:
            # 计算插件文件的哈希值
            hash_md5 = hashlib.md5()
            for root, dirs, files in os.walk(plugin_path):
                for file in sorted(files):  # 排序确保一致性
                    file_path = os.path.join(root, file)
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
            
            actual_signature = hash_md5.hexdigest()
            is_valid = actual_signature == expected_signature
            
            return is_valid
            
        except Exception as e:
            logger.error(f"插件签名验证失败: {plugin_path}, 错误: {str(e)}")
            return False
    
    def monitor_plugin_resources(self, plugin_name: str) -> None:
        """
        监控插件资源使用情况
        
        Args:
            plugin_name: 插件名称
        """
        def monitor():
            limits = self.plugin_resource_limits.get(plugin_name, {})
            max_memory = limits.get('max_memory_mb', 512) * 1024 * 1024  # 转换为字节
            max_cpu = limits.get('max_cpu_percent', 80)
            max_runtime = limits.get('max_runtime_seconds', 300)  # 5分钟
            
            start_time = time.time()
            
            while time.time() - start_time < max_runtime:
                time.sleep(1)  # 每秒检查一次
                
                current_process = psutil.Process()
                memory_usage = current_process.memory_info().rss
                cpu_percent = current_process.cpu_percent()
                
                # 检查内存使用
                if memory_usage > max_memory:
                    logger.warning(f"插件内存使用超限: {plugin_name}, 使用: {memory_usage/1024/1024:.2f}MB, 限制: {max_memory/1024/1024:.2f}MB")
                
                # 检查CPU使用
                if cpu_percent > max_cpu:
                    logger.warning(f"插件CPU使用超限: {plugin_name}, 使用: {cpu_percent}%, 限制: {max_cpu}%")
        
        with self.lock:
            if plugin_name not in self.monitoring_threads:
                thread = threading.Thread(target=monitor, daemon=True)
                self.monitoring_threads[plugin_name] = thread
                thread.start()
                logger.debug(f"开始监控插件资源: {plugin_name}")
    
    def get_security_report(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件安全报告
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 安全报告
        """
        with self.lock:
            permissions = self.plugin_permissions.get(plugin_name, {})
            limits = self.plugin_resource_limits.get(plugin_name, {})
            
            report = {
                "plugin_name": plugin_name,
                "permissions": permissions,
                "resource_limits": limits,
                "is_monitored": plugin_name in self.monitoring_threads,
                "timestamp": time.time()
            }
            
            return report


# 全局安全管理器实例
security_manager = BarcodePluginSecurityManager()