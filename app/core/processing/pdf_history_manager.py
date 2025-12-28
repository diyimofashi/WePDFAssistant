"""PDF历史管理器 - 处理操作历史记录功能"""

import os
import sys

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('pdf_history_manager')

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

# 导入操作历史记录管理器
from ..editing.operation_history import OperationHistory, OperationType, OperationFactory

class PDFHistoryManager:
    """PDF历史管理器 - 专门处理操作历史记录功能"""
    
    def __init__(self):
        # 注意：信号需要在主QObject子类中定义
        # 操作历史记录管理器
        self.operation_history = OperationHistory(max_history_size=100)

    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return self.operation_history.can_undo()
    
    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return self.operation_history.can_redo()
    
    def undo_operation(self) -> tuple[bool, str]:
        """撤销上一个操作"""
        try:
            operation = self.operation_history.undo()
            if operation:
                # 执行实际的撤销逻辑
                success = self._execute_undo(operation)
                if success:
                    return True, f"撤销成功: {operation.description}"
                else:
                    # 如果撤销执行失败，恢复操作历史记录
                    self.operation_history.redo()
                    return False, "撤销操作执行失败"
            else:
                return False, "没有可撤销的操作"
        except Exception as e:
            logger.error(f"撤销操作失败: {e}")
            return False, f"撤销失败: {str(e)}"
    
    def redo_operation(self) -> tuple[bool, str]:
        """重做下一个操作"""
        try:
            operation = self.operation_history.redo()
            if operation:
                # 执行实际的重做逻辑
                success = self._execute_redo(operation)
                if success:
                    return True, f"重做成功: {operation.description}"
                else:
                    # 如果重做执行失败，恢复操作历史记录
                    self.operation_history.undo()
                    return False, "重做操作执行失败"
            else:
                return False, "没有可重做的操作"
        except Exception as e:
            logger.error(f"重做操作失败: {e}")
            return False, f"重做失败: {str(e)}"
    
    def _execute_undo(self, operation) -> bool:
        """执行撤销操作"""
        try:
            # 根据操作类型执行相应的撤销逻辑
            if operation.operation_type == OperationType.PAGE_ADD:
                # 撤销添加页面：删除该页面
                page_number = operation.parameters.get('page_number')
                return self._delete_page_by_number(page_number - 1)  # 转换为0基索引
            
            elif operation.operation_type == OperationType.PAGE_DELETE:
                # 撤销删除页面：恢复该页面
                page_data = operation.before_state
                return self._restore_page(page_data)
            
            elif operation.operation_type == OperationType.TEXT_ADD:
                # 撤销添加文本：删除该文本
                page_number = operation.parameters.get('page_number')
                position = operation.parameters.get('position')
                return self._delete_text(page_number - 1, position)
            
            elif operation.operation_type == OperationType.TEXT_EDIT:
                # 撤销编辑文本：恢复原始文本
                page_number = operation.parameters.get('page_number')
                old_text = operation.before_state.get('text')
                position = operation.parameters.get('position')
                return self._restore_text(page_number - 1, old_text, position)
            
            elif operation.operation_type == OperationType.ROTATE:
                # 撤销旋转：反向旋转
                page_number = operation.parameters.get('page_number')
                angle = operation.parameters.get('angle')
                return self._rotate_page(page_number - 1, -angle)
            
            # 其他操作类型的撤销逻辑...
            else:
                logger.warning(f"未实现的撤销操作类型: {operation.operation_type}")
                return False
                
        except Exception as e:
            logger.error(f"执行撤销操作失败: {e}")
            return False
    
    def _execute_redo(self, operation) -> bool:
        """执行重做操作"""
        try:
            # 根据操作类型执行相应的重做逻辑
            if operation.operation_type == OperationType.PAGE_ADD:
                # 重做添加页面：重新添加该页面
                page_data = operation.after_state
                return self._add_page_from_data(page_data)
            
            elif operation.operation_type == OperationType.PAGE_DELETE:
                # 重做删除页面：再次删除该页面
                page_number = operation.parameters.get('page_number')
                return self._delete_page_by_number(page_number - 1)
            
            elif operation.operation_type == OperationType.TEXT_ADD:
                # 重做添加文本：重新添加该文本
                page_number = operation.parameters.get('page_number')
                text = operation.parameters.get('text')
                position = operation.parameters.get('position')
                return self._add_text(page_number - 1, text, position)
            
            elif operation.operation_type == OperationType.TEXT_EDIT:
                # 重做编辑文本：重新应用编辑
                page_number = operation.parameters.get('page_number')
                new_text = operation.after_state.get('text')
                position = operation.parameters.get('position')
                return self._edit_text(page_number - 1, new_text, position)
            
            elif operation.operation_type == OperationType.ROTATE:
                # 重做旋转：重新旋转
                page_number = operation.parameters.get('page_number')
                angle = operation.parameters.get('angle')
                return self._rotate_page(page_number - 1, angle)
            
            # 其他操作类型的重做逻辑...
            else:
                logger.warning(f"未实现的重做操作类型: {operation.operation_type}")
                return False
                
        except Exception as e:
            logger.error(f"执行重做操作失败: {e}")
            return False
    
    def add_operation_to_history(self, operation_type: OperationType, **kwargs):
        """添加操作到历史记录"""
        return self.operation_history.add_operation(operation_type, **kwargs)
    
    def get_operation_history_info(self) -> dict:
        """获取操作历史记录信息"""
        return self.operation_history.get_history_info()
    
    def has_unsaved_changes(self) -> bool:
        """检查是否有未保存的更改"""
        return self.operation_history.has_unsaved_changes()
    
    def get_operation_summary(self) -> str:
        """获取操作历史摘要"""
        return self.operation_history.get_operation_summary()
    
    def clear_operation_history(self):
        """清空操作历史记录"""
        self.operation_history.clear_history()
    
    # 以下是具体的操作实现方法（简化示例）
    
    def _delete_page_by_number(self, page_index: int) -> bool:
        """删除指定页面"""
        # 实际实现会依赖于PDF文档对象
        logger.info(f"删除页面: {page_index + 1}")
        return True
    
    def _restore_page(self, page_data: dict) -> bool:
        """恢复被删除的页面"""
        # 实际实现需要根据page_data恢复页面
        logger.info("恢复页面")
        return True
    
    def _delete_text(self, page_index: int, position: dict) -> bool:
        """删除指定位置的文本"""
        logger.info(f"删除页面 {page_index + 1} 上的文本")
        return True
    
    def _restore_text(self, page_index: int, text: str, position: dict) -> bool:
        """恢复被删除的文本"""
        logger.info(f"恢复页面 {page_index + 1} 上的文本: {text}")
        return True
    
    def _add_text(self, page_index: int, text: str, position: dict) -> bool:
        """添加文本"""
        logger.info(f"在页面 {page_index + 1} 上添加文本: {text}")
        return True
    
    def _edit_text(self, page_index: int, text: str, position: dict) -> bool:
        """编辑文本"""
        logger.info(f"编辑页面 {page_index + 1} 上的文本: {text}")
        return True
    
    def _rotate_page(self, page_index: int, angle: int) -> bool:
        """旋转页面"""
        logger.info(f"旋转页面 {page_index + 1}: {angle}度")
        return True
    
    def _add_page_from_data(self, page_data: dict) -> bool:
        """从数据添加页面"""
        logger.info("从数据添加页面")
        return True

    def add_page(self, page_number: int, page_data: dict) -> tuple[bool, str]:
        """添加页面并记录操作"""
        try:
            # 实际添加页面的逻辑
            success = True  # 这里应该是实际的添加逻辑
            
            if success:
                # 记录操作到历史记录
                operation = OperationFactory.create_page_add_operation(page_number, page_data)
                self.add_operation_to_history(operation.operation_type, **{
                    'description': operation.description,
                    'parameters': operation.parameters,
                    'after_state': operation.after_state
                })
                return True, "页面添加成功"
            else:
                return False, "页面添加失败"
                
        except Exception as e:
            return False, f"添加页面失败: {str(e)}"
    
    def delete_page(self, page_number: int) -> tuple[bool, str]:
        """删除页面并记录操作"""
        try:
            # 获取页面数据用于撤销
            page_data = self._get_page_data(page_number)
            
            # 实际删除页面的逻辑
            success = self._delete_page_by_number(page_number - 1)
            
            if success:
                # 记录操作到历史记录
                operation = OperationFactory.create_page_delete_operation(page_number, page_data)
                self.add_operation_to_history(operation.operation_type, **{
                    'description': operation.description,
                    'parameters': operation.parameters,
                    'before_state': operation.before_state
                })
                return True, "页面删除成功"
            else:
                return False, "页面删除失败"
                
        except Exception as e:
            return False, f"删除页面失败: {str(e)}"
    
    def _get_page_data(self, page_number: int) -> dict:
        """获取页面数据（用于撤销操作）"""
        # 实际实现需要获取页面的完整数据
        return {
            'page_number': page_number,
            'content': f"页面{page_number}的内容"
        }
    
    def rotate_page(self, page_number: int, angle: int) -> tuple[bool, str]:
        """旋转页面并记录操作"""
        try:
            # 实际旋转页面的逻辑
            success = self._rotate_page(page_number - 1, angle)
            
            if success:
                # 记录操作到历史记录
                operation = OperationFactory.create_rotation_operation(page_number, angle)
                self.add_operation_to_history(operation.operation_type, **{
                    'description': operation.description,
                    'parameters': operation.parameters
                })
                return True, "页面旋转成功"
            else:
                return False, "页面旋转失败"
                
        except Exception as e:
            return False, f"旋转页面失败: {str(e)}"