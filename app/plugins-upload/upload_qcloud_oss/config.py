"""
腾讯云OSS上传插件 - 配置定义
定义腾讯云OSS上传插件的配置选项
"""

# 全局配置选项
global_options = {
    "timeout": {
        "type": "int",
        "default": 300,
        "description": "上传超时时间（秒）"
    },
    "max_retries": {
        "type": "int",
        "default": 3,
        "description": "最大重试次数"
    },
    "chunk_size": {
        "type": "int",
        "default": 1024 * 1024,  # 1MB
        "description": "分块上传大小（字节）"
    }
}

# 局部配置选项
local_options = {
    "region": {
        "title": "地域",
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
        "title": "存储桶名称",
        "type": "str",
        "default": "",
        "description": "COS存储桶名称（Bucket Name）",
        "required": True
    },
    "secret_id": {
        "title": "Secret ID",
        "type": "str",
        "default": "",
        "description": "腾讯云API密钥的Secret ID",
        "required": True,
        "password": True
    },
    "secret_key": {
        "title": "Secret Key",
        "type": "str",
        "default": "",
        "description": "腾讯云API密钥的Secret Key",
        "required": True,
        "password": True
    },
    "app_id": {
        "title": "APP ID",
        "type": "str",
        "default": "",
        "description": "腾讯云账户的APP ID（可选，旧版API使用）",
        "required": False
    },
    "path_prefix": {
        "title": "路径前缀",
        "type": "str",
        "default": "",
        "description": "文件上传的路径前缀，如 'uploads/'"
    },
    "acl": {
        "title": "访问权限",
        "type": "enum",
        "optionsList": [
            ["private", "私有（private）"],
            ["public-read", "公共读（public-read）"],
            ["public-read-write", "公共读写（public-read-write）"]
        ],
        "default": "private",
        "description": "文件的访问控制列表"
    }
}
