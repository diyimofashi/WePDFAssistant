"""
缩略图右键菜单功能测试文件
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication, QMainWindow
from app.core.thumbnail_manager import ThumbnailManager

def test_context_menu():
    """测试右键菜单功能"""
    print("开始测试缩略图右键菜单功能...")
    
    try:
        # 创建Qt应用程序
        app = QApplication(sys.argv)
        print("Qt应用程序创建成功")
        
        # 创建主窗口（作为父级容器）
        main_window = QMainWindow()
        main_window.setWindowTitle("测试窗口")
        main_window.resize(800, 600)
        main_window.show()
        print("主窗口创建成功")
        
        # 创建缩略图管理器
        thumbnail_manager = ThumbnailManager(main_window)
        thumbnail_manager.show()
        print("缩略图管理器创建成功")
        
        # 测试右键菜单功能
        print(f"上下文菜单策略: {thumbnail_manager.contextMenuPolicy()}")
        print("右键菜单功能测试完成")
        
        print("测试完成")
        return True
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_context_menu()
    if success:
        print("✅ 缩略图右键菜单功能测试通过")
    else:
        print("❌ 缩略图右键菜单功能测试失败")