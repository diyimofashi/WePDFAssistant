"""PDF操作器 - 处理PDF文件的各种操作功能"""

import os
import fitz  # PyMuPDF
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

    def _is_image_file(self, file_path):
        """判断是否为图片文件"""
        if not file_path:
            return False
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in image_extensions

    def _is_file_locked(self, filepath, timeout=2):
        """检查文件是否被锁定"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(filepath, 'a+'):
                    pass
                return False
            except (IOError, OSError):
                time.sleep(0.1)
        return True

    def _copy_page_content(self, src_doc, page_num, new_page, is_from_image=False, original_image_path=None):
        """复制页面内容到新页面"""
        src_page = src_doc[page_num]
        page_rect = src_page.rect

        if is_from_image and original_image_path and os.path.exists(original_image_path):
            try:
                new_page.insert_image(page_rect, filename=original_image_path)
                return
            except Exception:
                pass

        img_list = src_page.get_images()
        if img_list:
            xref = img_list[0][0]
            pix = fitz.Pixmap(src_doc, xref)
            new_page.insert_image(page_rect, pixmap=pix)
        else:
            pix = src_page.get_pixmap(alpha=False)
            new_page.insert_image(page_rect, pixmap=pix)

    def _save_document_to_file(self, src_doc, target_path, is_from_image=False, original_image_path=None, encryption=None, password=None):
        """保存文档到文件"""
        save_success = False

        if not is_from_image:
            try:
                save_args = {
                    'incremental': False,
                    'deflate': True,
                    'deflate_images': True,
                    'deflate_fonts': True,
                    'garbage': 1,
                    'clean': True
                }

                if encryption:
                    save_args['encryption'] = encryption
                    save_args['user_pw'] = password

                src_doc.save(target_path, **save_args)
                save_success = True
            except Exception as e:
                logger.warning(f"直接保存失败: {e}")

        if not save_success:
            new_doc = fitz.open()
            for page_num in range(len(src_doc)):
                src_page = src_doc[page_num]
                new_page = new_doc.new_page(width=src_page.rect.width, height=src_page.rect.height)

                try:
                    new_page.show_pdf_page(src_page.rect, src_doc, page_num)
                except ValueError:
                    self._copy_page_content(src_doc, page_num, new_page, is_from_image, original_image_path)

            save_args = {}
            if encryption:
                save_args['encryption'] = encryption
                save_args['user_pw'] = password

            new_doc.save(target_path, **save_args)
            new_doc.close()

    def save_pdf(self, file_path):
        """保存PDF文件到指定路径"""
        temp_path = None
        try:
            if not self.fitz_document:
                return False, "请先打开PDF文件"

            is_from_image = self._is_image_file(self.current_file)
            is_new_document = hasattr(self, 'is_new_document') and self.is_new_document
            is_saving_to_original = (self.current_file and
                                    os.path.abspath(file_path) == os.path.abspath(self.current_file))

            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='pypdf_save_')
            os.close(temp_fd)

            self._save_document_to_file(
                self.fitz_document,
                temp_path,
                is_from_image=is_from_image or is_new_document,
                original_image_path=self.current_file
            )

            if self._is_file_locked(file_path):
                logger.warning("目标文件被锁定，无法保存")
                return False, "文件正在被其他程序使用，请关闭后再试"

            import shutil
            shutil.copy2(temp_path, file_path)

            if is_saving_to_original:
                self.current_file = file_path

            return True, f"PDF文件已保存到: {file_path}"

        except Exception as e:
            logger.error(f"保存PDF文件失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"保存失败: {str(e)}"
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def merge_pdfs(self, file_paths, output_path):
        """合并多个PDF文件"""
        try:
            merged_doc = fitz.open()

            for file_path in file_paths:
                src_doc = fitz.open(file_path)
                merged_doc.insert_pdf(src_doc)
                src_doc.close()

            merged_doc.save(output_path, deflate=True, clean=True, garbage=1)
            merged_doc.close()

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
                for i in range(self.pdf_document.page_count):
                    new_doc = fitz.open()
                    new_doc.insert_pdf(self.pdf_document, from_page=i, to_page=i)

                    output_path = os.path.join(output_dir, f"page_{i+1}.pdf")
                    new_doc.save(output_path, deflate=True, clean=True, garbage=1)
                    new_doc.close()

            return True, "PDF分割成功"
        except Exception as e:
            return False, f"分割失败: {str(e)}"
    
    def encrypt_pdf(self, password, output_path):
        """加密PDF文件"""
        temp_path = None
        encrypted_temp_path = None
        try:
            if not self.fitz_document:
                return False, "请先打开PDF文件"

            is_from_image = self._is_image_file(self.current_file)
            is_new_document = hasattr(self, 'is_new_document') and self.is_new_document

            # 判断是否是保存到同一个文件
            is_same_file = (self.current_file and
                           os.path.abspath(output_path) == os.path.abspath(self.current_file))

            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='pypdf_encrypted_')
            os.close(temp_fd)

            self._save_document_to_file(
                self.fitz_document,
                temp_path,
                is_from_image=is_from_image or is_new_document,
                original_image_path=self.current_file
            )

            if self._is_file_locked(output_path):
                logger.warning("目标文件被锁定，无法保存")
                return False, "文件正在被其他程序使用，请关闭后再试"

            temp_doc = fitz.open(temp_path)

            # 如果是保存到同一个文件，先保存到临时文件再替换
            if is_same_file:
                encrypted_fd, encrypted_temp_path = tempfile.mkstemp(suffix='.pdf', prefix='pypdf_encrypted_final_')
                os.close(encrypted_fd)

                temp_doc.save(
                    encrypted_temp_path,
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    user_pw=password,
                    deflate=True,
                    clean=True,
                    garbage=1
                )
                temp_doc.close()

                import shutil
                shutil.copy2(encrypted_temp_path, output_path)
            else:
                # 保存到新文件
                temp_doc.save(
                    output_path,
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    user_pw=password,
                    deflate=True,
                    clean=True,
                    garbage=1
                )
                temp_doc.close()

            return True, "PDF加密成功"

        except Exception as e:
            logger.error(f"加密PDF文件失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"加密失败: {str(e)}"
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            if encrypted_temp_path and os.path.exists(encrypted_temp_path):
                try:
                    os.unlink(encrypted_temp_path)
                except:
                    pass