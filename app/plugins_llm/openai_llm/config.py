"""
OpenAI LLM插件配置定义
"""
from typing import Dict, Any, List

# 配置定义
CONFIG_SCHEMA: Dict[str, Any] = {
    "api_key": {
        "type": "string",
        "required": True,
        "description": "OpenAI API密钥"
    },
    "base_url": {
        "type": "string",
        "required": False,
        "default": "https://api.openai.com/v1",
        "description": "API基础URL"
    },
    "default_model": {
        "type": "string",
        "required": False,
        "default": "gpt-3.5-turbo",
        "description": "默认模型"
    },
    "max_tokens": {
        "type": "integer",
        "required": False,
        "default": 4096,
        "description": "最大token数"
    },
    "temperature": {
        "type": "float",
        "required": False,
        "default": 0.7,
        "description": "温度参数(0-2)"
    }
}


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    验证配置

    Args:
        config: 配置字典

    Returns:
        错误消息列表,如果为空则配置有效
    """
    errors = []

    for field, schema in CONFIG_SCHEMA.items():
        if schema.get("required", False) and field not in config:
            errors.append(f"Missing required field: {field}")

    # 验证温度参数
    if "temperature" in config:
        temp = config["temperature"]
        if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
            errors.append("Temperature must be between 0 and 2")

    return errors
