"""系统工具 - 缓存清理、撤销重做、搜索、缩略图等系统功能"""
from typing import Dict, Any
from app.core.llm.tools.base_tool import BaseTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ClearCacheTool(BaseTool):
    """清理缓存工具"""

    @property
    def name(self) -> str:
        return "clear_cache"

    @property
    def description(self) -> str:
        return "清理所有缓存,释放内存"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            # 检查是否有清理缓存的方法
            if hasattr(main_window, 'clear_cache'):
                main_window.clear_cache()

                logger.info("Cleared all caches")
                return {
                    "success": True,
                    "message": "所有缓存已清理"
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持清理缓存功能"
                }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"清理缓存失败: {str(e)}"
            }


class UndoOperationTool(BaseTool):
    """撤销操作工具"""

    @property
    def name(self) -> str:
        return "undo_operation"

    @property
    def description(self) -> str:
        return "撤销上一次PDF编辑操作"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            # 检查是否有打开的PDF文档
            if not hasattr(main_window, 'pdf_processor'):
                return {
                    "success": False,
                    "error": "请先打开PDF文档"
                }

            # 检查是否有撤销操作的方法
            if hasattr(main_window, 'undo_operation'):
                main_window.undo_operation()

                logger.info("Undoing last operation")
                return {
                    "success": True,
                    "message": "已撤销上一次操作"
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持撤销操作"
                }
        except Exception as e:
            logger.error(f"Error undoing operation: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"撤销操作失败: {str(e)}"
            }


class RedoOperationTool(BaseTool):
    """重做操作工具"""

    @property
    def name(self) -> str:
        return "redo_operation"

    @property
    def description(self) -> str:
        return "重做上一次撤销的操作"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            # 检查是否有打开的PDF文档
            if not hasattr(main_window, 'pdf_processor'):
                return {
                    "success": False,
                    "error": "请先打开PDF文档"
                }

            # 检查是否有重做操作的方法
            if hasattr(main_window, 'redo_operation'):
                main_window.redo_operation()

                logger.info("Redoing last operation")
                return {
                    "success": True,
                    "message": "已重做上一次撤销的操作"
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持重做操作"
                }
        except Exception as e:
            logger.error(f"Error redoing operation: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"重做操作失败: {str(e)}"
            }


class SearchTextTool(BaseTool):
    """文本搜索工具"""

    @property
    def name(self) -> str:
        return "search_text"

    @property
    def description(self) -> str:
        return "在PDF文档中搜索指定文本"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要搜索的文本"
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "是否区分大小写,默认false"
                }
            },
            "required": ["text"]
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text", "")
        case_sensitive = params.get("case_sensitive", False)

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

            # 检查是否有搜索功能
            if hasattr(main_window, 'search_manager'):
                # 设置搜索文本并执行搜索
                main_window.search_manager.search_text(text, case_sensitive)

                logger.info(f"Searching text: '{text}', case_sensitive={case_sensitive}")
                return {
                    "success": True,
                    "message": f"已搜索文本: '{text}'",
                    "text": text,
                    "case_sensitive": case_sensitive
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持搜索功能"
                }
        except Exception as e:
            logger.error(f"Error searching text: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"搜索文本失败: {str(e)}"
            }


class ShowThumbnailTool(BaseTool):
    """显示/隐藏缩略图工具"""

    @property
    def name(self) -> str:
        return "toggle_thumbnails"

    @property
    def description(self) -> str:
        return "显示或隐藏缩略图面板"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "show": {
                    "type": "boolean",
                    "description": "是否显示缩略图, true=显示, false=隐藏, 留空则切换"
                }
            },
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        show = params.get("show")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            # 检查主窗口是否有toggle_thumbnails方法
            if hasattr(main_window, 'toggle_thumbnails'):
                main_window.toggle_thumbnails()

                if show is True:
                    message = "缩略图面板已显示"
                elif show is False:
                    message = "缩略图面板已隐藏"
                else:
                    message = "缩略图面板已切换"

                logger.info(message)
                return {
                    "success": True,
                    "message": message,
                    "show": show
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持缩略图功能"
                }
        except Exception as e:
            logger.error(f"Error toggling thumbnails: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"切换缩略图失败: {str(e)}"
            }


