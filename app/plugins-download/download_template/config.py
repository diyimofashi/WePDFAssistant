"""
下载插件模板 - 配置定义
定义下载插件的配置选项
"""

# 全局配置选项
global_options = {
    "timeout": {
        "type": "int",
        "default": 30,
        "title": "超时时间（秒）",
        "description": "请求超时时间（秒）"
    },
    "max_retries": {
        "type": "int", 
        "default": 3,
        "title": "最大重试次数",
        "description": "最大重试次数"
    }
}

# 局部配置选项
local_options = {
    "server_url": {
        "type": "str",
        "default": "",
        "title": "服务器URL",
        "description": "服务器URL",
        "required": True
    },
    "auth_method": {
        "type": "str",
        "default": "none",
        "title": "认证方法",
        "description": "认证方法 (none, basic, token, api_key)",
        "options": ["none", "basic", "token", "api_key"]
    },
    "username": {
        "type": "str",
        "default": "",
        "title": "用户名",
        "description": "用户名（基本认证）"
    },
    "password": {
        "type": "str", 
        "default": "",
        "title": "密码",
        "description": "密码（基本认证）",
        "password": True
    },
    "token": {
        "type": "str",
        "default": "",
        "title": "认证Token",
        "description": "认证Token（Token认证）",
        "password": True
    },
    "api_key": {
        "type": "str",
        "default": "",
        "title": "API密钥",
        "description": "API密钥（API Key认证）",
        "password": True
    }
}