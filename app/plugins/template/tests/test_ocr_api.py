"""
OCR插件模板测试文件
"""

import unittest
import os
import sys
import base64

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.plugins.template.ocr_api import TemplateOCR
from app.core.ocr_plugin_interface import OCRErrorCode


class TestTemplateOCR(unittest.TestCase):
    """模板OCR插件测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.plugin = TemplateOCR()
        config = {
            "threads": 4,
            "timeout": 300,
            "language": "auto",
            "confidence_threshold": 0.5
        }
        result = self.plugin.initialize(config)
        self.assertTrue(result.is_success(), f"插件初始化失败: {result.message}")
    
    def test_initialize(self):
        """测试插件初始化"""
        self.assertTrue(self.plugin.is_initialized, "插件应该已初始化")
        self.assertEqual(self.plugin.plugin_name, "Template OCR Plugin", "插件名称应该正确")
    
    def test_get_supported_languages(self):
        """测试获取支持的语言列表"""
        languages = self.plugin.get_supported_languages()
        self.assertIsInstance(languages, list, "支持的语言应该是列表")
        self.assertIn("zh", languages, "应该支持中文")
        self.assertIn("en", languages, "应该支持英文")
    
    def test_recognize_from_file_with_nonexistent_file(self):
        """测试识别不存在的文件"""
        result = self.plugin.recognize_from_file("/non/existent/file.jpg")
        self.assertFalse(result.is_success(), "识别不存在的文件应该失败")
        self.assertEqual(result.code, OCRErrorCode.FILE_NOT_FOUND, "错误码应该是FILE_NOT_FOUND")
    
    def test_recognize_from_file_with_unsupported_language(self):
        """测试使用不支持的语言识别"""
        result = self.plugin.recognize_from_file(
            os.path.join(os.path.dirname(__file__), "sample.jpg"),
            language="unsupported_lang"
        )
        # 注意：由于模板实现中没有真正检查文件存在性，这里主要测试语言检查逻辑
        # 在实际插件中，可能会先报文件不存在错误
        if result.code != OCRErrorCode.FILE_NOT_FOUND:
            self.assertEqual(result.code, OCRErrorCode.UNSUPPORTED_LANGUAGE, 
                           "错误码应该是UNSUPPORTED_LANGUAGE")
    
    def test_recognize_from_bytes(self):
        """测试从字节流识别"""
        # 创建模拟的图片字节流
        mock_image_bytes = b"fake image data"
        result = self.plugin.recognize_from_bytes(mock_image_bytes)
        self.assertTrue(result.is_success(), f"从字节流识别应该成功: {result.message}")
        self.assertIsInstance(result.data, list, "识别结果应该是列表")
    
    def test_recognize_from_base64(self):
        """测试从Base64字符串识别"""
        # 创建模拟的Base64字符串
        mock_base64 = base64.b64encode(b"fake image data").decode('utf-8')
        result = self.plugin.recognize_from_base64(mock_base64)
        self.assertTrue(result.is_success(), f"从Base64识别应该成功: {result.message}")
        self.assertIsInstance(result.data, list, "识别结果应该是列表")
    
    def test_plugin_info(self):
        """测试插件信息获取"""
        info = self.plugin.get_plugin_info()
        self.assertIn("name", info, "插件信息应该包含名称")
        self.assertIn("version", info, "插件信息应该包含版本")
        self.assertIn("author", info, "插件信息应该包含作者")
        self.assertIn("initialized", info, "插件信息应该包含初始化状态")
    
    def tearDown(self):
        """测试清理"""
        self.plugin.cleanup()
        self.assertFalse(self.plugin.is_initialized, "插件应该已清理")


if __name__ == "__main__":
    unittest.main()