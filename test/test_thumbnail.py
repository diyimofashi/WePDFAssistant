"""
缩略图功能测试文件
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication
from app.core.thumbnail_manager import ThumbnailManager

def test_thumbnail_manager():
    """测试缩略图管理器"""
    print("开始测试缩略图管理器...")
    
    try:
        # 创建Qt应用程序
        app = QApplication(sys.argv)
        print("Qt应用程序创建成功")
        
        # 创建缩略图管理器
        thumbnail_manager = ThumbnailManager()
        print("缩略图管理器创建成功")
        
        # 测试初始化
        print(f"缩略图管理器初始化完成，图标尺寸: {thumbnail_manager.iconSize()}")
        print(f"视图模式: {thumbnail_manager.viewMode()}")
        
        print("测试完成")
        return True
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_thumbnail_manager()
    if success:
        print("✅ 缩略图管理器测试通过")
    else:
        print("❌ 缩略图管理器测试失败")