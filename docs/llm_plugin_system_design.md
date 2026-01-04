# LLM插件系统设计文档

## 一、概述

本文档描述了PyPDF项目的LLM(大语言模型)插件系统设计，该系统允许用户通过与大模型对话来使用项目的所有功能。

### 设计目标
1. 支持多LLM厂商接入，各厂商插件互相独立、可拔插
2. 提供统一的API接口，屏蔽底层实现差异
3. 支持工具函数调用，让LLM能够操作PDF、OCR、条码等功能
4. 提供记忆系统，支持连续对话
5. 高扩展性，便于后续功能扩展

## 二、架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户界面层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  主窗口UI     │  │  LLM对话UI   │  │   配置管理UI          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼───────────────────────┼─────────────┘
          │                 │                       │
┌─────────┼─────────────────┼───────────────────────┼─────────────┐
│         ▼                 ▼                       ▼             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   LLM管理混入类                          │   │
│  │              (LLMManagerMixin)                           │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    LLM集成层                             │  │
│  │              (LLMIntegration)                            │  │
│  └──────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
┌────────┼──────────┐  ┌──────┼──────────┐  ┌─────┼──────────┐
│        ▼          │  │      ▼          │  │     ▼          │
│  ┌─────────┐     │  │  ┌─────────┐     │  │  ┌─────────┐   │
│  │ LLM插件 │     │  │  │ 记忆系统 │     │  │  │ 工具函数 │   │
│  │ 管理器  │     │  │  │ 管理器  │     │  │  │  工厂   │   │
│  └────┬────┘     │  │  └────┬────┘     │  │  └─────────┘   │
│       │          │  │       │          │  │                │
│       ▼          │  │       ▼          │  │                │
│  ┌──────────────────────────────────────┐  │                │
│  │         LLM插件接口层                  │  │                │
│  │    (LLMPluginInterface - ABC)         │  │                │
│  └──────────────────────────────────────┘  │                │
│              │                              │                │
│  ┌───────────┼──────────────────────────────┘                │
│  │           ▼                                               │
│  │  ┌────────────────────────────────────────────────────┐  │
│  │  │            具体LLM插件实现                         │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │  │OpenAI    │  │Claude    │  │本地模型  │  ...    │  │
│  │  │  │插件      │  │插件      │  │插件      │        │  │
│  │  │  └──────────┘  └──────────┘  └──────────┘        │  │
│  │  └────────────────────────────────────────────────────┘  │
│  └───────────────────────────────────────────────────────────┘
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                       业务功能层                                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────┐ │
│  │ PDF处理 │  │ OCR识别 │  │条码分割 │  │ 上传   │  │ 下载 │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └──────┘ │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 数据流设计

```
┌──────────────┐
│  用户输入    │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│         LLM对话UI (llm_chat_dialog)         │
│  - 用户消息输入                             │
│  - 消息历史显示                             │
│  - 流式输出显示                             │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│        LLM管理混入类 (LLMManagerMixin)      │
│  - 管理对话状态                             │
│  - 调用LLM集成API                           │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│         LLM集成层 (LLMIntegration)           │
│  - 插件路由选择                             │
│  - 工具调用管理                             │
│  - 记忆系统集成                             │
└──────┬──────────────────────────────────────┘
       │
   ┌───┴────────────────────┐
   │                        │
   ▼                        ▼
┌────────────┐      ┌──────────────┐
│ LLM插件    │      │  记忆系统    │
│ 管理器     │      │  MemoryManager│
└──────┬─────┘      └──────────────┘
       │
   ┌───┴────────────────┐
   │                    │
   ▼                    ▼
┌──────────┐       ┌──────────┐
│具体插件  │       │ 工具函数 │
│OpenAI等  │       │ PDF/OCR  │
└──────────┘       └────┬─────┘
                        │
                        ▼
              ┌───────────────────┐
              │   业务功能层      │
              │ PDF/OCR/条码等    │
              └───────────────────┘
```

