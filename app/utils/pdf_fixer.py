#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF修复工具模块 - 提供修复不完整PDF文件的功能
"""
import os
import tempfile
import fitz  # PyMuPDF


def try_fix_pdf_file(file_path):
    """
    尝试修复不完整的PDF文件
    返回修复后的文件路径，如果修复失败则返回None
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        # 检查是否已有EOF标记
        if b'%%EOF' in content[-20:]:  # 检查最后20个字节
            return None  # 已有EOF标记，无需修复

        # 尝试添加基本的PDF尾部结构
        fixed_content = content + b'\ntrailer\n<<\n/Size 1\n>>\nstartxref\n' + str(len(content)).encode() + b'\n%%EOF\n'

        # 生成修复后的文件路径（使用临时文件）
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='fixed_')

        try:
            with os.fdopen(temp_fd, 'wb') as tmp_file:
                tmp_file.write(fixed_content)

            # 验证修复后的文件是否可以打开
            try:
                test_doc = fitz.open(temp_path)
                test_doc.close()
                # 如果能成功打开，返回临时文件路径
                return temp_path
            except Exception:
                # 如果还是打不开，删除临时文件并返回None
                os.close(temp_fd)  # 确保文件句柄已关闭
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return None
        except Exception:
            # 如果写入临时文件失败，确保清理
            os.close(temp_fd)  # 确保文件句柄已关闭
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None
    except Exception:
        return None