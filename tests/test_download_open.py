#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整测试从下载到打开PDF的流程
"""
import os
import tempfile
import requests
import PyPDF2
from PyPDF2.errors import PdfReadError
from urllib.parse import urlparse
import time

def download_pdf(url, timeout=30):
    """下载PDF文件"""
    print(f"开始下载: {url}")
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # 检查HTTP错误
        
        # 确保tests目录存在
        tests_dir = os.path.join(os.getcwd(), 'tests')
        os.makedirs(tests_dir, exist_ok=True)
        
        # 生成文件名
        filename = f"downloaded_test_{int(time.time())}.pdf"
        file_path = os.path.join(tests_dir, filename)
        
        # 保存文件到tests目录
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"文件已下载到: {file_path}")
        return file_path
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {e}")
        return None
    except Exception as e:
        print(f"下载过程中出现错误: {e}")
        return None

def test_pdf_with_pypdf2(file_path):
    """使用PyPDF2测试PDF文件"""
    print(f"使用PyPDF2测试PDF文件: {file_path}")
    
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            page_count = len(pdf_reader.pages)
            print(f"PDF打开成功，共 {page_count} 页")
            return True, f"成功打开，共 {page_count} 页"
    except PdfReadError as e:
        error_msg = str(e)
        print(f"PyPDF2 PdfReadError: {error_msg}")
        if "EOF" in error_msg or "marker" in error_msg:
            print("检测到EOF marker错误: PDF文件不完整或已损坏")
            return False, f"PDF文件不完整或已损坏: {error_msg}"
        else:
            print(f"PDF文件格式错误: {error_msg}")
            return False, f"PDF文件格式错误: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        print(f"PyPDF2 其他错误: {error_msg}")
        if "EOF" in error_msg or "marker" in error_msg:
            print("检测到EOF marker错误: PDF文件不完整或已损坏")
            return False, f"PDF文件不完整或已损坏: {error_msg}"
        else:
            print(f"读取PDF失败: {error_msg}")
            return False, f"读取PDF失败: {error_msg}"

def test_pdf_with_pymupdf(file_path):
    """使用PyMuPDF测试PDF文件"""
    print(f"使用PyMuPDF测试PDF文件: {file_path}")
    
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()
        print(f"PyMuPDF测试成功，共 {page_count} 页")
        return True, f"PyMuPDF成功打开，共 {page_count} 页"
    except Exception as e:
        error_msg = str(e)
        print(f"PyMuPDF错误: {error_msg}")
        return False, f"PyMuPDF打开失败: {error_msg}"

def complete_test(url):
    """完整测试流程：下载 -> 验证"""
    print("="*60)
    print("开始完整测试：下载 -> 验证PDF文件")
    print(f"测试URL: {url}")
    print("="*60)
    
    # 1. 下载文件
    downloaded_file = download_pdf(url)
    if not downloaded_file:
        print("下载失败，终止测试")
        return
    
    try:
        # 2. 使用PyPDF2测试
        print("\n--- 测试PyPDF2兼容性 ---")
        success1, msg1 = test_pdf_with_pypdf2(downloaded_file)
        
        # 3. 使用PyMuPDF测试
        print("\n--- 测试PyMuPDF兼容性 ---")
        success2, msg2 = test_pdf_with_pymupdf(downloaded_file)
        
        # 4. 显示结果
        print("\n" + "="*60)
        print("测试结果总结:")
        print(f"PyPDF2测试: {'✓ 成功' if success1 else '✗ 失败'} - {msg1}")
        print(f"PyMuPDF测试: {'✓ 成功' if success2 else '✗ 失败'} - {msg2}")
        print("="*60)
        
        if not success1:
            print("\n建议:")
            print("1. 如果是EOF marker错误，说明下载的PDF文件不完整")
            print("2. 可能是服务器返回的PDF内容不完整")
            print("3. 网络传输过程中可能有数据丢失")
        
    finally:
        # 5. 清理临时文件 - 不删除保存在tests目录中的文件
        print(f"\n文件已保存到: {downloaded_file}")

if __name__ == "__main__":
    # 使用您提供的链接
    test_url = "http://localhost:30010/fnp/file/download/2002/162"
    complete_test(test_url)