## 三、目录结构

```
app/
├── config/
│   └── llm_plugin_config.py          # LLM插件配置管理器
├── core/
│   └── llm/                          # LLM核心模块
│       ├── __init__.py
│       ├── llm_plugin_interface.py   # LLM插件抽象接口
│       ├── llm_integration.py        # LLM系统集成类
│       ├── llm_plugin_manager.py     # LLM插件管理器
│       ├── llm_error_handler.py      # LLM错误处理器
│       ├── llm_plugin_security.py    # LLM安全管理器
│       ├── llm_performance_optimizer.py  # LLM性能优化器
│       ├── memory/                   # 记忆系统
│       │   ├── __init__.py
│       │   ├── memory_interface.py   # 记忆系统抽象接口
│       │   ├── memory_manager.py     # 记忆管理器
│       │   └── backends/
│       │       ├── __init__.py
│       │       ├── in_memory_backend.py   # 内存存储
│       │       ├── file_backend.py         # 文件存储
│       │       └── database_backend.py     # 数据库存储(可选)
│       └── tools/                    # LLM工具函数
│           ├── __init__.py
│           ├── pdf_tools.py          # PDF相关工具
│           ├── ocr_tools.py          # OCR相关工具
│           ├── barcode_tools.py      # 条码相关工具
│           ├── upload_tools.py       # 上传相关工具
│           ├── download_tools.py     # 下载相关工具
│           └── base_tool.py          # 工具基类
├── managers/
│   └── llm_plugin_manager.py         # LLM插件管理器(业务层)
├── core/main/
│   └── llm_manager_mixin.py          # LLM管理混入类
├── ui/
│   ├── llm_chat_dialog.py            # LLM对话对话框
│   ├── llm_settings_dialog.py        # LLM设置对话框
│   └── llm_plugin_manager_dialog.py  # LLM插件管理对话框
└── plugins-llm/                      # LLM插件目录
    ├── openai_llm/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── llm_api.py
    │   └── tests/
    ├── claude_llm/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── llm_api.py
    │   └── tests/
    ├── qwen_llm/                     # 通义千问
    │   ├── __init__.py
    │   ├── config.py
    │   ├── llm_api.py
    │   └── tests/
    ├── ollama_llm/                   # 本地模型
    │   ├── __init__.py
    │   ├── config.py
    │   ├── llm_api.py
    │   └── tests/
    └── template/                     # 插件开发模板
        ├── __init__.py
        ├── config.py
        ├── llm_api.py
        └── README.md
```

## 四、核心接口设计

### 4.1 LLM插件接口

```python
# app/core/llm/llm_plugin_interface.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Iterator, Optional
from dataclasses import dataclass

@dataclass
class LLMMessage:
    """LLM消息"""
    role: str  # "system", "user", "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LLMResult:
    """LLM结果"""
    success: bool
    content: str
    model: str
    usage: Dict[str, int]  # {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LLMModelInfo:
    """LLM模型信息"""
    name: str
    provider: str
    max_tokens: int
    supports_stream: bool
    supports_functions: bool
    context_length: int
    pricing: Optional[Dict[str, float]] = None

class LLMPluginInterface(ABC):
    """LLM插件抽象接口"""

    @abstractmethod
    def get_plugin_name(self) -> str:
        """获取插件名称"""
        pass

    @abstractmethod
    def get_plugin_version(self) -> str:
        """获取插件版本"""
        pass

    @abstractmethod
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> LLMResult:
        """初始化插件"""
        pass

    @abstractmethod
    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResult:
        """单次对话"""
        pass

    @abstractmethod
    def chat_stream(self, messages: List[LLMMessage], **kwargs) -> Iterator[LLMResult]:
        """流式对话"""
        pass

    @abstractmethod
    def chat_with_functions(
        self,
        messages: List[LLMMessage],
        functions: List[Dict],
        **kwargs
    ) -> LLMResult:
        """支持函数调用的对话"""
        pass

    @abstractmethod
    def get_supported_models(self) -> List[LLMModelInfo]:
        """获取支持的模型列表"""
        pass

    @abstractmethod
    def get_model_info(self, model_name: str) -> LLMModelInfo:
        """获取模型信息"""
        pass

    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """计算token数量"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """清理资源"""
        pass
```

