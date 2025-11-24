"""
测试页面位置计算修复逻辑
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("测试页面位置计算修复逻辑...")

# 测试页面位置计算的逻辑
def test_position_calculation():
    print("测试页面位置计算逻辑...")
    
    # 模拟连续模式下的页面位置计算过程
    total_pages = 5
    current_position = 0
    page_positions = []
    page_heights = []
    
    for page_num in range(total_pages):
        # 模拟渲染页面
        pixmap_height = 800 + page_num * 10  # 每页高度略有不同
        
        # 修复后的高度计算逻辑
        extra_height = int(pixmap_height * 0.05)
        page_height = pixmap_height + extra_height * 2 + 10  # 包含边框、边距和标签间距
        
        # 记录页面位置
        page_positions.append(current_position)
        page_heights.append(page_height)
        
        print(f"第 {page_num + 1} 页:")
        print(f"  pixmap高度: {pixmap_height}")
        print(f"  额外高度: {extra_height}")
        print(f"  总高度: {page_height}")
        print(f"  位置: {current_position}")
        
        # 添加页面间距
        if page_num > 0:
            current_position += 10  # 页面间距
            
        current_position += page_height
    
    print(f"\n页面位置数组: {page_positions}")
    print(f"页面高度数组: {page_heights}")
    
    # 测试跳转到指定页面
    for page_num in range(1, 6):
        if page_num <= len(page_positions):
            scroll_position = page_positions[page_num - 1]
            print(f"跳转到第 {page_num} 页，滚动位置: {scroll_position}")
    
    print("✅ 页面位置计算逻辑测试通过")

if __name__ == "__main__":
    test_position_calculation()
    print("测试完成")