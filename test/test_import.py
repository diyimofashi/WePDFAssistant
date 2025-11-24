"""
基本导入测试文件
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("开始测试导入...")

try:
    from PyQt5.QtWidgets import QApplication
    print("✅ PyQt5导入成功")
except ImportError as e:
    print(f"❌ PyQt5导入失败: {e}")

try:
    from app.core.thumbnail_manager import ThumbnailManager
    print("✅ 缩略图管理器导入成功")
except ImportError as e:
    print(f"❌ 缩略图管理器导入失败: {e}")

print("导入测试完成")