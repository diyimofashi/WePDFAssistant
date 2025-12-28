"""视图管理混入类 - 重构版"""

import os
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
    
    def set_zoom_level(self, level):
        """设置缩放级别"""
        # 根据缩放级别调整视图
        if hasattr(self.view_controller, 'set_zoom_level'):
            self.view_controller.set_zoom_level(level)
        else:
            # 如果视图控制器没有该方法，尝试其他方式
            logger.warning(f"视图控制器不支持设置缩放级别: {level}%")
            # 通过状态栏显示缩放级别
            if hasattr(self, 'zoom_label'):
                self.zoom_label.setText(f"{level}%")
    
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