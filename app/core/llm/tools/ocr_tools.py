"""
OCR相关工具函数
"""
from typing import Dict, Any
from app.core.llm.tools.base_tool import BaseTool
from app.core.ocr.ocr_integration import OCRIntegration
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OCRPDFFTool(BaseTool):
    """OCR识别PDF工具"""

    def __init__(self):
        super().__init__()
        self._ocr_integration = None

    def _get_ocr_integration(self) -> OCRIntegration:
        """获取OCR集成实例"""
        if self._ocr_integration is None:
            self._ocr_integration = OCRIntegration()
            self._ocr_integration.initialize_system()
        return self._ocr_integration

    def get_name(self) -> str:
        return "ocr_pdf"

    def get_description(self) -> str:
        return "使用OCR技术识别PDF中的文本内容"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pdf_path": {
                    "type": "string",
                    "description": "PDF文件路径"
                },
                "language": {
                    "type": "string",
                    "description": "识别语言,如'chinese','english','auto'等,默认为'auto'"
                },
                "page_range": {
                    "type": "string",
                    "description": "页码范围,如'1-3'或'all',默认为'all'"
                }
            },
            "required": ["pdf_path"]
        }

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行OCR识别"""
        if not self.validate_parameters(parameters):
            return {
                "success": False,
                "error": "Invalid parameters"
            }

        try:
            pdf_path = parameters['pdf_path']
            language = parameters.get('language', 'auto')
            page_range = parameters.get('page_range', 'all')

            ocr_integration = self._get_ocr_integration()

            # 获取可用的OCR插件
            available_plugins = ocr_integration.get_available_plugins()
            if not available_plugins:
                return {
                    "success": False,
                    "error": "No OCR plugin available"
                }

            # 使用第一个可用的插件
            plugin_name = available_plugins[0]

            # 执行OCR识别
            result = ocr_integration.recognize_single(
                plugin_name=plugin_name,
                file_path=pdf_path,
                language=language
            )

            if result.success:
                return {
                    "success": True,
                    "text": result.text,
                    "plugin": plugin_name,
                    "language": language
                }
            else:
                return {
                    "success": False,
                    "error": result.error or "OCR recognition failed"
                }

        except Exception as e:
            logger.error(f"Error in OCR PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
