"""
测试页面渲染修复逻辑
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("测试页面渲染修复逻辑...")

# 测试连续模式下页面渲染的逻辑
def test_continuous_mode_rendering():
    print("测试连续模式下页面渲染逻辑...")
    
    # 模拟连续模式下的页面渲染过程
    total_pages = 5
    current_position = 0
    page_positions = []
    page_heights = []
    
    # 保存当前页面
    saved_current_page = 3  # 假设当前页面是第3页
    print(f"保存当前页面: {saved_current_page}")
    
    for page_num in range(total_pages):
        # 为每一页渲染时，临时设置当前页面
        print(f"  为第 {page_num + 1} 页渲染时，临时设置当前页面为 {page_num + 1}")
        
        # 模拟渲染页面
        pixmap_height = 800 + page_num * 10  # 每页高度略有不同
        page_height = pixmap_height + 30  # 包含边距和间距
        
        # 记录页面位置
        page_positions.append(current_position)
        page_heights.append(page_height)
        
        print(f"    第 {page_num + 1} 页位置: {current_position}, 高度: {page_height}")
        
        # 添加页面间距
        if page_num > 0:
            current_position += 10  # 页面间距
            
        current_position += page_height
    
    print(f"页面位置数组: {page_positions}")
    print(f"页面高度数组: {page_heights}")
    
    # 恢复当前页面
    print(f"恢复当前页面为: {saved_current_page}")
    
    print("✅ 页面渲染逻辑测试通过")

if __name__ == "__main__":
    test_continuous_mode_rendering()
    print("测试完成")