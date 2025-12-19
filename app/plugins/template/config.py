"""
插件配置定义模板
开发者可以根据需要修改配置项
"""

# 全局配置项（适用于所有插件的配置）
global_options = {
    "title": "插件全局设置",
    "type": "group",
    "threads": {
        "title": "线程数",
        "type": "integer",
        "default": 4,
        "min": 1,
        "max": 16,
        "description": "处理并发线程数"
    },
    "timeout": {
        "title": "超时时间",
        "type": "integer",
        "default": 300,
        "min": 10,
        "max": 3600,
        "description": "OCR处理超时时间（秒）"
    }
}

# 局部配置项（每个插件独有的配置）
local_options = {
    "title": "插件局部设置",
    "type": "group",
    "language": {
        "title": "识别语言",
        "type": "enum",
        "optionsList": [
            ["auto", "自动识别"],
            ["zh", "简体中文"],
            ["en", "English"],
            ["ja", "日本語"]
        ],
        "default": "auto",
        "description": "文本识别语言"
    },
    "confidence_threshold": {
        "title": "置信度阈值",
        "type": "float",
        "default": 0.5,
        "min": 0.0,
        "max": 1.0,
        "description": "文本识别置信度阈值，低于此值的结果将被过滤"
    },
    "detect_direction": {
        "title": "文本方向检测",
        "type": "boolean",
        "default": False,
        "description": "是否检测文本方向"
    }
}