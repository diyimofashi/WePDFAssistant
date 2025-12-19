from . import api_rapidocr
from . import config

# 插件信息
PluginInfo = {
    # 插件组别
    "group": "ocr",
    # 全局配置
    "global_options": config.global_options,
    # 局部配置
    "local_options": config.local_options,
    # 接口类
    "api_class": api_rapidocr.Api,
}
