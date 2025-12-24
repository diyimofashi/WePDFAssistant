"""
上传插件模板 - 配置定义
定义插件的配置选项
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
    }
}

# 局部配置选项
local_options = {
    "server_url": {
        "type": "str",
        "default": "",
        "description": "服务器URL",
        "required": True
    },
    "auth_method": {
        "type": "select",
        "optionsList": [
            ["none", "无认证"],
            ["basic", "基本认证"],
            ["token", "Token认证"]
        ],
        "default": "none",
        "description": "认证方式"
    },
    "username": {
        "type": "str",
        "default": "",
        "description": "用户名（如需要）"
    },
    "password": {
        "type": "str", 
        "default": "",
        "description": "密码（如需要）",
        "password": True
    },
    "token": {
        "type": "str",
        "default": "",
        "description": "认证Token（如需要）",
        "password": True
    }
}