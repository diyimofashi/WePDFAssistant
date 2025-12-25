"""
HTTP下载插件 - 配置定义
定义HTTP下载插件的配置选项
"""

# 全局配置选项
global_options = {
    "timeout": {
        "type": "int",
        "title": "超时时间（秒）",
        "default": 30,
        "description": "HTTP请求超时时间（秒）"
    },
    "max_retries": {
        "type": "int", 
        "title": "最大重试次数",
        "default": 3,
        "description": "最大重试次数"
    }
}

# 局部配置选项
local_options = {
    "base_url": {
        "type": "str",
        "title": "服务器基础URL",
        "default": "",
        "description": "服务器基础URL",
        "required": True
    },
    "auth_type": {
        "type": "str",
        "title": "认证类型",
        "default": "none",
        "description": "认证类型 (none, basic, token, api_key)",
        "options": ["none", "basic", "token", "api_key"]
    },
    "username": {
        "type": "str",
        "title": "用户名",
        "default": "",
        "description": "用户名（基本认证）"
    },
    "password": {
        "type": "str", 
        "title": "密码",
        "default": "",
        "description": "密码（基本认证）",
        "password": True
    },
    "token": {
        "type": "str",
        "title": "认证Token",
        "default": "",
        "description": "认证Token（Token认证）",
        "password": True
    },
    "api_key": {
        "type": "str",
        "title": "API密钥",
        "default": "",
        "description": "API密钥（API Key认证）",
        "password": True
    },
    "api_key_header": {
        "type": "str",
        "title": "API密钥头部",
        "default": "X-API-Key",
        "description": "API密钥头部名称"
    },
    "custom_headers": {
        "type": "str",
        "title": "自定义请求头部",
        "default": "",
        "description": "自定义请求头部 (JSON格式或key:value格式)"
    }
}