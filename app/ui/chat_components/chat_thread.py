"""
聊天线程组件
处理LLM对话的后台线程
"""
from PyQt5.QtCore import QThread, pyqtSignal
from typing import List, Dict, Optional
from app.core.llm.llm_plugin_interface import LLMMessage


class LLMChatThread(QThread):
    """LLM对话线程"""
    response_signal = pyqtSignal(str, bool, str, bool, dict)
    
    def __init__(self, llm_integration, plugin_name: str, messages: List[LLMMessage], tools: Optional[List[Dict]] = None):
        super().__init__()
        self._llm_integration = llm_integration
        self._plugin_name = plugin_name
        self._messages = messages
        self._tools = tools
    
    def run(self):
        """运行对话"""
        try:
            full_response = ""
            # 传递tools参数给chat_stream
            for chunk in self._llm_integration.chat_stream(self._plugin_name, self._messages, tools=self._tools):
                if chunk.success:
                    full_response += chunk.content
                    # 传递metadata以支持工具调用
                    metadata = chunk.metadata or {}
                    self.response_signal.emit(chunk.content, False, "", False, metadata)
                else:
                    self.response_signal.emit("", True, chunk.error or "Unknown error", False, {})
                    return
            
            # 发送完成信号
            self.response_signal.emit("", False, "", True, {})
        
        except Exception as e:
            from app.utils.logger import get_logger
            logger = get_logger(__name__)
            logger.error(f"Error in chat thread: {e}", exc_info=True)
            self.response_signal.emit("", True, str(e), False, {})