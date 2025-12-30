# 条码插件开发指南

## 目录结构

条码插件应该放置在 `app/plugins-barcode/` 目录下，每个插件是一个独立的子目录：

```
app/plugins-barcode/
├── barcode_template/          # 示例插件模板
│   ├── __init__.py          # 插件初始化文件，定义PluginInfo
│   ├── barcode_api.py       # 插件API实现
│   └── config.py           # 配置项定义
└── your_plugin/            # 你的插件
    ├── __init__.py
    ├── api.py
    └── config.py
```

## 开发步骤

### 第一步：创建插件目录

在 `app/plugins-barcode/` 下创建你的插件目录，例如 `my_barcode_plugin/`。

### 第二步：创建 `__init__.py`

定义插件信息和导出API类：

```python
"""
你的条码插件描述
"""

from .api import YourPluginClass

# 插件信息定义（必需）
PluginInfo = {
    "name": "your_plugin_name",           # 插件唯一标识（必须与目录名一致）
    "title": "你的插件标题",               # 插件显示名称
    "version": "1.0.0",                   # 插件版本
    "author": "你的名字",                 # 作者
    "description": "插件功能描述",          # 详细描述
    "api_class": "YourPluginClass",       # API类名（必须与api.py中的类名一致）
    "global_options": {
        "title": "全局配置",
        "description": "全局配置选项"
    },
    "local_options": {
        "title": "插件配置",
        "description": "插件局部配置选项"
    }
}

__all__ = ['YourPluginClass']
```

### 第三步：创建 `api.py` 实现插件接口

实现 `BarcodePluginInterface` 接口：

```python
"""
条码插件API实现
"""

from typing import Dict, List, Any, Optional
from app.core.barcode.barcode_plugin_interface import BarcodePluginInterface, BarcodeResult, BarcodeErrorCode

class YourPluginClass(BarcodePluginInterface):
    """你的条码插件实现"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.plugin_name = "your_plugin_name"
        self.plugin_version = "1.0.0"
        self.plugin_author = "你的名字"
        self.config = config or {}
        self.is_initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> BarcodeResult:
        """初始化插件"""
        try:
            self.config.update(config)
            # 初始化你的插件逻辑
            self.is_initialized = True
            return BarcodeResult(code=BarcodeErrorCode.SUCCESS, message="插件初始化成功")
        except Exception as e:
            return BarcodeResult(code=BarcodeErrorCode.INIT_ERROR, message=f"插件初始化失败: {str(e)}")
    
    def detect_from_file(self, file_path: str) -> BarcodeResult:
        """从文件检测条码"""
        try:
            if not self.is_initialized:
                return BarcodeResult(code=BarcodeErrorCode.INIT_ERROR, message="插件未初始化")
            
            # 实现你的条码检测逻辑
            
            return BarcodeResult(
                code=BarcodeErrorCode.SUCCESS, 
                data=[条码数据列表], 
                message="检测成功"
            )
        except Exception as e:
            return BarcodeResult(code=BarcodeErrorCode.DETECTION_FAILED, message=f"检测失败: {str(e)}")
    
    def detect_from_pdf(self, doc: 'fitz.Document', config: Optional[Dict[str, Any]] = None) -> BarcodeResult:
        """从PDF文档检测条码"""
        # 实现PDF条码检测逻辑
        pass
    
    def get_supported_types(self) -> List[str]:
        """返回支持的条码类型"""
        return ['CODE128', 'CODE39', 'QR', 'EAN13']
    
    def split_document_by_barcodes(self, doc: fitz.Document, output_dir: str,
                                     config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """按条码拆分文档"""
        # 实现拆分逻辑
        pass
    
    def preview_split_result(self, doc: fitz.Document, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """预览拆分结果"""
        # 实现预览逻辑
        pass
    
    def cleanup(self) -> None:
        """清理资源"""
        self.is_initialized = False
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": self.plugin_name,
            "version": self.plugin_version,
            "author": self.plugin_author,
            "initialized": self.is_initialized
        }
```

### 第四步：创建 `config.py` 定义配置项

定义用户可配置的选项：

