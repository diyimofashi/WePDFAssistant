"""
文件存储后端
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from app.core.llm.memory.memory_interface import MemoryInterface
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileBackend(MemoryInterface):
    """文件存储后端"""

    def __init__(self, storage_path: str = None):
        """
        初始化文件后端

        Args:
            storage_path: 存储路径
        """
        if storage_path is None:
            # 使用项目目录下的默认存储路径
            project_root = Path(__file__).parent.parent.parent.parent
            storage_path = str(project_root / "data" / "llm_memory")

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._index_file = self.storage_path / "index.json"
        self._memories: Dict[str, Dict] = {}
        self._load_index()

        logger.info(f"FileBackend initialized with path={storage_path}")

    def _load_index(self) -> None:
        """加载索引文件"""
        if not self._index_file.exists():
            logger.info(f"Index file not found, creating new: {self._index_file}")
            self._save_index()
            return

        try:
            with open(self._index_file, 'r', encoding='utf-8') as f:
                self._memories = json.load(f)
            logger.info(f"Index loaded from: {self._index_file}")
        except Exception as e:
            logger.error(f"Error loading index: {e}", exc_info=True)
            self._memories = {}

    def _save_index(self) -> None:
        """保存索引文件"""
        try:
            with open(self._index_file, 'w', encoding='utf-8') as f:
                json.dump(self._memories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving index: {e}", exc_info=True)

    def _get_memory_file_path(self, key: str) -> Path:
        """
        获取记忆文件路径

        Args:
            key: 记忆键

        Returns:
            文件路径
        """
        # 使用key的hash作为文件名
        import hashlib
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.storage_path / f"{hash_key}.json"

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
        memory = {
            'key': key,
            'content': content,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # 保存到文件
        memory_file = self._get_memory_file_path(key)
        try:
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving memory file: {e}")
            return False

        # 更新索引
        self._memories[key] = {
            'key': key,
            'file_path': str(memory_file),
            'timestamp': memory['timestamp']
        }
        self._save_index()

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
        memory_file = self._get_memory_file_path(key)

        if not memory_file.exists():
            return None

        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory file: {e}")
            return None

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

        for key in self._memories.keys():
            memory = self.get_memory(key)
            if not memory:
                continue

            # 应用过滤器
            if filters:
                match = True
                for filter_key, filter_value in filters.items():
                    if filter_key in memory.get('metadata', {}):
                        if memory['metadata'][filter_key] != filter_value:
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

        memory = self.get_memory(key)
        if not memory:
            return False

        memory['content'] = content
        memory['updated_at'] = datetime.now().isoformat()

        if metadata is not None:
            memory['metadata'].update(metadata)

        # 保存到文件
        memory_file = self._get_memory_file_path(key)
        try:
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving memory file: {e}")
            return False

        # 更新索引
        self._memories[key]['timestamp'] = memory['timestamp']
        self._save_index()

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

        memory_file = self._get_memory_file_path(key)

        try:
            if memory_file.exists():
                memory_file.unlink()
        except Exception as e:
            logger.error(f"Error deleting memory file: {e}")

        del self._memories[key]
        self._save_index()

        logger.debug(f"Memory deleted: {key}")
        return True

    def clear_all_memories(self) -> bool:
        """
        清空所有记忆

        Returns:
            是否清空成功
        """
        # 删除所有记忆文件
        for key in list(self._memories.keys()):
            memory_file = self._get_memory_file_path(key)
            try:
                if memory_file.exists():
                    memory_file.unlink()
            except Exception as e:
                logger.error(f"Error deleting memory file: {e}")

        self._memories.clear()
        self._save_index()

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
