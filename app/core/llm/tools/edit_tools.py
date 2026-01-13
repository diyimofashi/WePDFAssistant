"""编辑工具 - 插入、删除、旋转、提取页面等PDF编辑功能"""
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget
from app.core.llm.tools.base_tool import BaseTool
from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InsertBlankPageTool(BaseTool):
    """插入空白页工具"""

    @property
    def name(self) -> str:
        return "insert_blank_page"

    @property
    def description(self) -> str:
        return "在指定页码后插入空白页"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_num": {
                    "type": "integer",
                    "description": "在第几页后插入(从1开始)"
                }
            },
            "required": ["page_num"]
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_num = params.get("page_num")

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

            # 检查是否有插入空白页的方法
            if hasattr(main_window.pdf_processor, 'insert_blank_page'):
                main_window.pdf_processor.insert_blank_page(page_num)

                # 更新界面
                if hasattr(main_window, 'view_controller'):
                    main_window.view_controller.load_thumbnails()
                    main_window.update_preview()
                    if hasattr(main_window, 'repaint'):
                        main_window.repaint()

                logger.info(f"Inserted blank page after page {page_num}")
                return {
                    "success": True,
                    "message": f"已在第{page_num}页后插入空白页",
                    "page_num": page_num
                }
            else:
                return {
                    "success": False,
                    "error": "PDF处理器不支持插入空白页功能"
                }
        except Exception as e:
            logger.error(f"Error inserting blank page: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"插入空白页失败: {str(e)}"
            }


class DeletePagesTool(BaseTool):
    """删除页面工具"""

    @property
    def name(self) -> str:
        return "delete_pages"

    @property
    def description(self) -> str:
        return "删除指定的页面,可以删除单个或多个页面"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_nums": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "要删除的页码列表,例如: [1, 3, 5]"
                }
            },
            "required": ["page_nums"]
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_nums = params.get("page_nums", [])

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

            # 检查是否有删除页面的方法
            if hasattr(main_window.pdf_processor, 'delete_pages'):
                # 删除页面(从小到大排序后再删除,避免索引变化)
                sorted_pages = sorted(page_nums)
                main_window.pdf_processor.delete_pages(sorted_pages)

                # 更新界面
                if hasattr(main_window, 'view_controller'):
                    main_window.view_controller.load_thumbnails()
                    main_window.update_preview()
                    if hasattr(main_window, 'repaint'):
                        main_window.repaint()

                logger.info(f"Deleted pages: {page_nums}")
                return {
                    "success": True,
                    "message": f"已删除 {len(page_nums)} 页: {page_nums}",
                    "page_nums": page_nums
                }
            else:
                return {
                    "success": False,
                    "error": "PDF处理器不支持删除页面功能"
                }
        except Exception as e:
            logger.error(f"Error deleting pages: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"删除页面失败: {str(e)}"
            }


class RotatePageTool(BaseTool):
    """旋转页面工具"""

    @property
    def name(self) -> str:
        return "rotate_page"

    @property
    def description(self) -> str:
        return "旋转指定页面,支持90度、180度、270度旋转"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_num": {
                    "type": "integer",
                    "description": "要旋转的页码(从1开始)"
                },
                "rotation": {
                    "type": "integer",
                    "description": "旋转角度: 90(顺时针90度), 180(180度), 270(顺时针270度)"
                }
            },
            "required": ["page_num", "rotation"]
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_num = params.get("page_num")
        rotation = params.get("rotation")

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

            # 检查是否有旋转页面的方法
            if hasattr(main_window.pdf_processor, 'rotate_page'):
                main_window.pdf_processor.rotate_page(page_num, rotation)

                # 更新界面
                if hasattr(main_window, 'view_controller'):
                    main_window.view_controller.load_thumbnails()
                    main_window.update_preview()
                    if hasattr(main_window, 'repaint'):
                        main_window.repaint()

                logger.info(f"Rotated page {page_num} by {rotation} degrees")
                return {
                    "success": True,
                    "message": f"已将第{page_num}页旋转{rotation}度",
                    "page_num": page_num,
                    "rotation": rotation
                }
            else:
                return {
                    "success": False,
                    "error": "PDF处理器不支持旋转页面功能"
                }
        except Exception as e:
            logger.error(f"Error rotating page: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"旋转页面失败: {str(e)}"
            }


