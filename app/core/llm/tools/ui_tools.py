"""
UI工具集合
提供消息提示、PDF显示等UI操作工具
"""
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget, QMessageBox
from app.core.llm.tools.base_tool import BaseTool
from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RenderPDFTool(BaseTool):
    """渲染PDF页面工具"""

    @property
    def name(self) -> str:
        return "render_pdf"

    @property
    def description(self) -> str:
        return "渲染PDF页面为图像，用于显示"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "PDF文件路径"
                },
                "page_range": {
                    "type": "string",
                    "description": "渲染的页面范围，例如: '0'（第1页）, '0-5'（前6页）, 'all'（全部）"
                },
                "width": {
                    "type": "integer",
                    "description": "渲染宽度，默认800"
                },
                "height": {
                    "type": "integer",
                    "description": "渲染高度，默认1000"
                }
            },
            "required": ["file_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "file_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="open"
            )
            widget.set_placeholder("选择PDF文件...")
            return widget
        return None

    def requires_main_thread(self) -> bool:
        """渲染PDF需要访问主窗口的渲染器，必须在主线程中执行"""
        return True

    def get_next_tool(self) -> Optional[str]:
        """渲染后需要显示PDF"""
        return "show_pdf"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("file_path")
        page_range = params.get("page_range", "0")
        width = params.get("width", 800)
        height = params.get("height", 1000)

        try:
            logger.info(f"Rendering PDF: {file_path}, page_range={page_range}, size={width}x{height}")

            # 渲染逻辑通过主窗口的渲染器实现
            # 这里先返回成功，实际渲染在show_pdf工具中完成
            # 这样设计是因为渲染和显示通常是一起的

            return {
                "success": True,
                "message": f"PDF渲染准备完成: {file_path}",
                "file_path": file_path,
                "page_range": page_range,
                "width": width,
                "height": height
            }

        except Exception as e:
            logger.error(f"Error rendering PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"渲染PDF失败: {str(e)}"
            }


class ShowPDFTool(BaseTool):
    """在UI中显示PDF工具"""

    @property
    def name(self) -> str:
        return "show_pdf"

    @property
    def description(self) -> str:
        return "在主窗口的PDF显示区域显示已渲染的PDF文档"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "PDF文件路径"
                },
                "page_num": {
                    "type": "integer",
                    "description": "起始页码，从0开始，默认为0"
                }
            },
            "required": ["file_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "file_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="open"
            )
            widget.set_placeholder("选择PDF文件...")
            return widget
        return None

    def requires_main_thread(self) -> bool:
        """显示PDF需要更新UI，必须在主线程中执行"""
        return True

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("file_path")
        page_num = params.get("page_num", 0)

        try:
            logger.info(f"Showing PDF: {file_path} at page {page_num}")

            # 实际的PDF显示逻辑通过LLMChatDialog的_open_pdf_file方法实现
            # 这个工具只是提供接口，实际执行在LLMChatDialog中完成
            # 这样可以保持工具的独立性

            return {
                "success": True,
                "message": f"PDF已显示: {file_path}",
                "file_path": file_path,
                "page_num": page_num
            }

        except Exception as e:
            logger.error(f"Error showing PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"显示PDF失败: {str(e)}"
            }


class ShowMessageTool(BaseTool):
    """显示消息通知工具"""

    @property
    def name(self) -> str:
        return "show_message"

    @property
    def description(self) -> str:
        return "向用户显示消息通知，包括成功、错误、警告等信息"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "要显示的消息内容"
                },
                "level": {
                    "type": "string",
                    "enum": ["info", "success", "warning", "error"],
                    "description": "消息级别: info(信息), success(成功), warning(警告), error(错误)"
                },
                "title": {
                    "type": "string",
                    "description": "消息标题，可选"
                }
            },
            "required": ["message"]
        }

    def requires_main_thread(self) -> bool:
        """显示消息需要更新UI，必须在主线程中执行"""
        return True

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        message = params.get("message", "")
        level = params.get("level", "info")
        title = params.get("title", "")

        try:
            logger.info(f"Showing message: level={level}, title={title}, message={message}")

            # 实际的消息显示逻辑在LLMChatDialog中实现
            # 这里只返回结果，实际UI更新在对话框中完成

            return {
                "success": True,
                "message": "消息已显示",
                "displayed_message": message,
                "level": level,
                "title": title
            }

        except Exception as e:
            logger.error(f"Error showing message: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"显示消息失败: {str(e)}"
            }


class NavigatePDFTool(BaseTool):
    """PDF导航工具（翻页、缩放等）"""

    @property
    def name(self) -> str:
        return "navigate_pdf"

    @property
    def description(self) -> str:
        return "导航PDF文档，支持翻页、跳转到指定页、缩放等操作"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["next_page", "prev_page", "first_page", "last_page", "goto_page", "zoom_in", "zoom_out", "zoom_fit"],
                    "description": "导航动作: next_page(下一页), prev_page(上一页), first_page(第一页), last_page(最后一页), goto_page(跳转), zoom_in(放大), zoom_out(缩小), zoom_fit(适应页面)"
                },
                "page_num": {
                    "type": "integer",
                    "description": "目标页码（仅对goto_page动作有效）"
                },
                "zoom_level": {
                    "type": "number",
                    "description": "缩放级别，例如: 1.0, 1.5, 2.0"
                }
            },
            "required": ["action"]
        }

    def requires_main_thread(self) -> bool:
        """PDF导航需要更新UI，必须在主线程中执行"""
        return True

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "next_page")
        page_num = params.get("page_num")
        zoom_level = params.get("zoom_level")

        try:
            logger.info(f"PDF navigation: action={action}, page_num={page_num}, zoom_level={zoom_level}")

            # 实际的导航逻辑在LLMChatDialog中实现
            # 这里只返回结果

            result_message = f"PDF导航: {action}"
            if page_num is not None:
                result_message += f" -> 第{page_num + 1}页"
            if zoom_level is not None:
                result_message += f" -> {zoom_level}x"

            return {
                "success": True,
                "message": result_message,
                "action": action,
                "page_num": page_num,
                "zoom_level": zoom_level
            }

        except Exception as e:
            logger.error(f"Error navigating PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"PDF导航失败: {str(e)}"
            }
