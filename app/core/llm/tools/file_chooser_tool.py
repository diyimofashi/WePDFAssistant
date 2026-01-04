"""
文件选择工具
用于在工具调用参数缺失时，弹出文件选择对话框
"""
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget, QFileDialog
from app.core.llm.tools.base_tool import BaseTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileChooserTool(BaseTool):
    """文件选择工具"""
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        super().__init__()
        self._parent_widget = parent_widget
        self._enabled = True

    @property
    def name(self) -> str:
        return "file_chooser"

    @property
    def description(self) -> str:
        return "弹出文件选择对话框，让用户选择文件路径。当其他工具需要文件路径但参数缺失时使用此工具。"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "purpose": {
                    "type": "string",
                    "description": "选择文件的目的，例如：'选择要打开的PDF文件'、'选择要保存的路径'、'选择加密后保存的文件路径'等"
                },
                "file_filter": {
                    "type": "string",
                    "description": "文件过滤器，例如：'PDF Files (*.pdf)', 'All Files (*)'"
                },
                "save_mode": {
                    "type": "boolean",
                    "description": "是否为保存模式，True 时显示保存对话框，False 时显示打开对话框。默认 False"
                },
                "directory_only": {
                    "type": "boolean",
                    "description": "是否仅选择目录，True 时只显示目录选择对话框。默认 False"
                }
            },
            "required": ["purpose"]
        }

    def get_parameters_schema(self) -> Dict[str, Any]:
        """获取参数模式（兼容旧版本）"""
        return self.get_parameters()

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行文件选择"""
        try:
            purpose = parameters.get("purpose", "选择文件")
            file_filter = parameters.get("file_filter", "All Files (*)")
            save_mode = parameters.get("save_mode", False)
            directory_only = parameters.get("directory_only", False)

            logger.info(f"Opening file dialog for purpose: {purpose}, filter: {file_filter}, save_mode: {save_mode}, directory_only: {directory_only}")

            file_path = ""

            if directory_only:
                # 仅选择目录
                file_path = QFileDialog.getExistingDirectory(
                    self._parent_widget,
                    purpose,
                    ""
                )
                logger.info(f"Directory selected: {file_path}")
            elif save_mode:
                # 保存模式，显示保存对话框
                file_path, _ = QFileDialog.getSaveFileName(
                    self._parent_widget,
                    purpose,
                    "",
                    file_filter
                )
                logger.info(f"Save path selected: {file_path}")
            else:
                # 打开模式，显示打开对话框
                file_path, _ = QFileDialog.getOpenFileName(
                    self._parent_widget,
                    purpose,
                    "",
                    file_filter
                )
                logger.info(f"File selected: {file_path}")

            if file_path:
                return {
                    "success": True,
                    "file_path": file_path,
                    "message": f"成功选择{'目录' if directory_only else ('保存路径' if save_mode else '文件')}: {file_path}",
                    "save_mode": save_mode
                }
            else:
                logger.info("File selection cancelled by user")
                return {
                    "success": False,
                    "file_path": None,
                    "message": "用户取消了选择",
                    "save_mode": save_mode
                }

        except Exception as e:
            logger.error(f"Error in file selection: {e}", exc_info=True)
            return {
                "success": False,
                "file_path": None,
                "error": str(e)
            }

    def set_parent_widget(self, parent_widget: QWidget) -> None:
        """设置父窗口"""
        self._parent_widget = parent_widget

    def get_next_tool(self) -> Optional[str]:
        """
        获取后续工具名称

        Returns:
            后续工具名称，对于文件选择工具，通常会打开PDF
        """
        # 根据目的决定后续工具
        # 这里可以根据选择的文件类型来决定后续工具
        # 暂时默认返回 open_pdf
        return "open_pdf"

    def requires_main_thread(self) -> bool:
        """
        文件选择工具需要GUI交互，必须在主线程中执行

        Returns:
            True
        """
        return True