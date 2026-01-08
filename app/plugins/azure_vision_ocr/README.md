***REMOVED*** Vision OCR插件

这是基于Azure认知服务的OCR插件实现。

## 插件结构

```
azure_vision_ocr/
├── __init__.py              # 插件元信息定义
├── azure_vision_ocr_api.py  ***REMOVED*** Vision OCR实现
├── azure_vision_ocr_config.py # 插件配置定义
└── README.md               # 本说明文档
```

## 功能特点

- 基于Azure认知服务的云端OCR识别
- 支持多种语言识别（中文、英文、日文、韩文等）
- 高精度文本识别
- 支持文本方向检测

## 配置说明

### 全局配置

- `app_key`: Azure认知服务的API密钥
- `server_url`: Azure认知服务的端点URL
- `timeout`: OCR处理超时时间（秒）

### 局部配置

- `language`: 识别语言（自动识别、简体中文、英文、日文、韩文）
- `detect_direction`: 是否检测文本方向
- `reading_order`: 文本阅读顺序（自动检测、从左到右）

## 使用说明

1. 需要拥有Azure认知服务的API密钥和端点URL
2. 在配置中填入正确的app_key和server_url
3. 选择合适的识别语言和其他参数
4. 插件将自动处理OCR识别请求

## 注意事项

- 该插件需要网络连接以访问Azure服务
- API调用可能产生费用，请参考Azure定价信息
- 识别结果将被缓存以提高性能和减少API调用次数