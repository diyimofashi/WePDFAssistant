"""PDF操作器 - 处理PDF文件的各种操作功能"""

import os
import PyPDF2
import fitz  # PyMuPDF - 用于PDF页面渲染
import sys
import tempfile

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
            logger.debug(f"开始保存PDF文件到: {file_path}")
            logger.debug(f"当前fitz_document: {self.fitz_document}")
            logger.debug(f"当前current_file: {self.current_file}")

            # 判断是否保存到原始文件
            is_saving_to_original = (self.current_file and
                                    os.path.abspath(file_path) == os.path.abspath(self.current_file))

            if is_saving_to_original:
                # 保存到原文件：先保存到临时文件，然后替换原文件
                # 这样可以避免增量保存的限制
                logger.debug("保存到原文件，使用临时文件替换")
                import tempfile
                import shutil

                # 创建临时文件
                temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='pypdf_save_')
                os.close(temp_fd)

                try:
                    # 保存到临时文件
                    self.fitz_document.save(temp_path, incremental=False)
                    logger.debug(f"已保存到临时文件: {temp_path}")

                    # 检查文件是否被锁定
                    def is_file_locked(filepath, timeout=2):
                        import time
                        start_time = time.time()
                        while time.time() - start_time < timeout:
                            try:
                                with open(filepath, 'a'):
                                    pass
                                return False
                            except IOError:
                                time.sleep(0.1)
                        return True

                    if is_file_locked(file_path):
                        logger.warning("原文件被锁定，无法保存")
                        os.unlink(temp_path)
                        return False, "文件正在被其他程序使用，请关闭后再试"

                    # 用临时文件替换原文件
                    shutil.copy2(temp_path, file_path)
                    logger.debug("临时文件已复制到原文件位置")
                    return True, f"PDF文件已保存到: {file_path}"

                except Exception as e:
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                    raise e
            else:
                # 保存到新文件，直接保存
                logger.debug("保存到新文件，使用普通保存")
                self.fitz_document.save(file_path, incremental=False)
                return True, f"PDF文件已保存到: {file_path}"

        except Exception as e:
            logger.error(f"保存PDF文件失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
        if not self.fitz_document:
            return False, "请先打开PDF文件"

        try:
            # 判断是否保存到原始文件
            is_saving_to_original = (self.current_file and
                                    os.path.abspath(output_path) == os.path.abspath(self.current_file))

            # 使用PyPDF2来处理加密
            from PyPDF2 import PdfWriter, PdfReader
            
            # 先将PyMuPDF文档保存到临时文件
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='pypdf_encrypted_')
            os.close(temp_fd)

            try:
                # 用PyMuPDF保存到临时文件
                self.fitz_document.save(temp_path, incremental=False)
                
                # 使用PyPDF2读取临时文件并加密
                with open(temp_path, 'rb') as temp_file:
                    pdf_reader = PdfReader(temp_file)
                    pdf_writer = PdfWriter()
                    
                    # 复制所有页面
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
                    
                    # 添加元数据（如果有的话）
                    if pdf_reader.metadata:
                        pdf_writer.add_metadata(pdf_reader.metadata)
                    
                    # 加密PDF
                    pdf_writer.encrypt(password)
                    
                    # 保存到目标路径
                    with open(output_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                
                logger.debug(f"已加密保存到文件: {output_path}")

                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

                return True, "PDF加密成功"

            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                raise e

        except Exception as e:
            logger.error(f"加密PDF文件失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"加密失败: {str(e)}"