"""界面样式定义"""

from PyQt5.QtCore import Qt

class AppStyles:
    """应用样式类"""
    
    # 颜色定义
    COLORS = {
        "dark": {
            "primary": "#007ACC",
            "secondary": "#2D2D30",
            "background": "#1E1E1E",
            "surface": "#252526",
            "text_primary": "#FFFFFF",
            "text_secondary": "#CCCCCC",
            "accent": "#007ACC",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336"
        },
        "light": {
            "primary": "#0066CC",
            "secondary": "#E0E0E0",
            "background": "#FAFAFA",
            "surface": "#FFFFFF",
            "text_primary": "#000000",
            "text_secondary": "#333333",
            "accent": "#0066CC",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336"
        }
    }
    
    @classmethod
    def get_theme_colors(cls, theme):
        """获取主题颜色"""
        return cls.COLORS.get(theme, cls.COLORS["dark"])
    
    @classmethod
    def get_stylesheet(cls, theme="dark"):
        """获取完整的样式表"""
        colors = cls.get_theme_colors(theme)
        
        return f"""
        /* 主窗口样式 */
        QMainWindow {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
            font-family: "微软雅黑";
        }}
        
        /* 菜单栏样式 */
        QMenuBar {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: none;
            padding: 4px;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
            border-radius: 3px;
        }}
        
        QMenuBar::item:selected {{
            background-color: rgba(75, 151, 244, 150);
        }}
        
        /* 工具栏样式 */
        QToolBar {{
            background-color: {colors['surface']};
            border: none;
            spacing: 5px;
            padding: 4px;
        }}
        
        /* 按钮样式 */
        QPushButton {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 2px solid {colors['secondary']};
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {colors['primary']};
            color: #FFFFFF;
            border-color: {colors['primary']};
        }}

        /* 工具栏按钮样式 */
        QToolButton {{
            background-color: transparent;
            border: none;
            padding: 4px;
            border-radius: 4px;
        }}

        QToolButton:hover {{
            background-color: rgba(75, 151, 244, 100);
        }}

        QToolButton:pressed {{
            background-color: rgba(75, 151, 244, 150);
        }}
        
        QPushButton:pressed {{
            background-color: {colors['accent']};
            color: #FFFFFF;
        }}
        
        /* 标签页样式 */
        QTabWidget::pane {{
            border: 1px solid {colors['secondary']};
            background-color: {colors['background']};
        }}
        
        QTabWidget::tab-bar {{
            alignment: center;
        }}
        
        QTabBar::tab {{
            background-color: {colors['surface']};
            color: {colors['text_secondary']};
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors['primary']};
            color: {colors['text_primary']};
        }}
        
        /* 列表样式 */
        QListWidget {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['secondary']};
            border-radius: 4px;
            outline: none;
        }}
        
        QListWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {colors['secondary']};
        }}
        
        QListWidget::item:selected {{
            background-color: {colors['primary']};
        }}
        
        /* 输入框样式 */
        QLineEdit {{
            background-color: #FFFFFF;
            color: #000000;
            border: 2px solid {colors['secondary']};
            border-radius: 4px;
            padding: 6px 8px;
            font-size: 12px;
        }}
        
        QLineEdit:focus {{
            border-color: {colors['primary']};
            outline: none;
        }}
        
        /* 下拉框样式 */
        QComboBox {{
            background-color: #FFFFFF;
            color: #000000;
            border: 2px solid {colors['secondary']};
            border-radius: 4px;
            padding: 6px 8px;
            font-size: 12px;
        }}
        
        QComboBox:focus {{
            border-color: {colors['primary']};
        }}
        
        /* 数值输入框样式 */
        QSpinBox {{
            background-color: #FFFFFF;
            color: #000000;
            border: 2px solid {colors['secondary']};
            border-radius: 4px;
            padding: 6px 8px;
            font-size: 12px;
        }}
        
        QSpinBox:focus {{
            border-color: {colors['primary']};
        }}
        
        /* 标签样式 */
        QLabel {{
            color: {colors['text_primary']};
            background-color: transparent;
            font-weight: bold;
        }}
        
        /* 滚动区域样式 */
        QScrollArea {{
            border: none;
            background-color: {colors['background']};
        }}
        
        /* 状态栏样式 */
        QStatusBar {{
            background-color: {colors['surface']};
            color: {colors['text_secondary']};
            border-top: 1px solid {colors['secondary']};
        }}
        
        /* 分割器样式 */
        QSplitter::handle {{
            background-color: {colors['secondary']};
            width: 1px;
            height: 1px;
        }}
        
        /* 对话框样式 */
        QDialog {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
        }}
        
        QMessageBox {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
        }}
        """