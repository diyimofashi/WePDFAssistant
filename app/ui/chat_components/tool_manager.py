"""
工具管理器组件
处理LLM工具的执行和交互
"""
from PyQt5.QtCore import QObject, pyqtSignal
from typing import Dict, Any, Callable, Optional
import asyncio


class ToolManager(QObject):
    """工具管理器组件"""
    tool_execution_completed = pyqtSignal(str, dict)
    action_required = pyqtSignal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tools = {}
        self._tool_functions = {}
    
    def register_tool(self, name: str, func: Callable, schema: Dict[str, Any]):
        """注册工具"""
        self._tools[name] = schema
        self._tool_functions[name] = func
    
    def get_tools_for_llm(self) -> list:
        """获取LLM可用的工具列表"""
        return [
            {
                "type": "function",
                "function": schema
            }
            for schema in self._tools.values()
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行工具"""
        if tool_name not in self._tool_functions:
            return {"success": False, "error": f"Tool {tool_name} not found"}
        
        try:
            result = await self._tool_functions[tool_name](arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def requires_user_action(self, tool_name: str, params: Dict[str, Any]):
        """工具需要用户操作"""
        self.action_required.emit(tool_name, params)