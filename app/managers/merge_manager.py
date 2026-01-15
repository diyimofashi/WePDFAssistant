"""PDF合并管理器模块"""

from app.utils.logger import get_logger
from app.ui.merge_dialog import MergeDialog

logger = get_logger('merge_manager')


class MergeManager:
    """PDF合并管理器"""
    
    def __init__(self, parent_window):
        """初始化合并管理器
        
        Args:
            parent_window: 父窗口对象
        """
        self.parent = parent_window
        
    def show_merge_dialog(self):
        """显示合并对话框"""
        try:
            dialog = MergeDialog(self.parent)
            
            # 如果有打开的文件,自动添加
            if hasattr(self.parent, 'pdf_processor') and self.parent.pdf_processor:
                if self.parent.pdf_processor.current_file:
                    dialog._add_files_to_list([self.parent.pdf_processor.current_file])
            
            if dialog.exec_() == MergeDialog.Accepted:
                logger.info("合并对话框已关闭")
            else:
                logger.info("合并对话框已取消")
                
        except Exception as e:
            logger.error(f"显示合并对话框时出错: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self.parent, "错误", f"打开合并对话框失败: {str(e)}")
