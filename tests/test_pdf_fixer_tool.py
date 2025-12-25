#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF修复工具 - 尝试修复不完整的PDF文件
"""
import os
import sys
import struct

def fix_pdf_eof_marker(file_path):
    """
    尝试修复PDF文件的EOF marker问题
    """
    print(f"尝试修复PDF文件: {file_path}")
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # 检查是否已有EOF标记
    eof_pos = content.rfind(b'%%EOF')
    if eof_pos != -1:
        print("PDF文件已有EOF标记，无需修复")
        return True, "文件已有EOF标记"
    
    # 查找xref和trailer部分
    xref_pos = content.rfind(b'xref')
    trailer_pos = content.rfind(b'trailer')
    
    if xref_pos != -1 and trailer_pos != -1 and trailer_pos > xref_pos:
        # 找到xref和trailer部分，尝试添加startxref
        print("找到xref和trailer部分，尝试修复...")
        
        # 计算xref部分的起始位置
        xref_start = xref_pos
        # 添加startxref和EOF
        fixed_content = content + f'\nstartxref\n{xref_start}\n%%EOF\n'.encode()
        
        # 生成修复后的文件名
        dir_path = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        fixed_file_path = os.path.join(dir_path, f"{base_name}_fixed.pdf")
        
        with open(fixed_file_path, 'wb') as f:
            f.write(fixed_content)
        
        print(f"修复后的文件已保存到: {fixed_file_path}")
        return True, f"修复完成，文件已保存到: {fixed_file_path}"
    
    # 如果没有找到xref和trailer，尝试查找对象
    obj_pos = content.rfind(b'obj')
    if obj_pos != -1:
        print("找到对象部分，尝试修复...")
        
        # 计算大概的交叉引用表位置
        xref_pos = obj_pos
        # 尝试添加xref、trailer、startxref和EOF
        fixed_content = content
        
        # 添加trailer部分
        trailer_part = b'\nxref\n0 1\n0000000000 65535 f\n' + content[obj_pos:obj_pos+100] + b'\ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\n'
        fixed_content = content + trailer_part + f'\nstartxref\n{len(content)}\n%%EOF\n'.encode()
        
        # 生成修复后的文件名
        dir_path = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        fixed_file_path = os.path.join(dir_path, f"{base_name}_fixed.pdf")
        
        with open(fixed_file_path, 'wb') as f:
            f.write(fixed_content)
        
        print(f"修复后的文件已保存到: {fixed_file_path}")
        return True, f"修复完成，文件已保存到: {fixed_file_path}"
    
    # 如果以上方法都不行，尝试简单添加EOF标记
    print("尝试简单添加EOF和trailer标记...")
    
    # 尝试添加基本的trailer和EOF
    fixed_content = content + b'\ntrailer\n<<\n/Size 1\n>>\nstartxref\n' + str(len(content)).encode() + b'\n%%EOF\n'
    
    # 生成修复后的文件名
    dir_path = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    fixed_file_path = os.path.join(dir_path, f"{base_name}_fixed.pdf")
    
    with open(fixed_file_path, 'wb') as f:
        f.write(fixed_content)
    
    print(f"修复后的文件已保存到: {fixed_file_path}")
    return True, f"修复完成，文件已保存到: {fixed_file_path}"


def test_fixed_pdf(file_path):
    """测试修复后的PDF文件"""
    import PyPDF2
    from PyPDF2.errors import PdfReadError
    
    print(f"测试修复后的PDF文件: {file_path}")
    
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            page_count = len(pdf_reader.pages)
            print(f"PDF修复成功！共 {page_count} 页")
            return True
    except PdfReadError as e:
        error_msg = str(e)
        print(f"PyPDF2 PdfReadError: {error_msg}")
        return False
    except Exception as e:
        error_msg = str(e)
        print(f"其他错误: {error_msg}")
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python pdf_fixer.py <pdf_file_path>")
        print("或者直接运行以修复下载的测试文件")
        # 默认修复测试目录中的文件
        test_dir = os.path.join(os.getcwd(), 'tests')
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.endswith('.pdf') and not file.endswith('_fixed.pdf'):
                    file_path = os.path.join(test_dir, file)
                    print(f"\n正在处理: {file_path}")
                    
                    success, msg = fix_pdf_eof_marker(file_path)
                    if success:
                        # 测试修复后的文件
                        dir_path = os.path.dirname(file_path)
                        base_name = os.path.splitext(os.path.basename(file_path))[0]
                        fixed_file_path = os.path.join(dir_path, f"{base_name}_fixed.pdf")
                        if os.path.exists(fixed_file_path):
                            print("\n测试修复后的文件:")
                            test_fixed_pdf(fixed_file_path)
                    else:
                        print(f"修复失败: {msg}")
        return
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    
    success, msg = fix_pdf_eof_marker(file_path)
    if success:
        # 测试修复后的文件
        dir_path = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        fixed_file_path = os.path.join(dir_path, f"{base_name}_fixed.pdf")
        if os.path.exists(fixed_file_path):
            print("\n测试修复后的文件:")
            test_fixed_pdf(fixed_file_path)
    else:
        print(f"修复失败: {msg}")


if __name__ == "__main__":
    main()