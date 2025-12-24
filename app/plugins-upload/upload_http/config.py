"""
HTTP上传插件 - 配置定义
定义HTTP上传插件的配置选项
"""

# 全局配置选项
global_options = {
    "timeout": {
        "type": "int",
        "default": 30,
        "description": "上传超时时间（秒）"
    },
    "chunk_size": {
        "type": "int", 
        "default": 1024 * 1024,  # 1MB
        "description": "分块上传大小（字节）"
    },
    "max_retries": {
        "type": "int",
        "default": 3,
        "description": "最大重试次数"
    }
}

# 局部配置选项
local_options = {
    "base_url": {
        "type": "str",
        "default": "",
        "description": "服务器基础URL",
        "required": True
    },
    "auth_type": {
        "type": "select",
        "optionsList": [
            ["none", "无认证"],
            ["basic", "基本认证"],
            ["token", "Token认证"],
            ["api_key", "API Key认证"]
        ],
        "default": "none",
        "description": "认证类型"
    },
    "username": {
        "type": "str",
        "default": "",
        "description": "用户名（基本认证时使用）"
    },
    "password": {
        "type": "str", 
        "default": "",
        "description": "密码（基本认证时使用）",
        "password": True
    },
    "token": {
        "type": "str",
        "default": "",
        "description": "认证Token（Token认证时使用）",
        "password": True
    },
    "api_key": {
        "type": "str",
        "default": "",
        "description": "API Key（API Key认证时使用）",
        "password": True
    },
    "api_key_header": {
        "type": "str",
        "default": "X-API-Key",
        "description": "API Key请求头名称"
    },
    "custom_headers": {
        "type": "dict",
        "default": {},
        "description": "自定义请求头"
    }
}