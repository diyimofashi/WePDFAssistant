"""OCR工具增强版 - PDF文字识别功能"""
from typing import Dict, Any
from app.core.llm.tools.base_tool import BaseTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OCRLikePageTool(BaseTool):
    """OCR识别页面工具"""

    @property
    def name(self) -> str:
        return "ocr_page"

    @property
    def description(self) -> str:
        return "对PDF文档的指定页面进行OCR文字识别"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_nums": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "要识别的页码列表,例如: [1, 2, 3], 留空则识别全部"
                },
                "language": {
                    "type": "string",
                    "description": "识别语言,例如: chi_sim(简体中文), eng(英语), chi_sim+eng(中英混合)"
                }
            },
            "required": []
        }

    def requires_main_thread(self) -> bool:
        """OCR工具需要在主线程中执行,因为涉及GUI操作"""
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """同步执行OCR工具"""
        page_nums = params.get("page_nums", [])
        language = params.get("language", "chi_sim+eng")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口,请先打开PDF文档"
                }

            # 检查是否有打开的PDF文档
            if not hasattr(main_window, 'pdf_processor') or not main_window.pdf_processor.fitz_document:
                return {
                    "success": False,
                    "error": "请先打开PDF文档"
                }

            # 调用主窗口已有的OCR功能
            # 如果没有指定页码或指定了多页,使用批量OCR
            if not page_nums or len(page_nums) > 1:
                if hasattr(main_window, 'perform_ocr_on_all_pages'):
                    main_window.perform_ocr_on_all_pages()
                    return {
                        "success": True,
                        "message": "已启动批量OCR识别,处理完成后会自动生成可搜索PDF。请稍候...",
                        "language": language,
                        "mode": "batch"
                    }
                else:
                    return {
                        "success": False,
                        "error": "主窗口不支持批量OCR功能"
                    }
            else:
                # 识别单页
                target_page = page_nums[0]  # 保持1-based索引

                try:
                    # 先跳转到目标页 (go_to_page使用1-based索引)
                    if hasattr(main_window, 'go_to_page'):
                        main_window.go_to_page(target_page)

                    # 执行单页OCR (对当前页进行OCR)
                    # perform_ocr_on_current_page()内部会自动处理刷新和跳转回原页面
                    # 注意: 这个方法会弹出对话框,可能导致阻塞,需要在主线程中执行
                    if hasattr(main_window, 'perform_ocr_on_current_page'):
                        main_window.perform_ocr_on_current_page()

                    # OCR结束后再跳转到目标页,确保看到OCR后的页面
                    if hasattr(main_window, 'go_to_page'):
                        main_window.go_to_page(target_page)

                    return {
                        "success": True,
                        "message": f"已完成第{page_nums[0]}页的OCR识别,已生成可搜索PDF。您现在可以搜索识别到的文本了。",
                        "language": language,
                        "page_nums": page_nums,
                        "mode": "single"
                    }
                except Exception as ocr_error:
                    logger.error(f"OCR执行失败: {ocr_error}", exc_info=True)
                    return {
                        "success": False,
                        "error": f"OCR识别失败: {str(ocr_error)}"
                    }

        except Exception as e:
            logger.error(f"Error performing OCR: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"OCR识别失败: {str(e)}"
            }


class CreateSearchablePDFTool(BaseTool):
    """创建可搜索PDF工具"""

    @property
    def name(self) -> str:
        return "create_searchable_pdf"

    @property
    def description(self) -> str:
        return "为当前PDF文档创建可搜索版本(通过OCR识别)"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "识别语言,例如: chi_sim(简体中文), eng(英语), chi_sim+eng(中英混合)"
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径(留空则覆盖原文件)"
                }
            },
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        language = params.get("language", "chi_sim+eng")
        output_path = params.get("output_path", "")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口,请先打开PDF文档"
                }

            # 检查是否有打开的PDF文档
            if not hasattr(main_window, 'pdf_processor') or not main_window.pdf_processor.fitz_document:
                return {
                    "success": False,
                    "error": "请先打开PDF文档"
                }

            # 调用批量OCR功能生成可搜索PDF
            if hasattr(main_window, 'perform_ocr_on_all_pages'):
                main_window.perform_ocr_on_all_pages()

                message = "已启动OCR识别,处理完成后会生成可搜索PDF。请稍候..."
                if output_path:
                    message += f"输出文件: {output_path}"

                logger.info(f"Creating searchable PDF with language: {language}, output: {output_path}")
                return {
                    "success": True,
                    "message": message,
                    "language": language,
                    "output_path": output_path
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持OCR功能"
                }
        except Exception as e:
            logger.error(f"Error creating searchable PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"创建可搜索PDF失败: {str(e)}"
            }
