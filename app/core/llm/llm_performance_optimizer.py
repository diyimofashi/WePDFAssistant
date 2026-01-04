"""
LLM性能优化器
"""
import time
from typing import Dict, Any, Optional
from collections import deque
from dataclasses import dataclass
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_calls: int = 0
    total_tokens: int = 0
    total_time: float = 0.0
    error_count: int = 0
    last_call_time: Optional[float] = None

    @property
    def average_tokens_per_call(self) -> float:
        """平均每次调用的token数"""
        return self.total_tokens / self.total_calls if self.total_calls > 0 else 0

    @property
    def average_time_per_call(self) -> float:
        """平均每次调用时间(秒)"""
        return self.total_time / self.total_calls if self.total_calls > 0 else 0

    @property
    def error_rate(self) -> float:
        """错误率"""
        return self.error_count / self.total_calls if self.total_calls > 0 else 0


class LLMPerformanceOptimizer:
    """LLM性能优化器"""

    def __init__(self, max_history: int = 100):
        self._metrics: Dict[str, PerformanceMetrics] = {}
        self._call_history: Dict[str, deque] = {}
        self._max_history = max_history
        self._cache: Dict[str, Any] = {}
        self._cache_max_size = 1000

    def record_call(
        self,
        plugin_name: str,
        model: str,
        tokens: int,
        success: bool,
        duration: float
    ) -> None:
        """
        记录调用信息

        Args:
            plugin_name: 插件名称
            model: 模型名称
            tokens: 使用的token数
            success: 是否成功
            duration: 调用耗时(秒)
        """
        key = f"{plugin_name}:{model}"

        if key not in self._metrics:
            self._metrics[key] = PerformanceMetrics()

        metrics = self._metrics[key]
        metrics.total_calls += 1
        metrics.total_tokens += tokens
        metrics.total_time += duration
        if not success:
            metrics.error_count += 1
        metrics.last_call_time = time.time()

        # 记录调用历史
        if key not in self._call_history:
            self._call_history[key] = deque(maxlen=self._max_history)

        self._call_history[key].append({
            "tokens": tokens,
            "success": success,
            "duration": duration,
            "timestamp": time.time()
        })

        logger.debug(
            f"LLM call recorded: {key} | "
            f"Tokens: {tokens} | "
            f"Duration: {duration:.2f}s | "
            f"Success: {success}"
        )

    def get_metrics(self, plugin_name: str, model: Optional[str] = None) -> Optional[PerformanceMetrics]:
        """
        获取性能指标

        Args:
            plugin_name: 插件名称
            model: 模型名称(可选)

        Returns:
            性能指标
        """
        key = f"{plugin_name}:{model}" if model else plugin_name
        return self._metrics.get(key)

    def get_all_metrics(self) -> Dict[str, PerformanceMetrics]:
        """获取所有性能指标"""
        return self._metrics.copy()

    def cache_result(self, key: str, result: Any, ttl: int = 3600) -> None:
        """
        缓存结果

        Args:
            key: 缓存键
            result: 结果
            ttl: 过期时间(秒)
        """
        if len(self._cache) >= self._cache_max_size:
            self._cache.clear()

        self._cache[key] = {
            "result": result,
            "expire_time": time.time() + ttl
        }
        logger.debug(f"Result cached: {key}")

    def get_cached_result(self, key: str) -> Optional[Any]:
        """
        获取缓存结果

        Args:
            key: 缓存键

        Returns:
            缓存的结果或None
        """
        if key not in self._cache:
            return None

        cache_entry = self._cache[key]
        if time.time() > cache_entry["expire_time"]:
            del self._cache[key]
            return None

        logger.debug(f"Cache hit: {key}")
        return cache_entry["result"]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("LLM result cache cleared")

    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取性能报告

        Returns:
            性能报告字典
        """
        report = {
            "total_plugins": len(self._metrics),
            "total_calls": sum(m.total_calls for m in self._metrics.values()),
            "total_tokens": sum(m.total_tokens for m in self._metrics.values()),
            "total_time": sum(m.total_time for m in self._metrics.values()),
            "total_errors": sum(m.error_count for m in self._metrics.values()),
            "cache_size": len(self._cache),
            "cache_max_size": self._cache_max_size,
            "details": {}
        }

        for key, metrics in self._metrics.items():
            report["details"][key] = {
                "total_calls": metrics.total_calls,
                "total_tokens": metrics.total_tokens,
                "total_time": metrics.total_time,
                "error_count": metrics.error_count,
                "average_tokens_per_call": metrics.average_tokens_per_call,
                "average_time_per_call": metrics.average_time_per_call,
                "error_rate": metrics.error_rate,
                "last_call_time": metrics.last_call_time
            }

        return report

    def reset_metrics(self, plugin_name: Optional[str] = None) -> None:
        """
        重置性能指标

        Args:
            plugin_name: 插件名称(可选),如果为None则重置所有
        """
        if plugin_name:
            keys_to_reset = [k for k in self._metrics.keys() if k.startswith(plugin_name)]
            for key in keys_to_reset:
                self._metrics[key] = PerformanceMetrics()
                if key in self._call_history:
                    self._call_history[key].clear()
            logger.info(f"Metrics reset for plugin: {plugin_name}")
        else:
            self._metrics.clear()
            self._call_history.clear()
            logger.info("All metrics reset")

    def get_slow_calls(self, threshold: float = 5.0) -> Dict[str, list]:
        """
        获取慢速调用

        Args:
            threshold: 时间阈值(秒)

        Returns:
            慢速调用字典
        """
        slow_calls = {}
        for key, history in self._call_history.items():
            slow = [call for call in history if call["duration"] > threshold]
            if slow:
                slow_calls[key] = slow

        return slow_calls
