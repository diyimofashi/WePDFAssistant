# -*- coding: utf-8 -*-
"""
阿里云OSS下载插件 - 配置定义
定义阿里云OSS下载插件的配置选项
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
    "title": "阿里云 OSS 下载",
    "region": {
        "type": "enum",
        "optionsList": [
            ["oss-cn-hangzhou", "杭州"],
            ["oss-cn-shanghai", "上海"],
            ["oss-cn-beijing", "北京"],
            ["oss-cn-shenzhen", "深圳"],
            ["oss-cn-qingdao", "青岛"],
            ["oss-cn-zhangjiakou", "张家口"],
            ["oss-cn-huhehaote", "呼和浩特"],
            ["oss-cn-wulanchabu", "乌兰察布"],
            ["oss-cn-chengdu", "成都"],
            ["oss-rg-chengdu", "成都（内网）"],
            ["oss-cn-heyuan", "河源"],
            ["oss-cn-guangzhou", "广州"],
            ["oss-cn-nanjing", "南京"],
            ["oss-cn-wuhan", "武汉"],
            ["oss-cn-fuzhou", "福州"],
            ["oss-ap-northeast-1", "东京"],
            ["oss-ap-southeast-1", "新加坡"],
            ["oss-ap-southeast-2", "悉尼"],
            ["oss-ap-southeast-3", "吉隆坡"],
            ["oss-ap-southeast-5", "雅加达"],
            ["oss-ap-south-1", "孟买"],
            ["oss-me-east-1", "迪拜"],
            ["oss-eu-central-1", "法兰克福"],
            ["oss-eu-west-1", "伦敦"],
            ["oss-us-east-1", "弗吉尼亚"],
            ["oss-us-west-1", "硅谷"]
        ],
        "default": "oss-cn-hangzhou",
        "description": "选择存储桶所在地域"
    },
    "endpoint": {
        "type": "string",
        "default": "",
        "description": "OSS访问域名（留空则自动根据region生成，格式如: oss-cn-shanghai.aliyuncs.com）",
        "required": False
    },
    "bucket_name": {
        "type": "string",
        "default": "",
        "description": "OSS存储桶名称（Bucket Name，如: my-bucket-name）",
        "required": True
    },
    "access_key_id": {
        "type": "password",
        "default": "",
        "description": "阿里云AccessKey ID（建议使用RAM子账号，授予OSS只读权限）",
        "required": True
    },
    "access_key_secret": {
        "type": "password",
        "default": "",
        "description": "阿里云AccessKey Secret（与AccessKey ID配对使用）",
        "required": True
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
