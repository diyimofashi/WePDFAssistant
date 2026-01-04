"""
LLM插件错误处理器
"""
from typing import Dict, Any, List
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMError(Exception):
    """LLM基础错误类"""
    def __init__(self, message: str, error_code: str = "UNKNOWN", details: Dict[str, Any] | None = None):
        super().__init__(message)
        self.message: str = message
        self.error_code: str = error_code
        self.details: Dict[str, Any] = details or {}


class LLMPluginNotFoundError(LLMError):
    """插件未找到错误"""
    def __init__(self, plugin_name: str):
        super().__init__(
            f"LLM plugin '{plugin_name}' not found",
            error_code="PLUGIN_NOT_FOUND",
            details={"plugin_name": plugin_name}
        )


class LLMInitializationError(LLMError):
    """初始化错误"""
    def __init__(self, plugin_name: str, reason: str):
        super().__init__(
            f"Failed to initialize LLM plugin '{plugin_name}': {reason}",
            error_code="INITIALIZATION_ERROR",
            details={"plugin_name": plugin_name, "reason": reason}
        )


class LLMChatError(LLMError):
    """对话错误"""
    def __init__(self, plugin_name: str, reason: str, details: Dict[str, Any] | None = None):
        super().__init__(
            f"LLM chat error in '{plugin_name}': {reason}",
            error_code="CHAT_ERROR",
            details={"plugin_name": plugin_name, "reason": reason, **(details or {})}
        )


class LLMConfigError(LLMError):
    """配置错误"""
    def __init__(self, plugin_name: str, reason: str):
        super().__init__(
            f"Configuration error in '{plugin_name}': {reason}",
            error_code="CONFIG_ERROR",
            details={"plugin_name": plugin_name, "reason": reason}
        )


class LLMTokenLimitError(LLMError):
    """Token限制错误"""
    def __init__(self, model: str, requested: int, limit: int):
        super().__init__(
            f"Token limit exceeded for model '{model}': requested {requested}, limit {limit}",
            error_code="TOKEN_LIMIT_EXCEEDED",
            details={"model": model, "requested": requested, "limit": limit}
        )


class LLMToolExecutionError(LLMError):
    """工具执行错误"""
    def __init__(self, tool_name: str, reason: str, details: Dict[str, Any] | None = None):
        super().__init__(
            f"Tool execution error in '{tool_name}': {reason}",
            error_code="TOOL_EXECUTION_ERROR",
            details={"tool_name": tool_name, "reason": reason, **(details or {})}
        )


class LLMErrorHandler:
    """LLM错误处理器"""

    @staticmethod
    def handle_error(error: Exception, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        处理错误并返回统一格式的错误信息

        Args:
            error: 异常对象
            context: 上下文信息

        Returns:
            错误信息字典
        """
        error_info: Dict[str, Any] = {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "context": context or {}
        }

        if isinstance(error, LLMError):
            error_info["error_code"] = error.error_code
            error_info["details"] = error.details

        logger.error(
            f"LLM Error: {error_info['error']} | "
            f"Type: {error_info['error_type']} | "
            f"Context: {error_info['context']}"
        )

        return error_info

    @staticmethod
    def validate_config(plugin_name: str, config: Dict[str, Any], required_fields: List[str]) -> None:
        """
        验证配置

        Args:
            plugin_name: 插件名称
            config: 配置字典
            required_fields: 必需字段列表

        Raises:
            LLMConfigError: 配置验证失败
        """
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise LLMConfigError(
                plugin_name,
                f"Missing required fields: {', '.join(missing_fields)}"
            )

    @staticmethod
    def validate_messages(messages: list[dict]) -> None:
        """
        验证消息列表

        Args:
            messages: 消息列表

        Raises:
            LLMChatError: 消息验证失败
        """
        if not messages:
            raise LLMChatError("unknown", "Messages list cannot be empty")

        valid_roles = {"system", "user", "assistant"}
        for msg in messages:
            if not isinstance(msg, dict):
                raise LLMChatError("unknown", f"Message must be a dict, got {type(msg)}")
            if "role" not in msg or "content" not in msg:
                raise LLMChatError("unknown", "Message must contain 'role' and 'content' fields")
            if msg["role"] not in valid_roles:
                raise LLMChatError("unknown", f"Invalid role: {msg['role']}")
