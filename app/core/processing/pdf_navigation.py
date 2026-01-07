"""PDF导航器 - 处理PDF页面导航和缩放功能"""

import os
import fitz  # PyMuPDF - 用于PDF页面渲染
import sys

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('pdf_navigation')

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

class PDFNavigation:
    """PDF导航器 - 专门处理页面导航和缩放功能"""
    
    def __init__(self):
        # 注意：信号需要在主QObject子类中定义
        # fitz_document 由 PDFProcessor 统一管理，不在子模块中初始化
        self.current_page = 0  # 当前页码（从0开始）
        self.zoom_factor = 2.0  # 缩放因子（设置为2.0，即200%作为新的100%基准）
        self.base_zoom = 2.0  # 基准缩放因子（用户看到的100%实际是200%基准）

        # 连续浏览模式属性
        self.continuous_mode = True  # 是否启用连续浏览模式
        self.pages_per_view = 3  # 连续模式下每次显示的页面数
        self.page_spacing = 20  # 页面间距（像素）

    def get_current_page(self):
        """获取当前页码（用户可见的页码，从1开始）"""
        return self.current_page + 1 if self.fitz_document else 0

    def get_total_pages(self):
        """获取总页数"""
        return len(self.fitz_document) if self.fitz_document else 0

    def go_to_page(self, page_number):
        """跳转到指定页面 - 增强版本，支持边界检测和状态反馈"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        total_pages = len(self.fitz_document)
        
        # 验证页码输入
        if not isinstance(page_number, int) or page_number < 1:
            return False, f"页码无效，请输入1-{total_pages}之间的数字"
        
        # 转换用户页码（1开始）为内部页码（0开始）
        internal_page = page_number - 1
        
        if 0 <= internal_page < total_pages:
            self.current_page = internal_page
            return True, f"已跳转到第{page_number}页"
        elif internal_page >= total_pages:
            # 超过最后一页时，跳转到最后一页
            self.current_page = total_pages - 1
            return True, f"已跳转到最后一页（第{total_pages}页）"
        else:
            return False, f"页码无效，请输入1-{total_pages}之间的数字"

    def next_page(self):
        """下一页 - 增强版本，支持循环浏览"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        total_pages = len(self.fitz_document)
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            return True, f"已跳转到第{self.current_page + 1}页"
        else:
            # 已经是最后一页时，可选择循环到第一页
            if total_pages > 1:
                self.current_page = 0
                return True, "已回到第一页"
            else:
                return False, "已经是最后一页"

    def previous_page(self):
        """上一页 - 增强版本，支持循环浏览"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        total_pages = len(self.fitz_document)
        
        if self.current_page > 0:
            self.current_page -= 1
            return True, f"已跳转到第{self.current_page + 1}页"
        else:
            # 已经是第一页时，可选择循环到最后一页
            if total_pages > 1:
                self.current_page = total_pages - 1
                return True, f"已跳转到最后一页（第{total_pages}页）"
            else:
                return False, "已经是第一页"

    def set_zoom(self, zoom_factor):
        """设置缩放比例 - 基于新的基准缩放（用户看到的100%实际是300%）"""
        # 将用户的缩放值转换为实际缩放值
        actual_zoom = zoom_factor * self.base_zoom
        
        # 限制实际缩放范围在75%-1200%（对应用户看到的25%-400%）
        if 0.25 <= zoom_factor <= 4.0:
            self.zoom_factor = actual_zoom
            return True, f"缩放比例已设置为{int(zoom_factor * 100)}%"
        else:
            return False, "缩放比例必须在25%-400%之间"
    
    def get_zoom(self):
        """获取当前缩放比例（返回用户看到的相对值）"""
        return self.zoom_factor / self.base_zoom

    def set_continuous_mode(self, enabled=True, pages_per_view=3):
        """设置连续浏览模式"""
        self.continuous_mode = enabled
        self.pages_per_view = max(1, min(10, pages_per_view))  # 限制1-10页

    def get_page_dimensions(self, page_num=None):
        """获取指定页面的尺寸信息"""
        if not self.fitz_document:
            return None
            
        if page_num is None:
            page_num = self.current_page
            
        try:
            page = self.fitz_document[page_num]
            rect = page.rect
            return {
                'width': rect.width,
                'height': rect.height,
                'size': f"{rect.width:.1f} × {rect.height:.1f} 点"
            }
        except:
            return None