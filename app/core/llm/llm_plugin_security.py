"""
LLM安全管理器
"""
from typing import Dict, Any, Optional, List
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMPluginSecurity:
    """LLM插件安全管理器"""

    def __init__(self):
        self._allowed_plugins: set = set()
        self._allowed_tools: set = set()
        self._api_keys: Dict[str, str] = {}
        self._rate_limits: Dict[str, Dict] = {}
        self._call_counts: Dict[str, int] = {}

    def set_allowed_plugins(self, plugins: List[str]) -> None:
        """
        设置允许的插件列表

        Args:
            plugins: 插件名称列表
        """
        self._allowed_plugins = set(plugins)
        logger.info(f"Allowed plugins set: {', '.join(plugins)}")

    def is_plugin_allowed(self, plugin_name: str) -> bool:
        """
        检查插件是否允许

        Args:
            plugin_name: 插件名称

        Returns:
            是否允许
        """
        if not self._allowed_plugins:
            return True
        return plugin_name in self._allowed_plugins

    def set_allowed_tools(self, tools: List[str]) -> None:
        """
        设置允许的工具列表

        Args:
            tools: 工具名称列表
        """
        self._allowed_tools = set(tools)
        logger.info(f"Allowed tools set: {', '.join(tools)}")

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        检查工具是否允许

        Args:
            tool_name: 工具名称

        Returns:
            是否允许
        """
        if not self._allowed_tools:
            return True
        return tool_name in self._allowed_tools

    def set_api_key(self, plugin_name: str, api_key: str) -> None:
        """
        设置API密钥

        Args:
            plugin_name: 插件名称
            api_key: API密钥
        """
        self._api_keys[plugin_name] = api_key
        logger.info(f"API key set for plugin: {plugin_name}")

    def get_api_key(self, plugin_name: str) -> Optional[str]:
        """
        获取API密钥

        Args:
            plugin_name: 插件名称

        Returns:
            API密钥或None
        """
        return self._api_keys.get(plugin_name)

    def set_rate_limit(self, plugin_name: str, max_calls: int, time_window: int = 60) -> None:
        """
        设置速率限制

        Args:
            plugin_name: 插件名称
            max_calls: 最大调用次数
            time_window: 时间窗口(秒)
        """
        self._rate_limits[plugin_name] = {
            "max_calls": max_calls,
            "time_window": time_window,
            "reset_time": 0,
            "call_count": 0
        }
        logger.info(f"Rate limit set for plugin {plugin_name}: {max_calls} calls/{time_window}s")

    def check_rate_limit(self, plugin_name: str) -> bool:
        """
        检查速率限制

        Args:
            plugin_name: 插件名称

        Returns:
            是否允许调用
        """
        if plugin_name not in self._rate_limits:
            return True

        import time
        now = int(time.time())
        limit_info = self._rate_limits[plugin_name]

        if now >= limit_info["reset_time"]:
            limit_info["reset_time"] = now + limit_info["time_window"]
            limit_info["call_count"] = 0

        if limit_info["call_count"] >= limit_info["max_calls"]:
            logger.warning(f"Rate limit exceeded for plugin: {plugin_name}")
            return False

        limit_info["call_count"] += 1
        return True

    def reset_rate_limits(self) -> None:
        """重置所有速率限制"""
        for plugin_name in self._rate_limits:
            self._rate_limits[plugin_name]["call_count"] = 0
        logger.info("All rate limits reset")

    def sanitize_input(self, text: str, max_length: int = 100000) -> str:
        """
        清理输入文本

        Args:
            text: 输入文本
            max_length: 最大长度

        Returns:
            清理后的文本
        """
        if not text:
            return ""

        # 截断过长文本
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Input text truncated to {max_length} characters")

        # 移除危险字符(简单过滤)
        dangerous_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05']
        for char in dangerous_chars:
            text = text.replace(char, '')

        return text

    def validate_file_path(self, file_path: str) -> bool:
        """
        验证文件路径是否安全

        Args:
            file_path: 文件路径

        Returns:
            是否安全
        """
        if not file_path:
            return False

        import os
        # 防止路径遍历攻击
        if '..' in file_path:
            logger.warning(f"Path traversal attempt detected: {file_path}")
            return False

        # 检查文件扩展名
        allowed_extensions = {'.pdf', '.txt', '.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        _, ext = os.path.splitext(file_path.lower())
        return ext in allowed_extensions

    def get_security_info(self) -> Dict[str, Any]:
        """
        获取安全信息

        Returns:
            安全信息字典
        """
        return {
            "allowed_plugins": list(self._allowed_plugins),
            "allowed_tools": list(self._allowed_tools),
            "rate_limits_enabled": len(self._rate_limits) > 0,
            "api_keys_count": len(self._api_keys)
        }
