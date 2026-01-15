"""
LLM插件抽象接口定义
"""
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
