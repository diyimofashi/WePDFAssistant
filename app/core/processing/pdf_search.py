"""PDF搜索器 - 处理PDF文本搜索和高亮功能"""

import os
import fitz  # PyMuPDF - 用于PDF页面渲染
import sys

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('pdf_search')

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt as QtCore

class PDFSearch:
    """PDF搜索器 - 专门处理文本搜索和高亮功能"""
    
    def __init__(self):
        # 注意：信号需要在主QObject子类中定义
        # fitz_document 由 PDFProcessor 统一管理，不在子模块中初始化
        self.current_page = 0  # 当前页码（从0开始）
    
    def adjust_rect_for_page_rotation(self, rect, page):
        """
        根据页面旋转角度调整矩形坐标
        """
        rotation = page.rotation
        
        # 如果没有旋转，直接返回原矩形
        if rotation == 0 or rotation == 360:
            return rect
        
        # 获取页面尺寸
        page_width = page.rect.width
        page_height = page.rect.height
        
        # 计算旋转中心点
        center_x = page_width / 2
        center_y = page_height / 2
        
        # 获取矩形的四个角点
        x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
        
        # 将所有点转换到以页面中心为原点的坐标系
        corners = [
            (x0 - center_x, y0 - center_y),  # 左上角
            (x1 - center_x, y0 - center_y),  # 右上角
            (x1 - center_x, y1 - center_y),  # 右下角
            (x0 - center_x, y1 - center_y)   # 左下角
        ]
        
        # 计算旋转角度的三角函数值
        import math
        rad = math.radians(-rotation)  # 负号是因为我们需要反向旋转
        cos_val = math.cos(rad)
        sin_val = math.sin(rad)
        
        # 对每个角点应用旋转变换
        rotated_corners = []
        for px, py in corners:
            # 旋转变换公式
            new_x = px * cos_val - py * sin_val
            new_y = px * sin_val + py * cos_val
            rotated_corners.append((new_x + center_x, new_y + center_y))
        
        # 计算旋转后的新边界框
        xs = [corner[0] for corner in rotated_corners]
        ys = [corner[1] for corner in rotated_corners]
        
        new_x0 = min(xs)
        new_y0 = min(ys)
        new_x1 = max(xs)
        new_y1 = max(ys)
        
        # 确保矩形在页面范围内
        new_x0 = max(0, min(new_x0, page_width))
        new_y0 = max(0, min(new_y0, page_height))
        new_x1 = max(0, min(new_x1, page_width))
        new_y1 = max(0, min(new_y1, page_height))
        
        return fitz.Rect(new_x0, new_y0, new_x1, new_y1)

    def search_text(self, search_text, match_case=False, whole_word=False, 
                   search_backwards=False, start_page=None):
        """
        在PDF中搜索文本
        
        Args:
            search_text: 要搜索的文本
            match_case: 是否区分大小写
            whole_word: 是否全词匹配
            search_backwards: 是否向后搜索
            start_page: 开始搜索的页面（None表示从当前页开始）
            
        Returns:
            (success, result_info) 元组
        """
        logger.debug(f"PDFSearch.search_text: 开始搜索文本 '{search_text}', 区分大小写: {match_case}, 全词匹配: {whole_word}")
        
        if not self.fitz_document:
            logger.debug("PDFSearch.search_text: 未打开PDF文件")
            return False, "请先打开PDF文件"
        
        if not search_text.strip():
            logger.debug("PDFSearch.search_text: 搜索文本为空")
            return False, "请输入搜索内容"
        
        try:
            # 确定开始搜索的页面
            if start_page is None:
                start_page = self.current_page
            
            total_pages = len(self.fitz_document)
            
            # 搜索结果列表
            search_results = []
            
            # 搜索范围（向前或向后）
            if search_backwards:
                # 向后搜索：从当前页向前搜索到第1页
                pages_to_search = list(range(start_page, -1, -1))
            else:
                # 向前搜索：从当前页向后搜索到最后一页
                pages_to_search = list(range(start_page, total_pages))
            
            # 搜索标志
            search_flags = 0
            if match_case:
                search_flags |= fitz.TEXT_PRESERVE_LIGATURES
            if whole_word:
                search_flags |= fitz.TEXT_PRESERVE_WHITESPACE
            
            # 执行搜索
            total_found = 0
            for page_num in pages_to_search:
                page = self.fitz_document[page_num]
                
                # 搜索当前页
                # 使用搜索标志，确保区分大小写和全词匹配参数有效
                # 注意：PyMuPDF的search_for参数格式为 search_for(text, flags=flags, hit_max=max_hits)
                text_instances = page.search_for(
                    search_text,
                    flags=search_flags,
                    hit_max=1000  # 增加命中上限
                )
                
                logger.debug(f"在页面 {page_num+1} 中找到 {len(text_instances)} 个匹配项")
                
                # 记录搜索结果
                for rect in text_instances:
                    # 如果页面有旋转，需要调整矩形坐标
                    adjusted_rect = self.adjust_rect_for_page_rotation(rect, page)
                    
                    search_results.append({
                        'page': page_num + 1,  # 转换为用户页码
                        'page_index': page_num,
                        'rect': adjusted_rect,
                        'text': search_text,
                        'position': {
                            'x': adjusted_rect.x0,
                            'y': adjusted_rect.y0,
                            'width': adjusted_rect.width,
                            'height': adjusted_rect.height
                        }
                    })
                
                total_found += len(text_instances)
            
            logger.debug(f"总共找到 {total_found} 个匹配项，搜索文本: '{search_text}'")
            
            # 处理搜索结果
            if search_results:
                logger.debug(f"搜索成功，找到 {len(search_results)} 个匹配项")
                # 如果有搜索结果，跳转到第一个匹配项
                first_result = search_results[0]
                self.current_page = first_result['page_index']
                
                return True, {
                    'total_matches': len(search_results),
                    'current_match': 1,
                    'results': search_results,
                    'message': f"找到 {len(search_results)} 个匹配项"
                }
            else:
                logger.debug(f"搜索完成，未找到匹配的文本: '{search_text}'")
                return False, "未找到匹配的文本"
                
        except Exception as e:
            return False, f"搜索失败: {str(e)}"
    
    def search_next(self, search_text, match_case=False, whole_word=False):
        """搜索下一个匹配项"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        try:
            # 从当前页的下一个位置开始搜索
            start_page = self.current_page + 1
            
            return self.search_text(search_text, match_case, whole_word, 
                                  search_backwards=False, start_page=start_page)
        except Exception as e:
            return False, f"搜索失败: {str(e)}"
    
    def search_previous(self, search_text, match_case=False, whole_word=False):
        """搜索上一个匹配项"""
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        try:
            # 从当前页的前一个位置开始搜索
            start_page = self.current_page - 1
            
            return self.search_text(search_text, match_case, whole_word, 
                                  search_backwards=True, start_page=start_page)
        except Exception as e:
            return False, f"搜索失败: {str(e)}"
    
    def highlight_search_result(self, page_num, rect, color=(1, 1, 0, 0.4)):
        """高亮显示搜索结果（黄色半透明背景）"""
        if not self.fitz_document:
            return False

        try:
            # 获取页面
            page = self.fitz_document[page_num]

            # 如果页面有旋转，需要调整矩形坐标
            adjusted_rect = self.adjust_rect_for_page_rotation(rect, page)

            # 添加高亮注释
            highlight = page.add_highlight_annot(adjusted_rect)
            
            # 设置高亮颜色（黄色）
            highlight.set_colors(stroke=(1.0, 1.0, 0.0), fill=(1.0, 1.0, 0.0))  # 黄色
            highlight.set_opacity(0.3)  # 设置透明度
            highlight.update()
            
            # 设置注释内容，便于识别为搜索高亮
            highlight.set_info(content="Search Highlight", title="SearchHighlight")

            logger.debug(f"已添加高亮：页面{page_num+1}，原始位置{rect}，调整后位置{adjusted_rect}")
            return True
        except Exception as e:
            logger.error(f"高亮失败: {e}")
            return False
    
    def clear_highlights(self, page_num=None):
        """清除高亮标记"""
        if not self.fitz_document:
            return False
        
        try:
            if page_num is not None:
                # 清除指定页面的高亮
                page = self.fitz_document[page_num]
                # 删除所有高亮注释（类型8）和带有搜索高亮标记的注释
                annotations_to_delete = []
                for annot in page.annots():
                    if annot.type[0] == 8:  # 高亮注释类型
                        # 检查是否是搜索高亮（通过内容或标题判断）
                        info = annot.info
                        if 'Search Highlight' in info.get('content', ''):
                            annotations_to_delete.append(annot)
                # 删除收集到的注释
                for annot in annotations_to_delete:
                    page.delete_annot(annot)
            else:
                # 清除所有页面的高亮
                for page_num in range(len(self.fitz_document)):
                    page = self.fitz_document[page_num]
                    annotations_to_delete = []
                    for annot in page.annots():
                        if annot.type[0] == 8:  # 高亮注释类型
                            # 检查是否是搜索高亮（通过内容或标题判断）
                            info = annot.info
                            if 'Search Highlight' in info.get('content', ''):
                                annotations_to_delete.append(annot)
                    # 删除收集到的注释
                    for annot in annotations_to_delete:
                        page.delete_annot(annot)
            
            return True
        except Exception as e:
            logger.error(f"清除高亮失败: {e}")
            return False

    def get_text_from_rect(self, page_num, rect):
        """从指定矩形区域提取文本"""
        if not self.fitz_document:
            return ""
        
        try:
            page = self.fitz_document[page_num]
            
            # 如果页面有旋转，需要调整矩形坐标
            adjusted_rect = self.adjust_rect_for_page_rotation(rect, page)
            
            text = page.get_text("text", clip=adjusted_rect)
            return text.strip()
        except Exception as e:
            logger.error(f"提取文本失败: {e}")
            return ""