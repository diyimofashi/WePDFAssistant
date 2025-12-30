"""
高级条码拆分插件
支持首页规则、尾页规则、分隔页规则
"""

from .api import AdvancedBarcodePlugin

# 插件信息定义
PluginInfo = {
    "name": "advanced_barcode",
    "title": "高级条码拆分插件",
    "version": "1.0.0",
    "author": "Aurora PDF",
    "description": "支持首页规则、尾页规则、分隔页规则的高级条码拆分插件，包含条码类型过滤、区域过滤、正则过滤等高级功能",
    "api_class": "AdvancedBarcodePlugin",
    "global_options": {
        "title": "全局配置",
        "description": "全局配置选项"
    },
    "local_options": {
        "title": "高级条码拆分",
        "description": "支持首页规则、尾页规则、分隔页规则的条码拆分，包含条码类型过滤、区域过滤、正则过滤等高级功能"
    }
}

__all__ = ['AdvancedBarcodePlugin']
