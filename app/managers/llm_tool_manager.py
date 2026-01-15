"""
LLM工具管理器
管理所有工具和工具交互
"""
from typing import Optional, List, Dict, Any
from app.core.llm.tools.tool_registry import ToolRegistry
# 文件操作工具
from app.core.llm.tools.file_operation_tools import (
    OpenPDFTool,
    SavePDFTool
)

# 导航工具
from app.core.llm.tools.navigation_tools import (
    NavigatePDFTool
)

# 编辑工具
from app.core.llm.tools.edit_tools import (
    InsertBlankPageTool,
    DeletePagesTool,
    RotatePageTool,
    ExtractPagesTool,
    InsertPDFPageTool,
    InsertImagePageTool
)

# 合并拆分工具
from app.core.llm.tools.merge_split_tools import (
    SplitPDFTool,
    MergePDFTool
)

# OCR工具
from app.core.llm.tools.ocr_tools_enhanced import (
    OCRLikePageTool,
    CreateSearchablePDFTool
)

# 加密工具
from app.core.llm.tools.encryption_tools import (
    EncryptPDFTool
)

# 系统工具
from app.core.llm.tools.system_tools import (
    ClearCacheTool,
    UndoOperationTool,
    RedoOperationTool,
    SearchTextTool,
    ShowThumbnailTool,
    GetPageTextTool
)

# 消息工具
from app.core.llm.tools.message_tools import (
    ShowMessageTool
)
from app.core.llm.tools.file_chooser_tool import FileChooserTool
from app.core.llm.tool_interactions.interaction_handler import ToolInteractionHandler
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMToolManager:
    """LLM工具管理器"""

    _instance: Optional["LLMToolManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化工具管理器"""
        if self._initialized:
            return

        self._tool_registry = ToolRegistry()
        self._interaction_handler: Optional[ToolInteractionHandler] = None
        self._initialized = True

        # 注册默认工具
        self._register_default_tools()

        logger.info("LLMToolManager initialized")

    def _register_default_tools(self):
        """注册默认工具"""
        tools = [
            # PDF文件操作
            OpenPDFTool(),
            SavePDFTool(),

            # PDF导航操作
            NavigatePDFTool(),

            # PDF编辑操作
            InsertBlankPageTool(),
            DeletePagesTool(),
            RotatePageTool(),
            ExtractPagesTool(),
            InsertPDFPageTool(),
            InsertImagePageTool(),

            # PDF批量操作
            SplitPDFTool(),
            MergePDFTool(),

            # OCR功能
            OCRLikePageTool(),
            CreateSearchablePDFTool(),

            # 安全功能
            EncryptPDFTool(),

            # UI工具
            ShowMessageTool(),
            ShowThumbnailTool(),

            # 系统工具
            ClearCacheTool(),
            UndoOperationTool(),
            RedoOperationTool(),
            SearchTextTool(),
            GetPageTextTool(),

            # 文件选择工具
            FileChooserTool()
        ]

        for tool in tools:
            self._tool_registry.register_tool(tool)

        logger.info(f"Registered {len(tools)} default tools")

    def set_interaction_handler(self, handler: ToolInteractionHandler) -> None:
        """
        设置交互处理器

        Args:
            handler: 交互处理器实例
        """
        self._interaction_handler = handler
        
        # 设置文件选择工具的父窗口
        file_chooser_tool = self._tool_registry.get_tool("file_chooser")
        if file_chooser_tool and hasattr(file_chooser_tool, 'set_parent_widget'):
            # 获取交互处理器的父窗口
            parent_widget = handler._parent_widget if hasattr(handler, '_parent_widget') else None
            if parent_widget:
                file_chooser_tool.set_parent_widget(parent_widget)

    def get_interaction_handler(self) -> Optional[ToolInteractionHandler]:
        """获取交互处理器"""
        return self._interaction_handler

    def get_tool_registry(self) -> ToolRegistry:
        """获取工具注册中心"""
        return self._tool_registry

    def list_tools(self, include_disabled: bool = False) -> List[str]:
        """列出所有工具名称"""
        return self._tool_registry.list_tools(include_disabled)

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """获取用于LLM函数调用的工具列表"""
        return self._tool_registry.get_tools_for_llm()

    def get_all_tools_info(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """获取所有工具信息"""
        return self._tool_registry.get_all_tools_info(include_disabled)

    async def handle_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理工具调用

        Args:
            tool_name: 工具名称
            params: 参数字典

        Returns:
            执行结果
        """
        if self._interaction_handler is None:
            error_msg = "交互处理器未初始化"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "tool_name": tool_name
            }

        return await self._interaction_handler.handle_tool_call(tool_name, params)

    def enable_tool(self, tool_name: str) -> bool:
        """
        启用工具

        Args:
            tool_name: 工具名称

        Returns:
            是否成功
        """
        tool = self._tool_registry.get_tool(tool_name)
        if tool:
            tool.set_enabled(True)
            logger.info(f"Tool enabled: {tool_name}")
            return True
        return False

    def disable_tool(self, tool_name: str) -> bool:
        """
        禁用工具

        Args:
            tool_name: 工具名称

        Returns:
            是否成功
        """
        tool = self._tool_registry.get_tool(tool_name)
        if tool:
            tool.set_enabled(False)
            logger.info(f"Tool disabled: {tool_name}")
            return True
        return False
