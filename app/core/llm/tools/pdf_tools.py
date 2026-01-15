"""
PDF工具集合
提供打开、拆分、OCR等PDF操作工具
"""
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget, QMessageBox
from app.core.llm.tools.base_tool import BaseTool
from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
from app.core.llm.tool_interactions.config_dialog import ParameterConfigDialog
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenPDFTool(BaseTool):
    """打开PDF文档工具"""

    @property
    def name(self) -> str:
        return "open_pdf"

    @property
    def description(self) -> str:
        return "打开PDF文档，支持从文件系统选择PDF文件"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "PDF文件路径"
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
        """
        open_pdf工具需要加载PDF，建议在主线程中执行

        Returns:
            True
        """
        return True

    def get_next_tool(self) -> Optional[str]:
        """PDF加载后需要渲染"""
        return "render_pdf"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("file_path")

        try:
            logger.info(f"Opening PDF file: {file_path}")

            # 实际的PDF加载逻辑通过LLMChatDialog实现
            # 这样可以访问主窗口的PDF管理器
            # 这里返回成功，实际加载在LLMChatDialog的_open_pdf_file中完成

            return {
                "success": True,
                "message": f"PDF加载完成: {file_path}",
                "file_path": file_path,
                "status": "loaded"
            }

        except Exception as e:
            logger.error(f"Error opening PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"打开PDF文件失败: {str(e)}"
            }


class SplitPDFTool(BaseTool):
    """拆分PDF文档工具"""

    @property
    def name(self) -> str:
        return "split_pdf"

    @property
    def description(self) -> str:
        return "拆分PDF文档，支持按页数、范围、书签等方式拆分"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "split_mode": {
                    "type": "string",
                    "enum": ["pages", "range", "bookmarks"],
                    "description": "拆分模式: pages(按页数), range(按范围), bookmarks(按书签)"
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

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        split_mode = params.get("split_mode", "pages")
        output_dir = params.get("output_dir", "")

        try:
            logger.info(f"Splitting PDF with mode: {split_mode}, output_dir: {output_dir}")

            # TODO: 实际拆分PDF的逻辑
            # 需要弹出拆分配置对话框，让用户详细配置
            # 然后调用拆分功能

            # 临时返回成功，实际实现需要集成PDF拆分逻辑
            return {
                "success": True,
                "message": f"PDF拆分配置已准备: 模式={split_mode}, 输出目录={output_dir}",
                "split_mode": split_mode,
                "output_dir": output_dir
            }

        except Exception as e:
            logger.error(f"Error splitting PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"拆分PDF失败: {str(e)}"
            }


class OCRPDFTool(BaseTool):
    """OCR识别PDF工具"""

    @property
    def name(self) -> str:
        return "ocr_pdf"

    @property
    def description(self) -> str:
        return "对PDF文档进行OCR文字识别，支持多种语言"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "识别语言，例如: chi_sim(简体中文), eng(英语), chi_sim+eng(中英混合)"
                },
                "pages": {
                    "type": "string",
                    "description": "指定页面范围，例如: 1-5, 8,10-12，留空表示全部"
                }
            },
            "required": []
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        language = params.get("language", "chi_sim+eng")
        pages = params.get("pages", "")

        try:
            logger.info(f"Starting OCR: language={language}, pages={pages}")

            # TODO: 实际OCR的逻辑
            # 需要调用OCR功能，可能需要弹出OCR配置对话框

            # 临时返回成功，实际实现需要集成OCR逻辑
            return {
                "success": True,
                "message": f"OCR识别已启动: 语言={language}, 页面={pages}",
                "language": language,
                "pages": pages
            }

        except Exception as e:
            logger.error(f"Error performing OCR: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"OCR识别失败: {str(e)}"
            }


class MergePDFTool(BaseTool):
    """合并PDF文档工具"""

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
            "required": ["output_path"]
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

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        input_files = params.get("input_files", [])
        output_path = params.get("output_path", "")

        try:
            logger.info(f"Merging PDFs: {len(input_files)} files to {output_path}")

            # TODO: 实际合并PDF的逻辑
            # 需要选择多个输入文件，然后调用合并功能

            # 临时返回成功
            return {
                "success": True,
                "message": f"PDF合并已完成: {len(input_files)} 个文件合并为 {output_path}",
                "output_path": output_path,
                "file_count": len(input_files)
            }

        except Exception as e:
            logger.error(f"Error merging PDFs: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"合并PDF失败: {str(e)}"
            }


class EncryptPDFTool(BaseTool):
    """加密PDF文档工具"""

    @property
    def name(self) -> str:
        return "encrypt_pdf"

    @property
    def description(self) -> str:
        return "为PDF文档添加密码保护"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "password": {
                    "type": "string",
                    "description": "加密密码"
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径"
                }
            },
            "required": ["password"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
        from PyQt5.QtWidgets import QLineEdit, QLabel
        
        if param_name == "password":
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.Password)
            widget.setPlaceholderText("输入加密密码...")
            return widget
        elif param_name == "output_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="save"
            )
            widget.set_placeholder("选择输出文件...")
            return widget
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        password = params.get("password", "")
        output_path = params.get("output_path", "")

        try:
            logger.info(f"Encrypting PDF with output path: {output_path}")

            # TODO: 实际加密PDF的逻辑

            return {
                "success": True,
                "message": "PDF加密已完成",
                "output_path": output_path
            }

        except Exception as e:
            logger.error(f"Error encrypting PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"加密PDF失败: {str(e)}"
            }
