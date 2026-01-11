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
        # fitz_document 和 pdf_document 由 PDFProcessor 统一管理，不在子模块中初始化
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

            # 检查当前文档是否是从图片文件打开的
            # 通过检查文件扩展名来判断
            is_from_image = False
            if self.current_file:
                image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
                file_ext = os.path.splitext(self.current_file)[1].lower()
                if file_ext in image_extensions:
                    is_from_image = True
            
            # 检查是否是新建的多图片文档
            is_new_document = hasattr(self, 'is_new_document') and getattr(self, 'is_new_document', False)

            # 判断是否保存到原始文件
            is_saving_to_original = (self.current_file and
                                    os.path.abspath(file_path) == os.path.abspath(self.current_file))

            # 创建临时文件用于保存
            import tempfile
            import shutil
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='pypdf_save_')
            os.close(temp_fd)

            try:
                # 根据文档类型选择保存方法
                save_success = False
                
                # 首先尝试直接保存（适用于普通PDF文档）
                if not is_from_image and not is_new_document:
                    try:
                        # 使用平衡参数保存PDF文档，控制文件大小
                        self.fitz_document.save(temp_path, incremental=False, deflate=True, deflate_images=True, deflate_fonts=True, garbage=1, clean=True)
                        save_success = True
                        logger.debug("直接保存PDF文档成功")
                    except Exception as save_error:
                        logger.warning(f"直接保存PDF失败: {save_error}, 尝试通用方法")
                        # 如果直接保存失败，使用通用方法
                
                # 如果是图片文档或直接保存失败，使用通用方法创建标准PDF
                if not save_success:
                    try:
                        # 创建一个新的标准PDF文档
                        new_doc = fitz.open()

                        # 逐页复制内容
                        for page_num in range(len(self.fitz_document)):
                            page = self.fitz_document[page_num]
                            
                            # 获取页面尺寸并创建新页面
                            page_rect = page.rect
                            new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)
                            
                            # 根据文档类型采用适当的复制方法
                            if is_from_image or is_new_document:
                                # 对于图片文档，尝试多种方法保留原始图片质量
                                # 检查是否可以从原始文件直接读取图片数据
                                if self.current_file and os.path.exists(self.current_file):
                                    file_ext = os.path.splitext(self.current_file)[1].lower()
                                    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico']:
                                        # 如果原始文件存在且是图片格式，直接嵌入图片
                                        try:
                                            new_page.insert_image(new_page.rect, filename=self.current_file)
                                            logger.debug(f"成功直接嵌入原始图片文件: {self.current_file}")
                                        except Exception as e:
                                            logger.warning(f"直接嵌入原始图片失败: {e}, 尝试其他方法")
                                            # 如果直接嵌入失败，尝试获取页面图片信息
                                            img_list = page.get_images()
                                            if img_list:
                                                # 如果页面包含图片，直接使用原始图片数据
                                                xref = img_list[0][0]  # 第一个图片的xref
                                                pix = fitz.Pixmap(self.fitz_document, xref)
                                                new_page.insert_image(new_page.rect, pixmap=pix)
                                                logger.debug("成功嵌入原始图片数据")
                                            else:
                                                # 如果没有找到现有图片，则使用像素数据复制
                                                pix = page.get_pixmap(alpha=False)
                                                new_page.insert_image(new_page.rect, pixmap=pix)
                                                logger.debug("成功嵌入像素数据")
                                    else:
                                        # 如果不是图片格式，尝试常规方法
                                        img_list = page.get_images()
                                        if img_list:
                                            # 如果页面包含图片，直接使用原始图片数据
                                            xref = img_list[0][0]  # 第一个图片的xref
                                            pix = fitz.Pixmap(self.fitz_document, xref)
                                            new_page.insert_image(new_page.rect, pixmap=pix)
                                            logger.debug("成功嵌入原始图片数据")
                                        else:
                                            # 如果没有找到现有图片，则使用像素数据复制
                                            pix = page.get_pixmap(alpha=False)
                                            new_page.insert_image(new_page.rect, pixmap=pix)
                                            logger.debug("成功嵌入像素数据")
                                else:
                                    # 如果原始文件不存在，尝试常规方法
                                    img_list = page.get_images()
                                    if img_list:
                                        # 如果页面包含图片，直接使用原始图片数据
                                        xref = img_list[0][0]  # 第一个图片的xref
                                        pix = fitz.Pixmap(self.fitz_document, xref)
                                        new_page.insert_image(new_page.rect, pixmap=pix)
                                        logger.debug("成功嵌入原始图片数据")
                                    else:
                                        # 如果没有找到现有图片，则使用像素数据复制
                                        pix = page.get_pixmap(alpha=False)
                                        new_page.insert_image(new_page.rect, pixmap=pix)
                                        logger.debug("成功嵌入像素数据")
                            else:
                                # 对于普通PDF文档，优先使用show_pdf_page方法保持原始内容
                                try:
                                    new_page.show_pdf_page(new_page.rect, self.fitz_document, page_num)
                                except ValueError:
                                    # 如果show_pdf_page失败，尝试直接嵌入原始图片
                                    img_list = page.get_images()
                                    if img_list:
                                        # 如果页面包含图片，直接使用原始图片数据
                                        xref = img_list[0][0]  # 第一个图片的xref
                                        pix = fitz.Pixmap(self.fitz_document, xref)
                                        new_page.insert_image(new_page.rect, pixmap=pix)
                                    else:
                                        # 否则回退到像素复制
                                        mat = fitz.Matrix(1.5, 1.5)  # 1.5倍放大以平衡清晰度和文件大小
                                        pix = page.get_pixmap(matrix=mat, alpha=False)
                                        new_page.insert_image(new_page.rect, pixmap=pix)
                        
                        # 保存新创建的标准PDF文档
                        new_doc.save(temp_path)
                        new_doc.close()
                        save_success = True
                        logger.debug(f"成功创建标准PDF文档，包含 {len(self.fitz_document)} 页")
                        
                    except Exception as new_doc_error:
                        logger.error(f"创建新PDF文档失败: {new_doc_error}")
                        save_success = False
                        
                if not save_success:
                    raise RuntimeError("无法将文档保存为标准PDF格式")
                
                # 检查目标文件是否被锁定
                def is_file_locked(filepath, timeout=2):
                    import time
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        try:
                            # 尝试以追加模式打开文件，如果成功则文件未被锁定
                            with open(filepath, 'a+'):
                                pass
                            return False  # 文件未被锁定
                        except (IOError, OSError):
                            time.sleep(0.1)
                    return True  # 超时，认为文件被锁定

                if is_file_locked(file_path):
                    logger.warning("目标文件被锁定，无法保存")
                    os.unlink(temp_path)
                    return False, "文件正在被其他程序使用，请关闭后再试"

                # 用临时文件替换目标文件
                shutil.copy2(temp_path, file_path)
                logger.debug("临时文件已复制到目标文件位置")
                
                # 如果保存成功，更新current_file
                if is_saving_to_original:
                    self.current_file = file_path

                return True, f"PDF文件已保存到: {file_path}"

            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                raise e

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

            # 检查当前文档是否是从图片文件打开的
            # 通过检查文件扩展名来判断
            is_from_image = False
            if self.current_file:
                image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
                file_ext = os.path.splitext(self.current_file)[1].lower()
                if file_ext in image_extensions:
                    is_from_image = True
                    
            # 检查是否是新建的多图片文档
            is_new_document = hasattr(self, 'is_new_document') and getattr(self, 'is_new_document', False)
                
            # 使用PyPDF2来处理加密
            from PyPDF2 import PdfWriter, PdfReader
                
            # 先将PyMuPDF文档保存到临时文件
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='pypdf_encrypted_')
            os.close(temp_fd)

            try:
                # 用PyMuPDF保存到临时文件
                # 如果是从图片打开的文档或特殊格式，需要特殊处理
                save_success = False
                    
                # 首先尝试直接保存（适用于普通PDF文档）
                if not is_from_image and not is_new_document:
                    try:
                        # 使用平衡参数保存PDF文档，控制文件大小
                        self.fitz_document.save(temp_path, incremental=False, deflate=True, deflate_images=True, deflate_fonts=True, garbage=1, clean=True)
                        save_success = True
                        logger.debug("直接保存PDF文档成功")
                    except Exception as save_error:
                        logger.warning(f"直接保存PDF失败: {save_error}, 尝试通用方法")
                        # 如果直接保存失败，使用通用方法
                                        
                # 如果是图片文档或直接保存失败，使用通用方法创建标准PDF
                if not save_success:
                    try:
                        # 创建一个新的标准PDF文档
                        new_doc = fitz.open()
                                        
                        # 逐页复制内容
                        for page_num in range(len(self.fitz_document)):
                            page = self.fitz_document[page_num]
                                                    
                            # 获取页面尺寸并创建新页面
                            page_rect = page.rect
                            new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)
                                                    
                            # 根据文档类型采用适当的复制方法
                            if is_from_image or is_new_document:
                                # 对于图片文档，尝试多种方法保留原始图片质量
                                # 检查是否可以从原始文件直接读取图片数据
                                if self.current_file and os.path.exists(self.current_file):
                                    file_ext = os.path.splitext(self.current_file)[1].lower()
                                    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico']:
                                        # 如果原始文件存在且是图片格式，直接嵌入图片
                                        try:
                                            new_page.insert_image(new_page.rect, filename=self.current_file)
                                            logger.debug(f"成功直接嵌入原始图片文件: {self.current_file}")
                                        except Exception as e:
                                            logger.warning(f"直接嵌入原始图片失败: {e}, 尝试其他方法")
                                            # 如果直接嵌入失败，尝试获取页面图片信息
                                            img_list = page.get_images()
                                            if img_list:
                                                # 如果页面包含图片，直接使用原始图片数据
                                                xref = img_list[0][0]  # 第一个图片的xref
                                                pix = fitz.Pixmap(self.fitz_document, xref)
                                                new_page.insert_image(new_page.rect, pixmap=pix)
                                                logger.debug("成功嵌入原始图片数据")
                                            else:
                                                # 如果没有找到现有图片，则使用像素数据复制
                                                pix = page.get_pixmap(alpha=False)
                                                new_page.insert_image(new_page.rect, pixmap=pix)
                                                logger.debug("成功嵌入像素数据")
                                    else:
                                        # 如果不是图片格式，尝试常规方法
                                        img_list = page.get_images()
                                        if img_list:
                                            # 如果页面包含图片，直接使用原始图片数据
                                            xref = img_list[0][0]  # 第一个图片的xref
                                            pix = fitz.Pixmap(self.fitz_document, xref)
                                            new_page.insert_image(new_page.rect, pixmap=pix)
                                            logger.debug("成功嵌入原始图片数据")
                                        else:
                                            # 如果没有找到现有图片，则使用像素数据复制
                                            pix = page.get_pixmap(alpha=False)
                                            new_page.insert_image(new_page.rect, pixmap=pix)
                                            logger.debug("成功嵌入像素数据")
                                else:
                                    # 如果原始文件不存在，尝试常规方法
                                    img_list = page.get_images()
                                    if img_list:
                                        # 如果页面包含图片，直接使用原始图片数据
                                        xref = img_list[0][0]  # 第一个图片的xref
                                        pix = fitz.Pixmap(self.fitz_document, xref)
                                        new_page.insert_image(new_page.rect, pixmap=pix)
                                        logger.debug("成功嵌入原始图片数据")
                                    else:
                                        # 如果没有找到现有图片，则使用像素数据复制
                                        pix = page.get_pixmap(alpha=False)
                                        new_page.insert_image(new_page.rect, pixmap=pix)
                                        logger.debug("成功嵌入像素数据")
                            else:
                                # 对于普通PDF文档，优先使用show_pdf_page方法保持原始内容
                                try:
                                    new_page.show_pdf_page(new_page.rect, self.fitz_document, page_num)
                                except ValueError:
                                    # 如果show_pdf_page失败，尝试直接嵌入原始图片
                                    img_list = page.get_images()
                                    if img_list:
                                        # 如果页面包含图片，直接使用原始图片数据
                                        xref = img_list[0][0]  # 第一个图片的xref
                                        pix = fitz.Pixmap(self.fitz_document, xref)
                                        new_page.insert_image(new_page.rect, pixmap=pix)
                                    else:
                                        # 否则回退到像素复制
                                        mat = fitz.Matrix(1.5, 1.5)  # 1.5倍放大以平衡清晰度和文件大小
                                        pix = page.get_pixmap(matrix=mat, alpha=False)
                                        new_page.insert_image(new_page.rect, pixmap=pix)
                                        
                        # 保存新创建的标准PDF文档
                        new_doc.save(temp_path)
                        new_doc.close()
                        save_success = True
                        logger.debug(f"成功创建标准PDF文档，包含 {len(self.fitz_document)} 页")
                                        
                    except Exception as new_doc_error:
                        logger.error(f"创建新PDF文档失败: {new_doc_error}")
                        save_success = False
                                        
                if not save_success:
                    raise RuntimeError("无法将文档保存为标准PDF格式")
                    
                # 检查目标文件是否被锁定
                def is_file_locked(filepath, timeout=2):
                    import time
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        try:
                            # 尝试以追加模式打开文件，如果成功则文件未被锁定
                            with open(filepath, 'a+'):
                                pass
                            return False  # 文件未被锁定
                        except (IOError, OSError):
                            time.sleep(0.1)
                    return True  # 超时，认为文件被锁定
                
                if is_file_locked(output_path):
                    logger.warning("目标文件被锁定，无法保存")
                    os.unlink(temp_path)
                    return False, "文件正在被其他程序使用，请关闭后再试"
                
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
                                
                # 加密操作会改变原始文档状态，需要通知上层组件重新加载文档
                # 但不能在这里直接关闭当前文档，因为可能还有其他操作正在使用
                # 我们只是完成加密文件的保存，让调用者知道操作已完成
                
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