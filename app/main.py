

import sys
import os
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QIcon
from PyQt5.QtWidgets import QApplication
# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.core.main.main_window_base import MainWindowBase
from app.core.main.pdf_manager_mixin import PDFManagerMixin
from app.core.main.view_manager_mixin import ViewManagerMixin
from app.core.main.thumbnail_manager_mixin import ThumbnailManagerMixin
from app.core.main.search_manager_mixin import SearchManagerMixin
from app.core.main.ocr_manager_mixin import OCRManagerMixin
from app.core.main.upload_manager_mixin import UploadManagerMixin
from app.core.main.download_manager_mixin import DownloadManagerMixin
from app.core.main.operation_manager_mixin import OperationManagerMixin
from app.core.main.shortcut_manager_mixin import ShortcutManagerMixin
from app.config.settings import AppSettings

# 全局窗口列表，用于管理所有打开的窗口
open_windows = []

class AuroraPDF(MainWindowBase, PDFManagerMixin, ViewManagerMixin, ThumbnailManagerMixin,
                  SearchManagerMixin, OCRManagerMixin, UploadManagerMixin,
                  DownloadManagerMixin, OperationManagerMixin, ShortcutManagerMixin):
    """PDFAssistant主窗口"""

    def zoom_in(self):
        """放大：跳转到下一个更大的缩放级别"""
        current_zoom = self.pdf_processor.get_zoom()
        # 获取下一个更大的缩放级别
        next_zoom = self._get_next_zoom_level(current_zoom, direction=1)
        
        if next_zoom is not None:
            success, message = self.pdf_processor.set_zoom(next_zoom)
            if success:
                self.update_preview()
                # 更新缩放比例下拉列表
                zoom_percentage = int(next_zoom * 100)
                zoom_text = f"{zoom_percentage}%"
                if hasattr(self, 'zoom_combo'):
                    self.zoom_combo.setCurrentText(zoom_text)
            self.show_message(message)
    
    def zoom_out(self):
        """缩小：跳转到下一个更小的缩放级别"""
        current_zoom = self.pdf_processor.get_zoom()
        # 获取下一个更小的缩放级别
        next_zoom = self._get_next_zoom_level(current_zoom, direction=-1)
        
        if next_zoom is not None:
            success, message = self.pdf_processor.set_zoom(next_zoom)
            if success:
                self.update_preview()
                # 更新缩放比例下拉列表
                zoom_percentage = int(next_zoom * 100)
                zoom_text = f"{zoom_percentage}%"
                if hasattr(self, 'zoom_combo'):
                    self.zoom_combo.setCurrentText(zoom_text)
            self.show_message(message)
        
    def _get_next_zoom_level(self, current_zoom, direction):
        """获取下一个缩放级别"""
        # 预定义的缩放级别列表
        zoom_levels = [0.08, 0.125, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0]
        
        if direction == 1:  # 放大
            for level in zoom_levels:
                if level > current_zoom:
                    return level
            # 如果当前缩放已经最大，返回最大值
            return zoom_levels[-1]
        else:  # 缩小
            # 从大到小遍历，找到第一个小于当前缩放的级别
            for level in reversed(zoom_levels):
                if level < current_zoom:
                    return level
            # 如果当前缩放已经最小，返回最小值
            return zoom_levels[0]
        
    def fit_to_width(self):
        # 获取虚拟滚动区域的实际容器宽度
        container_width = self.virtual_scroll.width() - 40  # 减去一些边距
        return self.view_controller.fit_to_width(container_width)
        
    def fit_to_height(self):
        # 获取虚拟滚动区域的实际容器高度
        container_height = self.virtual_scroll.height() - 40  # 减去一些边距
        return self.view_controller.fit_to_height(container_height)
        
    def fit_to_container(self):
        # 获取虚拟滚动区域的实际容器尺寸
        container_width = self.virtual_scroll.width() - 40  # 减去一些边距
        container_height = self.virtual_scroll.height() - 40  # 减去一些边距
        return self.view_controller.fit_to_container(container_width, container_height)

    def set_actual_size(self):
        return self.view_controller.set_actual_size()
        
    def on_zoom_combo_changed(self, text):
        """处理缩放比例下拉列表的变化"""
        try:
            # 从文本中提取数值（例如从"100%"提取100）
            zoom_value = int(float(text.replace('%', '')))
            # 将百分比转换为小数（例如100% -> 1.0）
            zoom_factor = zoom_value / 100.0
            
            # 调用PDF处理器设置缩放
            success, message = self.pdf_processor.set_zoom(zoom_factor)
            if success:
                # 更新预览
                self.update_preview()
                
                # 更新缩放标签显示（已移除）
                # if hasattr(self, 'zoom_label'):
                #     self.zoom_label.setText(f"{zoom_value}%")
                    
                # 更新下拉列表显示，以防输入了无效值
                self.zoom_combo.setCurrentText(f"{zoom_value}%")
                
            self.show_message(message)
        except ValueError:
            # 如果转换失败，保持当前缩放
            current_zoom = int(self.pdf_processor.get_zoom() * 100)
            self.zoom_combo.setCurrentText(f"{current_zoom}%")
            self.show_message(f"无效的缩放值: {text}")
        except Exception as e:
            logger.error(f"设置缩放比例失败: {e}")
            self.show_message(f"设置缩放比例失败: {str(e)}")

    def update_zoom_label(self):
        """更新缩放显示 - 已移除缩放显示功能"""
        # 此方法保留以兼容调用，但不执行任何操作
        pass
    
    def _find_closest_zoom_level(self, current_zoom):
        """查找最接近的预定义缩放级别"""
        zoom_levels = [0.08, 0.125, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0]
        
        # 找到最接近当前缩放级别的预定义级别
        closest_level = min(zoom_levels, key=lambda x: abs(x - current_zoom))
        return closest_level

