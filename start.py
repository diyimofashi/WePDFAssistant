"""极灵PDF - 启动脚本"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🚀 启动极灵PDF（集成性能优化版）...")
print("⚡ 包含以下优化特性:")
print("   • 异步PDF加载 - 不再阻塞UI")
print("   • 虚拟滚动技术 - 流畅浏览大文件")
print("   • 智能缓存管理 - 显著提升渲染性能")
print("   • 延迟加载缩略图 - 按需生成节省内存")
print("   • 实时性能监控 - 自动优化资源使用")
print()

from app.main import main

if __name__ == '__main__':
    main()