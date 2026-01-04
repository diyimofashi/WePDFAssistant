"""
通义千问 LLM插件实现
"""
import requests
from typing import Dict, List, Any, Iterator, Optional
from app.core.llm.llm_plugin_interface import (
    LLMPluginInterface,
    LLMMessage,
    LLMResult,
    LLMModelInfo
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QwenLLMPlugin(LLMPluginInterface):
    """通义千问 LLM插件"""

    # 支持的模型列表
    SUPPORTED_MODELS = {
        "qwen-turbo": {
            "max_tokens": 8000,
            "supports_stream": True,
            "supports_functions": True,
            "context_length": 8000
        },
        "qwen-plus": {
            "max_tokens": 32000,
            "supports_stream": True,
            "supports_functions": True,
            "context_length": 32000
        },
        "qwen-max": {
            "max_tokens": 32000,
            "supports_stream": True,
            "supports_functions": True,
            "context_length": 32000
        }
    }

    def __init__(self):
        """初始化插件"""
        self._config: Dict[str, Any] = {}
        self._initialized = False
        self._session = None

    def get_plugin_name(self) -> str:
        return "qwen"

    def get_plugin_version(self) -> str:
        return "1.0.0"

    def get_plugin_info(self) -> Dict[str, Any]:
        return {
            "name": self.get_plugin_name(),
            "version": self.get_plugin_version(),
            "description": "阿里云通义千问 API LLM插件",
            "author": "Aurora PDF Team",
            "provider": "Alibaba Cloud"
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
                "Authorization": f"Bearer {self._config['api_key']}",
                "Content-Type": "application/json"
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
        """准备消息格式"""
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

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
            model = kwargs.get("model", self._config.get("default_model", "qwen-turbo"))
            max_tokens = kwargs.get("max_tokens", self._config.get("max_tokens", 8000))
            temperature = kwargs.get("temperature", self._config.get("temperature", 0.7))
            functions = kwargs.get("functions")

            api_messages = self._prepare_messages(messages)

            # 构建请求体
            payload = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # 如果有函数定义,添加到请求中
            if functions:
                payload["tools"] = [{"type": "function", "function": f} for f in functions]
                payload["tool_choice"] = "auto"

            # 发送请求
            base_url = self._config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            url = f"{base_url}/chat/completions"
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
            choice = data["choices"][0]
            message = choice["message"]

            # 提取内容
            content = message.get("content", "")

            # 检查是否有工具调用
            tool_calls = None
            if "tool_calls" in message:
                tool_calls = [
                    {
                        "id": tc["id"],
                        "type": tc["type"],
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                    for tc in message["tool_calls"]
                ]

            # 构建结果
            result = LLMResult(
                success=True,
                content=content,
                model=model,
                usage={
                    "prompt_tokens": data["usage"]["prompt_tokens"],
                    "completion_tokens": data["usage"]["completion_tokens"],
                    "total_tokens": data["usage"]["total_tokens"]
                }
            )

            if tool_calls:
                result.metadata = {"tool_calls": tool_calls}

            return result

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
            model = kwargs.get("model", self._config.get("default_model", "qwen-turbo"))
            max_tokens = kwargs.get("max_tokens", self._config.get("max_tokens", 8000))
            temperature = kwargs.get("temperature", self._config.get("temperature", 0.7))
            tools = kwargs.get("tools")

            api_messages = self._prepare_messages(messages)

            # 构建请求体
            payload = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True
            }

            # 添加工具支持
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
                logger.info(f"Sending request with {len(tools)} tools")
            else:
                logger.warning("No tools in request")

            # 发送流式请求
            base_url = self._config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            url = f"{base_url}/chat/completions"
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
            tool_calls_buffer = {}
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if not line.startswith('data: '):
                        continue

                    data_str = line[6:]

                    if data_str.strip() == '[DONE]':
                        # 发送剩余的工具调用（即使不完整也要发送，让系统处理）
                        if tool_calls_buffer:
                            tool_calls = list(tool_calls_buffer.values())
                            # 只发送有名称的工具调用
                            valid_tool_calls = [tc for tc in tool_calls if tc.get("name")]
                            if valid_tool_calls:
                                logger.info(f"Stream ended with tool calls: {valid_tool_calls}")
                                yield LLMResult(
                                    success=True,
                                    content="",
                                    model=model,
                                    usage={},
                                    metadata={"tool_calls": valid_tool_calls}
                                )
                            else:
                                logger.warning(f"Stream ended with tool calls but all missing names: {tool_calls}")
                        else:
                            logger.info("Stream ended with no tool calls")
                        break

                    try:
                        import json
                        data = json.loads(data_str)

                        # 提取增量内容
                        delta = data["choices"][0]["delta"]
                        content = delta.get("content", "")

                        # 调试：打印完整的delta内容（只在第一次）
                        if not hasattr(self, '_debug_delta_logged'):
                            logger.debug(f"Delta structure: {delta}")
                            self._debug_delta_logged = True

                        # 检查工具调用
                        if "tool_calls" in delta:
                            for tool_call_delta in delta["tool_calls"]:
                                index = tool_call_delta.get("index", 0)
                                if index not in tool_calls_buffer:
                                    tool_calls_buffer[index] = {
                                        "id": tool_call_delta.get("id", ""),
                                        "type": tool_call_delta.get("type", "function"),
                                        "name": "",
                                        "arguments": ""
                                    }
                                    logger.debug(f"New tool call at index {index}")

                                tool_call = tool_calls_buffer[index]

                                if "function" in tool_call_delta:
                                    if "name" in tool_call_delta["function"] and tool_call_delta["function"]["name"]:
                                        tool_call["name"] = tool_call_delta["function"]["name"]
                                        logger.debug(f"Tool call name: {tool_call['name']}")

                                    # qwen可能一次性返回完整的arguments（作为JSON字符串）
                                    if "arguments" in tool_call_delta["function"]:
                                        # 如果arguments已经是完整JSON，直接使用
                                        new_args = tool_call_delta["function"]["arguments"]
                                        # 确保new_args不是None且不是空字符串
                                        if new_args is not None and new_args != '':
                                            # 如果当前arguments为空，使用新arguments；否则追加
                                            if not tool_call["arguments"]:
                                                tool_call["arguments"] = new_args
                                            else:
                                                tool_call["arguments"] += new_args
                                            logger.debug(f"Tool call arguments: {new_args[:100] if new_args and len(new_args) > 100 else new_args}")

                        if content:
                            # 先发送工具调用（如果有完整的）
                            complete_tool_calls = [tc for tc in tool_calls_buffer.values()
                                                if tc.get("name") and tc.get("arguments")]
                            if complete_tool_calls:
                                logger.info(f"Sending complete tool calls: {complete_tool_calls}")
                                yield LLMResult(
                                    success=True,
                                    content="",
                                    model=model,
                                    usage={},
                                    metadata={"tool_calls": complete_tool_calls}
                                )
                                # 发送后清空工具调用缓冲区，避免重复发送
                                tool_calls_buffer = {}

                            yield LLMResult(
                                success=True,
                                content=content,
                                model=model,
                                usage={}
                            )

                    except json.JSONDecodeError:
                        continue

            # 流结束后,如果有剩余的工具调用
            if tool_calls_buffer:
                tool_calls = list(tool_calls_buffer.values())
                logger.info(f"Stream ended with {len(tool_calls)} tool calls (already sent during stream)")
                # 注意:不再次发送工具调用,因为已经在流中发送过了

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
        """支持函数调用的对话"""
        return self.chat(messages, functions=functions, **kwargs)

    def get_supported_models(self) -> List[LLMModelInfo]:
        """获取支持的模型列表"""
        return [
            LLMModelInfo(
                name=model_name,
                provider="Alibaba Cloud",
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