def get_app_icon():
    """获取应用程序图标，优先使用外部图标文件，否则使用内置生成的图标"""
    # 尝试加载外部图标文件
    icon_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'assets', 'app_icon.ico'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'assets', 'app_icon.png'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'app_icon.ico'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'app_icon.png')
    ]
    
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            return QIcon(icon_path)
    
    # 如果外部图标文件不存在，则生成内置图标
    return create_builtin_icon()


def create_builtin_icon():
    """创建内置应用程序图标"""
    # 创建一个128x128像素的图标
    pixmap = QPixmap(128, 128)
    pixmap.fill(QColor(255, 255, 255))  # 白色背景
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 绘制蓝色矩形代表PDF文档
    painter.setBrush(QColor(0, 100, 200))  # 深蓝色填充
    painter.setPen(QPen(QColor(0, 80, 160), 4))  # 蓝色边框
    painter.drawRect(20, 20, 88, 88)  # 主体矩形
    
    # 绘制PDF文字
    font = QFont()
    font.setPointSize(20)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))  # 白色文字
    painter.drawText(35, 70, "PDF")
    
    # 绘制一个简单的'A'字母代表Aurora
    font.setPointSize(16)
    painter.setFont(font)
    painter.drawText(45, 95, "A")
    
    painter.end()
    return QIcon(pixmap)


def create_new_window(file_paths=None):
    """创建新窗口并添加到全局列表"""
    global open_windows
    viewer = AuroraPDF()
    viewer.setWindowIcon(get_app_icon())
    viewer.show()
    open_windows.append(viewer)

    # 如果传入了文件路径，打开这些文件
    if file_paths:
        if len(file_paths) > 1:
            viewer.file_manager._open_multiple_files_as_temp_pdf(file_paths)
        else:
            file_path = file_paths[0]
            file_ext = os.path.splitext(file_path)[1].lower()
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.ico'}

            if file_ext in image_extensions:
                viewer.file_manager._load_multiple_images([file_path])
            else:
                viewer.file_manager._open_pdf_file(file_path)
                AppSettings.set_last_open_dir(file_path)

    return viewer

def main():
    """主函数"""
    global open_windows
    app = QApplication(sys.argv)

    app.setApplicationName(AppSettings.APP_NAME)
    app.setApplicationVersion(AppSettings.APP_VERSION)
    app.setOrganizationName(AppSettings.ORGANIZATION)

    # 设置应用程序图标
    app_icon = get_app_icon()
    app.setWindowIcon(app_icon)

    # 创建第一个窗口
    viewer = create_new_window()

    # 处理命令行参数（打开指定文件）
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        # 处理可能的路径格式（如带引号的路径）
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]

        if os.path.exists(file_path) and file_path.lower().endswith('.pdf'):
            # 使用延迟调用，确保UI完全加载
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: viewer.file_manager._open_pdf_file(file_path))

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()