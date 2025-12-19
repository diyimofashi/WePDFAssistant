"""
OCR插件模板 - 插件元信息定义
这是开发新OCR插件的起点
"""

from .ocr_api import TemplateOCR
from .config import global_options, local_options

# 插件信息
PluginInfo = {
    # 插件组别
    "group": "ocr",
    
    # 全局配置
    "global_options": global_options,
    
    # 局部配置
    "local_options": local_options,
    
    # 接口类
    "api_class": TemplateOCR,
}