```python
"""
插件配置项定义
"""

from app.config.barcode_plugin_config import ConfigItem, ConfigItemType

PLUGIN_CONFIG_DEFINITIONS = [
    # 基础配置
    ConfigItem(
        key="enabled_types",
        title="启用的条码类型",
        type_=ConfigItemType.LIST,
        default=["ALL_TYPES"],
        description="要检测的条码类型列表"
    ),
    ConfigItem(
        key="min_length",
        title="最小长度",
        type_=ConfigItemType.INTEGER,
        default=1,
        min_value=1,
        max_value=1000,
        description="条码内容最小长度"
    ),
    ConfigItem(
        key="max_length",
        title="最大长度",
        type_=ConfigItemType.INTEGER,
        default=1000,
        min_value=1,
        max_value=10000,
        description="条码内容最大长度"
    ),
    # 添加更多配置项...
]
```

## 接口说明

### BarcodePluginInterface 方法

| 方法 | 必需 | 说明 |
|------|------|------|
| `initialize(config)` | 是 | 初始化插件 |
| `detect_from_file(file_path)` | 否 | 从图片文件检测条码 |
| `detect_from_bytes(image_bytes)` | 否 | 从字节流检测条码 |
| `detect_from_base64(base64_string)` | 否 | 从Base64字符串检测条码 |
| `detect_from_pdf(doc, config)` | 是 | 从PDF文档检测条码 |
| `get_supported_types()` | 是 | 返回支持的条码类型列表 |
| `split_document_by_barcodes(doc, output_dir, config)` | 是 | 按条码拆分文档 |
| `preview_split_result(doc, config)` | 是 | 预览拆分结果 |
| `cleanup()` | 是 | 清理资源 |
| `get_plugin_info()` | 是 | 返回插件信息 |

### BarcodeResult 说明

返回结果对象，包含：
- `code`: 错误码（BarcodeErrorCode）
- `data`: 返回的数据
- `message`: 提示信息

### BarcodeErrorCode 说明

- `SUCCESS`: 成功
- `INIT_ERROR`: 初始化错误
- `FILE_NOT_FOUND`: 文件不存在
- `DETECTION_FAILED`: 检测失败
- `SPLIT_FAILED`: 拆分失败

## ConfigItemType 类型

| 类型 | 说明 | 控件 |
|------|------|------|
| `STRING` | 字符串 | QLineEdit |
| `INTEGER` | 整数 | QSpinBox |
| `FLOAT` | 浮点数 | QDoubleSpinBox |
| `BOOLEAN` | 布尔值 | QCheckBox |
| `ENUM` | 枚举 | QComboBox |
| `LIST` | 列表 | 支持多选的控件 |
| `DICT` | 字典 | 高级配置 |

## 插件管理器

插件管理器会自动：
1. 扫描 `app/plugins-barcode/` 下的所有子目录
2. 加载包含 `__init__.py` 和 `PluginInfo` 的插件
3. 加载 `config.py` 中定义的配置项
4. 注册到配置管理器

## 测试插件

创建测试文件验证插件功能：

```python
from app.managers.barcode_plugin_manager import barcode_plugin_manager

# 加载所有插件
barcode_plugin_manager.load_all_plugins()

# 获取你的插件
plugin = barcode_plugin_manager.get_plugin("your_plugin_name")

# 初始化插件
result = plugin.initialize({"min_length": 5, "max_length": 20})

# 测试检测
doc = fitz.open("test.pdf")
result = plugin.detect_from_pdf(doc)
print(result.data)
```

## 最佳实践

1. **错误处理**：所有方法都应该捕获异常并返回合适的错误码
2. **类型注解**：使用类型注解提高代码可读性
3. **文档注释**：为每个方法添加详细的文档字符串
4. **配置验证**：在 `initialize` 中验证配置参数
5. **资源清理**：在 `cleanup` 中释放所有资源
6. **日志记录**：使用 `picologging` 记录重要操作

## 注意事项

1. 插件目录名、`PluginInfo['name']`、API类的 `plugin_name` 必须保持一致
2. `PluginInfo` 中的 `api_class` 必须与实际类名一致
3. `__init__.py` 中必须定义 `PluginInfo` 字典
4. `config.py` 中必须定义 `PLUGIN_CONFIG_DEFINITIONS` 列表
5. 避免使用阻塞操作，耗时操作应考虑使用进度回调

## 示例插件

查看 `barcode_template/` 和 `advanced_barcode/` 目录中的示例代码，了解完整的插件实现。
