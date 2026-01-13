"""消息工具 - 向用户显示消息通知"""
from typing import Dict, Any
from app.core.llm.tools.base_tool import BaseTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ShowMessageTool(BaseTool):
    """显示消息通知工具"""

    @property
    def name(self) -> str:
        return "show_message"

    @property
    def description(self) -> str:
        return "向用户显示消息通知,包括成功、错误、警告等信息"

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
                    "description": "消息标题,可选"
                }
            },
            "required": ["message"]
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        message = params.get("message", "")
        level = params.get("level", "info")
        title = params.get("title", "")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            # 检查是否有显示消息的方法
            if hasattr(main_window, 'show_message'):
                main_window.show_message(message)

                logger.info(f"Showing message: level={level}, title={title}, message={message}")
                return {
                    "success": True,
                    "message": "消息已显示",
                    "displayed_message": message,
                    "level": level,
                    "title": title
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持显示消息功能"
                }
        except Exception as e:
            logger.error(f"Error showing message: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"显示消息失败: {str(e)}"
            }
