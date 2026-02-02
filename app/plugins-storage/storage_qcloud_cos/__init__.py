# -*- coding: utf-8 -*-
"""
腾讯云COS云存储插件
"""

from .storage_api import QcloudCosStorage
from . import config

# 插件信息
PluginInfo = {
    "name": "storage_qcloud_cos",
    "title": "腾讯云 COS 存储",
    "version": "2.0.0",
    "author": "PyPDF Team",
    "description": "使用腾讯云对象存储（COS）实现文件上传、下载、删除和列表功能",
    "api_class": "QcloudCosStorage",
    "global_options": config.global_options,
    "local_options": config.local_options,
}

__all__ = ['QcloudCosStorage']
