"""
LLM插件模板
"""

PLUGIN_NAME = "template"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Aurora PDF Team"
PLUGIN_DESCRIPTION = "LLM插件模板"


def get_plugin():
    """获取插件实例"""
    from app.plugins_llm.template.llm_api import TemplateLLMPlugin
    return TemplateLLMPlugin()
