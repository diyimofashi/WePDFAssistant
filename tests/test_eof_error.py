#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试EOF marker错误处理
"""
import os
import tempfile
import PyPDF2
from PyPDF2.errors import PdfReadError

def create_incomplete_pdf():
    """创建一个不完整的PDF文件用于测试"""
    # 创建一个不完整的PDF内容
    incomplete_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 10\n>>\nstream\nBT\n/Font\nET\nendstream\nendobj\n'
    
    # 注意：这个PDF缺少EOF marker，所以是不完整的
    
    temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    try:
        os.write(temp_fd, incomplete_pdf_content)
        os.close(temp_fd)
        return temp_path
    except:
        os.close(temp_fd)
        os.remove(temp_path)
        raise

def test_eof_error():
    """测试EOF错误处理"""
    print("创建不完整的PDF文件...")
    pdf_path = create_incomplete_pdf()
    
    print(f"测试文件路径: {pdf_path}")
    
    try:
        print("尝试用PyPDF2打开不完整的PDF...")
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"PDF页数: {len(pdf_reader.pages)}")
    except PdfReadError as e:
        print(f"捕获到PdfReadError: {str(e)}")
        error_msg = str(e)
        if "EOF" in error_msg or "marker" in error_msg:
            print("检测到EOF marker错误: PDF文件不完整或已损坏")
        else:
            print(f"PDF文件格式错误: {error_msg}")
    except Exception as e:
        print(f"捕获到其他异常: {str(e)}")
        error_msg = str(e)
        if "EOF" in error_msg or "marker" in error_msg:
            print("检测到EOF marker错误: PDF文件不完整或已损坏")
        else:
            print(f"读取PDF失败: {error_msg}")
    finally:
        # 清理临时文件
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"已删除临时文件: {pdf_path}")

if __name__ == "__main__":
    test_eof_error()