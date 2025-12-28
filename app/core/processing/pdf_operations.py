"""PDF操作器 - 处理PDF文件的各种操作功能"""

import os
import PyPDF2
import fitz  # PyMuPDF - 用于PDF页面渲染
import sys

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('pdf_operations')

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

class PDFOperations:
    """PDF操作器 - 专门处理PDF文件操作功能"""
    
    def __init__(self):
        # 注意：信号需要在主QObject子类中定义
        self.fitz_document = None  # PyMuPDF文档对象
        self.pdf_document = None   # PyPDF2文档对象
        self.current_file = None

    def save_pdf(self, file_path):
        """保存PDF文件到指定路径"""
        try:
            if not self.fitz_document:
                return False, "请先打开PDF文件"
            
            # 使用PyMuPDF保存当前文档
            self.fitz_document.save(file_path)
            return True, f"PDF文件已保存到: {file_path}"
            
        except Exception as e:
            return False, f"保存失败: {str(e)}"
    
    def merge_pdfs(self, file_paths, output_path):
        """合并多个PDF文件"""
        try:
            merger = PyPDF2.PdfMerger()
            
            for file_path in file_paths:
                with open(file_path, 'rb') as file:
                    merger.append(file)
            
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
                
            return True, "PDF合并成功"
        except Exception as e:
            return False, f"合并失败: {str(e)}"
    
    def split_pdf(self, output_dir, pages_per_file=None):
        """分割PDF文件"""
        if not self.pdf_document:
            return False, "请先打开PDF文件"
            
        try:
            if pages_per_file:
                # 按指定页数分割
                pass
            else:
                # 按单页分割
                for i, page in enumerate(self.pdf_document.pages):
                    writer = PyPDF2.PdfWriter()
                    writer.add_page(page)
                    
                    output_path = os.path.join(output_dir, f"page_{i+1}.pdf")
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                        
            return True, "PDF分割成功"
        except Exception as e:
            return False, f"分割失败: {str(e)}"
    
    def encrypt_pdf(self, password, output_path):
        """加密PDF文件"""
        if not self.pdf_document:
            return False, "请先打开PDF文件"
            
        try:
            writer = PyPDF2.PdfWriter()
            
            # 复制所有页面
            for page in self.pdf_document.pages:
                writer.add_page(page)
            
            # 加密
            writer.encrypt(password)
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
                
            return True, "PDF加密成功"
        except Exception as e:
            return False, f"加密失败: {str(e)}"