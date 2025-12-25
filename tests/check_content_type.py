#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查下载内容的类型
"""
import requests
from urllib.parse import urlparse

def check_content_type(url, timeout=30):
    """检查URL返回的内容类型"""
    print(f"检查URL内容类型: {url}")
    
    try:
        response = requests.head(url, timeout=timeout)  # 使用HEAD请求获取头部信息
        print(f"状态码: {response.status_code}")
        print(f"内容类型: {response.headers.get('content-type', 'Unknown')}")
        print(f"内容长度: {response.headers.get('content-length', 'Unknown')}")
        
        # 检查重定向
        if response.history:
            print("检测到重定向:")
            for hist_resp in response.history:
                print(f"  {hist_resp.status_code} -> {hist_resp.url}")
            print(f"最终URL: {response.url}")
        
        # 获取部分内容检查类型
        response = requests.get(url, timeout=timeout)
        print(f"实际请求状态码: {response.status_code}")
        print(f"实际内容类型: {response.headers.get('content-type', 'Unknown')}")
        
        # 检查前100个字符
        content_preview = response.text[:200]  # 取前200个字符
        print(f"内容预览 (前200字符):")
        print(content_preview)
        
        # 检查是否是HTML内容
        if content_preview.lower().startswith('<!doctype html') or '<html' in content_preview.lower():
            print("\n确认: 返回的是HTML内容 (很可能是登录页面)")
        elif content_preview.lower().startswith('%pdf'):
            print("\n确认: 返回的是PDF内容")
        else:
            print(f"\n内容类型不确定，开头字符: {repr(content_preview[:50])}")
        
        return response.status_code, response.headers.get('content-type'), content_preview
        
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None, None, None

if __name__ == "__main__":
    # 测试您提供的链接
    test_url = "http://localhost:30010/fnp/file/download/2002/162"
    check_content_type(test_url)