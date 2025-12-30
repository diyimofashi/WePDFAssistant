"""
条码插件模板
这是一个示例插件，展示如何创建条码插件
实现系统已有的条码识别、拆分和设置功能
"""

# 导入API类
from .barcode_api import BarcodePluginTemplate

# 插件信息定义
PluginInfo = {
    "name": "barcode_template",
    "title": "条码插件模板",
    "version": "1.0.0",
    "author": "Aurora PDF",
    "description": "实现系统已有的条码识别、拆分和设置功能的插件模板",
    "api_class": "BarcodePluginTemplate",
    "global_options": {
        "title": "全局配置",
        "description": "全局配置选项"
    },
    "local_options": {
        "title": "条码插件模板",
        "description": "实现系统已有的条码识别、拆分和设置功能的插件模板，支持条码检测、PDF拆分和预览功能"
    }
}