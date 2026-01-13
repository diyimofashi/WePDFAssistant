"""文件操作工具 - 打开、保存PDF文档"""
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget
from app.core.llm.tools.base_tool import BaseTool
from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenPDFTool(BaseTool):
    """打开PDF文档工具"""

    @property
    def name(self) -> str:
        return "open_pdf"

    @property
    def description(self) -> str:
        return "打开PDF文档,支持从文件系统选择PDF文件"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "PDF文件路径"
                }
            },
            "required": []
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
        return True

    def get_next_tool(self) -> Optional[str]:
        return "render_pdf"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("file_path")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            if hasattr(main_window, 'open_file'):
                main_window.open_file(file_path)
                logger.info(f"Opened PDF file: {file_path}")
                return {
                    "success": True,
                    "message": f"PDF加载完成: {file_path}",
                    "file_path": file_path,
                    "status": "loaded"
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持打开文件功能"
                }
        except Exception as e:
            logger.error(f"Error opening PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"打开PDF文件失败: {str(e)}"
            }


class SavePDFTool(BaseTool):
    """保存PDF文档工具"""

    @property
    def name(self) -> str:
        return "save_pdf"

    @property
    def description(self) -> str:
        return "保存当前PDF文档到指定路径"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "保存的文件路径"
                }
            },
            "required": []
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "file_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="save"
            )
            widget.set_placeholder("选择保存位置...")
            return widget
        return None

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("file_path")

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

            # 如果指定了文件路径，使用另存为
            if file_path:
                # 暂时保存文件路径，然后调用保存
                original_file = main_window.pdf_processor.current_file
                main_window.pdf_processor.current_file = file_path

                if hasattr(main_window, 'save_file'):
                    main_window.save_file()

                    # 恢复原文件路径
                    main_window.pdf_processor.current_file = original_file

                    logger.info(f"Saved PDF to: {file_path}")
                    return {
                        "success": True,
                        "message": f"PDF已保存: {file_path}",
                        "file_path": file_path
                    }
                else:
                    return {
                        "success": False,
                        "error": "主窗口不支持保存功能"
                    }
            else:
                # 直接保存到当前文件
                if hasattr(main_window, 'save_file'):
                    saved_path = main_window.pdf_processor.current_file
                    main_window.save_file()
                    logger.info(f"Saved PDF to: {saved_path}")
                    return {
                        "success": True,
                        "message": f"PDF已保存: {saved_path}",
                        "file_path": saved_path
                    }
                else:
                    return {
                        "success": False,
                        "error": "主窗口不支持保存功能"
                    }
        except Exception as e:
            logger.error(f"Error saving PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"保存PDF失败: {str(e)}"
            }
