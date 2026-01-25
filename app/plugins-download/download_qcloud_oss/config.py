"""
腾讯云OSS下载插件 - 配置定义
定义腾讯云OSS下载插件的配置选项
"""

# 全局配置选项
global_options = {
    "timeout": {
        "type": "integer",
        "default": 300,
        "description": "下载超时时间（秒）"
    },
    "max_retries": {
        "type": "integer",
        "default": 3,
        "description": "最大重试次数"
    }
}

# 局部配置选项
local_options = {
    "title": "腾讯云 COS 下载",
    "region": {
        "type": "enum",
        "optionsList": [
            ["ap-beijing", "北京（华北）"],
            ["ap-chengdu", "成都（西南）"],
            ["ap-guangzhou", "广州（华南）"],
            ["ap-shanghai", "上海（华东）"],
            ["ap-nanjing", "南京（华东）"],
            ["ap-hongkong", "香港"],
            ["ap-singapore", "新加坡"],
            ["ap-tokyo", "东京"],
            ["ap-bangkok", "曼谷"],
            ["ap-mumbai", "孟买"],
            ["ap-seoul", "首尔"],
            ["ap-frankfurt", "法兰克福"],
            ["ap-siliconvalley", "硅谷"],
            ["ap-toronto", "多伦多"]
        ],
        "default": "ap-guangzhou",
        "description": "选择存储桶所在地域"
    },
    "bucket_name": {
        "type": "string",
        "default": "",
        "description": "COS存储桶名称（Bucket Name）",
        "required": True
    },
    "secret_id": {
        "type": "password",
        "default": "",
        "description": "腾讯云API密钥的Secret ID",
        "required": True
    },
    "secret_key": {
        "type": "password",
        "default": "",
        "description": "腾讯云API密钥的Secret Key",
        "required": True
    },
    "app_id": {
        "type": "string",
        "default": "",
        "description": "腾讯云账户的APP ID（可选，旧版API使用）",
        "required": False
    },
    "path_prefix": {
        "type": "string",
        "default": "",
        "description": "文件下载的路径前缀"
    }
}

PluginInfo = {
    "global_options": global_options,
    "local_options": local_options
}
