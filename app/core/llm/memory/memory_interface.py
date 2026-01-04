"""
记忆系统抽象接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class MemoryInterface(ABC):
    """记忆系统抽象接口"""

    @abstractmethod
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
        pass

    @abstractmethod
    def get_memory(self, key: str) -> Optional[Dict]:
        """
        获取记忆

        Args:
            key: 记忆键

        Returns:
            记忆内容或None
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def delete_memory(self, key: str) -> bool:
        """
        删除记忆

        Args:
            key: 记忆键

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    def clear_all_memories(self) -> bool:
        """
        清空所有记忆

        Returns:
            是否清空成功
        """
        pass

    @abstractmethod
    def get_all_keys(self) -> List[str]:
        """
        获取所有记忆键

        Returns:
            记忆键列表
        """
        pass
