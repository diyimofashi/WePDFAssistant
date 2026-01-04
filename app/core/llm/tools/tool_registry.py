"""
工具注册中心
管理所有可用的工具
"""
from typing import Dict, List, Optional, Any
from app.core.llm.tools.base_tool import BaseTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """工具注册中心"""

    _instance: Optional["ToolRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化工具注册中心"""
        if self._initialized:
            return

        self._tools: Dict[str, BaseTool] = {}
        self._initialized = True
        logger.info("ToolRegistry initialized")

    def register_tool(self, tool: BaseTool) -> bool:
        """
        注册工具

        Args:
            tool: 工具实例

        Returns:
            是否注册成功
        """
        if not tool.name:
            logger.error("Cannot register tool without name")
            return False

        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")

        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")
        return True

    def unregister_tool(self, tool_name: str) -> bool:
        """
        注销工具

        Args:
            tool_name: 工具名称

        Returns:
            是否注销成功
        """
        if tool_name not in self._tools:
            logger.warning(f"Tool '{tool_name}' not found")
            return False

        del self._tools[tool_name]
        logger.info(f"Tool unregistered: {tool_name}")
        return True

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具

        Args:
            tool_name: 工具名称

        Returns:
            工具实例或None
        """
        return self._tools.get(tool_name)

    def list_tools(self, include_disabled: bool = False) -> List[str]:
        """
        列出所有工具名称

        Args:
            include_disabled: 是否包含禁用的工具

        Returns:
            工具名称列表
        """
        if include_disabled:
            return list(self._tools.keys())
        else:
            return [name for name, tool in self._tools.items() if tool.is_enabled()]

    def get_all_tools_info(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        获取所有工具信息

        Args:
            include_disabled: 是否包含禁用的工具

        Returns:
            工具信息列表
        """
        tools = []
        for tool_name, tool in self._tools.items():
            if include_disabled or tool.is_enabled():
                tools.append(tool.get_tool_info())
        return tools

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        获取用于LLM函数调用的工具列表

        Returns:
            符合LLM函数调用格式的工具列表
        """
        tools = []
        for tool_name, tool in self._tools.items():
            if tool.is_enabled():
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.get_parameters_schema()
                    }
                })
        return tools

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        logger.info("All tools cleared")
