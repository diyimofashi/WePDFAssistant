"""页面编辑功能模块
提供PDF页面的插入、删除、复制、旋转等编辑功能"""

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, QObject, pyqtSignal
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
import logging

logger = logging.getLogger(__name__)

class PageEditor(QObject):
    """PDF页面编辑器"""
    
    # 定义状态变化信号
    state_changed = pyqtSignal()
    
    def __init__(self, pdf_processor):
        super().__init__()
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
        logger.debug(f"开始撤销操作，当前历史记录数量: {len(self.history)}")
        if not self.history:
            logger.debug("没有可撤销的操作")
            return False, "没有可撤销的操作"
        
        # 取出最后一次操作
        operation = self.history.pop()
        self.redo_stack.append(operation)
        logger.debug(f"取出操作: {operation['type']}")
        
        # 根据操作类型执行相应的撤销逻辑
        if operation['type'] == 'insert_page':
            logger.debug("执行插入页面的撤销操作")
            result = self._undo_insert_page(operation['data'])
            logger.debug(f"撤销结果: {result}")
        elif operation['type'] == 'delete_page':
            logger.debug("执行删除页面的撤销操作")
            result = self._undo_delete_page(operation['data'])
            logger.debug(f"撤销结果: {result}")
        elif operation['type'] == 'rotate_page':
            logger.debug("执行旋转页面的撤销操作")
            result = self._undo_rotate_page(operation['data'])
            logger.debug(f"撤销结果: {result}")
        elif operation['type'] == 'insert_pdf_page':
            logger.debug("执行插入PDF页面的撤销操作")
            result = self._undo_insert_pdf_page(operation['data'])
            logger.debug(f"撤销结果: {result}")
        elif operation['type'] == 'insert_image_page':
            logger.debug("执行插入图片页面的撤销操作")
            result = self._undo_insert_image_page(operation['data'])
            logger.debug(f"撤销结果: {result}")
        else:
            logger.debug(f"不支持的撤销操作类型: {operation['type']}")
            result = (False, f"不支持撤销操作类型: {operation['type']}")
        
        # 如果撤销成功，更新状态
        success, message = result
        if success:
            self.is_modified = True
            # 发出状态变化信号
            self._emit_state_changed()
            logger.debug("撤销操作成功，状态已更新")
        
        return result
    
    def redo_operation(self):
        """重做上一次撤销的操作"""
        if not self.redo_stack:
            return False, "没有可重做的操作"
        
        # 取出最后一次撤销的操作
        operation = self.redo_stack.pop()
        self.history.append(operation)
        
        # 根据操作类型执行相应的重做逻辑
        if operation['type'] == 'insert_page':
            result = self._redo_insert_page(operation['data'])
        elif operation['type'] == 'delete_page':
            result = self._redo_delete_page(operation['data'])
        elif operation['type'] == 'rotate_page':
            result = self._redo_rotate_page(operation['data'])
        elif operation['type'] == 'insert_pdf_page':
            result = self._redo_insert_pdf_page(operation['data'])
        elif operation['type'] == 'insert_image_page':
            result = self._redo_insert_image_page(operation['data'])
        else:
            result = (False, f"不支持重做操作类型: {operation['type']}")
        
        # 如果重做成功，更新状态
        success, message = result
        if success:
            self.is_modified = True
            # 发出状态变化信号
            self._emit_state_changed()
            logger.debug("重做操作成功，状态已更新")
        
        return result
    
    def _undo_insert_page(self, data):
        """撤销插入页面操作"""
        page_num = data['page_num']
        logger.debug(f"开始撤销插入页面操作，页码: {page_num}")
        try:
            # 删除刚刚插入的页面
            logger.debug("调用delete_page方法删除页面")
            result = self.delete_page(page_num)
            logger.debug(f"删除页面结果: {result}")
            return True, "已撤销插入页面操作"
        except Exception as e:
            logger.error(f"撤销插入页面失败: {str(e)}")
            return False, f"撤销插入页面失败: {str(e)}"
    
    def _undo_delete_page(self, data):
        """撤销删除页面操作"""
        page_num = data['page_num']
        try:
            logger.debug(f"开始撤销删除页面操作，页码: {page_num}")
            
            # 如果还没有临时文件，自动创建一个
            if not self.temp_file:
                if not self.original_file:
                    return False, "没有打开的PDF文件"
                
                success, message = self.create_temp_file()
                if not success:
                    return False, f"创建临时文件失败: {message}"
            
            # 使用PyPDF2恢复被删除的页面
            reader = PdfReader(self.temp_file)
            writer = PdfWriter()
            
            # 复制到插入位置前的所有页面
            for i in range(page_num - 1):
                if i < len(reader.pages):
                    writer.add_page(reader.pages[i])
            
            # 插入被删除的页面数据
            if 'page_data' in data and data['page_data']:
                writer.add_page(data['page_data'])
            else:
                # 如果没有页面数据，插入空白页作为替代
                blank_page = PyPDF2.PageObject.create_blank_page(width=595, height=842)
                writer.add_page(blank_page)
            
            # 复制剩余页面
            for i in range(page_num - 1, len(reader.pages)):
                writer.add_page(reader.pages[i])
            
            # 写入临时文件
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            
            # 通知PDF处理器加载临时文件
            if self.pdf_processor:
                original_current_file = self.pdf_processor.current_file
                self.pdf_processor.load_pdf(self.temp_file)
                if self.original_file:
                    self.pdf_processor.current_file = self.original_file
            
            logger.debug("撤销删除页面操作成功")
            return True, "已撤销删除页面操作"
        except Exception as e:
            logger.error(f"撤销删除页面失败: {str(e)}")
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
        logger.debug(f"检查是否有未保存的更改: is_modified={self.is_modified}, temp_file={self.temp_file}, original_file={self.original_file}")
        return self.is_modified
    
    def can_undo(self):
        """检查是否可以撤销操作"""
        return len(self.history) > 0
    
    def can_redo(self):
        """检查是否可以重做操作"""
        return len(self.redo_stack) > 0
    
    def get_original_filename(self):
        """获取原始文件名"""
        return self.original_file
    
    def _emit_state_changed(self):
        """发出状态变化信号"""
        logger.debug("发出状态变化信号")
        self.state_changed.emit()
    
    def create_temp_file(self, original_file=None):
        """创建临时文件"""
        if self.temp_file and os.path.exists(self.temp_file):
            self.cleanup_temp_file()
        
        # 如果没有提供original_file，则从PDF处理器获取
        if original_file is None and self.pdf_processor:
            original_file = self.pdf_processor.current_file
            
        # 检查是否有有效的原始文件
        if not original_file:
            return False, "没有打开的PDF文件"
            
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
        """在指定页码后插入空白页"""
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                # 检查是否有打开的PDF文件
                if not self.pdf_processor or not self.pdf_processor.current_file:
                    return False, "没有打开的PDF文件"
            
            # 创建临时文件
            success, message = self.create_temp_file()
            if not success:
                return False, f"创建临时文件失败: {message}"
        
        try:
            # 调整页码：在指定页码后插入（用户界面页码从1开始）
            insert_position = page_num
            
            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': insert_position
            }
            
            # 使用PyPDF2插入空白页
            reader = PdfReader(self.temp_file)
            writer = PdfWriter()
            
            # 复制insert_position之前的页面
            for i in range(min(insert_position, len(reader.pages))):
                writer.add_page(reader.pages[i])
            
            # 添加空白页（A4大小）
            blank_page = PyPDF2.PageObject.create_blank_page(width=595, height=842)  # A4尺寸
            writer.add_page(blank_page)
            
            # 复制剩余页面
            for i in range(insert_position, len(reader.pages)):
                writer.add_page(reader.pages[i])
            
            # 写入临时文件
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            
            # 更新状态
            self.is_modified = True
            
            # 记录操作
            self.record_operation('insert_page', operation_data)
            logger.debug(f"记录操作完成，当前历史记录数量: {len(self.history)}")
            
            # 通知PDF处理器加载临时文件以显示编辑效果，但保持原始文件引用
            if self.pdf_processor:
                # 保存当前的原始文件引用
                original_current_file = self.pdf_processor.current_file
                # 加载临时文件
                self.pdf_processor.load_pdf(self.temp_file)
                # 恢复原始文件引用，确保关闭时能正确检测到未保存的更改
                if self.original_file:
                    self.pdf_processor.current_file = self.original_file
            
            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()
            
            logger.debug(f"插入空白页完成，can_undo结果: {self.can_undo()}")
            return True, f"已在第{page_num}页后插入空白页"
        except Exception as e:
            return False, f"插入空白页失败: {str(e)}"
    
    def delete_page(self, page_num):
        """删除指定页面"""
        logger.debug(f"开始删除页面，页码: {page_num}")
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            logger.debug("没有临时文件，尝试创建")
            if not self.original_file:
                # 检查是否有打开的PDF文件
                if not self.pdf_processor or not self.pdf_processor.current_file:
                    logger.debug("没有打开的PDF文件")
                    return False, "没有打开的PDF文件"
            
            # 创建临时文件
            logger.debug("创建临时文件")
            success, message = self.create_temp_file()
            if not success:
                logger.debug(f"创建临时文件失败: {message}")
                return False, f"创建临时文件失败: {message}"
        
        try:
            logger.debug("开始执行删除操作")
            # 记录操作前的状态用于撤销
            reader = PdfReader(self.temp_file)
            if page_num < 1 or page_num > len(reader.pages):
                logger.debug(f"页码超出范围：{page_num}")
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
            logger.debug("写入临时文件")
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            
            # 更新状态
            self.is_modified = True
            
            # 记录操作
            self.record_operation('delete_page', operation_data)
            
            # 通知PDF处理器加载临时文件以显示编辑效果，但保持原始文件引用
            if self.pdf_processor:
                logger.debug("通知PDF处理器加载临时文件")
                # 保存当前的原始文件引用
                original_current_file = self.pdf_processor.current_file
                # 加载临时文件
                self.pdf_processor.load_pdf(self.temp_file)
                # 恢复原始文件引用，确保关闭时能正确检测到未保存的更改
                if self.original_file:
                    self.pdf_processor.current_file = self.original_file
            
            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()
            
            logger.debug(f"删除成功，页码: {page_num}")
            return True, f"已删除第{page_num}页"
        except Exception as e:
            logger.error(f"删除页面失败: {str(e)}")
            return False, f"删除页面失败: {str(e)}"
    
    def rotate_page(self, page_num, rotation):
        """旋转页面"""
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                # 检查是否有打开的PDF文件
                if not self.pdf_processor or not self.pdf_processor.current_file:
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
            
            # 通知PDF处理器加载临时文件以显示编辑效果，但保持原始文件引用
            if self.pdf_processor:
                # 保存当前的原始文件引用
                original_current_file = self.pdf_processor.current_file
                # 加载临时文件
                self.pdf_processor.load_pdf(self.temp_file)
                # 恢复原始文件引用，确保关闭时能正确检测到未保存的更改
                if self.original_file:
                    self.pdf_processor.current_file = self.original_file
            
            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()
            
            return True, f"已将第{page_num}页旋转{rotation}度"
        except Exception as e:
            return False, f"旋转页面失败: {str(e)}"
    
    def insert_pdf_page(self, page_num, pdf_path):
        """在指定页码后插入PDF页面"""
        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                # 检查是否有打开的PDF文件
                if not self.pdf_processor or not self.pdf_processor.current_file:
                    return False, "没有打开的PDF文件"
            
            # 创建临时文件
            success, message = self.create_temp_file()
            if not success:
                return False, f"创建临时文件失败: {message}"
        
        try:
            # 调整页码：在指定页码后插入（用户界面页码从1开始）
            insert_position = page_num
            
            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': insert_position,
                'pdf_path': pdf_path
            }
            
            # 使用PyPDF2插入PDF页面
            original_reader = PdfReader(self.temp_file)
            insert_reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            # 复制insert_position之前的页面
            for i in range(min(insert_position, len(original_reader.pages))):
                writer.add_page(original_reader.pages[i])
            
            # 添加要插入的PDF页面
            for insert_page in insert_reader.pages:
                writer.add_page(insert_page)
            
            # 复制剩余页面
            for i in range(insert_position, len(original_reader.pages)):
                writer.add_page(original_reader.pages[i])
            
            # 写入临时文件
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            
            # 更新状态
            self.is_modified = True
            
            # 记录操作
            self.record_operation('insert_pdf_page', operation_data)
            
            # 通知PDF处理器加载临时文件以显示编辑效果，但保持原始文件引用
            if self.pdf_processor:
                # 保存当前的原始文件引用
                original_current_file = self.pdf_processor.current_file
                # 加载临时文件
                self.pdf_processor.load_pdf(self.temp_file)
                # 恢复原始文件引用，确保关闭时能正确检测到未保存的更改
                if self.original_file:
                    self.pdf_processor.current_file = self.original_file
            
            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()
            
            return True, f"已从{os.path.basename(pdf_path)}插入{len(insert_reader.pages)}页"
        except Exception as e:
            return False, f"插入PDF页面失败: {str(e)}"
    
    def insert_image_page(self, page_num, image_path):
        """在指定页码后插入图片页面"""
        logger.info(f"开始插入图片，page_num={page_num}, image_path={image_path}")
        logger.debug(f"temp_file={self.temp_file}, original_file={self.original_file}")

        # 如果还没有临时文件，自动创建一个
        if not self.temp_file:
            if not self.original_file:
                # 检查是否有打开的PDF文件
                if not self.pdf_processor or not self.pdf_processor.current_file:
                    logger.error("没有打开的PDF文件")
                    return False, "没有打开的PDF文件"

            # 创建临时文件
            logger.info("创建临时文件")
            success, message = self.create_temp_file()
            if not success:
                logger.error(f"创建临时文件失败: {message}")
                return False, f"创建临时文件失败: {message}"
            logger.debug(f"临时文件创建成功: {self.temp_file}")

        try:
            # 调整页码：在指定页码后插入（用户界面页码从1开始）
            insert_position = page_num
            logger.debug(f"插入位置: {insert_position}")

            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': insert_position,
                'image_path': image_path
            }

            # 使用PyPDF2插入图片页面
            logger.debug("读取临时文件")
            original_reader = PdfReader(self.temp_file)
            writer = PdfWriter()

            logger.debug(f"原始文件页数: {len(original_reader.pages)}")

            # 复制insert_position之前的页面
            logger.debug(f"复制前{insert_position}页")
            for i in range(min(insert_position, len(original_reader.pages))):
                writer.add_page(original_reader.pages[i])

            # 将图片转换为PDF页面
            try:
                logger.debug(f"打开图片文件: {image_path}")
                image = Image.open(image_path)

                # 获取图片尺寸（转换为点，72 DPI）
                img_width, img_height = image.size
                logger.debug(f"图片尺寸: {img_width}x{img_height}")

                # 转换为RGB模式（如果需要）
                if image.mode in ('RGBA', 'LA', 'P'):
                    # 创建白色背景
                    background = Image.new('RGB', (img_width, img_height), (255,255,255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                    image = background
                    logger.debug("图片已转换为RGB模式（带白色背景）")
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                    logger.debug("图片已转换为RGB模式")

                # 计算合适的PDF页面尺寸（A4是595x842点）
                # 如果图片太大，按比例缩放到A4尺寸内
                a4_width, a4_height = 595, 842
                scale = min(a4_width / img_width, a4_height / img_height)
                if scale < 1:
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    image = image.resize((new_width, new_height), Resampling.LANCZOS)
                    img_width, img_height = new_width, new_height
                    logger.debug(f"图片已缩放到: {img_width}x{img_height}")

                # 将图片绘制到PDF页面上
                # 使用fitz来创建包含图片的PDF页面
                logger.debug("使用fitz创建图片PDF页面")
                img_doc = fitz.open()
                img_page = img_doc.new_page(width=img_width, height=img_height)
                img_rect = fitz.Rect(0, 0, img_width, img_height)

                # 将图片数据转换为字节
                from io import BytesIO
                img_bytes = BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes.seek(0)

                # 插入图片到页面
                img_page.insert_image(img_rect, stream=img_bytes.read())
                logger.debug("图片已插入到fitz页面")

                # 将fitz页面转换为PyPDF2页面
                # 创建临时文件
                logger.debug("创建临时PDF文件")
                temp_pdf_fd, temp_pdf_path = tempfile.mkstemp(suffix='.pdf')
                os.close(temp_pdf_fd)

                # 保存图片为PDF
                img_doc.save(temp_pdf_path)
                logger.debug(f"图片PDF已保存到: {temp_pdf_path}")
                
                # 读取临时PDF并添加页面
                image_reader = PdfReader(temp_pdf_path)
                for image_page in image_reader.pages:
                    writer.add_page(image_page)
                logger.debug("图片页面已添加到writer")

                # 删除临时PDF文件
                os.unlink(temp_pdf_path)
                logger.debug("临时PDF文件已删除")

            except Exception as e:
                import traceback
                logger.error(f"图片转换失败: {str(e)}\n{traceback.format_exc()}")
                return False, f"图片转换失败: {str(e)}"

            # 复制剩余页面
            logger.debug(f"复制剩余页面，从{insert_position}开始")
            for i in range(insert_position, len(original_reader.pages)):
                writer.add_page(original_reader.pages[i])

            # 写入临时文件
            logger.debug("写入临时文件")
            with open(self.temp_file, 'wb') as output_file:
                writer.write(output_file)
            logger.debug("临时文件写入成功")

            # 更新状态
            self.is_modified = True

            # 记录操作
            self.record_operation('insert_image_page', operation_data)

            # 通知PDF处理器加载临时文件以显示编辑效果，但保持原始文件引用
            if self.pdf_processor:
                logger.debug("通知PDF处理器加载临时文件")
                # 保存当前的原始文件引用
                original_current_file = self.pdf_processor.current_file
                # 加载临时文件
                self.pdf_processor.load_pdf(self.temp_file)
                # 恢复原始文件引用，确保关闭时能正确检测到未保存的更改
                if self.original_file:
                    self.pdf_processor.current_file = self.original_file
                logger.debug("PDF处理器已加载临时文件")

            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()

            logger.info(f"图片插入成功: {os.path.basename(image_path)}")
            return True, f"已从{os.path.basename(image_path)}插入图片页面"
        except Exception as e:
            import traceback
            logger.error(f"插入图片页面失败: {str(e)}\n{traceback.format_exc()}")
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