"""
上传相关工具函数
"""
from typing import Dict, Any
from pathlib import Path
from app.core.llm.tools.base_tool import BaseTool
from app.managers.upload_plugin_manager import UploadPluginManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UploadFileTool(BaseTool):
    """文件上传工具"""

    def __init__(self):
        super().__init__()
        self._upload_manager = None

    def _get_upload_manager(self) -> UploadPluginManager:
        """获取上传管理器"""
        if self._upload_manager is None:
            self._upload_manager = UploadPluginManager()
        return self._upload_manager

    @property
    def name(self) -> str:
        return "upload_file"

    @property
    def description(self) -> str:
        return "上传文件到远程服务器"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "本地文件路径"
                },
                "remote_path": {
                    "type": "string",
                    "description": "远程路径"
                },
                "plugin": {
                    "type": "string",
                    "description": "上传插件名称,如'upload_http','upload_ftp'等"
                }
            },
            "required": ["file_path", "plugin"]
        }

    def check_parameters_complete(self, params: Dict[str, Any]) -> tuple:
        """检查参数是否完整"""
        schema = self.get_parameters_schema()
        required = schema.get("required", [])
        missing = []
        for param_name in required:
            if param_name not in params or not params[param_name]:
                missing.append(param_name)
        return len(missing) == 0, missing

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行文件上传"""
        is_complete, missing = self.check_parameters_complete(parameters)
        if not is_complete:
            return {
                "success": False,
                "error": f"缺少必要参数: {', '.join(missing)}"
            }

        try:
            file_path = parameters['file_path']
            remote_path = parameters.get('remote_path', '')
            plugin_name = parameters['plugin']

            # 验证文件存在
            if not Path(file_path).exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            upload_manager = self._get_upload_manager()

            # 执行上传
            result = upload_manager.upload_file(
                plugin_name=plugin_name,
                file_path=file_path,
                remote_path=remote_path
            )

            if result.get('success', False):
                return {
                    "success": True,
                    "remote_path": result.get('remote_path', ''),
                    "plugin": plugin_name,
                    "message": result.get('message', 'Upload successful')
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', 'Upload failed')
                }

        except Exception as e:
            logger.error(f"Error in file upload: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
