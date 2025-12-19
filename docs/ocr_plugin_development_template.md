# OCR插件开发模板

本文档为OCR插件开发者提供标准模板和开发指南，帮助快速开发兼容系统的OCR插件。

## 1. 插件目录结构规范

```
your_plugin_name/
├── __init__.py              # 插件元信息定义（必需）
├── ocr_api.py              # OCR接口实现（推荐命名）
├── config.py               # 插件配置定义（可选）
├── i18n.csv                # 国际化支持文件（可选）
├── models/                 # 模型文件目录（如需要）
│   ├── *.onnx             # 模型文件
│   └── *.txt              # 字典文件
├── utils/                  # 工具模块目录（可选）
│   └── *.py
└── tests/                  # 测试文件目录（可选）
    ├── test_ocr_api.py
    └── sample_images/     # 测试图片样本
        ├── sample1.jpg
        └── sample2.png
```

## 2. __init__.py文件格式

每个插件必须包含`__init__.py`文件，定义插件元信息：

```python
# -*- coding: utf-8 -*-
"""
OCR插件示例 - 插件描述
"""

from .ocr_api import YourOCRClass  # 导入OCR实现类
from .config import global_options, local_options  # 导入配置定义（可选）

# 插件信息（必需）
PluginInfo = {
    # 插件组别（必需）
    "group": "ocr",
    
    # 全局配置（可选）
    "global_options": global_options,  # 全局配置定义
    
    # 局部配置（可选）
    "local_options": local_options,    # 局部配置定义
    
    # 接口类（必需）
    "api_class": YourOCRClass,         # OCR实现类
}
```

## 3. OCR实现类基类和接口

所有OCR插件必须继承`OCRPluginInterface`并实现所有抽象方法：

```python
# ocr_api.py
from app.core.ocr_plugin_interface import OCRPluginInterface, OCRResult, OCRErrorCode
from typing import Dict, List, Any
import os

class YourOCRClass(OCRPluginInterface):
    """OCR插件实现类"""
    
    def __init__(self):
        super().__init__()
        self.plugin_name = "Your Plugin Name"
        self.plugin_version = "1.0.0"
        self.plugin_author = "Your Name"
        # 添加其他必要的属性
        
    def initialize(self, config: Dict[str, Any]) -> OCRResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            OCRResult: 初始化结果
        """
        try:
            # 在这里进行插件初始化操作
            # 如加载模型、设置参数等
            
            self.is_initialized = True
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                message="插件初始化成功",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            self.is_initialized = False
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message=f"插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def recognize_from_file(self, file_path: str, language: str = "auto") -> OCRResult:
        """
        从文件路径识别文本
        
        Args:
            file_path: 图片文件路径
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return OCRResult(
                code=OCRErrorCode.FILE_NOT_FOUND,
                message=f"文件不存在: {file_path}",
                plugin_name=self.plugin_name
            )
        
        try:
            # 在这里实现OCR识别逻辑
            # 示例返回格式：
            result_data = [
                {
                    "text": "识别的文本内容",
                    "confidence": 0.95,  # 置信度 0-1
                    "bbox": [10, 20, 100, 50],  # 文本框坐标 [x1, y1, x2, y2]
                    "language": "zh"  # 语言标识
                }
            ]
            
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                data=result_data,
                message="OCR识别成功",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def recognize_from_bytes(self, image_bytes: bytes, language: str = "auto") -> OCRResult:
        """
        从字节流识别文本
        
        Args:
            image_bytes: 图片字节流
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        try:
            # 在这里实现OCR识别逻辑
            # 可以将字节流保存为临时文件再处理，或直接处理字节流
            
            result_data = []  # 按上述格式填充识别结果
            
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                data=result_data,
                message="OCR识别成功",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def recognize_from_base64(self, base64_string: str, language: str = "auto") -> OCRResult:
        """
        从Base64字符串识别文本
        
        Args:
            base64_string: Base64编码的图片字符串
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        try:
            # 在这里实现OCR识别逻辑
            # 可以先解码Base64再处理
            
            result_data = []  # 按上述格式填充识别结果
            
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                data=result_data,
                message="OCR识别成功",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def get_supported_languages(self) -> List[str]:
        """
        获取支持的语言列表
        
        Returns:
            List[str]: 支持的语言标识列表
        """
        # 返回插件支持的语言列表
        return ["zh", "en", "ja", "ko"]  # 示例
    
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        # 在这里清理插件使用的资源
        # 如关闭模型、删除临时文件等
        pass
```

