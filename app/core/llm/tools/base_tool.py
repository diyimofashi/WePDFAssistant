"""
工具基类
定义LLM工具的通用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List
from PyQt5.QtWidgets import QWidget
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseTool(ABC):
    """工具基类"""

    def __init__(self):
        self._name = ""
        self._description = ""
        self._enabled = True

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """
        获取参数schema定义

        Returns:
            JSON Schema格式的参数定义
        """
        pass

    def check_parameters_complete(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        检查参数是否完整

        Args:
            params: 参数字典

        Returns:
            (是否完整, 缺失参数列表)
        """
        schema = self.get_parameters_schema()
        required = schema.get("required", [])

        missing = []
        for param_name in required:
            if param_name not in params or not params[param_name]:
                missing.append(param_name)

        return len(missing) == 0, missing

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        """
        获取参数输入UI组件

        Args:
            param_name: 参数名称
            parent: 父窗口

        Returns:
            UI组件或None
        """
        return None

    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证参数有效性

        Args:
            params: 参数字典

        Returns:
            (是否有效, 错误信息)
        """
        return True, ""

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具

        Args:
            params: 参数字典

        Returns:
            执行结果字典
        """
        pass

    def get_default_params(self) -> Dict[str, Any]:
        """
        获取默认参数

        Returns:
            默认参数字典
        """
        return {}

    def is_enabled(self) -> bool:
        """检查工具是否启用"""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """设置工具启用状态"""
        self._enabled = enabled

    def get_tool_info(self) -> Dict[str, Any]:
        """
        获取工具信息

        Returns:
            工具信息字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.is_enabled(),
            "parameters_schema": self.get_parameters_schema(),
            "next_tool": self.get_next_tool()
        }

    def get_next_tool(self) -> Optional[str]:
        """
        获取后续工具名称

        Returns:
            后续工具名称，如果没有则返回None
        """
        return None

    def requires_main_thread(self) -> bool:
        """
        判断工具是否需要在主线程中执行（例如需要GUI交互的工具）

        Returns:
            是否需要在主线程中执行
        """
        return False
