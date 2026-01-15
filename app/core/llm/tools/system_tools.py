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
        return "获取指定页面的文本内容。如果页面包含原生文本,直接返回;如果没有文本,会自动进行OCR识别然后返回结果。支持使用-1表示最后一页,0表示当前页。"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_number": {
                    "type": "integer",
                    "description": "目标页码。从1开始编号,例如1表示第一页,-1表示最后一页,0或不填写表示当前页"
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
                    page_number = main_window.virtual_scroll.get_current_page()  # 已经是1-based
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

            # 检查页面是否有OCR数据或原生文本
            has_text = False
            page_text = ""
            is_native_text = False

            if hasattr(main_window, 'virtual_scroll') and hasattr(main_window.virtual_scroll, 'ocr_results'):
                ocr_result = main_window.virtual_scroll.ocr_results.get(page_index)
                if ocr_result:
                    has_text = True
                    # 提取OCR文本
                    if isinstance(ocr_result, dict):
                        lines = ocr_result.get("lines", [])
                        page_text = "\n".join([line.get("text", "") for line in lines])
                    elif isinstance(ocr_result, str):
                        page_text = ocr_result
                    else:
                        page_text = str(ocr_result)

            # 如果没有OCR数据,尝试从PDF提取原生文本
            if not has_text:
                try:
                    page = main_window.pdf_processor.fitz_document[page_index]
                    page_text = page.get_text()
                    if page_text.strip():
                        has_text = True
                        is_native_text = True
                except Exception as e:
                    logger.warning(f"Failed to extract native text from page {page_number}: {e}")

            # 如果仍然没有文本,需要执行OCR
            if not has_text or not page_text.strip():
                logger.info(f"Page {page_number} has no text, performing OCR")

                # 检查主窗口是否有perform_ocr方法
                if hasattr(main_window, 'perform_ocr'):
                    # 执行单页OCR
                    ocr_result = main_window.perform_ocr(page_index)

                    if ocr_result and ocr_result.is_success():
                        # 弹出对话框显示OCR识别结果
                        from app.ui.screenshot_result_dialog import ScreenshotOCRResultDialog
                        dialog = ScreenshotOCRResultDialog(ocr_result, main_window)
                        dialog.setWindowTitle(f"第{page_number}页 - OCR识别结果")
                        dialog.exec_()

                        # 提取OCR文本用于缓存
                        page_text = ocr_result.text if hasattr(ocr_result, 'text') else str(ocr_result)
                        has_text = True
                        is_native_text = False

                        # 将OCR结果保存到virtual_scroll的ocr_results中（如果存在）
                        if hasattr(main_window, 'virtual_scroll') and hasattr(main_window.virtual_scroll, 'ocr_results'):
                            main_window.virtual_scroll.ocr_results[page_index] = {
                                "lines": [{"text": line} for line in page_text.split('\n')],
                                "full_text": page_text
                            }

                        # OCR识别成功,只返回成功状态,不返回文本(用户已通过对话框看到)
                        return {
                            "success": True,
                            "page_number": page_number,
                            "message": f"第{page_number}页OCR识别完成"
                        }
                    else:
                        # OCR失败
                        return {
                            "success": False,
                            "error": f"OCR识别失败: {ocr_result.message if hasattr(ocr_result, 'message') else '未知错误'}"
                        }
                else:
                    return {
                        "success": False,
                        "error": "主窗口不支持OCR功能"
                    }

            # 返回结果
            # 如果是原生文本,返回文本内容
            # 如果是OCR识别,已经在上面的代码中返回了成功状态
            if is_native_text and page_text.strip():
                result = {
                    "success": True,
                    "page_number": page_number,
                    "page_text": page_text,
                    "text_length": len(page_text),
                    "message": f"第{page_number}页原生文本提取成功"
                }
                logger.info(f"Retrieved native text from page {page_number}, length: {len(page_text)}")
                return result
            elif has_text and page_text.strip():
                # 缓存的OCR文本,返回文本
                result = {
                    "success": True,
                    "page_number": page_number,
                    "page_text": page_text,
                    "text_length": len(page_text),
                    "message": f"第{page_number}页OCR文本提取成功"
                }
                logger.info(f"Retrieved cached OCR text from page {page_number}, length: {len(page_text)}")
                return result
            else:
                return {
                    "success": False,
                    "error": f"页面{page_number}无法提取文本"
                }

        except Exception as e:
            logger.error(f"Error getting page text: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"获取页面文本失败: {str(e)}"
            }
