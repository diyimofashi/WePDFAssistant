"""
操作历史记录管理器
统一管理所有PDF编辑操作，支持撤销/重做功能
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('operation_history')

from PyQt5.QtCore import QObject, pyqtSignal


class OperationType(Enum):
    """操作类型枚举"""
    PAGE_ADD = "page_add"           # 添加页面
    PAGE_DELETE = "page_delete"     # 删除页面
    PAGE_MOVE = "page_move"         # 移动页面
    TEXT_ADD = "text_add"           # 添加文本
    TEXT_EDIT = "text_edit"         # 编辑文本
    TEXT_DELETE = "text_delete"     # 删除文本
    IMAGE_ADD = "image_add"         # 添加图片
    IMAGE_MOVE = "image_move"       # 移动图片
    IMAGE_DELETE = "image_delete"   # 删除图片
    ANNOTATION_ADD = "annotation_add"      # 添加注释
    ANNOTATION_EDIT = "annotation_edit"    # 编辑注释
    ANNOTATION_DELETE = "annotation_delete" # 删除注释
    FORM_EDIT = "form_edit"         # 编辑表单
    MERGE = "merge"                 # 合并PDF
    SPLIT = "split"                 # 分割PDF
    ROTATE = "rotate"               # 旋转页面
    CROP = "crop"                   # 裁剪页面
    WATERMARK = "watermark"         # 添加水印


class OperationState:
    """操作状态"""
    def __init__(self, operation_type: OperationType, **kwargs):
        self.operation_type = operation_type
        self.timestamp = datetime.now()
        self.description = kwargs.get('description', '')
        self.parameters = kwargs.get('parameters', {})
        self.before_state = kwargs.get('before_state', None)  # 操作前的状态数据
        self.after_state = kwargs.get('after_state', None)    # 操作后的状态数据
        
    def __str__(self):
        return f"{self.operation_type.value}: {self.description} ({self.timestamp.strftime('%H:%M:%S')})"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'operation_type': self.operation_type.value,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'parameters': self.parameters,
            'before_state': self.before_state,
            'after_state': self.after_state
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationState':
        """从字典创建实例"""
        operation_type = OperationType(data['operation_type'])
        timestamp = datetime.fromisoformat(data['timestamp'])
        
        op = cls(operation_type, **{
            'description': data.get('description', ''),
            'parameters': data.get('parameters', {}),
            'before_state': data.get('before_state'),
            'after_state': data.get('after_state')
        })
        op.timestamp = timestamp
        return op


class OperationHistory(QObject):
    """操作历史记录管理器"""
    
    # 信号定义
    history_changed = pyqtSignal()  # 历史记录发生变化
    operation_added = pyqtSignal(OperationState)  # 添加了新操作
    operation_undone = pyqtSignal(OperationState)  # 操作被撤销
    operation_redone = pyqtSignal(OperationState)  # 操作被重做
    
    def __init__(self, max_history_size: int = 100):
        super().__init__()
        self.max_history_size = max_history_size
        self.undo_stack: List[OperationState] = []  # 撤销栈
        self.redo_stack: List[OperationState] = []  # 重做栈
        self.current_operation: Optional[OperationState] = None
        
        logger.info(f"操作历史管理器已创建，最大历史记录数: {max_history_size}")
    
    def add_operation(self, operation_type: OperationType, **kwargs) -> OperationState:
        """添加新操作到历史记录"""
        # 清除重做栈（添加新操作时重做栈失效）
        if self.redo_stack:
            self.redo_stack.clear()
            logger.debug("添加新操作，清空重做栈")
        
        # 创建操作状态
        operation = OperationState(operation_type, **kwargs)
        
        # 添加到撤销栈
        self.undo_stack.append(operation)
        
        # 限制历史记录大小
        if len(self.undo_stack) > self.max_history_size:
            removed_operation = self.undo_stack.pop(0)
            logger.debug(f"历史记录达到上限，移除最旧操作: {removed_operation}")
        
        # 设置当前操作
        self.current_operation = operation
        
        logger.info(f"添加操作: {operation}")
        
        # 发送信号
        self.operation_added.emit(operation)
        self.history_changed.emit()
        
        return operation
    
    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return len(self.redo_stack) > 0
    
    def get_undo_count(self) -> int:
        """获取可撤销的操作数量"""
        return len(self.undo_stack)
    
    def get_redo_count(self) -> int:
        """获取可重做的操作数量"""
        return len(self.redo_stack)
    
    def get_last_operation(self) -> Optional[OperationState]:
        """获取最后一个操作"""
        return self.undo_stack[-1] if self.undo_stack else None
    
    def undo(self) -> Optional[OperationState]:
        """撤销上一个操作"""
        if not self.can_undo():
            logger.warning("无法撤销，撤销栈为空")
            return None
        
        # 从撤销栈取出最后一个操作
        operation = self.undo_stack.pop()
        
        # 添加到重做栈
        self.redo_stack.append(operation)
        
        # 更新当前操作
        self.current_operation = self.undo_stack[-1] if self.undo_stack else None
        
        logger.info(f"撤销操作: {operation}")
        
        # 发送信号
        self.operation_undone.emit(operation)
        self.history_changed.emit()
        
        return operation
    
    def redo(self) -> Optional[OperationState]:
        """重做下一个操作"""
        if not self.can_redo():
            logger.warning("无法重做，重做栈为空")
            return None
        
        # 从重做栈取出最后一个操作
        operation = self.redo_stack.pop()
        
        # 重新添加到撤销栈
        self.undo_stack.append(operation)
        
        # 更新当前操作
        self.current_operation = operation
        
        logger.info(f"重做操作: {operation}")
        
        # 发送信号
        self.operation_redone.emit(operation)
        self.history_changed.emit()
        
        return operation
    
    def clear_history(self):
        """清空所有历史记录"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_operation = None
        
        logger.info("清空所有操作历史记录")
        
        # 发送信号
        self.history_changed.emit()
    
    def clear_redo_stack(self):
        """清空重做栈"""
        self.redo_stack.clear()
        logger.debug("清空重做栈")
    
    def get_history_info(self) -> Dict[str, Any]:
        """获取历史记录信息"""
        return {
            'undo_count': len(self.undo_stack),
            'redo_count': len(self.redo_stack),
            'max_size': self.max_history_size,
            'current_operation': self.current_operation.to_dict() if self.current_operation else None,
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo()
        }
    
    def save_history(self, file_path: str) -> bool:
        """保存历史记录到文件"""
        try:
            import json
            
            history_data = {
                'undo_stack': [op.to_dict() for op in self.undo_stack],
                'redo_stack': [op.to_dict() for op in self.redo_stack],
                'max_history_size': self.max_history_size,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"历史记录已保存到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")
            return False
    
    def load_history(self, file_path: str) -> bool:
        """从文件加载历史记录"""
        try:
            import json
            
            if not os.path.exists(file_path):
                logger.warning(f"历史记录文件不存在: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # 清空当前历史记录
            self.clear_history()
            
            # 加载撤销栈
            for op_data in history_data.get('undo_stack', []):
                operation = OperationState.from_dict(op_data)
                self.undo_stack.append(operation)
            
            # 加载重做栈
            for op_data in history_data.get('redo_stack', []):
                operation = OperationState.from_dict(op_data)
                self.redo_stack.append(operation)
            
            # 更新最大历史记录大小
            self.max_history_size = history_data.get('max_history_size', self.max_history_size)
            
            # 设置当前操作
            self.current_operation = self.undo_stack[-1] if self.undo_stack else None
            
            logger.info(f"历史记录已从文件加载: {file_path}")
            
            # 发送信号
            self.history_changed.emit()
            
            return True
            
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            return False
    
    def get_operation_summary(self) -> str:
        """获取操作历史摘要"""
        undo_count = len(self.undo_stack)
        redo_count = len(self.redo_stack)
        
        if undo_count == 0 and redo_count == 0:
            return "无操作历史"
        
        summary = f"可撤销: {undo_count} 个操作 | 可重做: {redo_count} 个操作"
        
        if self.current_operation:
            summary += f"\n当前操作: {self.current_operation}"
        
        return summary
    
    def has_unsaved_changes(self) -> bool:
        """检查是否有未保存的更改"""
        # 如果有任何操作记录，则认为有未保存的更改
        return len(self.undo_stack) > 0
    
    def batch_add_operations(self, operations: List[OperationState]):
        """批量添加操作"""
        if not operations:
            return
        
        # 清除重做栈
        if self.redo_stack:
            self.redo_stack.clear()
        
        # 批量添加操作
        for operation in operations:
            self.undo_stack.append(operation)
        
        # 限制历史记录大小
        while len(self.undo_stack) > self.max_history_size:
            self.undo_stack.pop(0)
        
        # 设置当前操作
        self.current_operation = operations[-1]
        
        logger.info(f"批量添加 {len(operations)} 个操作")
        
        # 发送信号
        self.history_changed.emit()
    
    def get_operation_by_type(self, operation_type: OperationType) -> List[OperationState]:
        """根据类型获取操作列表"""
        return [op for op in self.undo_stack if op.operation_type == operation_type]
    
    def get_recent_operations(self, count: int = 10) -> List[OperationState]:
        """获取最近的操作"""
        return self.undo_stack[-count:] if self.undo_stack else []


# 操作工厂类，用于创建标准操作
class OperationFactory:
    """操作工厂类"""
    
    @staticmethod
    def create_page_add_operation(page_number: int, page_data: Dict[str, Any]) -> OperationState:
        """创建添加页面操作"""
        return OperationState(
            OperationType.PAGE_ADD,
            description=f"添加第 {page_number} 页",
            parameters={'page_number': page_number},
            after_state=page_data
        )
    
    @staticmethod
    def create_page_delete_operation(page_number: int, page_data: Dict[str, Any]) -> OperationState:
        """创建删除页面操作"""
        return OperationState(
            OperationType.PAGE_DELETE,
            description=f"删除第 {page_number} 页",
            parameters={'page_number': page_number},
            before_state=page_data
        )
    
    @staticmethod
    def create_text_add_operation(page_number: int, text: str, position: Dict[str, float]) -> OperationState:
        """创建添加文本操作"""
        return OperationState(
            OperationType.TEXT_ADD,
            description=f"在第 {page_number} 页添加文本",
            parameters={
                'page_number': page_number,
                'text': text,
                'position': position
            }
        )
    
    @staticmethod
    def create_text_edit_operation(page_number: int, old_text: str, new_text: str, 
                                 position: Dict[str, float]) -> OperationState:
        """创建编辑文本操作"""
        return OperationState(
            OperationType.TEXT_EDIT,
            description=f"在第 {page_number} 页编辑文本",
            parameters={
                'page_number': page_number,
                'old_text': old_text,
                'new_text': new_text,
                'position': position
            },
            before_state={'text': old_text},
            after_state={'text': new_text}
        )
    
    @staticmethod
    def create_rotation_operation(page_number: int, angle: int) -> OperationState:
        """创建旋转页面操作"""
        return OperationState(
            OperationType.ROTATE,
            description=f"旋转第 {page_number} 页 {angle} 度",
            parameters={
                'page_number': page_number,
                'angle': angle
            }
        )
    
    @staticmethod
    def create_watermark_operation(text: str, pages: List[int]) -> OperationState:
        """创建添加水印操作"""
        return OperationState(
            OperationType.WATERMARK,
            description=f"为 {len(pages)} 个页面添加水印: {text}",
            parameters={
                'text': text,
                'pages': pages
            }
        )


# 全局操作历史管理器实例
_global_operation_history: Optional[OperationHistory] = None

def get_global_operation_history() -> OperationHistory:
    """获取全局操作历史管理器实例"""
    global _global_operation_history
    if _global_operation_history is None:
        _global_operation_history = OperationHistory()
    return _global_operation_history

def set_global_operation_history(history: OperationHistory):
    """设置全局操作历史管理器实例"""
    global _global_operation_history
    _global_operation_history = history

def clear_global_operation_history():
    """清空全局操作历史管理器实例"""
    global _global_operation_history
    _global_operation_history = None