class GetPageTextTool(BaseTool):
    """获取页面文本工具"""

    @property
    def name(self) -> str:
        return "get_page_text"

    @property
    def description(self) -> str:
        return "获取指定页面的文本内容。如果页面没有OCR文本,会自动进行OCR识别然后返回文本。"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_number": {
                    "type": "integer",
                    "description": "页码,从1开始。例如1表示第一页,-1表示最后一页,0表示当前页"
                }
            },
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_number = params.get("page_number")

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

            # 确定目标页码
            if page_number is None or page_number == 0:
                # 获取当前页
                if hasattr(main_window, 'virtual_scroll'):
                    page_number = main_window.virtual_scroll.current_page + 1  # 转换为1-based
                else:
                    return {
                        "success": False,
                        "error": "无法获取当前页码"
                    }
            elif page_number == -1:
                # 最后一页
                page_number = main_window.pdf_processor.fitz_document.page_count
            elif page_number < 1 or page_number > main_window.pdf_processor.fitz_document.page_count:
                return {
                    "success": False,
                    "error": f"页码超出范围,文档共{main_window.pdf_processor.fitz_document.page_count}页"
                }

            # 转换为0-based索引
            page_index = page_number - 1

            # 检查页面是否有OCR数据
            has_ocr = False
            page_text = ""

            if hasattr(main_window, 'virtual_scroll') and hasattr(main_window.virtual_scroll, 'ocr_results'):
                ocr_result = main_window.virtual_scroll.ocr_results.get(page_index)
                if ocr_result:
                    has_ocr = True
                    # 提取OCR文本
                    if isinstance(ocr_result, dict):
                        lines = ocr_result.get("lines", [])
                        page_text = "\n".join([line.get("text", "") for line in lines])
                    elif isinstance(ocr_result, str):
                        page_text = ocr_result
                    else:
                        page_text = str(ocr_result)

            # 如果没有OCR数据,尝试从PDF提取原生文本
            if not has_ocr:
                try:
                    page = main_window.pdf_processor.fitz_document[page_index]
                    page_text = page.get_text()
                    if page_text.strip():
                        has_ocr = True
                except Exception as e:
                    logger.warning(f"Failed to extract native text from page {page_number}: {e}")

            # 如果仍然没有文本,需要执行OCR
            if not has_ocr or not page_text.strip():
                logger.info(f"Page {page_number} has no text, performing OCR")

                # 检查是否有perform_ocr方法
                if hasattr(main_window, 'perform_ocr'):
                    # 执行单页OCR
                    ocr_result = main_window.perform_ocr(page_index, page_index)
                    if ocr_result and "success" in ocr_result:
                        # 获取OCR结果
                        if hasattr(main_window, 'virtual_scroll') and hasattr(main_window.virtual_scroll, 'ocr_results'):
                            ocr_data = main_window.virtual_scroll.ocr_results.get(page_index)
                            if ocr_data:
                                if isinstance(ocr_data, dict):
                                    lines = ocr_data.get("lines", [])
                                    page_text = "\n".join([line.get("text", "") for line in lines])
                                elif isinstance(ocr_data, str):
                                    page_text = ocr_data
                                else:
                                    page_text = str(ocr_data)
                                has_ocr = True
                    else:
                        return {
                            "success": False,
                            "error": f"OCR识别失败: {ocr_result.get('error', '未知错误')}"
                        }
                else:
                    return {
                        "success": False,
                        "error": "主窗口不支持OCR功能"
                    }

            # 返回结果
            result = {
                "success": True,
                "page_number": page_number,
                "page_text": page_text,
                "text_length": len(page_text),
                "is_ocr": not (has_ocr and main_window.pdf_processor.fitz_document[page_index].get_text().strip())
            }

            logger.info(f"Retrieved text from page {page_number}, length: {len(page_text)}")
            return result

        except Exception as e:
            logger.error(f"Error getting page text: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"获取页面文本失败: {str(e)}"
            }
