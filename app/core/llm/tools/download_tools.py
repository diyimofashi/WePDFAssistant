"""
下载相关工具函数
"""
from typing import Dict, Any
from app.core.llm.tools.base_tool import BaseTool
from app.managers.download_plugin_manager import DownloadPluginManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadFileTool(BaseTool):
    """文件下载工具"""

    def __init__(self):
        super().__init__()
        self._download_manager = None

    def _get_download_manager(self) -> DownloadPluginManager:
        """获取下载管理器"""
        if self._download_manager is None:
            self._download_manager = DownloadPluginManager()
        return self._download_manager

    @property
    def name(self) -> str:
        return "download_file"

    @property
    def description(self) -> str:
        return "从远程服务器下载文件"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "文件URL"
                },
                "local_path": {
                    "type": "string",
                    "description": "本地保存路径"
                },
                "plugin": {
                    "type": "string",
                    "description": "下载插件名称,如'download_http'等"
                }
            },
            "required": ["url", "plugin"]
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
        """执行文件下载"""
        is_complete, missing = self.check_parameters_complete(parameters)
        if not is_complete:
            return {
                "success": False,
                "error": f"缺少必要参数: {', '.join(missing)}"
            }

        try:
            url = parameters['url']
            local_path = parameters.get('local_path', '')
            plugin_name = parameters['plugin']

            download_manager = self._get_download_manager()

            # 执行下载
            result = download_manager.download_file(
                plugin_name=plugin_name,
                remote_url=url,
                local_path=local_path
            )

            if result.get('success', False):
                return {
                    "success": True,
                    "local_path": result.get('local_path', ''),
                    "plugin": plugin_name,
                    "message": result.get('message', 'Download successful')
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', 'Download failed')
                }

        except Exception as e:
            logger.error(f"Error in file download: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
