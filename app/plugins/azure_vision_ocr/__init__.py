"""
Azure Vision OCR插件 - 插件元信息定义
"""

from .azure_vision_ocr_api import AzureVisionOCR
from .azure_vision_ocr_config import global_options, local_options

# 插件信息
PluginInfo = {
    # 插件组别
    "group": "ocr",
    
    # 全局配置
    "global_options": global_options,
    
    # 局部配置
    "local_options": local_options,
    
    # 接口类
    "api_class": AzureVisionOCR,
}