### 4.2 LLM集成API

```python
# app/core/llm/llm_integration.py
from typing import Dict, List, Iterator, Optional
from app.core.llm.llm_plugin_interface import LLMMessage, LLMResult, LLMModelInfo

class LLMIntegration:
    """LLM系统集成类 - 统一API入口"""

    _instance = None
    _plugins: Dict[str, Any] = {}
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize_system(self, plugin_configs: Optional[Dict] = None) -> Dict[str, bool]:
        """初始化LLM系统"""
        pass

    def chat(
        self,
        plugin_name: str,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResult:
        """单次对话"""
        pass

    def chat_stream(
        self,
        plugin_name: str,
        messages: List[LLMMessage],
        **kwargs
    ) -> Iterator[LLMResult]:
        """流式对话"""
        pass

    def chat_with_memory(
        self,
        plugin_name: str,
        messages: List[LLMMessage],
        memory_key: str,
        **kwargs
    ) -> LLMResult:
        """带记忆的对话"""
        pass

    def chat_with_tools(
        self,
        plugin_name: str,
        messages: List[LLMMessage],
        tools: List[str],
        **kwargs
    ) -> LLMResult:
        """支持工具调用的对话"""
        pass

    def get_available_plugins(self) -> List[str]:
        """获取可用插件列表"""
        pass

    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件信息"""
        pass

    def get_supported_models(self, plugin_name: str) -> List[LLMModelInfo]:
        """获取支持的模型"""
        pass

    def set_plugin_config(self, plugin_name: str, config: Dict) -> Dict[str, str]:
        """设置插件配置"""
        pass

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件配置"""
        pass
```

### 4.3 工具函数接口

```python
# app/core/llm/tools/base_tool.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    """工具函数基类"""

    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """获取参数定义(JSON Schema格式)"""
        pass

    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        pass

    def to_function_definition(self) -> Dict[str, Any]:
        """转换为OpenAI函数定义格式"""
        return {
            "type": "function",
            "function": {
                "name": self.get_name(),
                "description": self.get_description(),
                "parameters": self.get_parameters()
            }
        }
```

### 4.4 记忆系统接口

```python
# app/core/llm/memory/memory_interface.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class MemoryInterface(ABC):
    """记忆系统抽象接口"""

    @abstractmethod
    def add_memory(
        self,
        key: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """添加记忆"""
        pass

    @abstractmethod
    def get_memory(self, key: str) -> Optional[Dict]:
        """获取记忆"""
        pass

    @abstractmethod
    def search_memories(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """搜索记忆"""
        pass

    @abstractmethod
    def update_memory(
        self,
        key: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """更新记忆"""
        pass

    @abstractmethod
    def delete_memory(self, key: str) -> bool:
        """删除记忆"""
        pass

    @abstractmethod
    def clear_all_memories(self) -> bool:
        """清空所有记忆"""
        pass
```

## 五、LLM工具函数设计

| 工具名称 | 功能描述 | 参数 | 返回值 |
|---------|---------|------|--------|
| `pdf_summary` | 生成PDF摘要 | `pdf_path`, `max_length` | 摘要文本 |
| `pdf_qa` | PDF问答 | `pdf_path`, `question` | 答案 |
| `pdf_extract_text` | 提取PDF文本 | `pdf_path`, `page_range` | 文本内容 |
| `ocr_pdf` | OCR识别PDF | `pdf_path`, `language` | OCR结果 |
| `split_pdf` | 拆分PDF | `pdf_path`, `mode`, `params` | 拆分结果 |
| `merge_pdf` | 合并PDF | `pdf_paths`, `output_path` | 合并结果 |
| `barcode_split` | 条码分割PDF | `pdf_path`, `barcode_type` | 分割结果 |
| `upload_file` | 上传文件 | `file_path`, `plugin` | 上传结果 |
| `download_file` | 下载文件 | `url`, `local_path` | 下载结果 |

