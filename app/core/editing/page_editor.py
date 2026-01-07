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
                # 使用open_pdf加载临时文件（不要改回original_file）
                self.pdf_processor.open_pdf(self.temp_file, async_mode=False)
            
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
        """创建临时文件

        注意：此方法仅在第一次编辑时调用，后续编辑应该继续在现有的 temp_file 上操作
        """
        logger.info(f"[create_temp_file] 开始创建临时文件，当前temp_file={self.temp_file}, original_file={self.original_file}, 参数original_file={original_file}")

        # 如果已经有临时文件，不需要重新创建
        if self.temp_file and os.path.exists(self.temp_file):
            logger.info(f"[create_temp_file] 临时文件已存在: {self.temp_file}，无需重新创建")
            return True, "临时文件已存在"

        # 如果没有提供original_file，则从PDF处理器获取
        if original_file is None and self.pdf_processor:
            original_file = self.pdf_processor.current_file
            logger.info(f"[create_temp_file] 从pdf_processor获取current_file: {original_file}")

        # 检查是否有有效的原始文件
        if not original_file:
            return False, "没有打开的PDF文件"

        self.original_file = original_file
        logger.info(f"[create_temp_file] 设置original_file为: {self.original_file}")

        try:
            # 创建临时文件
            temp_fd, self.temp_file = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)

            logger.info(f"[create_temp_file] 创建新临时文件: {self.temp_file}")

            # 复制原始文件到临时文件
            shutil.copy2(original_file, self.temp_file)
            logger.info(f"[create_temp_file] 已从{original_file}复制到临时文件")

            self.is_modified = False
            return True, "临时文件创建成功"
        except Exception as e:
            logger.error(f"[create_temp_file] 创建临时文件失败: {str(e)}")
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
        if not self.pdf_processor or not self.pdf_processor.current_file:
            return False, "没有打开的PDF文件"

        if not self.pdf_processor.fitz_document:
            return False, "PDF文档未加载"

        if not self.is_modified:
            return True, "没有需要应用的更改"

        # 检查原始文件是否被锁定
        if self.is_file_locked(self.pdf_processor.current_file):
            return False, "原始文件正在被其他程序使用，请关闭其他程序后再试"

        try:
            logger.info(f"开始保存更改: current_file={self.pdf_processor.current_file}")

            # 将 fitz_document 保存到原始文件[先保存到临时文件，然后再替换原始文件]
            tmp_path = str(self.pdf_processor.current_file) + '.tmp'
            self.pdf_processor.fitz_document.save(tmp_path)          # 整文件重写
            shutil.move(tmp_path, self.pdf_processor.current_file)   # 原子覆盖
            logger.info(f"文档已保存到: {self.pdf_processor.current_file}")

            # 重置状态
            self.is_modified = False
            self.history.clear()
            self.redo_stack.clear()

            return True, "更改已保存到原始文件"
        except Exception as e:
            logger.error(f"应用更改失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"保存失败: {str(e)}"

    def save_changes(self):
        """保存更改到原始文件"""
        if not self.has_unsaved_changes():
            return True, "没有需要保存的更改"

        success, message = self._apply_changes()
        if success:
            # 清理临时文件（如果有）
            self.cleanup_temp_file()
        return success, message
    
    def discard_changes(self):
        """放弃更改"""
        if not self.pdf_processor or not self.pdf_processor.current_file:
            return False, "没有打开的PDF文件"

        # 重新加载原始PDF文档，恢复到保存时的状态
        logger.info(f"放弃更改，重新加载原始文件: {self.pdf_processor.current_file}")
        self.pdf_processor.load_pdf(self.pdf_processor.current_file)

        # 重置状态
        self.is_modified = False
        self.history.clear()
        self.redo_stack.clear()

        # 清理临时文件（如果有）
        self.cleanup_temp_file()

        return True, "已放弃所有更改"
    
    def insert_blank_page(self, page_num):
        """在指定页码后插入空白页"""
        logger.info(f"[insert_blank_page] 开始插入空白页，page_num(1-based)={page_num}")

        try:
            # 调整页码：在指定页码后插入（用户界面页码从1开始）
            # insert_position 是 0-based，表示在第几页后插入
            insert_position = page_num

            logger.info(f"[insert_blank_page] 插入位置(0-based): {insert_position}")

            # 检查PDF文档是否存在
            if not self.pdf_processor or not self.pdf_processor.fitz_document:
                return False, "没有打开的PDF文件"

            # 获取当前总页数
            total_pages = len(self.pdf_processor.fitz_document)
            logger.info(f"[insert_blank_page] 当前文档总页数: {total_pages}")

            if insert_position < 0 or insert_position > total_pages:
                return False, f"页码超出范围：{page_num}"

            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': page_num
            }

            # 使用fitz在指定位置插入空白页（A4大小）
            new_page = self.pdf_processor.fitz_document.new_page(insert_position, width=595, height=842)
            logger.info(f"[insert_blank_page] 新建空白页，文档总页数: {len(self.pdf_processor.fitz_document)}")

            # 更新状态
            self.is_modified = True

            # 记录操作
            self.record_operation('insert_page', operation_data)

            # 清除渲染缓存
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()

            # 注意：这里不立即保存到原始文件，只标记为已修改
            # 用户点击保存时才会写入原始文件
            logger.info(f"[insert_blank_page] 文档已在内存中修改，等待用户保存")

            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()

            logger.info(f"[insert_blank_page] 插入空白页成功")
            return True, f"已在第{page_num}页后插入空白页"
        except Exception as e:
            logger.error(f"插入空白页失败: {str(e)}")
            import traceback
            logger.error(f"插入空白页失败，堆栈信息: {traceback.format_exc()}")
            return False, f"插入空白页失败: {str(e)}"
    
    def delete_page(self, page_num):
        """删除指定页面"""
        logger.info(f"[delete_page] 开始删除页面，page_num(1-based)={page_num}")

        try:
            # 检查PDF文档是否存在
            if not self.pdf_processor or not self.pdf_processor.fitz_document:
                return False, "没有打开的PDF文件"

            # 获取当前总页数
            total_pages_before = len(self.pdf_processor.fitz_document)
            logger.info(f"[delete_page] 删除前 - 页码(1-based): {page_num}, 总页数: {total_pages_before}")

            if page_num < 1 or page_num > total_pages_before:
                return False, f"页码超出范围：{page_num}"

            # 计算要删除的页面索引（0-based）
            page_index_to_delete = page_num - 1

            # 保存被删除页面的数据用于撤销
            operation_data = {
                'page_num': page_num
                # 注意：由于fitz页面对象引用在删除后会失效，这里不保存page_data
                # 撤销时需要重新构建页面或使用其他方法
            }

            logger.info(f"[delete_page] 准备删除页面索引: {page_index_to_delete}")

            # 使用fitz删除指定页面
            self.pdf_processor.fitz_document.delete_page(page_index_to_delete)

            total_pages_after = len(self.pdf_processor.fitz_document)
            logger.info(f"[delete_page] 删除后 - 文档总页数: {total_pages_after}")

            # 更新状态
            self.is_modified = True

            # 记录操作
            self.record_operation('delete_page', operation_data)

            # 清除渲染缓存
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()

            # 确定删除页面后应该跳转到的页面
            if page_num == total_pages_before:
                target_page_index = total_pages_after - 1 if total_pages_after > 0 else 0
            else:
                target_page_index = page_num - 1

            logger.info(f"[delete_page] 目标页码(0-based): {target_page_index}")

            # 设置到正确的页面位置
            if target_page_index >= 0 and target_page_index < total_pages_after:
                self.pdf_processor.current_page = target_page_index
            elif total_pages_after > 0:
                self.pdf_processor.current_page = 0

            logger.info(f"[delete_page] current_page: {self.pdf_processor.current_page}")

            # 注意：这里不立即保存到原始文件，只标记为已修改
            # 用户点击保存时才会写入原始文件
            logger.info(f"[delete_page] 文档已在内存中修改，等待用户保存")

            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()

            logger.info(f"[delete_page] 删除成功 - 页码(1-based): {page_num}")
            return True, f"已删除第{page_num}页"
        except Exception as e:
            logger.error(f"删除页面失败: {str(e)}")
            import traceback
            logger.error(f"删除页面失败，堆栈信息: {traceback.format_exc()}")
            return False, f"删除页面失败: {str(e)}"
    
    def rotate_page(self, page_num, rotation):
        """旋转页面"""
        logger.info(f"[rotate_page] 开始旋转页面，page_num(1-based)={page_num}, rotation={rotation}")

        try:
            # 检查PDF文档是否存在
            if not self.pdf_processor or not self.pdf_processor.fitz_document:
                return False, "没有打开的PDF文件"

            # 获取当前总页数
            total_pages = len(self.pdf_processor.fitz_document)

            if page_num < 1 or page_num > total_pages:
                return False, f"页码超出范围：{page_num}"

            # 计算页面索引（0-based）
            page_index = page_num - 1

            # 获取当前旋转角度
            page = self.pdf_processor.fitz_document[page_index]
            current_rotation = page.rotation
            logger.info(f"[rotate_page] 页面当前旋转角度: {current_rotation}")

            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': page_num,
                'original_rotation': current_rotation,
                'new_rotation': rotation
            }

            # 旋转页面
            page.set_rotation(current_rotation + rotation)
            logger.info(f"[rotate_page] 旋转后角度: {page.rotation}")

            # 更新状态
            self.is_modified = True

            # 记录操作
            self.record_operation('rotate_page', operation_data)

            # 清除渲染缓存
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()

            # 注意：这里不立即保存到原始文件，只标记为已修改
            # 用户点击保存时才会写入原始文件
            logger.info(f"[rotate_page] 文档已在内存中修改，等待用户保存")

            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()

            logger.info(f"[rotate_page] 旋转成功")
            return True, f"已将第{page_num}页旋转{rotation}度"
        except Exception as e:
            logger.error(f"旋转页面失败: {str(e)}")
            import traceback
            logger.error(f"旋转页面失败，堆栈信息: {traceback.format_exc()}")
            return False, f"旋转页面失败: {str(e)}"
    
    def insert_pdf_page(self, page_num, pdf_path):
        """在指定页码后插入PDF页面"""
        logger.info(f"[insert_pdf_page] 开始插入PDF页面，page_num(1-based)={page_num}, pdf_path={pdf_path}")

        try:
            # 检查PDF文档是否存在
            if not self.pdf_processor or not self.pdf_processor.fitz_document:
                return False, "没有打开的PDF文件"

            # 检查要插入的PDF文件是否存在
            if not os.path.exists(pdf_path):
                return False, f"PDF文件不存在：{pdf_path}"

            # 调整页码：在指定页码后插入（用户界面页码从1开始）
            # insert_position 是 0-based，表示在第几页后插入
            insert_position = page_num
            logger.info(f"[insert_pdf_page] 插入位置(0-based): {insert_position}")

            # 获取当前总页数
            total_pages = len(self.pdf_processor.fitz_document)
            logger.info(f"[insert_pdf_page] 当前文档总页数: {total_pages}")

            if insert_position < 0 or insert_position > total_pages:
                return False, f"页码超出范围：{page_num}"

            # 打开要插入的PDF文档
            insert_doc = fitz.open(pdf_path)
            insert_pages_count = len(insert_doc)
            logger.info(f"[insert_pdf_page] 要插入的PDF页数: {insert_pages_count}")

            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': page_num,
                'pdf_path': pdf_path
            }

            # 逐页插入
            for i in range(insert_pages_count):
                # 从插入的PDF中复制页面
                page_to_insert = insert_doc[i]

                # 在指定位置插入新页面
                new_page = self.pdf_processor.fitz_document.new_page(insert_position + i)
                new_page.show_pdf_page(new_page.rect, page_to_insert, keep_proportion=True)

                logger.info(f"[insert_pdf_page] 插入第{i+1}页，当前文档总页数: {len(self.pdf_processor.fitz_document)}")

            # 关闭插入的PDF文档
            insert_doc.close()

            # 更新状态
            self.is_modified = True

            # 记录操作
            self.record_operation('insert_pdf_page', operation_data)

            # 清除渲染缓存
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()

            # 注意：这里不立即保存到原始文件，只标记为已修改
            # 用户点击保存时才会写入原始文件
            logger.info(f"[insert_pdf_page] 文档已在内存中修改，等待用户保存")

            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()

            logger.info(f"[insert_pdf_page] 插入成功，共插入{insert_pages_count}页")
            return True, f"已从{os.path.basename(pdf_path)}插入{insert_pages_count}页"
        except Exception as e:
            logger.error(f"插入PDF页面失败: {str(e)}")
            import traceback
            logger.error(f"插入PDF页面失败，堆栈信息: {traceback.format_exc()}")
            return False, f"插入PDF页面失败: {str(e)}"
    
    def insert_image_page(self, page_num, image_path):
        """在指定页码后插入图片页面"""
        logger.info(f"[insert_image_page] 开始插入图片，page_num(1-based)={page_num}")

        try:
            # 检查PDF文档是否存在
            if not self.pdf_processor or not self.pdf_processor.fitz_document:
                return False, "没有打开的PDF文件"

            # 调整页码：在指定页码后插入（用户界面页码从1开始）
            # insert_position 是 0-based，表示在第几页后插入
            insert_position = page_num
            logger.info(f"[insert_image_page] 插入位置(0-based): {insert_position}")

            # 获取当前总页数
            total_pages = len(self.pdf_processor.fitz_document)
            logger.info(f"[insert_image_page] 当前文档总页数: {total_pages}")

            if insert_position < 0 or insert_position > total_pages:
                return False, f"页码超出范围：{page_num}"

            # 记录操作前的状态用于撤销
            operation_data = {
                'page_num': page_num,
                'image_path': image_path
            }

            # 打开图片
            try:
                image = Image.open(image_path)

                # 获取图片尺寸
                img_width, img_height = image.size
                logger.info(f"[insert_image_page] 图片尺寸: {img_width}x{img_height}")

                # 转换为RGB模式（如果需要）
                if image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', (img_width, img_height), (255,255,255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')

                # 使用标准PDF页面尺寸（A4纸张，72 DPI单位的点）
                page_width, page_height = 595, 842  # A4尺寸（点）
                
                # 设置页面边距（左右各50点，上下各50点）
                margin_x = 50
                margin_y = 50
                available_width = page_width - 2 * margin_x
                available_height = page_height - 2 * margin_y
                
                # 计算图片缩放比例，保持宽高比，确保图片在页面边距内
                scale = min(available_width / img_width, available_height / img_height)
                new_img_width = int(img_width * scale)
                new_img_height = int(img_height * scale)
                
                # 如果图片比可用空间大，需要缩放；如果比可用空间小，保持原始尺寸（除非过小）
                if scale < 1:
                    # 图片比页面大，需要缩小
                    image = image.resize((new_img_width, new_img_height), Resampling.LANCZOS)
                    img_width, img_height = new_img_width, new_img_height
                    logger.info(f"[insert_image_page] 缩放后图片尺寸: {img_width}x{img_height}")
                else:
                    # 图片比可用空间小，保持原始尺寸，但不超过可用空间
                    if img_width > available_width or img_height > available_height:
                        # 仍然需要缩放到可用区域内
                        image = image.resize((new_img_width, new_img_height), Resampling.LANCZOS)
                        img_width, img_height = new_img_width, new_img_height
                        logger.info(f"[insert_image_page] 调整到可用区域后图片尺寸: {img_width}x{img_height}")

                # 使用fitz在指定位置创建标准尺寸的新页面
                new_page = self.pdf_processor.fitz_document.new_page(insert_position, width=page_width, height=page_height)
                logger.info(f"[insert_image_page] 新建页面，文档总页数: {len(self.pdf_processor.fitz_document)}")

                # 计算图片在页面中的居中位置，考虑边距
                # 水平居中（在可用宽度内居中）
                x_offset = margin_x + (available_width - img_width) / 2
                # 垂直居中（在可用高度内居中）
                y_offset = margin_y + (available_height - img_height) / 2

                # 将图片数据转换为字节
                from io import BytesIO
                img_bytes = BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes.seek(0)

                # 插入图片到页面的居中位置
                img_rect = fitz.Rect(x_offset, y_offset, x_offset + img_width, y_offset + img_height)
                new_page.insert_image(img_rect, stream=img_bytes.read())
                logger.info(f"[insert_image_page] 图片插入成功，位置: ({x_offset}, {y_offset})")

            except Exception as e:
                import traceback
                logger.error(f"图片转换失败: {str(e)}\n{traceback.format_exc()}")
                return False, f"图片转换失败: {str(e)}"

            # 更新状态
            self.is_modified = True

            # 记录操作
            self.record_operation('insert_image_page', operation_data)

            # 清除渲染缓存
            if hasattr(self.pdf_processor, 'clear_render_cache'):
                self.pdf_processor.clear_render_cache()

            # 注意：这里不立即保存到原始文件，只标记为已修改
            # 用户点击保存时才会写入原始文件
            logger.info(f"[insert_image_page] 文档已在内存中修改，等待用户保存")

            # 发出状态变化信号，通知界面更新按钮状态
            self._emit_state_changed()

            logger.info(f"[insert_image_page] 图片插入成功: {os.path.basename(image_path)}")
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