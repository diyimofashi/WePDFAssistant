"""右键菜单管理器"""
import traceback
from PyQt5.QtWidgets import QMenu
from PyQt5.QtCore import Qt, QPoint
from app.utils.logger import get_logger
from app.ui.context_menu_styles import ContextMenuStyles
from app.ui.context_menu_builders import ContextMenuBuilder, ContextType
from app.config.settings import AppSettings

logger = get_logger(__name__)


class ContextMenuManager:
    """右键菜单管理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.menu_builder = ContextMenuBuilder(main_window)
        self.current_context_type = ContextType.GENERAL
        self.context_data = {}
    
    def detect_context(self, event):
        """检测当前上下文类型
        
        Args:
            event: 鼠标事件
            
        Returns:
            tuple: (context_type, context_data)
        """
        try:
            # 获取鼠标位置
            pos = event.pos()
            global_pos = event.globalPos()
            
            context_data = {
                'position': pos,
                'global_position': global_pos,
                'selected_text': None,
                'page_num': None
            }
            
            # 检查是否有选中的文本
            selected_text = self._get_selected_text()
            if selected_text:
                self.current_context_type = ContextType.TEXT
                context_data['selected_text'] = selected_text
                logger.debug(f"检测到文本选中上下文: {selected_text[:50]}...")
                return ContextType.TEXT, context_data
            
            # 检查鼠标是否在缩略图区域
            if self._is_on_thumbnail(event):
                page_num = self._get_thumbnail_page(event)
                if page_num is not None:
                    self.current_context_type = ContextType.THUMBNAIL
                    context_data['page_num'] = page_num
                    logger.debug(f"检测到缩略图上下文: 页面{page_num}")
                    return ContextType.THUMBNAIL, context_data
            
            # 检查鼠标是否在PDF页面区域
            if self._is_on_page(event):
                page_num = self._get_current_page(event)
                if page_num is not None:
                    self.current_context_type = ContextType.PAGE
                    context_data['page_num'] = page_num
                    logger.debug(f"检测到页面上下文: 页面{page_num}")
                    return ContextType.PAGE, context_data
            
            # 默认为通用上下文
            self.current_context_type = ContextType.GENERAL
            logger.debug("检测到通用上下文")
            return ContextType.GENERAL, context_data
            
        except Exception as e:
            logger.error(f"检测上下文失败: {e}")
            logger.error(traceback.format_exc())
            return ContextType.GENERAL, {}
    
    def build_context_menu(self, context_type=None, **kwargs):
        """构建上下文菜单
        
        Args:
            context_type: 上下文类型
            **kwargs: 上下文数据
            
        Returns:
            QMenu: 构建的菜单对象
        """
        if context_type is None:
            context_type = self.current_context_type
        
        try:
            menu = self.menu_builder.build_menu(context_type, **kwargs)
            
            # 应用样式
            if hasattr(self.main_window, 'theme'):
                menu.setStyleSheet(ContextMenuStyles.get_stylesheet(self.main_window.theme))
            else:
                menu.setStyleSheet(ContextMenuStyles.get_stylesheet(AppSettings.THEME))
            
            logger.debug(f"构建{context_type}类型菜单成功")
            return menu
            
        except Exception as e:
            logger.error(f"构建菜单失败: {e}")
            logger.error(traceback.format_exc())
            return QMenu(self.main_window)
    
    def show_context_menu(self, event):
        """显示右键菜单
        
        Args:
            event: 鼠标事件
        """
        try:
            # 检测上下文
            context_type, context_data = self.detect_context(event)
            
            # 构建菜单
            menu = self.build_context_menu(context_type, **context_data)
            
            # 显示菜单
            global_pos = event.globalPos()
            action = menu.exec_(global_pos)
            
            # 处理菜单动作
            if action:
                self._handle_menu_action(action)
            
            logger.debug(f"显示{context_type}类型菜单完成")
            
        except Exception as e:
            logger.error(f"显示菜单失败: {e}")
            logger.error(traceback.format_exc())
    
    def _handle_menu_action(self, action):
        """处理菜单动作
        
        Args:
            action: 菜单动作
        """
        try:
            # 菜单动作的触发通过连接的信号处理，这里只做日志记录
            logger.debug(f"执行菜单动作: {action.text()}")
        except Exception as e:
            logger.error(f"处理菜单动作失败: {e}")
    
    def _get_selected_text(self):
        """获取当前选中的文本
        
        Returns:
            str: 选中的文本，如果没有选中则返回None
        """
        try:
            # 检查虚拟滚动区域是否有选中的文本
            if hasattr(self.main_window, 'virtual_scroll'):
                virtual_scroll = self.main_window.virtual_scroll
                if hasattr(virtual_scroll, 'get_selected_text'):
                    text = virtual_scroll.get_selected_text()
                    if text and text.strip():
                        return text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"获取选中文本失败: {e}")
            return None
    
    def _is_on_thumbnail(self, event):
        """检查鼠标是否在缩略图上
        
        Args:
            event: 鼠标事件
            
        Returns:
            bool: 是否在缩略图上
        """
        try:
            if not hasattr(self.main_window, 'thumbnail_list') or not self.main_window.thumbnail_list:
                return False
            
            if not self.main_window.show_thumbnails:
                return False
            
            # 检查鼠标位置是否在缩略图部件内
            thumbnail_widget = self.main_window.thumbnail_list
            pos = event.pos()
            local_pos = thumbnail_widget.mapFrom(self.main_window, pos)
            
            return thumbnail_widget.rect().contains(local_pos)
            
        except Exception as e:
            logger.error(f"检查缩略图位置失败: {e}")
            return False
    
    def _get_thumbnail_page(self, event):
        """获取鼠标指向的缩略图页码
        
        Args:
            event: 鼠标事件
            
        Returns:
            int: 页码，如果无法获取则返回None
        """
        try:
            if not hasattr(self.main_window, 'thumbnail_list'):
                return None
            
            thumbnail_widget = self.main_window.thumbnail_list
            pos = event.pos()
            local_pos = thumbnail_widget.mapFrom(self.main_window, pos)
            
            # 如果缩略图列表有获取页码的方法
            if hasattr(thumbnail_widget, 'get_page_at_position'):
                return thumbnail_widget.get_page_at_position(local_pos)
            
            return None
            
        except Exception as e:
            logger.error(f"获取缩略图页码失败: {e}")
            return None
    
    def _is_on_page(self, event):
        """检查鼠标是否在PDF页面区域
        
        Args:
            event: 鼠标事件
            
        Returns:
            bool: 是否在PDF页面区域
        """
        try:
            if not hasattr(self.main_window, 'virtual_scroll'):
                return False
            
            # 检查鼠标位置是否在虚拟滚动区域内
            virtual_scroll = self.main_window.virtual_scroll
            pos = event.pos()
            local_pos = virtual_scroll.mapFrom(self.main_window, pos)
            
            return virtual_scroll.rect().contains(local_pos)
            
        except Exception as e:
            logger.error(f"检查页面位置失败: {e}")
            return False
    
    def _get_current_page(self, event):
        """获取鼠标指向的页面页码
        
        Args:
            event: 鼠标事件
            
        Returns:
            int: 页码，如果无法获取则返回None
        """
        try:
            if not hasattr(self.main_window, 'virtual_scroll'):
                return None
            
            virtual_scroll = self.main_window.virtual_scroll
            pos = event.pos()
            local_pos = virtual_scroll.mapFrom(self.main_window, pos)
            
            # 如果虚拟滚动区域有获取页码的方法
            if hasattr(virtual_scroll, 'get_page_at_position'):
                page_at_pos = virtual_scroll.get_page_at_position(local_pos)
                if page_at_pos is not None:
                    logger.debug(f"通过虚拟滚动区域获取到页面: {page_at_pos}")
                    return page_at_pos
            
            # 不再返回pdf_processor.current_page，避免误删当前页
            # 只有当能明确知道鼠标指向哪个页面时才返回页面号
            logger.debug("无法确定鼠标指向的具体页面，返回None")
            return None
            
        except Exception as e:
            logger.error(f"获取页面页码失败: {e}")
            return None
    
    def update_context(self, **kwargs):
        """更新上下文数据"""
        self.context_data.update(kwargs)
        logger.debug(f"更新上下文数据: {kwargs}")
