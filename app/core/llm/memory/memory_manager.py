"""
记忆管理器
"""
from typing import Dict, List, Optional
from app.core.llm.memory.memory_interface import MemoryInterface
from app.core.llm.memory.backends.in_memory_backend import InMemoryBackend
from app.core.llm.memory.backends.file_backend import FileBackend
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """记忆管理器"""

    def __init__(self, backend: MemoryInterface = None):
        """
        初始化记忆管理器

        Args:
            backend: 记忆后端实例,如果为None则使用内存后端
        """
        self._backend = backend or InMemoryBackend()

    @classmethod
    def create_in_memory(cls, max_size: int = 1000) -> 'MemoryManager':
        """
        创建内存后端管理器

        Args:
            max_size: 最大记忆数量

        Returns:
            记忆管理器实例
        """
        backend = InMemoryBackend(max_size=max_size)
        return cls(backend)

    @classmethod
    def create_file_backend(cls, storage_path: str = None) -> 'MemoryManager':
        """
        创建文件后端管理器

        Args:
            storage_path: 存储路径

        Returns:
            记忆管理器实例
        """
        backend = FileBackend(storage_path=storage_path)
        return cls(backend)

    def add_memory(
        self,
        key: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        添加记忆

        Args:
            key: 记忆键
            content: 记忆内容
            metadata: 元数据

        Returns:
            是否添加成功
        """
        return self._backend.add_memory(key, content, metadata)

    def get_memory(self, key: str) -> Optional[Dict]:
        """
        获取记忆

        Args:
            key: 记忆键

        Returns:
            记忆内容或None
        """
        return self._backend.get_memory(key)

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        搜索记忆

        Args:
            query: 搜索查询
            limit: 返回数量限制
            filters: 过滤条件

        Returns:
            记忆列表
        """
        return self._backend.search_memories(query, limit, filters)

    def update_memory(
        self,
        key: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        更新记忆

        Args:
            key: 记忆键
            content: 记忆内容
            metadata: 元数据

        Returns:
            是否更新成功
        """
        return self._backend.update_memory(key, content, metadata)

    def delete_memory(self, key: str) -> bool:
        """
        删除记忆

        Args:
            key: 记忆键

        Returns:
            是否删除成功
        """
        return self._backend.delete_memory(key)

    def clear_all_memories(self) -> bool:
        """
        清空所有记忆

        Returns:
            是否清空成功
        """
        return self._backend.clear_all_memories()

    def get_all_keys(self) -> List[str]:
        """
        获取所有记忆键

        Returns:
            记忆键列表
        """
        return self._backend.get_all_keys()

    def get_size(self) -> int:
        """获取当前记忆数量"""
        return self._backend.get_size()

    def get_backend(self) -> MemoryInterface:
        """获取后端实例"""
        return self._backend

    def add_conversation(
        self,
        conversation_key: str,
        messages: List[Dict],
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        添加对话记录

        Args:
            conversation_key: 对话键
            messages: 消息列表
            metadata: 元数据

        Returns:
            是否添加成功
        """
        import json
        content = json.dumps(messages, ensure_ascii=False)
        return self.add_memory(conversation_key, content, metadata)

    def get_conversation(self, conversation_key: str) -> Optional[List[Dict]]:
        """
        获取对话记录

        Args:
            conversation_key: 对话键

        Returns:
            消息列表或None
        """
        import json
        memory = self.get_memory(conversation_key)
        if not memory:
            return None

        try:
            messages = json.loads(memory['content'])
            return messages
        except Exception as e:
            logger.error(f"Error parsing conversation: {e}")
            return None

    def update_conversation(
        self,
        conversation_key: str,
        messages: List[Dict],
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        更新对话记录

        Args:
            conversation_key: 对话键
            messages: 消息列表
            metadata: 元数据

        Returns:
            是否更新成功
        """
        import json
        content = json.dumps(messages, ensure_ascii=False)
        return self.update_memory(conversation_key, content, metadata)

    def append_message(
        self,
        conversation_key: str,
        message: Dict,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        追加消息到对话

        Args:
            conversation_key: 对话键
            message: 消息
            metadata: 元数据

        Returns:
            是否追加成功
        """
        messages = self.get_conversation(conversation_key)
        if messages is None:
            messages = []

        messages.append(message)
        return self.update_conversation(conversation_key, messages, metadata)
