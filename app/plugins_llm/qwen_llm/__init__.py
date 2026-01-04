"""
通义千问 LLM插件
"""

PLUGIN_NAME = "qwen"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Aurora PDF Team"
PLUGIN_DESCRIPTION = "阿里云通义千问 API LLM插件"


def get_plugin():
    """获取插件实例"""
    from app.plugins_llm.qwen_llm.llm_api import QwenLLMPlugin
    return QwenLLMPlugin()
