"""
OpenAI LLM插件
"""

PLUGIN_NAME = "openai"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Aurora PDF Team"
PLUGIN_DESCRIPTION = "OpenAI API LLM插件"


def get_plugin():
    """获取插件实例"""
    from app.plugins_llm.openai_llm.llm_api import OpenAILLMPlugin
    return OpenAILLMPlugin()
