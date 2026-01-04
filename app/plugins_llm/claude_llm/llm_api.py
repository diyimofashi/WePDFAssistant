"""
Claude LLM插件实现
"""
import requests
from typing import Dict, List, Any, Iterator
from app.core.llm.llm_plugin_interface import (
    LLMPluginInterface,
    LLMMessage,
    LLMResult,
    LLMModelInfo
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeLLMPlugin(LLMPluginInterface):
    """Claude LLM插件"""

    # 支持的模型列表
    SUPPORTED_MODELS = {
        "claude-3-opus-20240229": {
            "max_tokens": 4096,
            "supports_stream": True,
            "supports_functions": False,
            "context_length": 200000
        },
        "claude-3-sonnet-20240229": {
            "max_tokens": 4096,
            "supports_stream": True,
            "supports_functions": False,
            "context_length": 200000
        },
        "claude-3-haiku-20240307": {
            "max_tokens": 4096,
            "supports_stream": True,
            "supports_functions": False,
            "context_length": 200000
        }
    }

    def __init__(self):
        """初始化插件"""
        self._config: Dict[str, Any] = {}
        self._initialized = False
        self._session = None

    def get_plugin_name(self) -> str:
        return "claude"

    def get_plugin_version(self) -> str:
        return "1.0.0"

    def get_plugin_info(self) -> Dict[str, Any]:
        return {
            "name": self.get_plugin_name(),
            "version": self.get_plugin_version(),
            "description": "Anthropic Claude API LLM插件",
            "author": "Aurora PDF Team",
            "provider": "Anthropic"
        }

    def initialize(self, config: Dict[str, Any]) -> LLMResult:
        """初始化插件"""
        try:
            # 验证配置
            if "api_key" not in config:
                return LLMResult(
                    success=False,
                    content="",
                    model="",
                    usage={},
                    error="Missing required field: api_key"
                )

            self._config = config
            self._initialized = True

            # 创建HTTP会话
            self._session = requests.Session()
            self._session.headers.update({
                "x-api-key": self._config['api_key'],
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            })

            logger.info(f"Plugin '{self.get_plugin_name()}' initialized successfully")
            return LLMResult(
                success=True,
                content="",
                model="",
                usage={},
                metadata={"message": "Initialized successfully"}
            )

        except Exception as e:
            logger.error(f"Error initializing plugin: {e}", exc_info=True)
            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error=str(e)
            )

    def _prepare_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """准备消息格式(Claude格式)"""
        # Claude需要system消息单独处理
        system_message = ""
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        return system_message, api_messages

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResult:
        """单次对话"""
        if not self._initialized:
            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error="Plugin not initialized"
            )

        try:
            model = kwargs.get("model", self._config.get("default_model", "claude-3-sonnet-20240229"))
            max_tokens = kwargs.get("max_tokens", self._config.get("max_tokens", 4096))

            system_message, api_messages = self._prepare_messages(messages)

            # 构建请求体
            payload = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens
            }

            if system_message:
                payload["system"] = system_message

            # 发送请求
            base_url = self._config.get("base_url", "https://api.anthropic.com")
            url = f"{base_url}/v1/messages"
            response = self._session.post(url, json=payload, timeout=60)

            if response.status_code != 200:
                error_data = response.json()
                return LLMResult(
                    success=False,
                    content="",
                    model=model,
                    usage={},
                    error=error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                )

            # 解析响应
            data = response.json()

            return LLMResult(
                success=True,
                content=data["content"][0]["text"],
                model=model,
                usage={
                    "prompt_tokens": data["usage"]["input_tokens"],
                    "completion_tokens": data["usage"]["output_tokens"],
                    "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                }
            )

        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return LLMResult(
                success=False,
                content="",
                model=model if 'model' in locals() else "",
                usage={},
                error=str(e)
            )

    def chat_stream(self, messages: List[LLMMessage], **kwargs) -> Iterator[LLMResult]:
        """流式对话"""
        if not self._initialized:
            yield LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error="Plugin not initialized"
            )
            return

        try:
            model = kwargs.get("model", self._config.get("default_model", "claude-3-sonnet-20240229"))
            max_tokens = kwargs.get("max_tokens", self._config.get("max_tokens", 4096))

            system_message, api_messages = self._prepare_messages(messages)

            # 构建请求体
            payload = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "stream": True
            }

            if system_message:
                payload["system"] = system_message

            # 发送流式请求
            base_url = self._config.get("base_url", "https://api.anthropic.com")
            url = f"{base_url}/v1/messages"
            response = self._session.post(url, json=payload, stream=True, timeout=60)

            if response.status_code != 200:
                error_data = response.json()
                yield LLMResult(
                    success=False,
                    content="",
                    model=model,
                    usage={},
                    error=error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                )
                return

            # 解析流式响应
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if not line.startswith('data: '):
                        continue

                    data_str = line[6:]

                    try:
                        import json
                        data = json.loads(data_str)

                        if data["type"] == "content_block_delta":
                            delta_text = data.get("delta", {}).get("text", "")
                            if delta_text:
                                yield LLMResult(
                                    success=True,
                                    content=delta_text,
                                    model=model,
                                    usage={}
                                )

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.error(f"Error in stream chat: {e}", exc_info=True)
            yield LLMResult(
                success=False,
                content="",
                model=model if 'model' in locals() else "",
                usage={},
                error=str(e)
            )

    def chat_with_functions(
        self,
        messages: List[LLMMessage],
        functions: List[Dict],
        **kwargs
    ) -> LLMResult:
        """Claude当前不支持函数调用"""
        return LLMResult(
            success=False,
            content="",
            model="",
            usage={},
            error="Claude does not support function calling yet"
        )

    def get_supported_models(self) -> List[LLMModelInfo]:
        """获取支持的模型列表"""
        return [
            LLMModelInfo(
                name=model_name,
                provider="Anthropic",
                max_tokens=model_info["max_tokens"],
                supports_stream=model_info["supports_stream"],
                supports_functions=model_info["supports_functions"],
                context_length=model_info["context_length"]
            )
            for model_name, model_info in self.SUPPORTED_MODELS.items()
        ]

    def get_model_info(self, model_name: str) -> LLMModelInfo:
        """获取模型信息"""
        models = {m.name: m for m in self.get_supported_models()}
        if model_name in models:
            return models[model_name]
        return self.get_supported_models()[0]

    def count_tokens(self, text: str, model: str) -> int:
        """计算token数量"""
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.3)

    def cleanup(self) -> None:
        """清理资源"""
        if self._session:
            self._session.close()
        logger.info(f"Plugin '{self.get_plugin_name()}' cleaned up")
