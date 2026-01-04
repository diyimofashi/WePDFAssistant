"""
LLM系统集成类 - 统一API入口
"""
import time
from typing import Dict, List, Iterator, Any
from app.core.llm.llm_plugin_interface import (
    LLMMessage,
    LLMResult,
    LLMModelInfo,
    LLMPluginInterface
)
from app.core.llm.llm_error_handler import (
    LLMChatError,
    LLMErrorHandler
)
from app.core.llm.llm_plugin_security import LLMPluginSecurity
from app.core.llm.llm_performance_optimizer import LLMPerformanceOptimizer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMIntegration:
    """LLM系统集成类 - 单例模式"""

    _instance: "LLMIntegration | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化LLM集成系统"""
        if self._initialized:
            return

        self._plugins: Dict[str, LLMPluginInterface] = {}
        self._plugin_manager: Any = None
        self._security = LLMPluginSecurity()
        self._optimizer = LLMPerformanceOptimizer()
        self._error_handler = LLMErrorHandler()
        self._memory_manager: Any = None  # 稍后初始化
        self._tool_manager: Any = None  # 稍后初始化
        self._default_plugin: str | None = None
        self._initialized: bool = True

        logger.info("LLMIntegration initialized")

    def set_plugin_manager(self, plugin_manager: Any) -> None:
        """
        设置插件管理器

        Args:
            plugin_manager: 插件管理器实例
        """
        self._plugin_manager = plugin_manager
        logger.info("Plugin manager set")

    def set_memory_manager(self, memory_manager: Any) -> None:
        """
        设置记忆管理器

        Args:
            memory_manager: 记忆管理器实例
        """
        self._memory_manager = memory_manager
        logger.info("Memory manager set")

    def set_tool_manager(self, tool_manager: Any) -> None:
        """
        设置工具管理器

        Args:
            tool_manager: 工具管理器实例
        """
        self._tool_manager = tool_manager
        logger.info("Tool manager set")

    def initialize_system(self, plugin_configs: Dict[str, Any] | None = None) -> Dict[str, bool]:
        """
        初始化LLM系统

        Args:
            plugin_configs: 插件配置字典

        Returns:
            初始化结果字典 {plugin_name: success}
        """
        if self._plugin_manager is None:
            logger.error("Plugin manager not set")
            return {}

        logger.info("Initializing LLM system...")

        # 加载所有插件
        results = self._plugin_manager.load_all_plugins(plugin_configs)

        # 获取已加载的插件
        for plugin_name, success in results.items():
            if success:
                plugin = self._plugin_manager.get_plugin(plugin_name)
                if plugin:
                    self._plugins[plugin_name] = plugin
                    logger.info(f"Plugin '{plugin_name}' integrated successfully")

        # 设置第一个成功的插件为默认插件
        loaded_plugins = [name for name, success in results.items() if success]
        if loaded_plugins:
            self._default_plugin = loaded_plugins[0]
            logger.info(f"Default plugin set to: {self._default_plugin}")

        logger.info(f"LLM system initialized with {len(self._plugins)} plugins")
        return results

    def chat(
        self,
        plugin_name: str | None,
        messages: List[LLMMessage],
        **kwargs: Any
    ) -> LLMResult:
        """
        单次对话

        Args:
            plugin_name: 插件名称,如果为None使用默认插件
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            LLM结果
        """
        plugin_name = plugin_name or self._default_plugin

        if plugin_name is None:
            error_msg = "No plugin available"
            logger.error(error_msg)
            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=error_msg
            )

        # 安全检查
        if not self._security.is_plugin_allowed(plugin_name):
            error_msg = f"Plugin '{plugin_name}' is not allowed"
            logger.error(error_msg)
            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=error_msg
            )

        # 检查速率限制
        if not self._security.check_rate_limit(plugin_name):
            error_msg = f"Rate limit exceeded for plugin '{plugin_name}'"
            logger.warning(error_msg)
            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=error_msg
            )

        # 获取插件
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            error_msg = f"Plugin '{plugin_name}' not found"
            logger.error(error_msg)
            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=error_msg
            )

        # 验证消息
        try:
            self._error_handler.validate_messages([msg.__dict__ for msg in messages])
        except LLMChatError as e:
            logger.error(f"Message validation failed: {e}")
            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=str(e)
            )

        # 执行对话
        start_time = time.time()
        try:
            result = plugin.chat(messages, **kwargs)
            duration = time.time() - start_time

            # 记录性能指标
            self._optimizer.record_call(
                plugin_name=plugin_name,
                model=result.model,
                tokens=result.usage.get("total_tokens", 0),
                success=result.success,
                duration=duration
            )

            if result.success:
                logger.info(
                    f"Chat successful: {plugin_name} | "
                    f"Model: {result.model} | "
                    f"Tokens: {result.usage.get('total_tokens', 0)} | "
                    f"Duration: {duration:.2f}s"
                )
            else:
                logger.error(f"Chat failed: {plugin_name} | Error: {result.error}")

            return result

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Chat error: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # 记录错误指标
            self._optimizer.record_call(
                plugin_name=plugin_name,
                model="unknown",
                tokens=0,
                success=False,
                duration=duration
            )

            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=error_msg
            )

    def chat_stream(
        self,
        plugin_name: str | None,
        messages: List[LLMMessage],
        **kwargs: Any
    ) -> Iterator[LLMResult]:
        """
        流式对话

        Args:
            plugin_name: 插件名称
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            LLM结果片段
        """
        plugin_name = plugin_name or self._default_plugin

        if plugin_name is None:
            yield LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error="No plugin available"
            )
            return

        plugin = self._plugins.get(plugin_name)

        if not plugin:
            logger.error(f"Plugin '{plugin_name}' not found")
            yield LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=f"Plugin '{plugin_name}' not found"
            )
            return

        try:
            for chunk in plugin.chat_stream(messages, **kwargs):
                yield chunk
        except Exception as e:
            logger.error(f"Stream chat error: {e}", exc_info=True)
            yield LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=str(e)
            )

    def chat_with_memory(
        self,
        plugin_name: str | None,
        messages: List[LLMMessage],
        memory_key: str,
        **kwargs: Any
    ) -> LLMResult:
        """
        带记忆的对话

        Args:
            plugin_name: 插件名称
            messages: 消息列表
            memory_key: 记忆键
            **kwargs: 额外参数

        Returns:
            LLM结果
        """
        if self._memory_manager is None:
            logger.warning("Memory manager not set, proceeding without memory")
            return self.chat(plugin_name, messages, **kwargs)

        # 从记忆中检索相关上下文
        try:
            memories = self._memory_manager.get_memory(memory_key)
            if memories:
                memory_messages = [LLMMessage(**msg) for msg in memories.get("messages", [])]
                # 将记忆消息插入到消息列表中
                messages = memory_messages + messages
                logger.info(f"Loaded {len(memory_messages)} messages from memory")
        except Exception as e:
            logger.error(f"Error loading memory: {e}")

        # 执行对话
        result = self.chat(plugin_name, messages, **kwargs)

        # 保存对话到记忆
        if result.success:
            try:
                self._memory_manager.update_memory(memory_key, messages + [
                    LLMMessage(role="assistant", content=result.content)
                ])
            except Exception as e:
                logger.error(f"Error saving memory: {e}")

        return result

    def chat_with_tools(
        self,
        plugin_name: str | None,
        messages: List[LLMMessage],
        tools: List[str] | None = None,
        **kwargs: Any
    ) -> LLMResult:
        """
        支持工具调用的对话

        Args:
            plugin_name: 插件名称
            messages: 消息列表
            tools: 工具名称列表
            **kwargs: 额外参数

        Returns:
            LLM结果
        """
        if self._tool_manager is None:
            logger.warning("Tool manager not set, proceeding without tools")
            return self.chat(plugin_name, messages, **kwargs)

        # 获取可用的工具
        available_tools = tools or self._tool_manager.get_available_tools()
        tool_definitions = [
            self._tool_manager.get_tool(tool_name).to_function_definition()
            for tool_name in available_tools
            if self._tool_manager.get_tool(tool_name) is not None
        ]

        # 执行对话并处理工具调用
        max_iterations = 5  # 防止无限循环
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # 调用LLM
            result = self.chat(
                plugin_name,
                messages,
                functions=tool_definitions if tool_definitions else None,
                **kwargs
            )

            if not result.success:
                return result

            # 检查是否有工具调用
            if result.metadata and "tool_calls" in result.metadata:
                tool_calls = result.metadata["tool_calls"]

                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("arguments", {})

                    # 安全检查
                    if not self._security.is_tool_allowed(tool_name):
                        error_msg = f"Tool '{tool_name}' is not allowed"
                        logger.error(error_msg)
                        messages.append(LLMMessage(
                            role="assistant",
                            content=f"Error: {error_msg}"
                        ))
                        continue

                    # 执行工具
                    try:
                        tool_result = self._tool_manager.execute_tool(tool_name, tool_args)

                        # 将工具结果添加到消息中
                        messages.append(LLMMessage(
                            role="assistant",
                            content="",
                            metadata={"tool_calls": [tool_call]}
                        ))
                        messages.append(LLMMessage(
                            role="user",
                            content=f"Tool result: {tool_result}"
                        ))

                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        messages.append(LLMMessage(
                            role="assistant",
                            content=f"Tool execution error: {str(e)}"
                        ))
                        return LLMResult(
                            success=False,
                            content="",
                            model=result.model,
                            usage=result.usage,
                            error=f"Tool execution error: {str(e)}"
                        )
            else:
                # 没有工具调用,直接返回结果
                return result

        # 达到最大迭代次数
        logger.warning(f"Max iterations ({max_iterations}) reached")
        return result

    def get_available_plugins(self) -> List[str]:
        """获取可用插件列表"""
        return list(self._plugins.keys())

    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any] | None:
        """
        获取插件信息

        Args:
            plugin_name: 插件名称

        Returns:
            插件信息字典或None
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return None

        return plugin.get_plugin_info()

    def get_supported_models(self, plugin_name: str) -> List[LLMModelInfo]:
        """
        获取支持的模型

        Args:
            plugin_name: 插件名称

        Returns:
            模型信息列表
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return []

        return plugin.get_supported_models()

    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> Dict[str, str]:
        """
        设置插件配置

        Args:
            plugin_name: 插件名称
            config: 配置字典

        Returns:
            设置结果
        """
        # 如果插件管理器存在,重新加载插件
        if self._plugin_manager:
            self._plugin_manager.reload_plugin(plugin_name, config)

        return {"status": "success", "message": f"Config updated for {plugin_name}"}

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件配置

        Args:
            plugin_name: 插件名称

        Returns:
            配置字典
        """
        if self._plugin_manager:
            plugin_config = self._plugin_manager.get_plugin_info(plugin_name)
            return plugin_config or {}

        return {}

    def get_default_plugin(self) -> str | None:
        """获取默认插件名称"""
        return self._default_plugin

    def set_default_plugin(self, plugin_name: str) -> bool:
        """
        设置默认插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否设置成功
        """
        if plugin_name not in self._plugins:
            logger.error(f"Cannot set default plugin: '{plugin_name}' not loaded")
            return False

        self._default_plugin = plugin_name
        logger.info(f"Default plugin set to: {plugin_name}")
        return True

    def get_security(self) -> LLMPluginSecurity:
        """获取安全管理器"""
        return self._security

    def get_optimizer(self) -> LLMPerformanceOptimizer:
        """获取性能优化器"""
        return self._optimizer

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return self._optimizer.get_performance_report()
