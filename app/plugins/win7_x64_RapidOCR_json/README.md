# RapidOCR插件

这是一个基于RapidOCR-json的OCR插件，支持多种语言的文字识别。

## 插件结构

```
win7_x64_RapidOCR_json/
├── RapidOCR-json.exe    # OCR引擎可执行文件
├── __init__.py          # 插件元信息定义
├── api_rapidocr.py      # OCR插件实现
├── config.py            # 插件配置定义
├── i18n.csv             # 国际化支持
├── models/              # 模型文件目录
│   ├── configs.txt      # 模型配置文件
│   ├── *.onnx           # 模型文件
│   └── *.txt            # 字典文件
├── rapidocr.py          # RapidOCR核心实现
├── test.png             # 测试图片
└── tests/               # 测试文件目录
    └── test_rapidocr.py # 插件测试文件
```

## 支持的语言

- 简体中文
- English
- 繁體中文
- 日本語
- 한국어
- Русский

## 使用方法

该插件已集成到OCR插件系统中，可通过标准接口调用：

```python
from app.managers.ocr_plugin_manager import OCRPluginManager

# 创建插件管理器
manager = OCRPluginManager()

# 加载插件
plugin_instance = manager.load_plugin("win7_x64_RapidOCR_json")

# 初始化插件
config = {"numThread": 4}
result = manager.initialize_plugin("win7_x64_RapidOCR_json", config)

# 执行OCR识别
ocr_result = manager.recognize_with_plugin(
    "win7_x64_RapidOCR_json",
    file_path="/path/to/image.png"
)
```

## 测试

运行插件测试：

```bash
python -m app.plugins.win7_x64_RapidOCR_json.tests.test_rapidocr
```