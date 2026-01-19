"""PDFAssistant - 启动脚本"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置应用根目录（用于资源文件和插件查找）
# 检测是否为编译环境（Nuitka或PyInstaller）
if hasattr(sys, 'frozen') or hasattr(sys, '_MEIPASS') or not os.path.exists(os.path.join(os.path.dirname(__file__), 'app')):
    # Nuitka/PyInstaller 编译后的环境
    # sys.executable 指向 start.exe，返回其所在目录
    APPLICATION_PATH = os.path.dirname(sys.executable)
    # 确保 sys.frozen 存在（Nuitka可能不会自动设置）
    if not hasattr(sys, 'frozen'):
        sys.frozen = True
else:
    # 开发环境
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))

# 将应用根目录添加到环境变量，供其他模块使用
os.environ['APPLICATION_PATH'] = APPLICATION_PATH
print(f"[DEBUG] APPLICATION_PATH set to: {APPLICATION_PATH}")

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("启动PDFAssistant（集成性能优化版）...")
print("包含以下优化特性:")
print("   - 异步PDF加载 - 不再阻塞UI")
print("   - 虚拟滚动技术 - 流畅浏览大文件")
print("   - 智能缓存管理 - 显著提升渲染性能")
print("   - 延迟加载缩略图 - 按需生成节省内存")
print("   - 实时性能监控 - 自动优化资源使用")
print("   - 智能右键菜单 - 快捷访问常用功能")
print()

from app.main import main

if __name__ == '__main__':
    # 处理命令行参数（用于文件关联）
    import sys
    sys.argv = ['start'] + sys.argv[1:]

    main()

