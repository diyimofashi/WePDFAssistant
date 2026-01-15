"""
OpenAI LLM插件实现
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


class OpenAILLMPlugin(LLMPluginInterface):
    """OpenAI LLM插件"""

    # 支持的模型列表
    SUPPORTED_MODELS = {
        "gpt-4": {
            "max_tokens": 8192,
            "supports_stream": True,
            "supports_functions": True,
            "context_length": 8192
        },
        "gpt-4-turbo": {
            "max_tokens": 128000,
            "supports_stream": True,
            "supports_functions": True,
            "context_length": 128000
        },
        "gpt-4o": {
            "max_tokens": 128000,
            "supports_stream": True,
            "supports_functions": True,
            "context_length": 128000
        },
        "gpt-3.5-turbo": {
            "max_tokens": 4096,
            "supports_stream": True,
            "supports_functions": True,
            "context_length": 16385
        }
    }

    def __init__(self):
        """初始化插件"""
        self._config: Dict[str, Any] = {}
        self._initialized = False
        self._session = None

    def get_plugin_name(self) -> str:
        return "openai"

    def get_plugin_version(self) -> str:
        return "1.0.0"

    def get_plugin_info(self) -> Dict[str, Any]:
        return {
            "name": self.get_plugin_name(),
            "version": self.get_plugin_version(),
            "description": "OpenAI API LLM插件",
            "author": "Aurora PDF Team",
            "provider": "OpenAI"
        }

    def initialize(self, config: Dict[str, Any]) -> LLMResult:
        """
        初始化插件

        Args:
            config: 配置字典

        Returns:
            初始化结果
        """
        try:
            # 验证配置
            from app.plugins_llm.openai_llm.config import validate_config
            errors = validate_config(config)

            if errors:
                return LLMResult(
                    success=False,
                    content="",
                    model="",
                    usage={},
                    error=f"Config validation failed: {', '.join(errors)}"
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
        """
        准备消息格式

        Args:
            messages: LLM消息列表

        Returns:
            API消息格式
        """
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResult:
        """
        单次对话

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            LLM结果
        """
        if not self._initialized:
            return LLMResult(
                success=False,
                content="",
                model="",
                usage={},
                error="Plugin not initialized"
            )

        try:
            # 准备请求参数
            model = kwargs.get("model", self._config.get("default_model", "gpt-3.5-turbo"))
            max_tokens = kwargs.get("max_tokens", self._config.get("max_tokens", 4096))
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
                payload["functions"] = functions
                payload["function_call"] = "auto"

            # 发送请求
            url = f"{self._config['base_url']}/chat/completions"
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

            # 检查是否有函数调用
            tool_calls = None
            if "function_call" in message:
                tool_calls = [{
                    "name": message["function_call"]["name"],
                    "arguments": message["function_call"]["arguments"]
                }]
            elif "tool_calls" in message:
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

        except requests.exceptions.Timeout:
            logger.error("OpenAI API request timeout")
            return LLMResult(
                success=False,
                content="",
                model=model if 'model' in locals() else "",
                usage={},
                error="Request timeout"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request error: {e}")
            return LLMResult(
                success=False,
                content="",
                model=model if 'model' in locals() else "",
                usage={},
                error=f"Request error: {str(e)}"
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
        """
        流式对话

        Args:
            messages: 消息列表
            **kwargs: 额外参数 (支持 functions, tools)

        Yields:
            LLM结果片段
        """
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
            # 准备请求参数
            model = kwargs.get("model", self._config.get("default_model", "gpt-3.5-turbo"))
            max_tokens = kwargs.get("max_tokens", self._config.get("max_tokens", 4096))
            temperature = kwargs.get("temperature", self._config.get("temperature", 0.7))
            functions = kwargs.get("functions")
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
            logger.debug(f"Request payload: {payload}")

            # 优先使用tools(新版API),如果没有则使用functions(旧版API)
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
                logger.info(f"Sending request with {len(tools)} tools")
                logger.debug(f"Request payload keys: {list(payload.keys())}")
            elif functions:
                payload["functions"] = functions
                payload["function_call"] = "auto"
                logger.info(f"Sending request with {len(functions)} functions")
            else:
                logger.warning("No tools or functions in request, LLM will not be able to call tools!")

            # 发送流式请求
            url = f"{self._config['base_url']}/chat/completions"
            response = self._session.post(url, json=payload, stream=True, timeout=60)
            logger.debug(f"response: {response}")

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

                    # SSE格式: "data: {...}"
                    if not line.startswith('data: '):
                        continue

                    data_str = line[6:]  # 去掉 "data: " 前缀

                    # [DONE] 表示流结束
                    if data_str.strip() == '[DONE]':
                        # 如果有工具调用缓冲,发送工具调用信息
                        if tool_calls_buffer:
                            tool_calls = list(tool_calls_buffer.values())
                            logger.info(f"Stream ended with tool calls: {tool_calls}")
                            yield LLMResult(
                                success=True,
                                content="",
                                model=model,
                                usage={},
                                metadata={"tool_calls": tool_calls}
                            )
                            tool_calls_buffer.clear()
                        else:
                            logger.info("Stream ended with no tool calls")
                        break

                    try:
                        import json
                        data = json.loads(data_str)

                        # 提取增量内容
                        delta = data["choices"][0]["delta"]
                        content = delta.get("content", "")

                        # 检查工具调用 (新版API格式)
                        if "tool_calls" in delta:
                            for tool_call_delta in delta["tool_calls"]:
                                index = tool_call_delta.get("index", 0)
                                if index not in tool_calls_buffer:
                                    tool_calls_buffer[index] = {
                                        "id": tool_call_delta.get("id", ""),
                                        "type": tool_call_delta.get("type", "function"),
                                        "name": tool_call_delta.get("function", {}).get("name", ""),
                                        "arguments": ""
                                    }
                                    # 如果name存在，在这里记录
                                    if tool_calls_buffer[index]["name"]:
                                        logger.debug(f"Tool call name received: {tool_calls_buffer[index]['name']}")

                                tool_call = tool_calls_buffer[index]

                                # 更新名称（仅当存在name字段时才更新，避免覆盖已设置的name）
                                if ("function" in tool_call_delta and 
                                    "name" in tool_call_delta["function"] and 
                                    tool_call_delta["function"]["name"]):  # 只有当name不为空时才更新
                                    tool_call["name"] = tool_call_delta["function"]["name"]
                                    logger.debug(f"Tool call name received: {tool_call['name']}")

                                # 追加参数
                                if "function" in tool_call_delta and "arguments" in tool_call_delta["function"]:
                                    # 确保 arguments 不为 None
                                    new_args = tool_call_delta["function"]["arguments"]
                                    if new_args is not None:
                                        tool_call["arguments"] = (tool_call["arguments"] or "") + new_args
                                    logger.debug(f"Tool call arguments received (partial)")

                        # 检查函数调用 (旧版API格式)
                        elif "function_call" in delta:
                            fc = delta["function_call"]
                            if "name" in fc and not tool_calls_buffer.get(0, {}).get("name"):
                                tool_calls_buffer[0] = {
                                    "name": fc["name"],
                                    "arguments": ""
                                }
                                logger.info(f"Legacy function_call format detected: {fc.get('name')}")

                            if "arguments" in fc:
                                if 0 not in tool_calls_buffer:
                                    tool_calls_buffer[0] = {"name": "", "arguments": ""}
                                tool_calls_buffer[0]["arguments"] += fc["arguments"]

                        if content:
                            # 如果有工具调用缓冲且收到内容,先发送工具调用
                            if tool_calls_buffer:
                                tool_calls = list(tool_calls_buffer.values())
                                logger.info(f"Sending tool calls: {tool_calls}")
                                yield LLMResult(
                                    success=True,
                                    content="",
                                    model=model,
                                    usage={},
                                    metadata={"tool_calls": tool_calls}
                                )
                                tool_calls_buffer.clear()

                            yield LLMResult(
                                success=True,
                                content=content,
                                model=model,
                                usage={}
                            )

                    except json.JSONDecodeError:
                        continue

            # 流结束后,如果有剩余的工具调用,发送它们
            if tool_calls_buffer:
                tool_calls = list(tool_calls_buffer.values())
                logger.info(f"Stream ended with pending tool calls: {tool_calls}")
                yield LLMResult(
                    success=True,
                    content="",
                    model=model,
                    usage={},
                    metadata={"tool_calls": tool_calls}
                )

        except requests.exceptions.Timeout:
            logger.error("OpenAI API stream request timeout")
            yield LLMResult(
                success=False,
                content="",
                model=model if 'model' in locals() else "",
                usage={},
                error="Request timeout"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API stream request error: {e}")
            yield LLMResult(
                success=False,
                content="",
                model=model if 'model' in locals() else "",
                usage={},
                error=f"Request error: {str(e)}"
            )
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
        """
        支持函数调用的对话

        Args:
            messages: 消息列表
            functions: 函数定义列表
            **kwargs: 额外参数

        Returns:
            LLM结果
        """
        # 调用chat方法,传入functions参数
        return self.chat(messages, functions=functions, **kwargs)

    def get_supported_models(self) -> List[LLMModelInfo]:
        """
        获取支持的模型列表

        Returns:
            模型信息列表
        """
        return [
            LLMModelInfo(
                name=model_name,
                provider="OpenAI",
                max_tokens=model_info["max_tokens"],
                supports_stream=model_info["supports_stream"],
                supports_functions=model_info["supports_functions"],
                context_length=model_info["context_length"]
            )
            for model_name, model_info in self.SUPPORTED_MODELS.items()
        ]

    def get_model_info(self, model_name: str) -> LLMModelInfo:
        """
        获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            模型信息
        """
        models = {m.name: m for m in self.get_supported_models()}
        if model_name in models:
            return models[model_name]

        # 返回默认模型信息
        return self.get_supported_models()[0]

    def count_tokens(self, text: str, model: str) -> int:
        """
        计算token数量

        Args:
            text: 文本
            model: 模型名称

        Returns:
            token数量
        """
        # 简单估算: 中文字符约1.5 tokens, 英文字符约0.3 tokens
        # 对于更准确的计算,应该使用tiktoken库
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.3)

    def cleanup(self) -> None:
        """清理资源"""
        if self._session:
            self._session.close()
        logger.info(f"Plugin '{self.get_plugin_name()}' cleaned up")
