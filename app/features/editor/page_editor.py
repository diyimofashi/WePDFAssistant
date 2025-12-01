"""页面编辑功能模块
提供PDF页面的插入、删除、复制、旋转等编辑功能"""

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
import os
import tempfile
import shutil
import fitz  # PyMuPDF
import PyPDF2
from PyPDF2 import PdfWriter, PdfReader
from PIL import Image
from PIL.Image import Resampling
import time
import copy

class PageEditor:
    """PDF页面编辑器"""
    
    def __init__(self, pdf_processor):
        self.pdf_processor = pdf_processor
        self.temp_file = None  # 临时文件路径
        self.original_file = None  # 原始文件路径
        self.is_modified = False  # 是否已修改
        
        # 撤销/重做历史
        self.history = []  # 操作历史栈
        self.redo_stack = []  # 重做栈
        self.max_history = 50  # 最大历史记录数
    
    def is_file_locked(self, file_path, timeout=5):
        """检查文件是否被锁定，并尝试等待解锁"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 尝试以独占模式打开文件
                with open(file_path, 'a'):
                    pass
                return False  # 文件未被锁定
            except IOError:
                time.sleep(0.1)  # 等待0.1秒后重试
        return True  # 文件被锁定超时
    
    def record_operation(self, operation_type, data):
        """记录操作到历史栈"""
        operation = {
            'type': operation_type,
            'data': copy.deepcopy(data),
            'timestamp': time.time()
        }
        
        self.history.append(operation)
        # 限制历史记录数量
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # 清空重做栈（新操作会覆盖重做历史）
        self.redo_stack.clear()
    
    def undo_operation(self):
        """撤销上一次操作"""
        if not self.history:
            return False, "没有可撤销的操作"
        
        # 取出最后一次操作
        operation = self.history.pop()
        self.redo_stack.append(operation)
        
        # 根据操作类型执行相应的撤销逻辑
        if operation['type'] == 'insert_page':
            return self._undo_insert_page(operation['data'])
        elif operation['type'] == 'delete_page':
            return self._undo_delete_page(operation['data'])
        elif operation['type'] == 'rotate_page':
            return self._undo_rotate_page(operation['data'])
        elif operation['type'] == 'insert_pdf_page':
            return self._undo_insert_pdf_page(operation['data'])
        elif operation['type'] == 'insert_image_page':
            return self._undo_insert_image_page(operation['data'])
        else:
            return False, f"不支持撤销操作类型: {operation['type']}"
    
    def redo_operation(self):
        """重做上一次撤销的操作"""
        if not self.redo_stack:
            return False, "没有可重做的操作"
        
        # 取出最后一次撤销的操作
        operation = self.redo_stack.pop()
        self.history.append(operation)
        
        # 根据操作类型执行相应的重做逻辑
        if operation['type'] == 'insert_page':
            return self._redo_insert_page(operation['data'])
        elif operation['type'] == 'delete_page':
            return self._redo_delete_page(operation['data'])
        elif operation['type'] == 'rotate_page':
            return self._redo_rotate_page(operation['data'])
        elif operation['type'] == 'insert_pdf_page':
            return self._redo_insert_pdf_page(operation['data'])
        elif operation['type'] == 'insert_image_page':
            return self._redo_insert_image_page(operation['data'])
        else:
            return False, f"不支持重做操作类型: {operation['type']}"
    
    def _undo_insert_page(self, data):
        """撤销插入页面操作"""
        page_num = data['page_num']
        try:
            # 删除刚刚插入的页面
            self.delete_page(page_num)
            return True, "已撤销插入页面操作"
        except Exception as e:
            return False, f"撤销插入页面失败: {str(e)}"
    
    def _undo_delete_page(self, data):
        """撤销删除页面操作"""
        page_num = data['page_num']
        page_data = data['page_data']
        try:
            # 重新插入被删除的页面数据
            # 这里需要更复杂的实现，因为我们需要恢复页面内容
            return False, "撤销删除页面操作暂未实现"
        except Exception as e:
            return False, f"撤销删除页面失败: {str(e)}"
    
    def _undo_rotate_page(self, data):
        """撤销旋转页面操作"""
        page_num = data['page_num']
        original_rotation = data['original_rotation']
        try:
            # 将页面旋转回原来的角度
            self.rotate_page(page_num, original_rotation)
            return True, "已撤销旋转页面操作"
        except Exception as e:
            return False, f"撤销旋转页面失败: {str(e)}"
    
    def _undo_insert_pdf_page(self, data):
        """撤销插入PDF页面操作"""
        page_num = data['page_num']
        try:
            # 删除刚刚插入的页面
            self.delete_page(page_num)
            return True, "已撤销插入PDF页面操作"
        except Exception as e:
            return False, f"撤销插入PDF页面失败: {str(e)}"
    
    def _undo_insert_image_page(self, data):
        """撤销插入图片页面操作"""
        page_num = data['page_num']
        try:
            # 删除刚刚插入的页面
            self.delete_page(page_num)
            return True, "已撤销插入图片页面操作"
        except Exception as e:
            return False, f"撤销插入图片页面失败: {str(e)}"
    
    def _redo_insert_page(self, data):
        """重做插入页面操作"""
        # 直接重新执行插入操作
        page_num = data['page_num']
        try:
            self.insert_blank_page(page_num)
            return True, "已重做插入页面操作"
        except Exception as e:
            return False, f"重做插入页面失败: {str(e)}"
    
    def _redo_delete_page(self, data):
        """重做删除页面操作"""
        page_num = data['page_num']
        try:
            self.delete_page(page_num)
            return True, "已重做删除页面操作"
        except Exception as e:
            return False, f"重做删除页面失败: {str(e)}"
    
    def _redo_rotate_page(self, data):
        """重做旋转页面操作"""
        page_num = data['page_num']
        new_rotation = data['new_rotation']
        try:
            self.rotate_page(page_num, new_rotation)
            return True, "已重做旋转页面操作"
        except Exception as e:
            return False, f"重做旋转页面失败: {str(e)}"
    
    def _redo_insert_pdf_page(self, data):
        """重做插入PDF页面操作"""
        page_num = data['page_num']
        pdf_path = data['pdf_path']
        try:
            self.insert_pdf_page(page_num, pdf_path)
            return True, "已重做插入PDF页面操作"
        except Exception as e:
            return False, f"重做插入PDF页面失败: {str(e)}"
    
    def _redo_insert_image_page(self, data):
        """重做插入图片页面操作"""
        page_num = data['page_num']
        image_path = data['image_path']
        try:
            self.insert_image_page(page_num, image_path)
            return True, "已重做插入图片页面操作"
        except Exception as e:
            return False, f"重做插入图片页面失败: {str(e)}"
    
    def has_unsaved_changes(self):
        """检查是否有未保存的更改"""
        return self.is_modified
    
    def get_original_filename(self):
        """获取原始文件名"""
        return self.original_file
    
    def create_temp_file(self, original_file):
        """创建临时文件"""
        if self.temp_file and os.path.exists(self.temp_file):
            self.cleanup_temp_file()
        
        self.original_file = original_file
        
        try:
            # 创建临时文件
            temp_fd, self.temp_file = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            
            # 复制原始文件到临时文件
            shutil.copy2(original_file, self.temp_file)
            
            self.is_modified = False
            return True, "临时文件创建成功"
        except Exception as e:
            self.temp_file = None
            self.original_file = None
            return False, f"创建临时文件失败: {str(e)}"
    
    def cleanup_temp_file(self):
        """清理临时文件"""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception as e:
                print(f"删除临时文件失败: {str(e)}")
        self.temp_file = None
        self.original_file = None
        self.is_modified = False
        self.history.clear()
        self.redo_stack.clear()
    
    def _apply_changes(self):
        """将更改应用到原始文件"""
        if not self.temp_file or not self.original_file:
            return False, "临时文件或原始文件路径为空"
        
        if not self.is_modified:
            return True, "没有需要应用的更改"
        
        # 检查原始文件是否被锁定
        if self.is_file_locked(self.original_file):
            return False, "原始文件正在被其他程序使用，请关闭其他程序后再试"
        
        try:
            # 将临时文件复制到原始文件位置
            shutil.copy2(self.temp_file, self.original_file)
            
            # 重新加载PDF文档
            if self.pdf_processor:
                self.pdf_processor.load_pdf(self.original_file)
            
            # 重置状态
            self.is_modified = False
            self.history.clear()
            self.redo_stack.clear()
            
            return True, "更改已应用到原始文件"
        except Exception as e:
            return False, f"应用更改失败: {str(e)}"
    
    def save_changes(self):
        """保存更改到原始文件"""
        if not self.has_unsaved_changes():
            return True, "没有需要保存的更改"
        
        success, message = self._apply_changes()
        if success:
            # 清理临时文件
            self.cleanup_temp_file()
        return success, message
    
    def discard_changes(self):
        """放弃更改"""
        self.cleanup_temp_file()
        # 重新加载原始PDF文档
        if self.pdf_processor and self.original_file:
            self.pdf_processor.load_pdf(self.original_file)
        return True, "已放弃所有更改"
    
    def insert_blank_page(self, page_num):
        """插入空白页"""
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                return False, "没有打开的PDF文件"
            
            # 创建临时文件
            success, message = self.create_temp_file()
            if not success:
                return False, f"创建临时文件失败: {message}"
        
        try:
            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': page_num
            }
            
            # 使用PyPDF2插入空白页
            reader = PdfReader(self.temp_file)
            writer = PdfWriter()
            
            # 复制page_num之前的页面
            for i in range(min(page_num - 1, len(reader.pages))):
                writer.add_page(reader.pages[i])
            
            # 添加空白页（A4大小）
            blank_page = PyPDF2.PageObject.create_blank_page(width=595, height=842)  # A4尺寸
            writer.add_page(blank_page)
            
            # 复制剩余页面
            for i in range(page_num - 1, len(reader.pages)):
                writer.add_page(reader.pages[i])
            
            # 写入临时文件
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            
            # 更新状态
            self.is_modified = True
            
            # 记录操作
            self.record_operation('insert_page', operation_data)
            
            return True, f"已在第{page_num}页后插入空白页"
        except Exception as e:
            return False, f"插入空白页失败: {str(e)}"
    
    def delete_page(self, page_num):
        """删除指定页面"""
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                return False, "没有打开的PDF文件"
            
            # 创建临时文件
            success, message = self.create_temp_file()
            if not success:
                return False, f"创建临时文件失败: {message}"
        
        try:
            # 记录操作前的状态用于撤销
            reader = PdfReader(self.temp_file)
            if page_num < 1 or page_num > len(reader.pages):
                return False, f"页码超出范围：{page_num}"
            
            # 保存被删除页面的数据用于撤销
            operation_data = {
                'page_num': page_num,
                'page_data': reader.pages[page_num - 1]  # 保存页面数据
            }
            
            # 创建新的PDF，排除指定页面
            writer = PdfWriter()
            for i, page in enumerate(reader.pages):
                if i != page_num - 1:  # 跳过要删除的页面
                    writer.add_page(page)
            
            # 写入临时文件
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            
            # 更新状态
            self.is_modified = True
            
            # 记录操作
            self.record_operation('delete_page', operation_data)
            
            return True, f"已删除第{page_num}页"
        except Exception as e:
            return False, f"删除页面失败: {str(e)}"
    
    def rotate_page(self, page_num, rotation):
        """旋转页面"""
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                return False, "没有打开的PDF文件"
            
            # 创建临时文件
            success, message = self.create_temp_file()
            if not success:
                return False, f"创建临时文件失败: {message}"
        
        try:
            # 记录操作前的状态用于撤销
            reader = PdfReader(self.temp_file)
            if page_num < 1 or page_num > len(reader.pages):
                return False, f"页码超出范围：{page_num}"
            
            original_rotation = reader.pages[page_num - 1].get("/Rotate", 0)
            operation_data = {
                'page_num': page_num,
                'original_rotation': original_rotation,
                'new_rotation': rotation
            }
            
            # 旋转指定页面
            reader.pages[page_num - 1].rotate(rotation)
            
            # 写入临时文件
            with open(self.temp_file, 'wb') as output_file:
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                writer.write(output_file)
            
            # 更新状态
            self.is_modified = True
            
            # 记录操作
            self.record_operation('rotate_page', operation_data)
            
            return True, f"已将第{page_num}页旋转{rotation}度"
        except Exception as e:
            return False, f"旋转页面失败: {str(e)}"
    
    def insert_pdf_page(self, page_num, pdf_path):
        """插入PDF页面"""
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                return False, "没有打开的PDF文件"
            
            # 创建临时文件
            success, message = self.create_temp_file()
            if not success:
                return False, f"创建临时文件失败: {message}"
        
        try:
            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': page_num,
                'pdf_path': pdf_path
            }
            
            # 使用PyPDF2插入PDF页面
            original_reader = PdfReader(self.temp_file)
            insert_reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            # 复制page_num之前的页面
            for i in range(min(page_num - 1, len(original_reader.pages))):
                writer.add_page(original_reader.pages[i])
            
            # 添加要插入的PDF页面
            for insert_page in insert_reader.pages:
                writer.add_page(insert_page)
            
            # 复制剩余页面
            for i in range(page_num - 1, len(original_reader.pages)):
                writer.add_page(original_reader.pages[i])
            
            # 写入临时文件
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            
            # 更新状态
            self.is_modified = True
            
            # 记录操作
            self.record_operation('insert_pdf_page', operation_data)
            
            return True, f"已从{os.path.basename(pdf_path)}插入{len(insert_reader.pages)}页"
        except Exception as e:
            return False, f"插入PDF页面失败: {str(e)}"
    
    def insert_image_page(self, page_num, image_path):
        """插入图片页面"""
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                return False, "没有打开的PDF文件"
            
            # 创建临时文件
            success, message = self.create_temp_file()
            if not success:
                return False, f"创建临时文件失败: {message}"
        
        try:
            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': page_num,
                'image_path': image_path
            }
            
            # 使用PyPDF2和PIL将图片转换为PDF页面
            original_reader = PdfReader(self.temp_file)
            writer = PdfWriter()
            
            # 复制page_num之前的页面
            for i in range(min(page_num - 1, len(original_reader.pages))):
                writer.add_page(original_reader.pages[i])
            
            # 将图片转换为PDF页面
            try:
                image = Image.open(image_path)
                # 转换为RGB模式（如果需要）
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                
                # 创建临时PDF文件来保存图片
                temp_pdf_fd, temp_pdf_path = tempfile.mkstemp(suffix='.pdf')
                image.save(temp_pdf_path, "PDF", resolution=100.0)
                os.close(temp_pdf_fd)
                
                # 读取临时PDF文件并添加页面
                image_reader = PdfReader(temp_pdf_path)
                for image_page in image_reader.pages:
                    writer.add_page(image_page)
                
                # 删除临时PDF文件
                os.unlink(temp_pdf_path)
            except Exception as e:
                return False, f"图片转换失败: {str(e)}"
            
            # 复制剩余页面
            for i in range(page_num - 1, len(original_reader.pages)):
                writer.add_page(original_reader.pages[i])
            
            # 写入临时文件
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            
            # 更新状态
            self.is_modified = True
            
            # 记录操作
            self.record_operation('insert_image_page', operation_data)
            
            return True, f"已从{os.path.basename(image_path)}插入图片页面"
        except Exception as e:
            return False, f"插入图片页面失败: {str(e)}"
    
    def extract_pages(self, page_nums, output_path):
        """提取指定页面到新文件"""
        try:
            if not self.pdf_processor.fitz_document:
                return False, "请先打开PDF文件"
            
            # 获取当前PDF文件路径
            if not self.pdf_processor.current_file:
                return False, "无法获取当前PDF文件路径"
            
            current_file = self.pdf_processor.current_file
            
            # 使用PyPDF2提取页面
            reader = PdfReader(current_file)
            writer = PdfWriter()
            
            # 添加指定页面到新文件
            for page_num in page_nums:
                if 1 <= page_num <= len(reader.pages):
                    writer.add_page(reader.pages[page_num - 1])  # page_num从1开始，索引从0开始
            
            # 保存到输出文件
            try:
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                return True, f"已成功提取 {len(page_nums)} 页到 {os.path.basename(output_path)}"
            except Exception as e:
                return False, f"保存提取页面失败: {str(e)}"
                
        except Exception as e:
            return False, f"提取页面失败: {str(e)}"