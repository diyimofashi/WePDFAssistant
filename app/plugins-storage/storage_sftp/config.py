"""
SFTP云存储插件 - 配置定义
定义SFTP存储插件的配置选项
"""

# 全局配置选项
global_options = {
    "timeout": {
        "type": "integer",
        "default": 300,
        "description": "操作超时时间（秒）"
    },
    "encoding": {
        "type": "string",
        "default": "utf-8",
        "description": "文件编码格式"
    },
    "host_key_fingerprint": {
        "type": "string",
        "default": "",
        "description": "服务器主机密钥指纹（用于验证服务器身份，可选）"
    }
}

# 局部配置选项
local_options = {
    "title": "SFTP 存储服务器",
    "host": {
        "type": "string",
        "default": "",
        "description": "SFTP服务器地址",
        "required": True
    },
    "port": {
        "type": "integer",
        "default": 22,
        "description": "SFTP服务器端口（默认22）",
        "required": False
    },
    "username": {
        "type": "string",
        "default": "",
        "description": "SFTP用户名",
        "required": True
    },
    "password": {
        "type": "password",
        "default": "",
        "description": "SFTP密码（与私钥二选一）",
        "required": False
    },
    "private_key_file": {
        "type": "file",
        "default": "",
        "description": "私钥文件路径（.pem或.key，与密码二选一）",
        "required": False
    },
    "path_prefix": {
        "type": "string",
        "default": "/",
        "description": "文件操作的路径前缀"
    },
    "enable_download": {
        "type": "boolean",
        "default": True,
        "description": "是否启用下载功能"
    },
    "enable_upload": {
        "type": "boolean",
        "default": True,
        "description": "是否启用上传功能"
    },
    "enable_delete": {
        "type": "boolean",
        "default": True,
        "description": "是否启用删除功能"
    }
}

PluginInfo = {
    "global_options": global_options,
    "local_options": local_options
}
