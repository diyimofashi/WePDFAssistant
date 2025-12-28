"""极灵PDF主程序入口 - 重构版"""

import sys
import os

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


class AuroraPDF(MainWindowBase, PDFManagerMixin, ViewManagerMixin, ThumbnailManagerMixin, 
                  SearchManagerMixin, OCRManagerMixin, UploadManagerMixin, 
                  DownloadManagerMixin, OperationManagerMixin):
    """极灵PDF主窗口 - 重构版本"""
    pass


def get_app_icon():
    """获取应用程序图标，优先使用外部图标文件，否则使用内置生成的图标"""
    import os
    from PyQt5.QtGui import QIcon
    
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
    from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont
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
    
    from PyQt5.QtGui import QIcon
    return QIcon(pixmap)


def main():
    """主函数"""
    from PyQt5.QtWidgets import QApplication
    from app.config.settings import AppSettings
    
    app = QApplication(sys.argv)
    
    app.setApplicationName(AppSettings.APP_NAME)
    app.setApplicationVersion(AppSettings.APP_VERSION)
    app.setOrganizationName(AppSettings.ORGANIZATION)
    
    # 设置应用程序图标
    app_icon = get_app_icon()
    app.setWindowIcon(app_icon)
    
    viewer = AuroraPDF()
    # 为窗口也设置图标
    viewer.setWindowIcon(app_icon)
    viewer.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()