## 4. 配置文件定义模板

```python
# config.py
"""
插件配置定义
"""

# 全局配置项（适用于所有插件的配置）
global_options = {
    "title": "插件全局设置",
    "type": "group",
    "threads": {
        "title": "线程数",
        "type": "integer",
        "default": 4,
        "min": 1,
        "max": 16,
        "description": "处理并发线程数"
    },
    # 可以添加更多全局配置项
}

# 局部配置项（每个插件独有的配置）
local_options = {
    "title": "插件局部设置",
    "type": "group",
    "language": {
        "title": "识别语言",
        "type": "enum",
        "optionsList": [
            ["auto", "自动识别"],
            ["zh", "简体中文"],
            ["en", "English"],
            ["ja", "日本語"]
        ],
        "default": "auto",
        "description": "文本识别语言"
    },
    "confidence_threshold": {
        "title": "置信度阈值",
        "type": "float",
        "default": 0.5,
        "min": 0.0,
        "max": 1.0,
        "description": "文本识别置信度阈值，低于此值的结果将被过滤"
    }
    # 可以添加更多局部配置项
}
```

## 5. 国际化支持(i18n.csv模板)

```csv
key,en_US,zh_CN,zh_TW,ja_JP
Plugin Title,Your OCR Plugin,您的OCR插件,您的OCR插件,あなたのOCRプラグイン
Plugin Description,OCR plugin description,OCR插件描述,OCR插件描述,OCRプラグインの説明
Setting Item 1,Setting Item 1,设置项1,設置項1,設定項目1
```

## 6. 插件测试示例

```python
# tests/test_ocr_api.py
import unittest
import os
from your_plugin_name.ocr_api import YourOCRClass

class TestYourOCRPlugin(unittest.TestCase):
    """OCR插件测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.plugin = YourOCRClass()
        config = {}  # 插件配置
        result = self.plugin.initialize(config)
        self.assertTrue(result.is_success(), f"插件初始化失败: {result.message}")
    
    def test_recognize_from_file(self):
        """测试文件识别功能"""
        # 准备测试图片
        test_image_path = os.path.join(os.path.dirname(__file__), "sample_images", "sample1.jpg")
        
        if os.path.exists(test_image_path):
            result = self.plugin.recognize_from_file(test_image_path)
            self.assertTrue(result.is_success(), f"文件识别失败: {result.message}")
            self.assertIsInstance(result.data, list, "识别结果应该是列表格式")
            
            # 检查结果格式
            if result.data:
                first_item = result.data[0]
                self.assertIn("text", first_item, "识别结果应包含text字段")
                self.assertIn("confidence", first_item, "识别结果应包含confidence字段")
                self.assertIn("bbox", first_item, "识别结果应包含bbox字段")
                self.assertIn("language", first_item, "识别结果应包含language字段")
    
    def test_get_supported_languages(self):
        """测试语言支持列表"""
        languages = self.plugin.get_supported_languages()
        self.assertIsInstance(languages, list, "支持的语言列表应该是列表格式")
        self.assertGreater(len(languages), 0, "应该至少支持一种语言")
    
    def tearDown(self):
        """测试清理"""
        self.plugin.cleanup()

if __name__ == "__main__":
    unittest.main()
```

## 7. 插件部署说明

1. 将插件目录复制到应用的`plugins`目录下
2. 确保插件目录包含必需的`__init__.py`文件
3. 重启应用使插件生效
4. 在应用的OCR设置中配置插件参数

## 8. 最佳实践建议

1. **错误处理**: 始终妥善处理异常，返回标准的OCRResult格式
2. **资源管理**: 在cleanup方法中释放所有占用的资源
3. **性能优化**: 对于耗时操作考虑使用异步或多线程处理
4. **日志记录**: 使用应用统一的日志系统记录重要信息
5. **配置验证**: 对用户输入的配置参数进行有效性验证
6. **兼容性**: 确保插件在不同操作系统上都能正常工作
7. **文档完善**: 提供详细的插件说明文档和使用示例