"""加密工具 - PDF加密功能"""
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget
from app.core.llm.tools.base_tool import BaseTool
from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EncryptPDFTool(BaseTool):
    """加密PDF工具"""

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
        from PyQt5.QtWidgets import QLineEdit

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

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        password = params.get("password", "")
        output_path = params.get("output_path", "")

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

            # 检查是否有加密PDF的方法
            if hasattr(main_window.pdf_processor, 'encrypt_pdf'):
                # 执行加密
                if output_path:
                    result = main_window.pdf_processor.encrypt_pdf(password, output_path)
                else:
                    result = main_window.pdf_processor.encrypt_pdf(password)

                if result:
                    logger.info(f"Encrypted PDF with output path: {output_path}")
                    return {
                        "success": True,
                        "message": "PDF加密已完成",
                        "output_path": output_path
                    }
                else:
                    return {
                        "success": False,
                        "error": "PDF加密失败"
                    }
            else:
                return {
                    "success": False,
                    "error": "PDF处理器不支持加密功能"
                }
        except Exception as e:
            logger.error(f"Error encrypting PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"加密PDF失败: {str(e)}"
            }
