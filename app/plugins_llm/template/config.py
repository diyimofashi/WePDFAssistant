"""
LLM插件配置定义
"""
from typing import Dict, Any, List

# 配置定义
CONFIG_SCHEMA: Dict[str, Any] = {
    "api_key": {
        "type": "string",
        "required": True,
        "description": "API密钥"
    },
    "base_url": {
        "type": "string",
        "required": False,
        "default": "https://api.example.com/v1",
        "description": "API基础URL"
    },
    "default_model": {
        "type": "string",
        "required": False,
        "default": "model-name",
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
        "description": "温度参数"
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

    return errors
