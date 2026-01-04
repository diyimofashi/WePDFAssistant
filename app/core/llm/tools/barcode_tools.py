"""
条码相关工具函数
"""
from typing import Dict, Any
from app.core.llm.tools.base_tool import BaseTool
from app.core.barcode.barcode_integration import BarcodeIntegration
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BarcodeSplitTool(BaseTool):
    """条码分割PDF工具"""

    def __init__(self):
        super().__init__()
        self._barcode_integration = None

    def _get_barcode_integration(self) -> BarcodeIntegration:
        """获取条码集成实例"""
        if self._barcode_integration is None:
            from app.core.barcode.barcode_integration import BarcodeIntegration
            self._barcode_integration = BarcodeIntegration()
        return self._barcode_integration

    def get_name(self) -> str:
        return "barcode_split"

    def get_description(self) -> str:
        return "根据条码位置分割PDF文档"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pdf_path": {
                    "type": "string",
                    "description": "PDF文件路径"
                },
                "barcode_type": {
                    "type": "string",
                    "description": "条码类型,如'QRCode','CODE128'等,默认为'QRCode'"
                },
                "output_dir": {
                    "type": "string",
                    "description": "输出目录,如果为None则使用默认目录"
                }
            },
            "required": ["pdf_path"]
        }

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行条码分割"""
        if not self.validate_parameters(parameters):
            return {
                "success": False,
                "error": "Invalid parameters"
            }

        try:
            pdf_path = parameters['pdf_path']
            barcode_type = parameters.get('barcode_type', 'QRCode')
            output_dir = parameters.get('output_dir')

            barcode_integration = self._get_barcode_integration()

            # 执行条码检测和分割
            result = barcode_integration.detect_and_split_by_barcode(
                pdf_path=pdf_path,
                barcode_type=barcode_type,
                output_dir=output_dir
            )

            if result.get('success', False):
                return {
                    "success": True,
                    "split_count": result.get('split_count', 0),
                    "output_files": result.get('output_files', []),
                    "barcode_type": barcode_type
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', 'Barcode split failed')
                }

        except Exception as e:
            logger.error(f"Error in barcode split: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
