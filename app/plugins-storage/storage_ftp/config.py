"""
FTP云存储插件 - 配置定义
定义FTP存储插件的配置选项
"""

# 全局配置选项
global_options = {
    "timeout": {
        "type": "integer",
        "default": 30,
        "description": "操作超时时间（秒）"
    },
    "encoding": {
        "type": "string",
        "default": "utf-8",
        "description": "文件编码格式"
    }
}

# 局部配置选项
local_options = {
    "title": "FTP 存储服务器",
    "host": {
        "type": "string",
        "default": "",
        "description": "FTP服务器地址",
        "required": True
    },
    "port": {
        "type": "integer",
        "default": 21,
        "description": "FTP服务器端口（默认21）",
        "required": False
    },
    "username": {
        "type": "string",
        "default": "",
        "description": "FTP用户名",
        "required": True
    },
    "password": {
        "type": "password",
        "default": "",
        "description": "FTP密码",
        "required": False
    },
    "path_prefix": {
        "type": "string",
        "default": "",
        "description": "文件操作的路径前缀"
    },
    "passive_mode": {
        "type": "boolean",
        "default": True,
        "description": "使用被动模式（PASV）"
    },
    "enable_download": {
        "type": "boolean",
        "default": True,
        "description": "是否启用下载功能"
    },
    "enable_upload": {
        "type": "boolean",
        "default": False,
        "description": "是否启用上传功能（允许上传当前打开的文档到服务器）"
    },
    "enable_delete": {
        "type": "boolean",
        "default": False,
        "description": "是否启用删除功能（允许从服务器删除文件）"
    }
}

PluginInfo = {
    "global_options": global_options,
    "local_options": local_options
}
