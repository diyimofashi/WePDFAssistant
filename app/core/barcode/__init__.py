"""
条码系统模块
包含条码检测、插件管理和配置功能
"""

from .barcode_plugin_interface import BarcodePluginInterface, BarcodeResult, BarcodeErrorCode
from .barcode_plugin_security import security_manager

# 避免循环导入，不直接导入集成模块
# from .barcode_integration import BarcodeIntegration, barcode_integration

__all__ = [
    'BarcodePluginInterface',
    'BarcodeResult', 
    'BarcodeErrorCode',
    'security_manager'
]