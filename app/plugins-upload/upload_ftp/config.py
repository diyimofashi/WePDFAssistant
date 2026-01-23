"""
FTP上传插件 - 配置定义
定义FTP上传插件的配置选项
"""

# 全局配置选项
global_options = {
    "timeout": {
        "type": "integer",
        "default": 30,
        "description": "FTP连接超时时间（秒）"
    },
    "buffer_size": {
        "type": "integer",
        "default": 8192,  # 8KB
        "description": "上传缓冲区大小（字节）"
    }
}

# 局部配置选项
local_options = {
    "host": {
        "type": "string",
        "default": "",
        "description": "FTP服务器地址",
        "required": True
    },
    "port": {
        "type": "integer",
        "default": 21,
        "description": "FTP服务器端口"
    },
    "username": {
        "type": "string",
        "default": "",
        "description": "用户名（留空表示匿名登录）",
        "required": False
    },
    "password": {
        "type": "password",
        "default": "",
        "description": "密码（留空表示匿名登录）",
        "required": False
    },
    "use_tls": {
        "type": "boolean",
        "default": False,
        "description": "是否使用TLS加密连接"
    },
    "remote_directory": {
        "type": "string",
        "default": "/uploads",
        "description": "远程上传目录"
    },
    "passive_mode": {
        "type": "boolean",
        "default": True,
        "description": "是否使用被动模式"
    }
}