"""
RapidOCR插件测试文件
"""

import unittest
import os
import sys

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.plugins.win7_x64_RapidOCR_json.api_rapidocr import Api


class TestRapidOCRAdapter(unittest.TestCase):
    """RapidOCR插件测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.adapter = Api()
        config = {
            "numThread": 4
        }
        result = self.adapter.initialize(config)
        self.assertTrue(result.is_success(), f"插件初始化失败: {result.message}")
    
    def test_initialize(self):
        """测试插件初始化"""
        self.assertTrue(self.adapter.is_initialized, "插件应该已初始化")
        self.assertEqual(self.adapter.plugin_name, "RapidOCR (Local)", "插件名称应该正确")
    
    def test_get_supported_languages(self):
        """测试获取支持的语言列表"""
        languages = self.adapter.get_supported_languages()
        self.assertIsInstance(languages, list, "支持的语言应该是列表")
        self.assertGreater(len(languages), 0, "应该支持至少一种语言")
    
    def test_recognize_from_file(self):
        """测试从文件识别"""
        # 使用插件自带的测试图片
        test_image_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'test.png'
        )
        test_image_path = os.path.abspath(test_image_path)
        
        if os.path.exists(test_image_path):
            result = self.adapter.recognize_from_file(test_image_path)
            self.assertTrue(result.is_success(), f"从文件识别应该成功: {result.message}")
            self.assertIsInstance(result.data, list, "识别结果应该是列表")
        else:
            self.skipTest("测试图片文件不存在")
    
    def test_plugin_info(self):
        """测试插件信息获取"""
        info = self.adapter.get_plugin_info()
        self.assertIn("name", info, "插件信息应该包含名称")
        self.assertIn("version", info, "插件信息应该包含版本")
        self.assertIn("author", info, "插件信息应该包含作者")
        self.assertIn("initialized", info, "插件信息应该包含初始化状态")
    
    def tearDown(self):
        """测试清理"""
        self.adapter.cleanup()
        self.assertFalse(self.adapter.is_initialized, "插件应该已清理")


if __name__ == "__main__":
    unittest.main()