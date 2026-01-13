"""导航工具 - 翻页、缩放、跳转等PDF导航功能"""
from typing import Dict, Any
from app.core.llm.tools.base_tool import BaseTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NavigatePDFTool(BaseTool):
    """PDF导航工具(翻页、跳转、缩放等)"""

    @property
    def name(self) -> str:
        return "navigate_pdf"

    @property
    def description(self) -> str:
        return "导航PDF文档,支持翻页、跳转到指定页、缩放等操作"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["next_page", "prev_page", "first_page", "last_page", "goto_page", "zoom_in", "zoom_out", "zoom_fit", "fit_width", "fit_height"],
                    "description": "导航动作: next_page(下一页), prev_page(上一页), first_page(第一页), last_page(最后一页), goto_page(跳转), zoom_in(放大), zoom_out(缩小), zoom_fit(适应页面), fit_width(适应宽度), fit_height(适应高度)"
                },
                "page_num": {
                    "type": "integer",
                    "description": "目标页码(仅对goto_page动作有效,从1开始)"
                },
                "zoom_level": {
                    "type": "number",
                    "description": "缩放级别,例如: 1.0, 1.5, 2.0"
                }
            },
            "required": ["action"]
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "next_page")
        page_num = params.get("page_num")
        zoom_level = params.get("zoom_level")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            # 检查是否有打开的PDF文档
            if not hasattr(main_window, 'pdf_processor') or not main_window.pdf_processor.fitz_document:
                return {
                    "success": False,
                    "error": "请先打开PDF文档"
                }

            # 执行对应的导航操作
            if action == "next_page":
                if hasattr(main_window, 'next_page'):
                    main_window.next_page()
                    result_message = "下一页"
            elif action == "prev_page":
                if hasattr(main_window, 'previous_page'):
                    main_window.previous_page()
                    result_message = "上一页"
            elif action == "first_page":
                if hasattr(main_window, 'go_to_page'):
                    main_window.go_to_page(1)
                    result_message = "第一页"
            elif action == "last_page":
                if hasattr(main_window, 'pdf_processor'):
                    total_pages = main_window.pdf_processor.total_pages
                    main_window.go_to_page(total_pages)
                    result_message = f"最后一页(第{total_pages}页)"
            elif action == "goto_page":
                if page_num is not None and hasattr(main_window, 'go_to_page'):
                    main_window.go_to_page(page_num)
                    result_message = f"跳转到第{page_num}页"
                else:
                    return {
                        "success": False,
                        "error": "跳转页面需要指定page_num参数"
                    }
            elif action == "zoom_in":
                if hasattr(main_window, 'zoom_in'):
                    main_window.zoom_in()
                    result_message = "放大"
            elif action == "zoom_out":
                if hasattr(main_window, 'zoom_out'):
                    main_window.zoom_out()
                    result_message = "缩小"
            elif action == "zoom_fit":
                if hasattr(main_window, 'set_actual_size'):
                    main_window.set_actual_size()
                    result_message = "适应页面"
            elif action == "fit_width":
                if hasattr(main_window, 'fit_to_width'):
                    main_window.fit_to_width()
                    result_message = "适应宽度"
            elif action == "fit_height":
                if hasattr(main_window, 'fit_to_height'):
                    main_window.fit_to_height()
                    result_message = "适应高度"
            else:
                return {
                    "success": False,
                    "error": f"未知的导航动作: {action}"
                }

            logger.info(f"PDF navigation: action={action}, page_num={page_num}, zoom_level={zoom_level}")
            return {
                "success": True,
                "message": f"PDF导航: {result_message}",
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