class ExtractPagesTool(BaseTool):
    """提取页面工具"""

    @property
    def name(self) -> str:
        return "extract_pages"

    @property
    def description(self) -> str:
        return "提取指定页面到新PDF文件"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_nums": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "要提取的页码列表,例如: [1, 2, 3]"
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径"
                }
            },
            "required": ["page_nums", "output_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "output_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="save"
            )
            widget.set_placeholder("选择输出文件...")
            return widget
        return None

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_nums = params.get("page_nums", [])
        output_path = params.get("output_path")

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

            # 检查是否有提取页面的方法
            if hasattr(main_window.pdf_processor, 'extract_pages'):
                main_window.pdf_processor.extract_pages(page_nums, output_path)

                logger.info(f"Extracted pages {page_nums} to {output_path}")
                return {
                    "success": True,
                    "message": f"已提取 {len(page_nums)} 页到 {output_path}",
                    "page_nums": page_nums,
                    "output_path": output_path
                }
            else:
                return {
                    "success": False,
                    "error": "PDF处理器不支持提取页面功能"
                }
        except Exception as e:
            logger.error(f"Error extracting pages: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"提取页面失败: {str(e)}"
            }


class InsertPDFPageTool(BaseTool):
    """插入PDF页面工具"""

    @property
    def name(self) -> str:
        return "insert_pdf_page"

    @property
    def description(self) -> str:
        return "从其他PDF文件插入页面到当前文档"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_num": {
                    "type": "integer",
                    "description": "在第几页后插入(从1开始)"
                },
                "pdf_path": {
                    "type": "string",
                    "description": "要插入的PDF文件路径"
                }
            },
            "required": ["page_num", "pdf_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "pdf_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="open"
            )
            widget.set_placeholder("选择要插入的PDF文件...")
            return widget
        return None

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_num = params.get("page_num")
        pdf_path = params.get("pdf_path")

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

            # 检查是否有插入PDF页面的方法
            if hasattr(main_window.pdf_processor, 'insert_pdf_page'):
                main_window.pdf_processor.insert_pdf_page(page_num, pdf_path)

                # 更新界面
                if hasattr(main_window, 'view_controller'):
                    main_window.view_controller.load_thumbnails()
                    main_window.update_preview()
                    if hasattr(main_window, 'repaint'):
                        main_window.repaint()

                logger.info(f"Inserted PDF pages from {pdf_path} after page {page_num}")
                return {
                    "success": True,
                    "message": f"已从PDF文件插入页面",
                    "page_num": page_num,
                    "pdf_path": pdf_path
                }
            else:
                return {
                    "success": False,
                    "error": "PDF处理器不支持插入PDF页面功能"
                }
        except Exception as e:
            logger.error(f"Error inserting PDF pages: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"插入PDF页面失败: {str(e)}"
            }


class InsertImagePageTool(BaseTool):
    """插入图片页面工具"""

    @property
    def name(self) -> str:
        return "insert_image_page"

    @property
    def description(self) -> str:
        return "插入图片作为新的PDF页面"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_num": {
                    "type": "integer",
                    "description": "在第几页后插入(从1开始)"
                },
                "image_path": {
                    "type": "string",
                    "description": "图片文件路径"
                }
            },
            "required": ["page_num", "image_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "image_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.tiff)",
                mode="open"
            )
            widget.set_placeholder("选择图片文件...")
            return widget
        return None

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_num = params.get("page_num")
        image_path = params.get("image_path")

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

            # 检查是否有插入图片页面的方法
            if hasattr(main_window.pdf_processor, 'insert_image_page'):
                main_window.pdf_processor.insert_image_page(page_num, image_path)

                # 更新界面
                if hasattr(main_window, 'view_controller'):
                    main_window.view_controller.load_thumbnails()
                    main_window.update_preview()
                    if hasattr(main_window, 'repaint'):
                        main_window.repaint()

                logger.info(f"Inserted image {image_path} after page {page_num}")
                return {
                    "success": True,
                    "message": f"已插入图片页面",
                    "page_num": page_num,
                    "image_path": image_path
                }
            else:
                return {
                    "success": False,
                    "error": "PDF处理器不支持插入图片页面功能"
                }
        except Exception as e:
            logger.error(f"Error inserting image page: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"插入图片页面失败: {str(e)}"
            }
