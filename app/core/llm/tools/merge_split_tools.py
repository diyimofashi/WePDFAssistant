"""合并拆分工具 - PDF合并和拆分功能"""
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget
from app.core.llm.tools.base_tool import BaseTool
from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SplitPDFTool(BaseTool):
    """拆分PDF工具"""

    @property
    def name(self) -> str:
        return "split_pdf"

    @property
    def description(self) -> str:
        return "拆分PDF文档,支持按页数、范围、书签等方式拆分"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "split_mode": {
                    "type": "string",
                    "enum": ["pages", "range", "bookmarks"],
                    "description": "拆分模式: pages(按页数), range(按范围), bookmarks(按书签)"
                },
                "pages_per_file": {
                    "type": "integer",
                    "description": "每个文件的页数(按页数拆分时使用)"
                },
                "output_dir": {
                    "type": "string",
                    "description": "输出目录"
                }
            },
            "required": []
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "output_dir":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="",
                mode="open"
            )
            widget._browse_button.setText("选择目录...")
            widget.set_placeholder("选择输出目录...")
            return widget
        return None

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        split_mode = params.get("split_mode", "pages")
        pages_per_file = params.get("pages_per_file", 1)
        output_dir = params.get("output_dir", "")

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

            # 检查是否有拆分PDF的方法
            if hasattr(main_window, 'split_pdf'):
                # 调用拆分PDF功能
                main_window.split_pdf()

                logger.info(f"Split PDF with mode: {split_mode}, pages_per_file: {pages_per_file}, output_dir: {output_dir}")
                return {
                    "success": True,
                    "message": "PDF拆分对话框已打开,请选择拆分参数",
                    "split_mode": split_mode,
                    "pages_per_file": pages_per_file,
                    "output_dir": output_dir
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持拆分PDF功能"
                }
        except Exception as e:
            logger.error(f"Error splitting PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"拆分PDF失败: {str(e)}"
            }


class MergePDFTool(BaseTool):
    """合并PDF工具"""

    @property
    def name(self) -> str:
        return "merge_pdf"

    @property
    def description(self) -> str:
        return "合并多个PDF文档为一个文档"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要合并的PDF文件路径列表"
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径"
                }
            },
            "required": ["input_files", "output_path"]
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
        input_files = params.get("input_files", [])
        output_path = params.get("output_path", "")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            # 检查是否有合并PDF的方法
            if hasattr(main_window, 'merge_manager') and hasattr(main_window.merge_manager, 'merge_pdfs'):
                # 执行合并
                main_window.merge_manager.merge_pdfs(input_files, output_path)

                logger.info(f"Merged PDFs: {len(input_files)} files to {output_path}")
                return {
                    "success": True,
                    "message": f"PDF合并已完成: {len(input_files)} 个文件合并为 {output_path}",
                    "output_path": output_path,
                    "file_count": len(input_files)
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持合并PDF功能"
                }
        except Exception as e:
            logger.error(f"Error merging PDFs: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"合并PDF失败: {str(e)}"
            }
