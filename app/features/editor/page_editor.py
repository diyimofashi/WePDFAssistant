"""
页面编辑功能模块
提供PDF页面的插入、删除、复制、旋转等编辑功能
"""

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
import os
import fitz  # PyMuPDF
import PyPDF2
from PyPDF2 import PdfWriter, PdfReader
from PIL import Image
from PIL.Image import Resampling
import time


class PageEditor:
    """PDF页面编辑器"""
    
    def __init__(self, pdf_processor):
        self.pdf_processor = pdf_processor
    
    def is_file_locked(self, file_path, timeout=5):
        """检查文件是否被锁定，并尝试等待解锁"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 尝试以独占模式打开文件
                with open(file_path, 'r+b') as f:
                    pass
                return False  # 文件未被锁定
            except IOError:
                # 文件被锁定，等待一段时间后重试
                time.sleep(0.1)
        return True  # 文件仍然被锁定
    
    def insert_blank_page(self, page_num):
        """插入空白页"""
        try:
            if not self.pdf_processor.fitz_document:
                return False, "请先打开PDF文件"
            
            # 获取当前PDF文件路径
            if not self.pdf_processor.current_file:
                return False, "无法获取当前PDF文件路径"
            
            # 关闭当前PDF文件句柄，避免文件锁定
            current_file = self.pdf_processor.current_file
            if not current_file:
                return False, "无法获取当前PDF文件路径"
            self.pdf_processor.close_pdf()
            
            # 使用PyPDF2插入空白页
            reader = PdfReader(current_file)
            writer = PdfWriter()
            
            # 复制所有页面直到插入位置
            for i in range(min(page_num, len(reader.pages))):
                writer.add_page(reader.pages[i])
            
            # 插入A4大小的空白页 (595 x 842 points)
            from PyPDF2 import PageObject
            blank_page = PageObject.create_blank_page(width=595, height=842)
            writer.add_page(blank_page)
            
            # 复制剩余页面
            for i in range(page_num, len(reader.pages)):
                writer.add_page(reader.pages[i])
            
            # 保存到临时文件
            temp_file = current_file + ".tmp"
            try:
                with open(temp_file, 'wb') as output_file:
                    writer.write(output_file)
                
                # 替换原文件
                os.replace(temp_file, current_file)
                
                # 重新加载PDF
                self.pdf_processor.load_pdf(current_file)
            except PermissionError:
                # 如果替换失败，尝试使用不同的方法
                try:
                    # 先删除原文件，再重命名临时文件
                    if os.path.exists(current_file):
                        os.remove(current_file)
                    os.rename(temp_file, current_file)
                    
                    # 重新加载PDF
                    self.pdf_processor.load_pdf(current_file)
                except Exception as e2:
                    # 如果还是失败，清理临时文件并返回错误
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False, f"插入空白页失败: {str(e2)}"
            except Exception as e:
                # 如果保存失败，清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False, f"插入空白页失败: {str(e)}"
            
            return True, f"已在第 {page_num} 页后插入空白页"
        except Exception as e:
            return False, f"插入空白页失败: {str(e)}"
        except Exception as e:
            return False, f"插入空白页失败: {str(e)}"
    
    def insert_pdf_pages(self, page_num, pdf_file_path):
        """插入PDF页面"""
        try:
            if not self.pdf_processor.fitz_document:
                return False, "请先打开PDF文件"
            
            if not os.path.exists(pdf_file_path):
                return False, "指定的PDF文件不存在"
            
            # 获取当前PDF文件路径
            if not self.pdf_processor.current_file:
                return False, "无法获取当前PDF文件路径"
            
            # 关闭当前PDF文件句柄，避免文件锁定
            current_file = self.pdf_processor.current_file
            if not current_file:
                return False, "无法获取当前PDF文件路径"
            self.pdf_processor.close_pdf()
            
            # 使用PyPDF2合并PDF文件
            current_reader = PdfReader(current_file)
            insert_reader = PdfReader(pdf_file_path)
            writer = PdfWriter()
            
            # 复制所有页面直到插入位置
            for i in range(min(page_num, len(current_reader.pages))):
                writer.add_page(current_reader.pages[i])
            
            # 插入新PDF的所有页面
            for page in insert_reader.pages:
                writer.add_page(page)
            
            # 复制剩余页面
            for i in range(page_num, len(current_reader.pages)):
                writer.add_page(current_reader.pages[i])
            
            # 保存到临时文件
            temp_file = current_file + ".tmp"
            try:
                with open(temp_file, 'wb') as output_file:
                    writer.write(output_file)
                
                # 替换原文件
                os.replace(temp_file, current_file)
                
                # 重新加载PDF
                self.pdf_processor.load_pdf(current_file)
            except PermissionError:
                # 如果替换失败，尝试使用不同的方法
                try:
                    # 先删除原文件，再重命名临时文件
                    if os.path.exists(current_file):
                        os.remove(current_file)
                    os.rename(temp_file, current_file)
                    
                    # 重新加载PDF
                    self.pdf_processor.load_pdf(current_file)
                except Exception as e2:
                    # 如果还是失败，清理临时文件并返回错误
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False, f"插入PDF页面失败: {str(e2)}"
            except Exception as e:
                # 如果保存失败，清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False, f"插入PDF页面失败: {str(e)}"
            
            return True, f"已将 {os.path.basename(pdf_file_path)} 插入到第 {page_num} 页"
        except Exception as e:
            return False, f"插入PDF页面失败: {str(e)}"
        except Exception as e:
            return False, f"插入PDF页面失败: {str(e)}"
    
    def insert_image_page(self, page_num, image_path):
        """插入图片页面"""
        try:
            if not self.pdf_processor.fitz_document:
                return False, "请先打开PDF文件"
            
            if not os.path.exists(image_path):
                return False, "指定的图片文件不存在"
            
            # 获取当前PDF文件路径
            if not self.pdf_processor.current_file:
                return False, "无法获取当前PDF文件路径"
            
            # 关闭当前PDF文件句柄，避免文件锁定
            current_file = self.pdf_processor.current_file
            if not current_file:
                return False, "无法获取当前PDF文件路径"
            self.pdf_processor.close_pdf()
            
            # 使用Pillow将图片转换为PDF，并调整为A4纸大小
            image = Image.open(image_path)
            
            # A4纸尺寸 (595 x 842 points)
            a4_width, a4_height = 595, 842
            
            # 调整图片大小以适应A4纸
            image.thumbnail((a4_width, a4_height), Resampling.LANCZOS)
            
            # 创建新的A4尺寸图片并居中放置原图
            a4_image = Image.new('RGB', (a4_width, a4_height), 'white')
            x = (a4_width - image.width) // 2
            y = (a4_height - image.height) // 2
            a4_image.paste(image, (x, y))
            
            # 创建临时PDF文件
            temp_pdf_path = image_path + ".tmp.pdf"
            a4_image.save(temp_pdf_path, "PDF", resolution=100.0)
            
            # 使用PyPDF2合并PDF文件
            current_reader = PdfReader(current_file)
            insert_reader = PdfReader(temp_pdf_path)
            writer = PdfWriter()
            
            # 复制所有页面直到插入位置
            for i in range(min(page_num, len(current_reader.pages))):
                writer.add_page(current_reader.pages[i])
            
            # 插入图片PDF的所有页面（通常只有一页）
            for page in insert_reader.pages:
                writer.add_page(page)
            
            # 复制剩余页面
            for i in range(page_num, len(current_reader.pages)):
                writer.add_page(current_reader.pages[i])
            
            # 保存到临时文件
            temp_file = current_file + ".tmp"
            try:
                with open(temp_file, 'wb') as output_file:
                    writer.write(output_file)
                
                # 清理临时文件
                os.remove(temp_pdf_path)
                
                # 替换原文件
                os.replace(temp_file, current_file)
                
                # 重新加载PDF
                self.pdf_processor.load_pdf(current_file)
            except PermissionError:
                # 如果替换失败，尝试使用不同的方法
                try:
                    # 先删除原文件，再重命名临时文件
                    if os.path.exists(current_file):
                        os.remove(current_file)
                    os.rename(temp_file, current_file)
                    
                    # 清理临时文件
                    if os.path.exists(temp_pdf_path):
                        os.remove(temp_pdf_path)
                    
                    # 重新加载PDF
                    self.pdf_processor.load_pdf(current_file)
                except Exception as e2:
                    # 如果还是失败，清理临时文件并返回错误
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    if os.path.exists(temp_pdf_path):
                        os.remove(temp_pdf_path)
                    return False, f"插入图片页面失败: {str(e2)}"
            except Exception as e:
                # 如果保存失败，清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
                return False, f"插入图片页面失败: {str(e)}"
            
            return True, f"已将 {os.path.basename(image_path)} 插入到第 {page_num} 页"
        except Exception as e:
            return False, f"插入图片页面失败: {str(e)}"
        except Exception as e:
            return False, f"插入图片页面失败: {str(e)}"
    
    def copy_page(self, page_num):
        """复制页面"""
        try:
            if not self.pdf_processor.fitz_document:
                return False, "请先打开PDF文件"
            
            # 获取当前PDF文件路径
            if not self.pdf_processor.current_file:
                return False, "无法获取当前PDF文件路径"
            
            # 关闭当前PDF文件句柄，避免文件锁定
            current_file = self.pdf_processor.current_file
            if not current_file:
                return False, "无法获取当前PDF文件路径"
            self.pdf_processor.close_pdf()
            
            # 使用PyPDF2复制页面
            reader = PdfReader(current_file)
            writer = PdfWriter()
            
            # 复制所有页面
            for page in reader.pages:
                writer.add_page(page)
            
            # 在指定位置插入复制的页面
            if 0 <= page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])
            
            # 保存到临时文件
            temp_file = current_file + ".tmp"
            try:
                with open(temp_file, 'wb') as output_file:
                    writer.write(output_file)
                
                # 替换原文件
                os.replace(temp_file, current_file)
                
                # 重新加载PDF
                self.pdf_processor.load_pdf(current_file)
            except PermissionError:
                # 如果替换失败，尝试使用不同的方法
                try:
                    # 先删除原文件，再重命名临时文件
                    if os.path.exists(current_file):
                        os.remove(current_file)
                    os.rename(temp_file, current_file)
                    
                    # 重新加载PDF
                    self.pdf_processor.load_pdf(current_file)
                except Exception as e2:
                    # 如果还是失败，清理临时文件并返回错误
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False, f"复制页面失败: {str(e2)}"
            except Exception as e:
                # 如果保存失败，清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False, f"复制页面失败: {str(e)}"
            
            return True, f"已复制第 {page_num} 页"
        except Exception as e:
            return False, f"复制页面失败: {str(e)}"
        except Exception as e:
            return False, f"复制页面失败: {str(e)}"
    
    def delete_page(self, page_num):
        """删除页面"""
        try:
            if not self.pdf_processor.fitz_document:
                return False, "请先打开PDF文件"
            
            # 获取当前PDF文件路径
            if not self.pdf_processor.current_file:
                return False, "无法获取当前PDF文件路径"
            
            # 关闭当前PDF文件句柄，避免文件锁定
            current_file = self.pdf_processor.current_file
            if not current_file:
                return False, "无法获取当前PDF文件路径"
            self.pdf_processor.close_pdf()
            
            # 使用PyPDF2删除页面
            reader = PdfReader(current_file)
            writer = PdfWriter()
            
            # 复制除要删除页面外的所有页面
            for i, page in enumerate(reader.pages):
                if i != page_num - 1:  # page_num从1开始，索引从0开始
                    writer.add_page(page)
            
            # 保存到临时文件
            temp_file = current_file + ".tmp"
            try:
                with open(temp_file, 'wb') as output_file:
                    writer.write(output_file)
                
                # 替换原文件
                os.replace(temp_file, current_file)
                
                # 重新加载PDF
                self.pdf_processor.load_pdf(current_file)
            except PermissionError:
                # 如果替换失败，尝试使用不同的方法
                try:
                    # 先删除原文件，再重命名临时文件
                    if os.path.exists(current_file):
                        os.remove(current_file)
                    os.rename(temp_file, current_file)
                    
                    # 重新加载PDF
                    self.pdf_processor.load_pdf(current_file)
                except Exception as e2:
                    # 如果还是失败，清理临时文件并返回错误
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False, f"删除页面失败: {str(e2)}"
            except Exception as e:
                # 如果保存失败，清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False, f"删除页面失败: {str(e)}"
            
            return True, f"已删除第 {page_num} 页"
        except Exception as e:
            return False, f"删除页面失败: {str(e)}"
        except Exception as e:
            return False, f"删除页面失败: {str(e)}"
    
    def rotate_page(self, page_num, angle):
        """旋转页面"""
        try:
            if not self.pdf_processor.fitz_document:
                return False, "请先打开PDF文件"
            
            # 获取当前PDF文件路径
            if not self.pdf_processor.current_file:
                return False, "无法获取当前PDF文件路径"
            
            # 关闭当前PDF文件句柄，避免文件锁定
            current_file = self.pdf_processor.current_file
            if not current_file:
                return False, "无法获取当前PDF文件路径"
            self.pdf_processor.close_pdf()
            
            # 使用PyPDF2旋转页面
            reader = PdfReader(current_file)
            writer = PdfWriter()
            
            # 复制所有页面，对指定页面进行旋转
            for i, page in enumerate(reader.pages):
                if i == page_num - 1:  # page_num从1开始，索引从0开始
                    page.rotate(angle)
                writer.add_page(page)
            
            # 保存到临时文件
            temp_file = current_file + ".tmp"
            try:
                with open(temp_file, 'wb') as output_file:
                    writer.write(output_file)
                
                # 替换原文件
                os.replace(temp_file, current_file)
                
                # 重新加载PDF
                self.pdf_processor.load_pdf(current_file)
            except PermissionError:
                # 如果替换失败，尝试使用不同的方法
                try:
                    # 先删除原文件，再重命名临时文件
                    if os.path.exists(current_file):
                        os.remove(current_file)
                    os.rename(temp_file, current_file)
                    
                    # 重新加载PDF
                    self.pdf_processor.load_pdf(current_file)
                except Exception as e2:
                    # 如果还是失败，清理临时文件并返回错误
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False, f"旋转页面失败: {str(e2)}"
            except Exception as e:
                # 如果保存失败，清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False, f"旋转页面失败: {str(e)}"
            
            return True, f"已将第 {page_num} 页旋转 {angle} 度"
        except Exception as e:
            return False, f"旋转页面失败: {str(e)}"
        except Exception as e:
            return False, f"旋转页面失败: {str(e)}"
    
    def rotate_all_pages(self, angle):
        """旋转所有页面"""
        try:
            if not self.pdf_processor.fitz_document:
                return False, "请先打开PDF文件"
            
            # 获取当前PDF文件路径
            if not self.pdf_processor.current_file:
                return False, "无法获取当前PDF文件路径"
            
            # 关闭当前PDF文件句柄，避免文件锁定
            current_file = self.pdf_processor.current_file
            if not current_file:
                return False, "无法获取当前PDF文件路径"
            self.pdf_processor.close_pdf()
            
            # 使用PyPDF2旋转所有页面
            reader = PdfReader(current_file)
            writer = PdfWriter()
            
            # 复制所有页面并旋转
            for page in reader.pages:
                page.rotate(angle)
                writer.add_page(page)
            
            # 保存到临时文件
            temp_file = current_file + ".tmp"
            try:
                with open(temp_file, 'wb') as output_file:
                    writer.write(output_file)
                
                # 替换原文件
                os.replace(temp_file, current_file)
                
                # 重新加载PDF
                self.pdf_processor.load_pdf(current_file)
            except PermissionError:
                # 如果替换失败，尝试使用不同的方法
                try:
                    # 先删除原文件，再重命名临时文件
                    if os.path.exists(current_file):
                        os.remove(current_file)
                    os.rename(temp_file, current_file)
                    
                    # 重新加载PDF
                    self.pdf_processor.load_pdf(current_file)
                except Exception as e2:
                    # 如果还是失败，清理临时文件并返回错误
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False, f"旋转所有页面失败: {str(e2)}"
            except Exception as e:
                # 如果保存失败，清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False, f"旋转所有页面失败: {str(e)}"
            
            return True, f"已将所有页面旋转 {angle} 度"
        except Exception as e:
            return False, f"旋转所有页面失败: {str(e)}"
        except Exception as e:
            return False, f"旋转所有页面失败: {str(e)}"