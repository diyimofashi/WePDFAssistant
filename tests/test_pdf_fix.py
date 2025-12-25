#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试PDF修复功能
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.utils.pdf_fixer import try_fix_pdf_file
import PyPDF2
from PyPDF2.errors import PdfReadError

def test_pdf_fix():
    # 测试目录中的PDF文件
    test_dir = os.path.join(os.getcwd(), 'tests')
    if not os.path.exists(test_dir):
        print("tests目录不存在")
        return
    
    for file in os.listdir(test_dir):
        if file.endswith('.pdf') and not file.endswith('_fixed.pdf'):
            file_path = os.path.join(test_dir, file)
            print(f"\n正在测试文件: {file_path}")
            
            # 首先尝试直接打开原始文件
            print("尝试直接打开原始文件...")
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    print(f"原始文件可以直接打开，共 {len(pdf_reader.pages)} 页")
            except PdfReadError as e:
                print(f"原始文件无法直接打开: {e}")
                
                # 尝试修复文件
                print("尝试修复文件...")
                fixed_file_path = try_fix_pdf_file(file_path)
                if fixed_file_path:
                    print(f"文件修复成功: {fixed_file_path}")
                    
                    # 尝试打开修复后的文件
                    try:
                        with open(fixed_file_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            print(f"修复后的文件可以打开，共 {len(pdf_reader.pages)} 页")
                            
                            # 尝试访问第一页验证完整性
                            if len(pdf_reader.pages) > 0:
                                first_page = pdf_reader.pages[0]
                                print("第一页可以正常访问")
                        # 清理临时文件
                        os.remove(fixed_file_path)
                        print("临时修复文件已清理")
                    except PdfReadError as e2:
                        print(f"修复后的文件仍无法打开: {e2}")
                        # 清理临时文件
                        if os.path.exists(fixed_file_path):
                            os.remove(fixed_file_path)
                            print("临时修复文件已清理")
                else:
                    print("文件修复失败")
            except Exception as e:
                print(f"打开原始文件时发生其他错误: {e}")

if __name__ == "__main__":
    test_pdf_fix()