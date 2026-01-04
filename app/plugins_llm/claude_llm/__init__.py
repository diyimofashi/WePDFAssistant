"""
Claude LLM插件
"""

PLUGIN_NAME = "claude"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Aurora PDF Team"
PLUGIN_DESCRIPTION = "Anthropic Claude API LLM插件"


def get_plugin():
    """获取插件实例"""
    from app.plugins_llm.claude_llm.llm_api import ClaudeLLMPlugin
    return ClaudeLLMPlugin()
