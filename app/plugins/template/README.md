# OCR插件模板

这是开发新OCR插件的标准模板。

## 插件结构

```
template/
├── __init__.py          # 插件元信息定义
├── config.py            # 插件配置定义
├── ocr_api.py           # OCR实现
├── i18n.csv            # 国际化支持
└── tests/               # 测试文件目录
    └── test_ocr_api.py # 插件测试文件
```

## 开发指南

1. 复制整个template目录并重命名为您的插件名称
2. 修改`__init__.py`文件中的插件信息
3. 在`ocr_api.py`中实现您的OCR功能
4. 更新`config.py`中的配置定义
5. 修改`i18n.csv`以支持国际化
6. 在`tests/`目录中添加测试文件

## 使用标准接口

所有插件都应该实现标准的OCR插件接口：

```python
class YourOCRClass(OCRPluginInterface):
    def initialize(self, config: Dict[str, Any]) -> OCRResult:
        pass
    
    def recognize_from_file(self, file_path: str, language: str = "auto") -> OCRResult:
        pass
    
    def recognize_from_bytes(self, image_bytes: bytes, language: str = "auto") -> OCRResult:
        pass
    
    def recognize_from_base64(self, base64_string: str, language: str = "auto") -> OCRResult:
        pass
    
    def get_supported_languages(self) -> List[str]:
        pass
    
    def cleanup(self) -> None:
        pass
```

## 测试

运行插件测试：

```bash
python -m app.plugins.template.tests.test_ocr_api
```