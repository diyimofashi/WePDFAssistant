# 上传插件系统

## 概述

上传插件系统允许用户根据需要实现不同的上传方式（HTTP、FTP、OSS等），并将生成的文件上传到指定的服务器。

## 插件接口

所有上传插件必须实现 `UploadPluginInterface` 接口，包含以下方法：

- `initialize(config)`: 初始化插件
- `upload_file(file_path, remote_path, **kwargs)`: 上传本地文件
- `upload_bytes(file_bytes, remote_path, original_filename, **kwargs)`: 上传字节流
- `get_supported_features()`: 获取插件支持的特性
- `cleanup()`: 清理资源

## 已实现的插件

### HTTP上传插件
- 支持基本认证、Token认证和API Key认证
- 支持自定义请求头
- 支持重试机制

### FTP上传插件
- 支持普通FTP和FTPS
- 支持主动/被动模式
- 自动创建远程目录

## 如何创建新插件

1. 在 `app/plugins/` 目录下创建新插件目录
2. 实现 `UploadPluginInterface` 接口
3. 创建 `__init__.py` 文件定义插件信息
4. 创建 `config.py` 文件定义配置选项
5. 创建 `upload_api.py` 文件实现上传逻辑

## 使用示例

```python
from app.managers.upload_plugin_manager import upload_plugin_manager

# 加载所有插件
results = upload_plugin_manager.load_all_plugins()

# 初始化特定插件
config = {
    "base_url": "https://example.com/upload",
    "auth_type": "token",
    "token": "your_token_here"
}
init_result = upload_plugin_manager.initialize_plugin("upload_http", config)

# 上传文件
upload_result = upload_plugin_manager.upload_with_plugin(
    plugin_name="upload_http",
    file_path="/path/to/file.pdf",
    remote_path="uploads/"
)
```