"""视图控制模块"""

from app.utils.logger import get_logger

logger = get_logger('view_controller')


class ViewController:
    """视图控制器 - 负责缩放、导航等视图控制功能"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        
    def zoom_in(self):
        """放大"""
        current_zoom = self.parent.pdf_processor.get_zoom()
        new_zoom = min(current_zoom * 1.2, 4.0)
        success, message = self.parent.pdf_processor.set_zoom(new_zoom)
        if success:
            self.parent.update_preview()
        self.parent.show_message(message)
    
    def zoom_out(self):
        """缩小"""
        current_zoom = self.parent.pdf_processor.get_zoom()
        new_zoom = max(current_zoom / 1.2, 0.25)
        success, message = self.parent.pdf_processor.set_zoom(new_zoom)
        if success:
            self.parent.update_preview()
        self.parent.show_message(message)
    
    def fit_to_width(self, container_width=None):
        """适应宽度"""
        success, message = self.parent.pdf_processor.fit_to_width(container_width)
        if success:
            self.parent.update_preview()
        self.parent.show_message("已适应宽度显示")
    
    def fit_to_height(self, container_height=None):
        """适应页面"""
        success, message = self.parent.pdf_processor.fit_to_height(container_height)
        if success:
            self.parent.update_preview()
        self.parent.show_message("已适应高度显示")
    
    def fit_to_container(self, container_width=None, container_height=None):
        """适应容器"""
        success, message = self.parent.pdf_processor.fit_to_container(container_width, container_height)
        if success:
            self.parent.update_preview()
        self.parent.show_message("已适应容器显示")
    
    def set_actual_size(self):
        """设置原始尺寸"""
        success, message = self.parent.pdf_processor.set_zoom(1.0)
        if success:
            self.parent.update_preview()
        self.parent.show_message("显示原始尺寸")
    
    def set_zoom_level(self, level):
        """设置缩放级别"""
        zoom_factor = level / 100.0
        success, message = self.parent.pdf_processor.set_zoom(zoom_factor)
        if success:
            self.parent.update_preview()
        self.parent.show_message(f"缩放到 {level}%")
        # 状态栏缩放显示已移除
    
    def previous_page(self):
        """上一页"""
        # 获取当前页面，VirtualScrollArea的get_current_page返回1基索引
        current_page = self.parent.scroll_area.get_current_page() - 1  # 转换为0基索引
        if current_page > 0:
            new_page = current_page - 1
            self.parent.scroll_area.scroll_to_page(new_page)  # 滚动到上一页（0基索引）
            # 立即更新工具栏页码显示
            self.parent.page_spinbox.blockSignals(True)
            self.parent.page_spinbox.setValue(new_page + 1)  # 转换为1基索引
            self.parent.page_spinbox.blockSignals(False)
            # 更新缩略图选中状态
            self.parent.update_thumbnail_selection(new_page + 1)
            self.parent.show_message("已跳转到上一页")
        else:
            self.parent.show_message("已是第一页")

    def next_page(self):
        """下一页"""
        # 获取当前页面，VirtualScrollArea的get_current_page返回1基索引
        current_page = self.parent.scroll_area.get_current_page() - 1  # 转换为0基索引
        total_pages = self.parent.pdf_processor.get_total_pages()
        if current_page < total_pages - 1:
            new_page = current_page + 1
            self.parent.scroll_area.scroll_to_page(new_page)  # 滚动到下一页（0基索引）
            # 立即更新工具栏页码显示
            self.parent.page_spinbox.blockSignals(True)
            self.parent.page_spinbox.setValue(new_page + 1)  # 转换为1基索引
            self.parent.page_spinbox.blockSignals(False)
            # 更新缩略图选中状态
            self.parent.update_thumbnail_selection(new_page + 1)
            self.parent.show_message("已跳转到下一页")
        else:
            self.parent.show_message("已是最后一页")
    
    def go_to_page(self, page_number=None):
        """跳转到指定页面"""
        try:
            if page_number is None:
                page_number = self.parent.page_spinbox.value()

            if 1 <= page_number <= self.parent.pdf_processor.get_total_pages():
                self.parent.pdf_processor.go_to_page(page_number)
                self.parent.scroll_area.scroll_to_page(page_number - 1)
                self.parent.show_message(f"跳转到第 {page_number} 页")
                
                current_page = self.parent.pdf_processor.get_current_page()
                total_pages = self.parent.pdf_processor.get_total_pages()
                
                self.parent.page_spinbox.blockSignals(True)
                self.parent.page_spinbox.setValue(current_page)
                self.parent.page_spinbox.blockSignals(False)
                
                self.parent.update_thumbnail_selection(current_page)
            else:
                self.parent.show_message("❌ 无效的页码")
        except ValueError:
            self.parent.show_message("❌ 请输入有效的页码")
    
    def toggle_thumbnails(self):
        """切换缩略图显示/隐藏"""
        self.parent.show_thumbnails = not self.parent.show_thumbnails
        # 更新菜单中的缩略图动作状态
        if hasattr(self.parent, 'thumbnail_action'):
            self.parent.thumbnail_action.setChecked(self.parent.show_thumbnails)
        
        if self.parent.show_thumbnails:
            self.parent.thumbnail_dock.show()
            self.parent.load_thumbnails()
        else:
            self.parent.thumbnail_dock.hide()
    
    def on_page_spinbox_changed(self, value):
        """处理页码输入框变化"""
        self.go_to_page(value)
    
    def load_thumbnails(self):
        """加载PDF页面缩略图"""
        if not self.parent.pdf_processor.fitz_document:
            return
        
        self.parent.thumbnail_list.load_thumbnails()
    
    def on_thumbnail_clicked(self, page_num):
        """处理缩略图点击事件"""
        self.go_to_page(page_num)
        
        self.parent.page_spinbox.blockSignals(True)
        self.parent.page_spinbox.setValue(page_num)
        self.parent.page_spinbox.blockSignals(False)
    
    def on_thumbnail_right_clicked(self, page_num):
        """处理缩略图右键点击事件"""
        logger.debug(f"右键点击第 {page_num} 页")
    
    def update_thumbnail_selection(self, current_page):
        """更新缩略图选中状态"""
        if self.parent.thumbnail_manager:
            self.parent.thumbnail_manager.update_thumbnail_selection(current_page)