## 六、扩展性设计

### 6.1 新增LLM厂商插件

只需在`app/plugins-llm/`下创建新插件目录，实现`LLMPluginInterface`接口:

```
plugins-llm/
└── new_provider_llm/
    ├── __init__.py           # 插件元信息
    ├── config.py             # 配置定义
    └── llm_api.py            # 实现LLMPluginInterface
```

### 6.2 新增工具函数

在`app/core/llm/tools/`下创建新工具类，继承`BaseTool`:

```python
class NewTool(BaseTool):
    def get_name(self) -> str:
        return "new_tool"

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # 实现具体逻辑
        pass
```

### 6.3 新增记忆后端

在`app/core/llm/memory/backends/`下创建新后端，实现`MemoryInterface`:

```python
class NewMemoryBackend(MemoryInterface):
    def add_memory(self, key: str, content: str, metadata: Optional[Dict] = None) -> bool:
        # 实现具体存储逻辑
        pass
```

## 七、配置管理

### 7.1 配置文件示例

LLM插件配置文件示例(`llm_plugins.json`):

```json
{
  "openai": {
    "enabled": true,
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "default_model": "gpt-4",
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "claude": {
    "enabled": true,
    "api_key": "sk-ant-xxx",
    "default_model": "claude-3-sonnet-20240229",
    "max_tokens": 4096
  },
  "memory": {
    "backend": "file",
    "storage_path": "C:/Users/{username}/.aurora_pdf/llm_memory"
  },
  "chat_settings": {
    "stream_enabled": true,
    "max_history": 20,
    "auto_save": true
  }
}
```

### 7.2 配置项说明

| 配置项 | 类型 | 说明 |
|-------|------|------|
| `enabled` | bool | 是否启用该插件 |
| `api_key` | str | API密钥 |
| `base_url` | str | API基础URL |
| `default_model` | str | 默认模型 |
| `max_tokens` | int | 最大token数 |
| `temperature` | float | 温度参数(0-1) |
| `memory.backend` | str | 记忆后端类型(in_memory/file/database) |
| `memory.storage_path` | str | 记忆存储路径 |
| `chat_settings.stream_enabled` | bool | 是否启用流式输出 |
| `chat_settings.max_history` | int | 最大历史记录数 |
| `chat_settings.auto_save` | bool | 是否自动保存对话 |

## 八、实现计划

### 阶段一：核心框架
1. LLM插件接口定义
2. LLM集成层
3. LLM插件管理器
4. 配置管理

### 阶段二：基础实现
5. OpenAI插件实现
6. 记忆系统(内存+文件)
7. 基础工具函数(PDF相关)

### 阶段三：UI集成
8. LLM对话UI
9. LLM设置对话框
10. 混入类集成

### 阶段四：扩展功能
11. Claude插件
12. 本地模型插件
13. 更多工具函数
14. 流式输出优化

## 九、安全考虑

1. **API密钥加密**: 配置文件中的API密钥加密存储
2. **权限控制**: 工具函数调用权限验证
3. **输入验证**: 严格验证所有用户输入
4. **沙箱隔离**: 插件在隔离环境中运行
5. **日志记录**: 完整的操作日志
6. **限流控制**: API调用频率限制

## 十、性能优化

1. **异步处理**: 大部分操作异步执行
2. **缓存机制**: 响应结果缓存
3. **连接池**: HTTP连接池管理
4. **流式输出**: 支持流式响应
5. **内存管理**: 及时清理不再使用的资源
