"""
内存存储后端
"""
from typing import Dict, List, Optional
from datetime import datetime
from app.core.llm.memory.memory_interface import MemoryInterface
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InMemoryBackend(MemoryInterface):
    """内存存储后端"""

    def __init__(self, max_size: int = 1000):
        """
        初始化内存后端

        Args:
            max_size: 最大记忆数量
        """
        self._memories: Dict[str, Dict] = {}
        self._max_size = max_size
        logger.info(f"InMemoryBackend initialized with max_size={max_size}")

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
        # 检查是否超过最大限制
        if len(self._memories) >= self._max_size:
            # 删除最旧的记忆
            oldest_key = min(self._memories.keys(),
                           key=lambda k: self._memories[k].get('timestamp', 0))
            del self._memories[oldest_key]
            logger.debug(f"Removed oldest memory: {oldest_key}")

        memory = {
            'key': key,
            'content': content,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        self._memories[key] = memory
        logger.debug(f"Memory added: {key}")
        return True

    def get_memory(self, key: str) -> Optional[Dict]:
        """
        获取记忆

        Args:
            key: 记忆键

        Returns:
            记忆内容或None
        """
        return self._memories.get(key)

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
        results = []

        for memory in self._memories.values():
            # 应用过滤器
            if filters:
                match = True
                for key, value in filters.items():
                    if key in memory.get('metadata', {}):
                        if memory['metadata'][key] != value:
                            match = False
                            break
                if not match:
                    continue

            # 简单文本搜索
            content = memory.get('content', '').lower()
            if query.lower() in content:
                results.append(memory)

        # 按时间戳排序(最新的在前)
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return results[:limit]

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
        if key not in self._memories:
            logger.warning(f"Memory not found for update: {key}")
            return False

        self._memories[key]['content'] = content
        self._memories[key]['updated_at'] = datetime.now().isoformat()

        if metadata is not None:
            self._memories[key]['metadata'].update(metadata)

        logger.debug(f"Memory updated: {key}")
        return True

    def delete_memory(self, key: str) -> bool:
        """
        删除记忆

        Args:
            key: 记忆键

        Returns:
            是否删除成功
        """
        if key not in self._memories:
            logger.warning(f"Memory not found for deletion: {key}")
            return False

        del self._memories[key]
        logger.debug(f"Memory deleted: {key}")
        return True

    def clear_all_memories(self) -> bool:
        """
        清空所有记忆

        Returns:
            是否清空成功
        """
        self._memories.clear()
        logger.info("All memories cleared")
        return True

    def get_all_keys(self) -> List[str]:
        """
        获取所有记忆键

        Returns:
            记忆键列表
        """
        return list(self._memories.keys())

    def get_size(self) -> int:
        """获取当前记忆数量"""
        return len(self._memories)
