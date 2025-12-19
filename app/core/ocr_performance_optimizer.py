"""
OCR插件系统性能优化模块
包括插件加载优化、并发处理、内存优化、缓存机制等
"""

import os
import threading
import time
import hashlib
import pickle
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil
from app.utils.logger import get_logger

logger = get_logger('ocr_performance_optimizer')


class OCRPerformanceOptimizer:
    """OCR性能优化器"""
    
    def __init__(self):
        """初始化性能优化器"""
        self.cache_enabled = True
        self.cache_storage = {}
        self.cache_lock = threading.RLock()
        self.resource_monitoring_enabled = True
        self.performance_metrics = {}
        self.model_sharing_enabled = True
        self.shared_models = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.process_pool = ProcessPoolExecutor(max_workers=2)
        
        logger.info("OCR性能优化器初始化")
    
    def enable_caching(self, enabled: bool = True) -> None:
        """
        启用或禁用缓存
        
        Args:
            enabled: 是否启用缓存
        """
        self.cache_enabled = enabled
        logger.info(f"缓存功能已{'启用' if enabled else '禁用'}")
    
    def cache_result(self, cache_key: str, result: Any, ttl: int = 3600) -> None:
        """
        缓存OCR结果
        
        Args:
            cache_key: 缓存键
            result: 要缓存的结果
            ttl: 缓存过期时间（秒），默认1小时
        """
        if not self.cache_enabled:
            return
        
        with self.cache_lock:
            self.cache_storage[cache_key] = {
                'result': result,
                'timestamp': time.time(),
                'expires_at': time.time() + ttl
            }
            logger.debug(f"结果已缓存: {cache_key}")
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """
        获取缓存的OCR结果
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存的结果，如果不存在或过期则返回None
        """
        if not self.cache_enabled:
            return None
        
        with self.cache_lock:
            if cache_key in self.cache_storage:
                cached_item = self.cache_storage[cache_key]
                # 检查是否过期
                if time.time() < cached_item['expires_at']:
                    logger.debug(f"命中缓存: {cache_key}")
                    return cached_item['result']
                else:
                    # 删除过期缓存
                    del self.cache_storage[cache_key]
                    logger.debug(f"缓存已过期并删除: {cache_key}")
        
        return None
    
    def generate_cache_key(self, plugin_name: str, input_data: Any, language: str = "auto") -> str:
        """
        生成缓存键
        
        Args:
            plugin_name: 插件名称
            input_data: 输入数据（文件路径、字节流或Base64字符串）
            language: 识别语言
            
        Returns:
            缓存键字符串
        """
        # 创建输入数据的哈希值
        if isinstance(input_data, str):
            # 文件路径或Base64字符串
            data_hash = hashlib.md5(input_data.encode('utf-8')).hexdigest()
        elif isinstance(input_data, bytes):
            # 字节流
            data_hash = hashlib.md5(input_data).hexdigest()
        else:
            # 其他类型转换为字符串再哈希
            data_hash = hashlib.md5(str(input_data).encode('utf-8')).hexdigest()
        
        # 组合生成缓存键
        cache_key = f"{plugin_name}:{data_hash}:{language}"
        return cache_key
    
    def clear_expired_cache(self) -> int:
        """
        清除过期缓存
        
        Returns:
            清除的缓存项数量
        """
        if not self.cache_enabled:
            return 0
        
        current_time = time.time()
        expired_keys = []
        
        with self.cache_lock:
            for key, item in self.cache_storage.items():
                if current_time >= item['expires_at']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache_storage[key]
        
        count = len(expired_keys)
        if count > 0:
            logger.info(f"清除了 {count} 个过期缓存项")
        
        return count
    
    def clear_all_cache(self) -> None:
        """清除所有缓存"""
        if not self.cache_enabled:
            return
        
        with self.cache_lock:
            self.cache_storage.clear()
        
        logger.info("所有缓存已清除")
    
    def enable_resource_monitoring(self, enabled: bool = True) -> None:
        """
        启用或禁用资源监控
        
        Args:
            enabled: 是否启用资源监控
        """
        self.resource_monitoring_enabled = enabled
        logger.info(f"资源监控已{'启用' if enabled else '禁用'}")
    
    def monitor_resources(self) -> Dict[str, Any]:
        """
        监控系统资源使用情况
        
        Returns:
            资源使用情况字典
        """
        if not self.resource_monitoring_enabled:
            return {}
        
        try:
            # 获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 获取内存使用情况
            memory_info = psutil.virtual_memory()
            
            # 获取磁盘使用情况
            disk_info = psutil.disk_usage('/')
            
            resources = {
                'cpu_percent': cpu_percent,
                'memory_total': memory_info.total,
                'memory_available': memory_info.available,
                'memory_percent': memory_info.percent,
                'disk_total': disk_info.total,
                'disk_free': disk_info.free,
                'disk_percent': 100 - (disk_info.free / disk_info.total * 100)
            }
            
            logger.debug(f"资源使用情况: {resources}")
            return resources
            
        except Exception as e:
            logger.error(f"监控资源时发生异常: {str(e)}")
            return {}
    
    def optimize_plugin_loading(self, plugin_loader_func: Callable) -> Callable:
        """
        插件加载性能优化装饰器
        
        Args:
            plugin_loader_func: 插件加载函数
            
        Returns:
            优化后的函数
        """
        @wraps(plugin_loader_func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # 执行插件加载
                result = plugin_loader_func(*args, **kwargs)
                
                # 记录加载时间
                elapsed_time = time.time() - start_time
                logger.info(f"插件加载耗时: {elapsed_time:.2f}秒")
                
                return result
                
            except Exception as e:
                logger.error(f"插件加载时发生异常: {str(e)}")
                raise
        
        return wrapper
    
    def enable_model_sharing(self, enabled: bool = True) -> None:
        """
        启用或禁用模型共享
        
        Args:
            enabled: 是否启用模型共享
        """
        self.model_sharing_enabled = enabled
        logger.info(f"模型共享已{'启用' if enabled else '禁用'}")
    
    def register_shared_model(self, model_key: str, model_instance: Any) -> None:
        """
        注册共享模型
        
        Args:
            model_key: 模型键
            model_instance: 模型实例
        """
        if not self.model_sharing_enabled:
            return
        
        with self.cache_lock:
            self.shared_models[model_key] = model_instance
            logger.debug(f"共享模型已注册: {model_key}")
    
    def get_shared_model(self, model_key: str) -> Optional[Any]:
        """
        获取共享模型
        
        Args:
            model_key: 模型键
            
        Returns:
            共享模型实例，不存在返回None
        """
        if not self.model_sharing_enabled:
            return None
        
        with self.cache_lock:
            return self.shared_models.get(model_key)
    
    def remove_shared_model(self, model_key: str) -> bool:
        """
        移除共享模型
        
        Args:
            model_key: 模型键
            
        Returns:
            是否成功移除
        """
        if not self.model_sharing_enabled:
            return False
        
        with self.cache_lock:
            if model_key in self.shared_models:
                del self.shared_models[model_key]
                logger.debug(f"共享模型已移除: {model_key}")
                return True
        return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标
        
        Returns:
            性能指标字典
        """
        return self.performance_metrics.copy()
    
    def reset_performance_metrics(self) -> None:
        """重置性能指标"""
        self.performance_metrics.clear()
        logger.info("性能指标已重置")
    
    def async_execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        异步执行函数
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        future = self.thread_pool.submit(func, *args, **kwargs)
        return future.result()
    
    def parallel_process(self, func: Callable, data_list: List[Any], 
                        max_workers: int = None) -> List[Any]:
        """
        并行处理数据列表
        
        Args:
            func: 处理函数
            data_list: 数据列表
            max_workers: 最大工作进程数
            
        Returns:
            处理结果列表
        """
        if max_workers is None:
            max_workers = min(len(data_list), os.cpu_count() or 1)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(func, data) for data in data_list]
            results = [future.result() for future in futures]
        
        return results
    
    def memory_efficient_processing(self, data_generator: Callable, 
                                 processor_func: Callable, 
                                 batch_size: int = 10) -> List[Any]:
        """
        内存高效处理大量数据
        
        Args:
            data_generator: 数据生成器函数
            processor_func: 数据处理函数
            batch_size: 批处理大小
            
        Returns:
            处理结果列表
        """
        results = []
        
        # 分批处理数据以节省内存
        batch = []
        for data in data_generator():
            batch.append(data)
            
            if len(batch) >= batch_size:
                # 处理批次
                batch_results = self.parallel_process(processor_func, batch)
                results.extend(batch_results)
                batch.clear()  # 清空批次以释放内存
        
        # 处理剩余数据
        if batch:
            batch_results = self.parallel_process(processor_func, batch)
            results.extend(batch_results)
        
        return results
    
    def close(self) -> None:
        """关闭性能优化器，释放资源"""
        try:
            self.thread_pool.shutdown(wait=True)
            self.process_pool.shutdown(wait=True)
            logger.info("性能优化器已关闭")
        except Exception as e:
            logger.error(f"关闭性能优化器时发生异常: {str(e)}")


# 全局性能优化器实例
performance_optimizer = OCRPerformanceOptimizer()


def cached_ocr_result(plugin_name: str, language: str = "auto"):
    """
    OCR结果缓存装饰器
    
    Args:
        plugin_name: 插件名称
        language: 识别语言
    """
    def decorator(func):
        @wraps(func)
        def wrapper(input_data, *args, **kwargs):
            # 生成缓存键
            cache_key = performance_optimizer.generate_cache_key(
                plugin_name, input_data, language
            )
            
            # 尝试从缓存获取结果
            cached_result = performance_optimizer.get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行OCR识别
            result = func(input_data, *args, **kwargs)
            
            # 缓存结果
            if result and hasattr(result, 'is_success') and result.is_success():
                performance_optimizer.cache_result(cache_key, result)
            
            return result
        
        return wrapper
    return decorator
