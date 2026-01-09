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
        pass
        self.current_page = 0  # 当前页码（从0开始）

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
        if not self.fitz_document:
            return False, "请先打开PDF文件"
        
        if not search_text.strip():
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
            for page_num in pages_to_search:
                page = self.fitz_document[page_num]
                
                # 搜索当前页
                text_instances = page.search_for(
                    search_text,
                    flags=search_flags
                )
                
                # 记录搜索结果
                for rect in text_instances:
                    search_results.append({
                        'page': page_num + 1,  # 转换为用户页码
                        'page_index': page_num,
                        'rect': rect,
                        'text': search_text,
                        'position': {
                            'x': rect.x0,
                            'y': rect.y0,
                            'width': rect.width,
                            'height': rect.height
                        }
                    })
            
            # 处理搜索结果
            if search_results:
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

            # 添加高亮注释
            highlight = page.add_highlight_annot(rect)

            # 设置高亮颜色（黄色半透明，透明度0.4）
            # color=(1, 1, 0, 0.4) 表示黄色RGB(255, 255, 0)，透明度40%
            highlight.set_colors(stroke=(1, 1, 0, 0.6), fill=(1, 1, 0, 0.4))
            highlight.update()

            logger.debug(f"已添加高亮：页面{page_num+1}，位置{rect}")
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
                for annot in page.annots():
                    if annot.type[0] == 8:  # 高亮注释类型
                        page.delete_annot(annot)
            else:
                # 清除所有页面的高亮
                for page_num in range(len(self.fitz_document)):
                    page = self.fitz_document[page_num]
                    for annot in page.annots():
                        if annot.type[0] == 8:  # 高亮注释类型
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
            text = page.get_text("text", clip=rect)
            return text.strip()
        except Exception as e:
            logger.error(f"提取文本失败: {e}")
            return ""