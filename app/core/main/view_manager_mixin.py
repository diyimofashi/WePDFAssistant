"""视图管理混入类 - 重构版"""
from PyQt5.QtGui import QContextMenuEvent
from app.utils.logger import get_logger

logger = get_logger('main')

class ViewManagerMixin:
    """视图管理混入类 - 处理视图和缩放功能"""
    
    def zoom_in(self):
        return self.view_controller.zoom_in()
        
    def zoom_out(self):
        return self.view_controller.zoom_out()
        
    def fit_to_width(self):
        return self.view_controller.fit_to_width()
        
    def fit_to_height(self):
        return self.view_controller.fit_to_height()
        
    def set_actual_size(self):
        return self.view_controller.set_actual_size()

    def toggle_actual_size(self):
        """切换实际大小（A4缩放）"""
        if hasattr(self, 'pdf_processor') and self.pdf_processor:
            # 获取当前设置
            current_a4_scaling = self.pdf_processor.get_use_a4_scaling()
            # 切换设置（实际大小 = 不使用A4缩放）
            new_a4_scaling = not current_a4_scaling
            self.pdf_processor.set_use_a4_scaling(new_a4_scaling)

            # 更新菜单项的选中状态
            if hasattr(self, 'actual_size_action'):
                self.actual_size_action.setChecked(not new_a4_scaling)

            # 重新渲染页面
            if hasattr(self, 'update_preview'):
                self.update_preview()

            # 显示提示信息
            status_msg = "使用实际大小" if not new_a4_scaling else "使用A4缩放"
            self.show_message(status_msg)
            logger.info(f"切换页面缩放模式: {status_msg}")
        else:
            logger.warning("PDF处理器不可用，无法切换实际大小模式")
    
    def set_zoom_level(self, level):
        """设置缩放级别"""
        # 根据缩放级别调整视图
        if hasattr(self.view_controller, 'set_zoom_level'):
            self.view_controller.set_zoom_level(level)
        else:
            # 如果视图控制器没有该方法，尝试其他方式
            logger.warning(f"视图控制器不支持设置缩放级别: {level}%")
            # 状态栏缩放显示已移除
            pass
    
    def previous_page(self):
        return self.view_controller.previous_page()
        
    def next_page(self):
        return self.view_controller.next_page()
        
    def go_to_page(self, page_number=None):
        return self.view_controller.go_to_page(page_number)
        
    def _on_page_spinbox_changed(self, value):
        return self.view_controller.on_page_spinbox_changed(value)
        
    def toggle_thumbnails(self):
        return self.view_controller.toggle_thumbnails()
        
    def load_thumbnails(self):
        return self.view_controller.load_thumbnails()
        
    def on_thumbnail_clicked(self, page_num):
        return self.view_controller.on_thumbnail_clicked(page_num)
        
    def on_thumbnail_right_clicked(self, page_num):
        return self.view_controller.on_thumbnail_right_clicked(page_num)
        
    def update_thumbnail_selection(self, current_page):
        return self.view_controller.update_thumbnail_selection(current_page)
    
    def show_context_menu_at(self, position):
        """在指定位置显示右键菜单
        
        Args:
            position: 鼠标位置 (QPoint)
        """
        if hasattr(self, 'context_menu_manager'):
            # 创建一个模拟的鼠标事件
            global_pos = self.mapToGlobal(position)
            event = QContextMenuEvent(
                QContextMenuEvent.Mouse,
                position,
                global_pos
            )
            self.context_menu_manager.show_context_menu(event)
            logger.debug(f"在位置 {position} 显示右键菜单")
