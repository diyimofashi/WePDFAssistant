"""右键菜单样式定义"""

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContextMenuStyles:
    """右键菜单样式类"""
    
    @staticmethod
    def get_stylesheet(theme='light'):
        """获取右键菜单样式表"""
        if theme == 'dark':
            return ContextMenuStyles._get_dark_stylesheet()
        else:
            return ContextMenuStyles._get_light_stylesheet()
    
    @staticmethod
    def _get_light_stylesheet():
        """浅色主题样式"""
        return """
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 4px;
                min-width: 200px;
            }
            
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
            
            QMenu::item:disabled {
                color: #b0b0b0;
                background-color: transparent;
            }
            
            QMenu::separator {
                height: 1px;
                background: #e0e0e0;
                margin: 6px 10px;
            }
            
            QMenu::indicator {
                width: 16px;
                height: 16px;
                left: 4px;
            }
            
            QMenu::indicator:checked {
                image: url(:/icons/checked.png);
            }
            
            QMenu::indicator:unchecked {
                image: none;
            }
        """
    
    @staticmethod
    def _get_dark_stylesheet():
        """深色主题样式"""
        return """
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 4px;
                min-width: 200px;
            }
            
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 4px;
                margin: 2px 4px;
                color: #ffffff;
            }
            
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
            
            QMenu::item:disabled {
                color: #606060;
                background-color: transparent;
            }
            
            QMenu::separator {
                height: 1px;
                background: #404040;
                margin: 6px 10px;
            }
            
            QMenu::indicator {
                width: 16px;
                height: 16px;
                left: 4px;
            }
        """
